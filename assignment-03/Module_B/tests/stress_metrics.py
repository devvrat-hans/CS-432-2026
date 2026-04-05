import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class PhaseMetrics:
    phase_name: str
    total_requests: int
    success_count: int
    error_count: int
    error_rate: float
    throughput_rps: float
    average_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    phase_duration_seconds: float
    recorded_at_utc: str


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0

    sorted_values = sorted(values)
    index = max(0, int(round((len(sorted_values) - 1) * percentile)))
    return float(sorted_values[index])


def build_phase_metrics(
    *,
    phase_name: str,
    statuses: list[int],
    latencies_ms: list[float],
    phase_duration_seconds: float,
    success_statuses: set[int],
) -> PhaseMetrics:
    total_requests = len(statuses)
    success_count = sum(1 for status in statuses if status in success_statuses)
    error_count = total_requests - success_count
    error_rate = (error_count / total_requests) if total_requests else 0.0

    safe_duration = phase_duration_seconds if phase_duration_seconds > 0 else 1e-9
    throughput_rps = total_requests / safe_duration

    average_latency_ms = (sum(latencies_ms) / len(latencies_ms)) if latencies_ms else 0.0
    p95_latency_ms = _percentile(latencies_ms, 0.95)
    p99_latency_ms = _percentile(latencies_ms, 0.99)

    return PhaseMetrics(
        phase_name=phase_name,
        total_requests=total_requests,
        success_count=success_count,
        error_count=error_count,
        error_rate=error_rate,
        throughput_rps=throughput_rps,
        average_latency_ms=average_latency_ms,
        p95_latency_ms=p95_latency_ms,
        p99_latency_ms=p99_latency_ms,
        phase_duration_seconds=phase_duration_seconds,
        recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def append_phase_metrics(
    *,
    metrics_path: Path,
    metrics: PhaseMetrics,
    context: dict | None = None,
) -> None:
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(metrics)
    if context:
        payload["context"] = context

    with metrics_path.open("a", encoding="utf-8") as metrics_file:
        metrics_file.write(json.dumps(payload, sort_keys=True) + "\n")
