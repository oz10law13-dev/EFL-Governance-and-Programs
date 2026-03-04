from efl_kernel.kernel.dependency_provider import InMemoryDependencyProvider
from efl_kernel.kernel.kernel import KernelRunner
from efl_kernel.kernel.kdo import KDOValidator
from efl_kernel.kernel.ral import RAL_SPEC


def _base_input():
    session_reg = RAL_SPEC["moduleRegistration"]["SESSION"]
    return {
        "moduleVersion": session_reg["moduleVersion"],
        "moduleViolationRegistryVersion": session_reg["moduleViolationRegistryVersion"],
        "registryHash": session_reg["registryHash"],
        "objectID": "obj-1",
        "evaluationContext": {"athleteID": "a1", "sessionID": "s1"},
        "windowContext": [
            {"windowType": "ROLLING7DAYS", "anchorDate": "2026-01-01", "startDate": "2025-12-26", "endDate": "2026-01-01", "timezone": "UTC"},
            {"windowType": "ROLLING28DAYS", "anchorDate": "2026-01-01", "startDate": "2025-12-05", "endDate": "2026-01-01", "timezone": "UTC"},
        ],
        "gateViolations": [{"code": "SCM.MAXDAILYLOAD", "moduleID": "SESSION"}],
    }


def test_happy_path_kdo_validates():
    kdo = KernelRunner(InMemoryDependencyProvider()).evaluate(_base_input(), "SESSION")
    errors = KDOValidator().validate(kdo)
    assert errors == []


def test_missing_window_halts_quarantine():
    payload = _base_input()
    payload["windowContext"] = payload["windowContext"][:1]
    kdo = KernelRunner(InMemoryDependencyProvider()).evaluate(payload, "SESSION")
    assert kdo.violations[0]["code"] == "RAL.MISSINGREQUIREDWINDOW"
