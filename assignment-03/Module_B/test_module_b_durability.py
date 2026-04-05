# pyright: reportMissingImports=false

"""Compatibility shim for moved durability tests."""

try:
	from tests.test_module_b_durability import *
except ModuleNotFoundError:
	from assignment03.Module_B.tests.test_module_b_durability import *
