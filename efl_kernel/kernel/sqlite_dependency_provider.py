from __future__ import annotations

from .audit_store import AuditStore
from .dependency_provider import InMemoryDependencyProvider


class SqliteDependencyProvider(InMemoryDependencyProvider):
    """A KernelDependencyProvider that sources override history from AuditStore.

    All other methods fall back to InMemoryDependencyProvider empty-data defaults,
    making the provider safe to use when external data sources are not present.
    """

    def __init__(self, audit_store: AuditStore):
        super().__init__()
        self.audit_store = audit_store

    def get_override_history(self, lineage_key: str, module_id: str, window_days: int = 28) -> dict:
        return self.audit_store.get_override_history(lineage_key, module_id, window_days)
