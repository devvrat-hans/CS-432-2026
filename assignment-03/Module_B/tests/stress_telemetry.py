import json
import os
import resource
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _collect_telemetry_stats() -> dict:
    usage = resource.getrusage(resource.RUSAGE_SELF)

    try:
        load_1m, load_5m, load_15m = os.getloadavg()
    except OSError:
        load_1m, load_5m, load_15m = (None, None, None)

    return {
        "pid": os.getpid(),
        "thread_count": threading.active_count(),
        "process_user_cpu_seconds": usage.ru_utime,
        "process_system_cpu_seconds": usage.ru_stime,
        "process_maxrss": usage.ru_maxrss,
        "involuntary_context_switches": usage.ru_nivcsw,
        "voluntary_context_switches": usage.ru_nvcsw,
        "system_loadavg_1m": load_1m,
        "system_loadavg_5m": load_5m,
        "system_loadavg_15m": load_15m,
    }


class PhaseTelemetrySampler:
    def __init__(
        self,
        *,
        telemetry_path: Path,
        phase_name: str,
        sample_interval_seconds: float = 0.5,
        context: dict | None = None,
    ):
        self.telemetry_path = telemetry_path
        self.phase_name = phase_name
        self.sample_interval_seconds = sample_interval_seconds
        self.context = context or {}

        self.run_id = str(uuid.uuid4())
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._sample_count = 0

    def __enter__(self):
        self.telemetry_path.parent.mkdir(parents=True, exist_ok=True)
        self._append_event("phase_start", _collect_telemetry_stats(), include_context=True)

        self._worker = threading.Thread(target=self._sample_loop, daemon=True)
        self._worker.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stop_event.set()
        if self._worker is not None:
            self._worker.join(timeout=max(self.sample_interval_seconds * 2, 1.0))

        self._append_event(
            "phase_end",
            _collect_telemetry_stats(),
            extra={"sample_count": self._sample_count},
        )

    def _sample_loop(self) -> None:
        while not self._stop_event.wait(self.sample_interval_seconds):
            self._sample_count += 1
            self._append_event("sample", _collect_telemetry_stats())

    def _append_event(
        self,
        event: str,
        stats: dict,
        *,
        include_context: bool = False,
        extra: dict | None = None,
    ) -> None:
        payload = {
            "run_id": self.run_id,
            "phase_name": self.phase_name,
            "event": event,
            "timestamp_utc": _utc_now_iso(),
            "monotonic_seconds": time.perf_counter(),
            "stats": stats,
        }
        if include_context and self.context:
            payload["context"] = self.context
        if extra:
            payload["extra"] = extra

        with self.telemetry_path.open("a", encoding="utf-8") as telemetry_file:
            telemetry_file.write(json.dumps(payload, sort_keys=True) + "\n")
