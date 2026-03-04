from datetime import datetime, date, timezone
from efl_kernel.kernel.dependency_provider import KernelDependencyProvider
from efl_kernel.kernel.kernel import KernelRunner
from efl_kernel.kernel.ral import RAL_SPEC

def main():
    dep = KernelDependencyProvider()
    kernel = KernelRunner(dep)

    reg = RAL_SPEC["moduleRegistration"]["SESSION"]

    today = date.today().isoformat()
    session_id = "session-smoke-ATH001"

    raw = {
        "moduleID": "SESSION",
        "moduleVersion": reg["moduleVersion"],
        "moduleViolationRegistryVersion": reg["moduleViolationRegistryVersion"],
        "registryHash": reg["registryHash"],
        "objectID": session_id,
        "evaluationContext": {
            "athleteID": "ATH001",
            "teamID": "TEAM-A",
            "sessionID": session_id,  # <-- add this
            "sessionType": "RESISTANCE",
            "sessionDate": datetime.now(timezone.utc).isoformat(),
        },
        "windowContext": [
            {
                "windowType": "ROLLING7DAYS",
                "anchorDate": today,
                "startDate": today,
                "endDate": today,
                "timezone": "America/Chicago",
                "totalContactLoad": 0,
            },
            {
                "windowType": "ROLLING28DAYS",
                "anchorDate": today,
                "startDate": today,
                "endDate": today,
                "timezone": "America/Chicago",
                "totalContactLoad": 0,
            },
        ],
        "session": {},
    }

    kdo = kernel.evaluate(raw, module_id="SESSION")
    print("Effective label:", kdo.resolution["finalEffectiveLabel"])
    print("Severity:", kdo.resolution["finalSeverity"])
    print("Publish state:", kdo.resolution["finalPublishState"])
    print("Violations:", [v["code"] for v in kdo.violations])

if __name__ == "__main__":
    main()
