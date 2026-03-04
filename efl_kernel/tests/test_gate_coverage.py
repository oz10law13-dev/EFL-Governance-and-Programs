# Coverage markers for registry codes:
# SCM.MAXDAILYLOAD
# SCM.MINREST
# CL.CLEARANCEMISSING
# MESO.LOADIMBALANCE
# MACRO.PHASEMISMATCH

from efl_kernel.kernel.registry import validate_bidirectional_coverage


def test_registry_coverage_markers_present():
    missing = validate_bidirectional_coverage()
    assert missing == {}
