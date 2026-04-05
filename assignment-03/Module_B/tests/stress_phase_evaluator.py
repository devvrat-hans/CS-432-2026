import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    from stress_config import DEFAULT_STRESS_THRESHOLDS
except ModuleNotFoundError:
    from assignment03.Module_B.tests.stress_config import DEFAULT_STRESS_THRESHOLDS


@dataclass(frozen=True)
class EvaluationPolicy:
    minimum_success_rate: float
    maximum_p95_latency_ms: float
    maximum_invariant_violations: int
    conditional_success_rate_floor: float
    conditional_p95_latency_ms: float


def default_policy() -> EvaluationPolicy:
    return EvaluationPolicy(
        minimum_success_rate=DEFAULT_STRESS_THRESHOLDS.minimum_success_rate,
        maximum_p95_latency_ms=DEFAULT_STRESS_THRESHOLDS.maximum_p95_latency_ms,
        maximum_invariant_violations=DEFAULT_STRESS_THRESHOLDS.maximum_invariant_violations,
        conditional_success_rate_floor=max(0.0, DEFAULT_STRESS_THRESHOLDS.minimum_success_rate - 0.02),
        conditional_p95_latency_ms=DEFAULT_STRESS_THRESHOLDS.maximum_p95_latency_ms * 1.25,
    )


def load_metric_records(metrics_path: Path) -> list[dict]:
    if not metrics_path.exists():
        return []

    records: list[dict] = []
    with metrics_path.open("r", encoding="utf-8") as metrics_file:
        for line in metrics_file:
            cleaned = line.strip()
            if not cleaned:
                continue
            try:
                records.append(json.loads(cleaned))
            except json.JSONDecodeError:
                continue

    return records


def _record_status(record: dict, policy: EvaluationPolicy) -> tuple[str, list[str], dict]:
    total_requests = int(record.get("total_requests", 0))
    success_count = int(record.get("success_count", 0))
    p95_latency_ms = float(record.get("p95_latency_ms", 0.0))

    success_rate = (success_count / total_requests) if total_requests else 0.0
    context = record.get("context") or {}
    invariant_violations = int(context.get("invariant_violations", 0))

    reasons: list[str] = []

    if invariant_violations > policy.maximum_invariant_violations:
        reasons.append(
            (
                f"invariant_violations={invariant_violations} exceed "
                f"max={policy.maximum_invariant_violations}"
            )
        )

    if success_rate < policy.minimum_success_rate:
        reasons.append(
            f"success_rate={success_rate:.4f} below min={policy.minimum_success_rate:.4f}"
        )

    if p95_latency_ms > policy.maximum_p95_latency_ms:
        reasons.append(
            f"p95_latency_ms={p95_latency_ms:.3f} above max={policy.maximum_p95_latency_ms:.3f}"
        )

    if not reasons:
        status = "pass"
    else:
        conditional_allowed = (
            invariant_violations <= policy.maximum_invariant_violations
            and success_rate >= policy.conditional_success_rate_floor
            and p95_latency_ms <= policy.conditional_p95_latency_ms
        )
        status = "conditional_pass" if conditional_allowed else "fail"

    observed = {
        "total_requests": total_requests,
        "success_count": success_count,
        "success_rate": success_rate,
        "p95_latency_ms": p95_latency_ms,
        "invariant_violations": invariant_violations,
    }

    return status, reasons, observed


def evaluate_phase(
    *,
    phase_name: str,
    phase_test_passed: bool,
    metric_records: list[dict],
    policy: EvaluationPolicy,
) -> dict:
    evaluations = []
    statuses = []

    for record in metric_records:
        status, reasons, observed = _record_status(record, policy)
        statuses.append(status)
        evaluations.append(
            {
                "metric_phase_name": record.get("phase_name"),
                "recorded_at_utc": record.get("recorded_at_utc"),
                "status": status,
                "reasons": reasons,
                "observed": observed,
            }
        )

    if not phase_test_passed:
        overall_status = "fail"
        overall_reasons = ["phase test execution failed"]
    elif not statuses:
        overall_status = "pass"
        overall_reasons = ["no_metrics_available_for_phase; evaluated from test outcome"]
    elif "fail" in statuses:
        overall_status = "fail"
        overall_reasons = ["one_or_more_metric_records_failed_thresholds"]
    elif "conditional_pass" in statuses:
        overall_status = "conditional_pass"
        overall_reasons = ["one_or_more_metric_records_met_conditional_thresholds_only"]
    else:
        overall_status = "pass"
        overall_reasons = ["all_metric_records_met_primary_thresholds"]

    return {
        "phase": phase_name,
        "test_passed": phase_test_passed,
        "status": overall_status,
        "reasons": overall_reasons,
        "policy": asdict(policy),
        "metric_evaluations": evaluations,
    }


def write_machine_readable_summary(
    *,
    output_path: Path,
    phase_summaries: list[dict],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase_count": len(phase_summaries),
        "phase_summaries": phase_summaries,
    }

    with output_path.open("w", encoding="utf-8") as summary_file:
        json.dump(payload, summary_file, indent=2, sort_keys=True)
