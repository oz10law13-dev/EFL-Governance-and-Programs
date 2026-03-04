from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ral import canonicalize_and_hash


@dataclass
class KDO:
    module_id: str
    module_version: str
    object_id: str
    ral_version: str
    evaluation_context: dict
    window_context: list[dict]
    violations: list[dict]
    resolution: dict
    reason_summary: str
    timestamp_normalized: str
    audit: dict


class KDOValidator:
    allowed_labels = {"QUARANTINE", "REGENERATE", "HARDFAILNOOVERRIDE", "HARDFAILOVERRIDEPOSSIBLE", "WARNING", "CLAMP"}
    allowed_publish = {"BLOCKED", "REGENERATE_REQUIRED", "PUBLISH_WITH_WARNING", "PUBLISH_WITH_CLAMP"}
    allowed_severity = {"QUARANTINE", "REGENERATE", "HARDFAIL", "WARNING", "CLAMP"}

    def validate(self, kdo: KDO) -> list[str]:
        errors: list[str] = []
        required = [
            ("module_id", str), ("module_version", str), ("object_id", str), ("ral_version", str),
            ("evaluation_context", dict), ("window_context", list), ("violations", list), ("resolution", dict),
            ("reason_summary", str), ("timestamp_normalized", str), ("audit", dict),
        ]
        for field_name, field_type in required:
            value = getattr(kdo, field_name, None)
            if not isinstance(value, field_type):
                errors.append(f"invalid_type:{field_name}")

        resolution = kdo.resolution if isinstance(kdo.resolution, dict) else {}
        if resolution.get("finalEffectiveLabel") not in self.allowed_labels:
            errors.append("invalid_finalEffectiveLabel")
        if resolution.get("finalPublishState") not in self.allowed_publish:
            errors.append("invalid_finalPublishState")
        if resolution.get("finalSeverity") not in self.allowed_severity:
            errors.append("invalid_finalSeverity")

        for v in kdo.violations:
            if not isinstance(v.get("code"), str):
                errors.append("invalid_violation_code")
            if v.get("moduleID") != kdo.module_id:
                errors.append("module_id_mismatch")

        for w in kdo.window_context:
            for key in ["windowType", "anchorDate", "startDate", "endDate", "timezone"]:
                if key not in w:
                    errors.append("malformed_window_entry")
                    break

        if resolution.get("finalEffectiveLabel") == "REGENERATE" and "REGENERATEREQUIRED" not in kdo.reason_summary:
            errors.append("missing_regenerate_reason_summary_token")
        return errors


def freeze_kdo(kdo: KDO) -> str | None:
    if "decisionHash" not in kdo.audit:
        return None
    kdo.audit["decisionHash"] = ""
    hashed = canonicalize_and_hash(kdo.__dict__)
    kdo.audit["decisionHash"] = hashed
    return hashed
