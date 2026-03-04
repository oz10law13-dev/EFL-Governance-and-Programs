from __future__ import annotations

from .audit_store import AuditStore
from .dependency_provider import KernelDependencyProvider


class SqliteDependencyProvider(KernelDependencyProvider):
    """A KernelDependencyProvider that sources override history from AuditStore.

    All other methods (athlete profile, window totals, etc.) require external data
    sources and raise NotImplementedError via the base class.
    """

    def __init__(self, audit_store: AuditStore):
        self.audit_store = audit_store

    def get_override_history(self, lineage_key: str, module_id: str, window_days: int = 28) -> dict:
        return self.audit_store.get_override_history(lineage_key, module_id, window_days)
