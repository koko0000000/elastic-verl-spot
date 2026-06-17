"""Local NVMe backend.

Intended for fast node-local cache such as temporary response cache or
trajectory shards. It must not be the only copy of correctness-critical state
on spot instances.
"""

from .storage_backend import StorageBackend


class LocalNVMeBackend(StorageBackend):
    """Local NVMe backend placeholder."""

