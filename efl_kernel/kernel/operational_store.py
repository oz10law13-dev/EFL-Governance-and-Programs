# Backward-compatibility shim.
# OperationalStore is now SqliteOperationalStore. Existing imports continue to work.
from .sqlite_operational_store import SqliteOperationalStore as OperationalStore

__all__ = ["OperationalStore"]
