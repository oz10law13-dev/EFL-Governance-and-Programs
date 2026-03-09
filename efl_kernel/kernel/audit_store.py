# Backward-compatibility shim.
# AuditStore is now SqliteAuditStore. Existing imports of AuditStore continue to work.
from .sqlite_audit_store import SqliteAuditStore as AuditStore

__all__ = ["AuditStore"]
