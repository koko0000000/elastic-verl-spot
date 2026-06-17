"""Generic storage backend interface.

Backends may target Redis, local NVMe, object storage, or a shared filesystem.
The controller should depend on this interface rather than direct storage APIs.
"""


class StorageBackend:
    """Simple key-value storage interface."""

    def put(self, key: str, value: bytes) -> None:
        """Store bytes by key."""
        raise NotImplementedError

    def get(self, key: str) -> bytes | None:
        """Read bytes by key."""
        raise NotImplementedError

