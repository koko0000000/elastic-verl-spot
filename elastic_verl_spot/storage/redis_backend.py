"""Redis metadata backend.

Intended for request status, leases, heartbeats, and other lightweight
CPU-side metadata. This file should stay optional so the package has no hard
Redis dependency until deployment wiring is added.
"""

from .storage_backend import StorageBackend


class RedisBackend(StorageBackend):
    """Redis backend placeholder."""

