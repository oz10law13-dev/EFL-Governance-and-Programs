"""Org-scoped dependency providers.

Wraps SqliteDependencyProvider / PgDependencyProvider with a store proxy
that injects ``org_id`` into every store method call. The kernel and gates
see the same KernelDependencyProvider interface — no org_id leaks into
evaluation logic.
"""
from __future__ import annotations


class _OrgScopedStoreProxy:
    """Transparent proxy that appends ``org_id=<value>`` to every store method call."""

    def __init__(self, store, org_id: str):
        self._store = store
        self._org_id = org_id

    def __getattr__(self, name):
        attr = getattr(self._store, name)
        if callable(attr):
            def _wrapper(*args, **kwargs):
                kwargs.setdefault("org_id", self._org_id)
                return attr(*args, **kwargs)
            return _wrapper
        return attr


class OrgScopedSqliteProvider:
    """SqliteDependencyProvider scoped to a single org_id.

    Delegates to the real SqliteDependencyProvider but wraps both stores
    with _OrgScopedStoreProxy so every query is filtered by org_id.
    """

    def __init__(self, op_store, audit_store, org_id: str):
        from .sqlite_dependency_provider import SqliteDependencyProvider
        self._org_id = org_id
        self._delegate = SqliteDependencyProvider(
            _OrgScopedStoreProxy(op_store, org_id),
            _OrgScopedStoreProxy(audit_store, org_id),
        )

    def __getattr__(self, name):
        return getattr(self._delegate, name)


class OrgScopedPgProvider:
    """PgDependencyProvider scoped to a single org_id.

    Same pattern as OrgScopedSqliteProvider but for PostgreSQL stores.
    """

    def __init__(self, op_store, audit_store, org_id: str):
        from .pg_dependency_provider import PgDependencyProvider
        self._org_id = org_id
        self._delegate = PgDependencyProvider(
            _OrgScopedStoreProxy(op_store, org_id),
            _OrgScopedStoreProxy(audit_store, org_id),
        )

    def __getattr__(self, name):
        return getattr(self._delegate, name)
