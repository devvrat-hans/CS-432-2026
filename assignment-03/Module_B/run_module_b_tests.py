#!/usr/bin/env python3
"""Run all Module B backend tests and print a clear pass/fail summary."""

from pathlib import Path
import sys
import unittest

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
    "assignment03.Module_B.tests.test_module_b_base",
    "assignment03.Module_B.tests.test_module_b_concurrent_usage",
    "assignment03.Module_B.tests.test_module_b_race_conditions",
    "assignment03.Module_B.tests.test_module_b_failure_simulation",
    "assignment03.Module_B.tests.test_module_b_durability",
    "assignment03.Module_B.tests.test_module_b_observability",
    "assignment03.Module_B.tests.test_module_b_stress",
    "assignment03.Module_B.tests.test_module_b_multiuser",
]


def build_suite() -> unittest.TestSuite:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for module_name in TEST_MODULES:
        suite.addTests(loader.loadTestsFromName(module_name))

    return suite


def main() -> int:
    suite = build_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    passed = total - failures - errors - skipped

    print("\n" + "=" * 72)
    print("Module B Backend Test Summary")
    print(f"Total:   {total}")
    print(f"Passed:  {passed}")
    print(f"Failed:  {failures}")
    print(f"Errors:  {errors}")
    print(f"Skipped: {skipped}")
    print(f"Status:  {'PASS' if result.wasSuccessful() else 'FAIL'}")
    print("=" * 72)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
