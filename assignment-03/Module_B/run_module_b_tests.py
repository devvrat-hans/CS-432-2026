#!/usr/bin/env python3
"""Run Module B backend tests with optional stress orchestrator integration."""

import argparse
from pathlib import Path
import sys
import unittest

from run_stress_orchestrator import main as run_stress_orchestrator_main

MODULE_B_DIR = Path(__file__).resolve().parent
TESTS_DIR = MODULE_B_DIR / "tests"
REPO_ROOT = MODULE_B_DIR.parent.parent

# Support running this script from either repo root or Module_B directory.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(MODULE_B_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_B_DIR))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

TEST_MODULES = [
    "test_module_b_base",
    "test_module_b_concurrent_usage",
    "test_module_b_race_conditions",
    "test_module_b_failure_simulation",
    "test_module_b_durability",
    "test_module_b_observability",
    "test_module_b_stress",
    "test_module_b_multiuser",
]


def build_suite(*, include_stress_module: bool) -> unittest.TestSuite:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    selected_modules = TEST_MODULES
    if not include_stress_module:
        selected_modules = [name for name in TEST_MODULES if name != "test_module_b_stress"]

    for module_name in selected_modules:
        suite.addTests(loader.loadTestsFromName(module_name))

    return suite


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Module B backend tests")
    parser.add_argument(
        "--verbosity",
        type=int,
        default=2,
        choices=[1, 2],
        help="unittest verbosity level for the main suite.",
    )
    parser.add_argument(
        "--skip-stress-module",
        action="store_true",
        help="Skip the test_module_b_stress unittest module in the main suite.",
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


def _run_integrated_stress_orchestrator(args: argparse.Namespace) -> int:
    orchestrator_args = ["--verbosity", str(args.stress_verbosity)]
    if args.stress_phases.strip():
        orchestrator_args.extend(["--phases", args.stress_phases.strip()])
    if args.stress_fast_fail:
        orchestrator_args.append("--fast-fail")

    print("\n[INTEGRATION] Running stress orchestrator from main test runner")
    return run_stress_orchestrator_main(orchestrator_args)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    suite = build_suite(include_stress_module=not args.skip_stress_module)
    runner = unittest.TextTestRunner(verbosity=args.verbosity)
    result = runner.run(suite)

    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    passed = total - failures - errors - skipped

    main_status = "PASS" if result.wasSuccessful() else "FAIL"
    _print_summary(
        title="Module B Backend Test Summary",
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
