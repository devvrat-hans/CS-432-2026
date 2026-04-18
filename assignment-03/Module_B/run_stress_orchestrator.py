"""Run ordered Module B stress phases with reliability safeguards."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import signal
from pathlib import Path
import sys
import unittest

MODULE_B_DIR = Path(__file__).resolve().parent
TESTS_DIR = MODULE_B_DIR / "tests"
REPO_ROOT = MODULE_B_DIR.parent.parent
RESULTS_PATH = MODULE_B_DIR / "test_results" / "stress_orchestrator_results.txt"
METRICS_PATH = MODULE_B_DIR / "test_results" / "stress_phase_metrics.jsonl"
PHASE_EVALUATION_PATH = MODULE_B_DIR / "test_results" / "stress_phase_evaluation.json"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(MODULE_B_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_B_DIR))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from stress_phase_evaluator import (
    default_policy,
    evaluate_phase,
    load_metric_records,
    write_machine_readable_summary,
)

PHASE_ORDER = [
    "baseline",
    "ramp",
    "spike",
    "soak",
    "breakpoint",
    "failure-under-load",
    "final-durability",
]

PHASE_TESTS = {
    "baseline": [
        "test_module_b_concurrent_usage.TestModuleBConcurrentUsage.test_parallel_unique_inserts_preserve_count",
    ],
    "ramp": [
        "test_module_b_stress.TestModuleBStress.test_high_volume_parallel_insert_stress",
    ],
    "spike": [
        "test_module_b_stress.TestModuleBStress.test_many_unique_token_consumptions_under_load",
    ],
    "soak": [
        "test_module_b_stress.TestModuleBStress.test_sustained_read_stress_consistency",
    ],
    "breakpoint": [
        "test_module_b_stress.TestModuleBStress.test_thousands_scale_insert_metrics",
        "test_module_b_stress.TestModuleBStress.test_hotspot_contention_detects_no_lost_updates_or_duplicate_commits",
    ],
    "failure-under-load": [
        "test_module_b_stress.TestModuleBStress.test_failure_injection_under_parallel_load_rolls_back_and_retry_succeeds",
    ],
    "final-durability": [
        "test_module_b_durability.TestModuleBDurability.test_committed_data_persists_after_restart_simulation",
        "test_module_b_durability.TestModuleBDurability.test_failed_transactions_absent_after_restart_simulation",
    ],
}

PHASE_METRIC_NAMES = {
    "baseline": [],
    "ramp": ["high_volume_parallel_insert_stress"],
    "spike": ["many_unique_token_consumptions_under_load"],
    "soak": ["sustained_read_stress_consistency"],
    "breakpoint": [
        "thousands_scale_insert_metrics",
        "hotspot_parallel_updates",
        "hotspot_duplicate_creates",
    ],
    "failure-under-load": [
        "failure_injection_parallel_path",
        "success_parallel_path",
        "retry_after_failure_path",
        "retry_idempotency_path",
    ],
    "final-durability": [],
}


@dataclass(frozen=True)
class PhaseResult:
    phase: str
    attempt: int
    passed: bool
    tests_run: int
    failures: int
    errors: int
    skipped: int
    timed_out: bool = False
    cancelled: bool = False
    error_message: str = ""


@contextmanager
def _phase_timeout(timeout_seconds: float):
    if timeout_seconds <= 0:
        yield
        return

    if not hasattr(signal, "SIGALRM"):
        # On platforms without SIGALRM support, proceed without hard timeout.
        yield
        return

    def _timeout_handler(_signum, _frame):
        raise TimeoutError(f"phase exceeded timeout of {timeout_seconds:.2f} seconds")

    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def _normalize_requested_phases(raw_phases: str) -> list[str]:
    if not raw_phases.strip():
        return PHASE_ORDER.copy()

    requested = [part.strip().lower() for part in raw_phases.split(",") if part.strip()]
    unknown = [phase for phase in requested if phase not in PHASE_TESTS]
    if unknown:
        available = ", ".join(PHASE_ORDER)
        unknown_text = ", ".join(unknown)
        raise ValueError(f"Unknown phases: {unknown_text}. Available phases: {available}")

    ordered_selection = [phase for phase in PHASE_ORDER if phase in requested]
    return ordered_selection


def _build_suite_for_phase(phase: str) -> unittest.TestSuite:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for test_name in PHASE_TESTS[phase]:
        suite.addTests(loader.loadTestsFromName(test_name))

    return suite


def _run_phase(
    phase: str,
    *,
    verbosity: int,
    attempt: int,
    timeout_seconds: float,
) -> PhaseResult:
    suite = _build_suite_for_phase(phase)
    runner = unittest.TextTestRunner(verbosity=verbosity)

    try:
        with _phase_timeout(timeout_seconds):
            result = runner.run(suite)
        return PhaseResult(
            phase=phase,
            attempt=attempt,
            passed=result.wasSuccessful(),
            tests_run=result.testsRun,
            failures=len(result.failures),
            errors=len(result.errors),
            skipped=len(result.skipped),
        )
    except KeyboardInterrupt:
        return PhaseResult(
            phase=phase,
            attempt=attempt,
            passed=False,
            tests_run=0,
            failures=0,
            errors=0,
            skipped=0,
            cancelled=True,
            error_message="cancelled by user",
        )
    except TimeoutError as exc:
        return PhaseResult(
            phase=phase,
            attempt=attempt,
            passed=False,
            tests_run=0,
            failures=0,
            errors=1,
            skipped=0,
            timed_out=True,
            error_message=str(exc),
        )
    except Exception as exc:
        return PhaseResult(
            phase=phase,
            attempt=attempt,
            passed=False,
            tests_run=0,
            failures=0,
            errors=1,
            skipped=0,
            error_message=f"{type(exc).__name__}: {exc}",
        )


def _write_summary(
    *,
    phase_results: list[PhaseResult],
    attempt_results: list[PhaseResult],
    fast_fail: bool,
    selected_phases: list[str],
    phase_retry_limit: int,
    phase_timeout_seconds: float,
    run_cancelled: bool,
) -> None:
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    passed_phases = sum(1 for phase in phase_results if phase.passed)
    failed_phases = len(phase_results) - passed_phases
    overall_pass = failed_phases == 0 and len(phase_results) == len(selected_phases)

    lines = [
        "=" * 72,
        f"Run started (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"Selected phases: {', '.join(selected_phases)}",
        f"Fast fail: {fast_fail}",
        f"Phase retry limit: {phase_retry_limit}",
        f"Phase timeout seconds: {phase_timeout_seconds}",
        f"Run cancelled: {run_cancelled}",
        "-" * 72,
        "Phase attempts:",
    ]

    for result in attempt_results:
        status = "PASS" if result.passed else "FAIL"
        suffix = ""
        if result.timed_out:
            suffix = " [TIMEOUT]"
        if result.cancelled:
            suffix = " [CANCELLED]"
        if result.error_message:
            suffix += f" [ERROR: {result.error_message}]"
        lines.append(
            (
                f"{result.phase} (attempt {result.attempt}): {status}{suffix} | "
                f"tests={result.tests_run} failures={result.failures} "
                f"errors={result.errors} skipped={result.skipped}"
            )
        )

    lines.append("-" * 72)
    lines.append("Final phase outcomes:")
    for result in phase_results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(
            (
                f"{result.phase}: {status} (attempt {result.attempt}) | tests={result.tests_run} "
                f"failures={result.failures} errors={result.errors} skipped={result.skipped}"
            )
        )

    lines.extend(
        [
            "-" * 72,
            f"Phases passed: {passed_phases}",
            f"Phases failed: {failed_phases}",
            f"Overall status: {'PASS' if overall_pass else 'FAIL'}",
            "=" * 72,
            "",
        ]
    )

    with RESULTS_PATH.open("a", encoding="utf-8") as report_file:
        report_file.write("\n".join(lines))


def _evaluate_phases(phase_results: list[PhaseResult]) -> list[dict]:
    metric_records = load_metric_records(METRICS_PATH)
    policy = default_policy()

    summaries = []
    for phase_result in phase_results:
        expected_metric_names = set(PHASE_METRIC_NAMES.get(phase_result.phase, []))
        phase_metric_records = [
            record
            for record in metric_records
            if record.get("phase_name") in expected_metric_names
        ]

        summary = evaluate_phase(
            phase_name=phase_result.phase,
            phase_test_passed=phase_result.passed,
            metric_records=phase_metric_records,
            policy=policy,
        )
        summary["tests_run"] = phase_result.tests_run
        summary["failures"] = phase_result.failures
        summary["errors"] = phase_result.errors
        summary["skipped"] = phase_result.skipped
        summaries.append(summary)

    write_machine_readable_summary(
        output_path=PHASE_EVALUATION_PATH,
        phase_summaries=summaries,
    )
    return summaries


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ordered Module B stress phases")
    parser.add_argument(
        "--phases",
        default="",
        help=(
            "Comma-separated phases to run. "
            "Defaults to full order: baseline,ramp,spike,soak,breakpoint,failure-under-load,final-durability"
        ),
    )
    parser.add_argument(
        "--fast-fail",
        action="store_true",
        help="Stop at first phase failure.",
    )
    parser.add_argument(
        "--verbosity",
        type=int,
        default=2,
        choices=[1, 2],
        help="unittest verbosity level.",
    )
    parser.add_argument(
        "--phase-timeout-seconds",
        type=float,
        default=0.0,
        help="Hard timeout per phase in seconds (0 disables timeout).",
    )
    parser.add_argument(
        "--phase-retry-limit",
        type=int,
        default=0,
        help="Number of retries per phase after a failing attempt.",
    )
    parser.add_argument(
        "--list-phases",
        action="store_true",
        help="Print available phases and exit.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if args.list_phases:
        print("Available phases (execution order):")
        for phase in PHASE_ORDER:
            print(f"- {phase}")
        return 0

    try:
        selected_phases = _normalize_requested_phases(args.phases)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2

    if args.phase_retry_limit < 0:
        print("Error: --phase-retry-limit must be >= 0")
        return 2
    if args.phase_timeout_seconds < 0:
        print("Error: --phase-timeout-seconds must be >= 0")
        return 2

    phase_results: list[PhaseResult] = []
    attempt_results: list[PhaseResult] = []
    run_cancelled = False

    print("=" * 72)
    print("Module B Stress Orchestrator")
    print(f"Selected phases: {', '.join(selected_phases)}")
    print(f"Fast fail: {args.fast_fail}")
    print(f"Phase retry limit: {args.phase_retry_limit}")
    print(f"Phase timeout seconds: {args.phase_timeout_seconds}")
    print("=" * 72)

    for phase in selected_phases:
        print(f"\n[PHASE START] {phase}")
        final_phase_result: PhaseResult | None = None

        for attempt in range(1, args.phase_retry_limit + 2):
            phase_result = _run_phase(
                phase,
                verbosity=args.verbosity,
                attempt=attempt,
                timeout_seconds=args.phase_timeout_seconds,
            )
            attempt_results.append(phase_result)

            status = "PASS" if phase_result.passed else "FAIL"
            suffix = ""
            if phase_result.timed_out:
                suffix += " [TIMEOUT]"
            if phase_result.cancelled:
                suffix += " [CANCELLED]"
            if phase_result.error_message:
                suffix += f" [ERROR: {phase_result.error_message}]"

            print(
                (
                    f"[PHASE ATTEMPT END] {phase} attempt={attempt} -> {status}{suffix} "
                    f"(tests={phase_result.tests_run}, failures={phase_result.failures}, "
                    f"errors={phase_result.errors}, skipped={phase_result.skipped})"
                )
            )

            final_phase_result = phase_result

            if phase_result.cancelled:
                run_cancelled = True
                break

            if phase_result.passed:
                break

            if attempt <= args.phase_retry_limit:
                print(f"Retrying phase '{phase}' (attempt {attempt + 1}/{args.phase_retry_limit + 1})...")

        if final_phase_result is None:
            final_phase_result = PhaseResult(
                phase=phase,
                attempt=1,
                passed=False,
                tests_run=0,
                failures=0,
                errors=1,
                skipped=0,
                error_message="phase did not execute",
            )

        phase_results.append(final_phase_result)

        if run_cancelled:
            print("Run cancelled; stopping orchestrator gracefully.")
            break

        if args.fast_fail and not final_phase_result.passed:
            print("Fast-fail enabled: stopping after first failing phase.")
            break

    _write_summary(
        phase_results=phase_results,
        attempt_results=attempt_results,
        fast_fail=args.fast_fail,
        selected_phases=selected_phases,
        phase_retry_limit=args.phase_retry_limit,
        phase_timeout_seconds=args.phase_timeout_seconds,
        run_cancelled=run_cancelled,
    )

    phase_evaluations = _evaluate_phases(phase_results)

    evaluation_statuses = [summary.get("status") for summary in phase_evaluations]
    has_failures = run_cancelled or any(status == "fail" for status in evaluation_statuses)
    has_conditionals = any(status == "conditional_pass" for status in evaluation_statuses)

    all_passed = (
        len(phase_results) == len(selected_phases)
        and not has_failures
        and not has_conditionals
    )

    overall_status = "PASS"
    if has_failures:
        overall_status = "FAIL"
    elif has_conditionals:
        overall_status = "CONDITIONAL_PASS"

    print("\n" + "=" * 72)
    print(f"Overall status: {overall_status}")
    print(f"Summary report: {RESULTS_PATH}")
    print(f"Machine-readable phase summary: {PHASE_EVALUATION_PATH}")
    print("=" * 72)

    if run_cancelled:
        return 130
    return 0 if not has_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
