from __future__ import annotations

from datetime import datetime, timedelta, timezone

from efl_kernel.kernel.audit_store import AuditStore
from efl_kernel.kernel.kdo import KDO
from efl_kernel.kernel.operational_store import OperationalStore
from efl_kernel.kernel.sqlite_dependency_provider import SqliteDependencyProvider


def _make_kdo(
    *,
    timestamp_normalized: str | None = None,
    violations: list[dict] | None = None,
    lineage_key: str = "a1|s1",
    module_id: str = "SESSION",
    object_id: str = "obj-1",
) -> KDO:
    return KDO(
        module_id=module_id,
        module_version="1.0",
        object_id=object_id,
        ral_version="1.0",
        evaluation_context={"athleteID": "a1", "sessionID": "s1", "lineageKey": lineage_key},
        window_context=[],
        violations=violations or [],
        resolution={
            "finalEffectiveLabel": "CLAMP",
            "finalSeverity": "CLAMP",
            "finalPublishState": "LEGALREADY",
            "mutationsApplied": [],
            "requiresRevalidation": False,
            "revalidatedModules": [],
        },
        reason_summary="NO_VIOLATIONS",
        timestamp_normalized=timestamp_normalized or datetime.now(timezone.utc).isoformat(),
        audit={"decisionHash": ""},
    )


def test_write_and_read_kdo_by_decision_hash():
    store = AuditStore(":memory:")
    kdo = _make_kdo()
    decision_hash = store.commit_kdo(kdo)

    result = store.get_kdo(decision_hash)

    assert result is not None
    assert result["module_id"] == "SESSION"
    assert result["object_id"] == "obj-1"
    assert result["audit"]["decisionHash"] == decision_hash
    assert store.get_kdo("nonexistent-hash") is None


def test_override_ledger_counts_both_axes():
    store = AuditStore(":memory:")
    violations = [
        {"code": "SCM.MAXDAILYLOAD", "moduleID": "SESSION", "overrideUsed": True, "overrideReasonCode": "OR-001"},
        {"code": "SCM.MINREST", "moduleID": "SESSION", "overrideUsed": True, "overrideReasonCode": "OR-001"},
    ]
    store.commit_kdo(_make_kdo(violations=violations))

    history = store.get_override_history("a1|s1", "SESSION", 28)

    assert history["byViolationCode"]["SCM.MAXDAILYLOAD"] == 1
    assert history["byViolationCode"]["SCM.MINREST"] == 1
    assert history["byReasonCode"]["OR-001"] == 2


def test_window_exclusion_omits_old_records():
    store = AuditStore(":memory:")
    violations = [
        {"code": "SCM.MAXDAILYLOAD", "moduleID": "SESSION", "overrideUsed": True, "overrideReasonCode": "OR-001"}
    ]
    old_ts = (datetime.now(timezone.utc) - timedelta(days=29)).isoformat()
    recent_ts = datetime.now(timezone.utc).isoformat()

    store.commit_kdo(_make_kdo(timestamp_normalized=old_ts, violations=violations))
    store.commit_kdo(_make_kdo(timestamp_normalized=recent_ts, violations=violations, object_id="obj-2"))

    history = store.get_override_history("a1|s1", "SESSION", 28)

    # Only the recent record falls inside the 28-day window
    assert history["byViolationCode"].get("SCM.MAXDAILYLOAD") == 1
    assert history["byReasonCode"].get("OR-001") == 1


def test_append_only_duplicate_hash_ignored():
    store = AuditStore(":memory:")
    violations = [
        {"code": "SCM.MAXDAILYLOAD", "moduleID": "SESSION", "overrideUsed": True, "overrideReasonCode": "OR-001"}
    ]
    kdo = _make_kdo(violations=violations)

    h1 = store.commit_kdo(kdo)
    h2 = store.commit_kdo(kdo)  # same object — same frozen hash

    assert h1 == h2

    kdo_count = store._conn.execute(
        "SELECT COUNT(*) FROM kdo_log WHERE decision_hash = ?", (h1,)
    ).fetchone()[0]
    assert kdo_count == 1

    override_count = store._conn.execute(
        "SELECT COUNT(*) FROM override_ledger WHERE lineage_key = 'a1|s1'"
    ).fetchone()[0]
    assert override_count == 1


def test_sqlite_dependency_provider_delegates_to_audit_store():
    store = AuditStore(":memory:")
    op_store = OperationalStore(":memory:")
    provider = SqliteDependencyProvider(op_store, store)
    violations = [
        {"code": "SCM.MAXDAILYLOAD", "moduleID": "SESSION", "overrideUsed": True, "overrideReasonCode": "OR-001"}
    ]
    store.commit_kdo(_make_kdo(violations=violations))

    history = provider.get_override_history("a1|s1", "SESSION", 28)

    assert history["byViolationCode"]["SCM.MAXDAILYLOAD"] == 1
