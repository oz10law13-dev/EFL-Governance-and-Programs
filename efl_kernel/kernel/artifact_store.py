# Backward-compatibility shim.
# ArtifactStore is now SqliteArtifactStore. Existing imports continue to work.
from .sqlite_artifact_store import SqliteArtifactStore as ArtifactStore

__all__ = ["ArtifactStore"]
