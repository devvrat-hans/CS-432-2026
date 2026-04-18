"""Run Assignment 04 backend tests with optional stress orchestrator integration."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

try:
    from run_stress_orchestrator import main as run_stress_orchestrator_main
except ModuleNotFoundError:
    run_stress_orchestrator_main = None

ASSIGNMENT_DIR = Path(__file__).resolve().parent
TESTS_DIR = ASSIGNMENT_DIR / "tests"
BACKEND_DIR = ASSIGNMENT_DIR / "db_management_system"
RESULTS_DIR = ASSIGNMENT_DIR / "test_results"
SHARDING_RESULTS_PATH = RESULTS_DIR / "test_results_sharding.txt"
REPO_ROOT = ASSIGNMENT_DIR.parent.parent

# Support running this script from either repo root or assignment-04 directory.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(ASSIGNMENT_DIR) not in sys.path:
    sys.path.insert(0, str(ASSIGNMENT_DIR))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

UPLOADS_DIR = BACKEND_DIR / "uploads"

TEST_MODULES = [
    "test_assignment04_sharding",
]

TRANSFER_TEST_MODULES = [
    "test_blinddrop_transfer",
    "test_blinddrop_expiry",
]

SHARDING_MODULE_NAME = "test_assignment04_sharding"


class RecordingTextTestResult(unittest.TextTestResult):
    """TextTestResult that tracks status by test id for reporting files."""

    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.test_statuses: list[tuple[str, str, str]] = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.test_statuses.append((test.id(), "PASS", ""))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.test_statuses.append((test.id(), "FAIL", self._exc_info_to_string(err, test)))

    def addError(self, test, err):
        super().addError(test, err)
        self.test_statuses.append((test.id(), "ERROR", self._exc_info_to_string(err, test)))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.test_statuses.append((test.id(), "SKIP", reason))


class RecordingTextTestRunner(unittest.TextTestRunner):
    """TextTestRunner that uses RecordingTextTestResult."""

    resultclass = RecordingTextTestResult


def _clean_uploads_dir():
    """Remove all files from the uploads directory except .gitkeep."""
    if UPLOADS_DIR.exists():
        for f in UPLOADS_DIR.iterdir():
            if f.name != ".gitkeep" and f.is_file():
                f.unlink()


def build_suite(
    *,
    include_sharding: bool = True,
    include_transfer: bool = True,
) -> unittest.TestSuite:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    selected_modules = TEST_MODULES
    if not include_sharding:
        selected_modules = [name for name in selected_modules if name != "test_assignment04_sharding"]

    for module_name in selected_modules:
        suite.addTests(loader.loadTestsFromName(module_name))

    if include_transfer:
        for module_name in TRANSFER_TEST_MODULES:
            suite.addTests(loader.loadTestsFromName(module_name))

    return suite


def _run_shard_migration() -> bool:
    """Run shard migration before sharding tests. Returns True on success."""
    try:
        from migrate_to_shards import migrate, verify
        print("\n[SETUP] Running shard migration...")
        migrate()
        ok = verify()
        if ok:
            print("[SETUP] Shard migration and verification successful.")
        else:
            print("[SETUP] WARNING: Shard migration verification reported issues.")
        return ok
    except Exception as exc:
        print(f"[SETUP] Shard migration failed: {exc}")
        return False


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Assignment 04 backend tests")
    parser.add_argument(
        "--verbosity",
        type=int,
        default=2,
        choices=[1, 2],
        help="unittest verbosity level for the main suite.",
    )
    parser.add_argument(
        "--skip-sharding",
        action="store_true",
        help="Skip sharding tests and skip running the shard migration step.",
    )
    parser.add_argument(
        "--skip-transfer",
        action="store_true",
        help="Skip file transfer tests (test_blinddrop_transfer, test_blinddrop_expiry).",
    )
    parser.add_argument(
        "--run-stress-orchestrator",
        action="store_true",
        help="Also run run_stress_orchestrator.py after the main unittest suite.",
    )
    parser.add_argument(
        "--stress-phases",
        default="",
        help="Comma-separated stress phases to pass to stress orchestrator.",
    )
    parser.add_argument(
        "--stress-fast-fail",
        action="store_true",
        help="Enable fast-fail mode for stress orchestrator.",
    )
    parser.add_argument(
        "--stress-verbosity",
        type=int,
        default=1,
        choices=[1, 2],
        help="Verbosity for stress orchestrator.",
    )
    return parser.parse_args(argv)


def _print_summary(*, title: str, total: int, passed: int, failures: int, errors: int, skipped: int, status: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print(f"Total:   {total}")
    print(f"Passed:  {passed}")
    print(f"Failed:  {failures}")
    print(f"Errors:  {errors}")
    print(f"Skipped: {skipped}")
    print(f"Status:  {status}")
    print("=" * 72)


def _write_sharding_results_file(result: RecordingTextTestResult, *, include_sharding: bool) -> None:
    """Persist sharding test outcomes to assignment-04/test_results/test_results_sharding.txt."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc).isoformat()

    sharding_entries = [
        (test_id, status, details)
        for test_id, status, details in result.test_statuses
        if SHARDING_MODULE_NAME in test_id
    ]

    counts = {
        "PASS": sum(1 for _, status, _ in sharding_entries if status == "PASS"),
        "FAIL": sum(1 for _, status, _ in sharding_entries if status == "FAIL"),
        "ERROR": sum(1 for _, status, _ in sharding_entries if status == "ERROR"),
        "SKIP": sum(1 for _, status, _ in sharding_entries if status == "SKIP"),
    }

    lines = [
        "TestAssignment04Sharding Results",
        f"Run started (UTC): {started_at}",
        "=" * 72,
        "",
    ]

    if not include_sharding:
        lines.extend([
            "Sharding tests were skipped (--skip-sharding).",
            "",
        ])
    elif not sharding_entries:
        lines.extend([
            "No sharding test results were captured in this run.",
            "",
        ])
    else:
        for test_id, status, details in sharding_entries:
            lines.append(f"[{status}] {test_id}")
            if details and status in {"FAIL", "ERROR"}:
                lines.append("Traceback:")
                lines.append(details.rstrip())
                lines.append("-" * 72)
            elif details and status == "SKIP":
                lines.append(f"Reason: {details}")
            lines.append("")

    total = len(sharding_entries)
    lines.extend([
        "=" * 72,
        "Run summary",
        f"Total: {total}",
        f"PASS: {counts['PASS']}",
        f"FAIL: {counts['FAIL']}",
        f"ERROR: {counts['ERROR']}",
        f"SKIP: {counts['SKIP']}",
    ])

    SHARDING_RESULTS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_integrated_stress_orchestrator(args: argparse.Namespace) -> int:
    if run_stress_orchestrator_main is None:
        print("\n[INTEGRATION] run_stress_orchestrator.py not found; skipping stress orchestrator integration")
        return 1

    orchestrator_args = ["--verbosity", str(args.stress_verbosity)]
    if args.stress_phases.strip():
        orchestrator_args.extend(["--phases", args.stress_phases.strip()])
    if args.stress_fast_fail:
        orchestrator_args.append("--fast-fail")

    print("\n[INTEGRATION] Running stress orchestrator from main test runner")
    return run_stress_orchestrator_main(orchestrator_args)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    include_sharding = not args.skip_sharding
    include_transfer = not args.skip_transfer

    # Run shard migration before sharding tests (setup).
    if include_sharding:
        _run_shard_migration()

    # Clean uploads directory before/after transfer tests.
    if include_transfer:
        _clean_uploads_dir()

    suite = build_suite(
        include_sharding=include_sharding,
        include_transfer=include_transfer,
    )
    runner = RecordingTextTestRunner(verbosity=args.verbosity)
    result = runner.run(suite)

    _write_sharding_results_file(result, include_sharding=include_sharding)

    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    passed = total - failures - errors - skipped

    main_status = "PASS" if result.wasSuccessful() else "FAIL"

    # Clean uploads after transfer tests.
    if include_transfer:
        _clean_uploads_dir()

    _print_summary(
        title="Assignment 04 Backend Test Summary",
        total=total,
        passed=passed,
        failures=failures,
        errors=errors,
        skipped=skipped,
        status=main_status,
    )

    orchestrator_exit_code = 0
    if args.run_stress_orchestrator:
        orchestrator_exit_code = _run_integrated_stress_orchestrator(args)
        orchestrator_status = "PASS" if orchestrator_exit_code == 0 else "FAIL"
        _print_summary(
            title="Integrated Stress Orchestrator Status",
            total=1,
            passed=1 if orchestrator_exit_code == 0 else 0,
            failures=1 if orchestrator_exit_code != 0 else 0,
            errors=0,
            skipped=0,
            status=orchestrator_status,
        )

    overall_success = result.wasSuccessful() and orchestrator_exit_code == 0
    print("\n" + "=" * 72)
    print(f"Combined Status: {'PASS' if overall_success else 'FAIL'}")
    print("=" * 72)

    return 0 if overall_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
