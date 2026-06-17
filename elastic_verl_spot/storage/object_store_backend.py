"""Object-store backend.

Intended for reliable cross-node storage such as S3, OSS, COS, OBS, MinIO, or
Ceph. Checkpoints and committed trajectory manifests should live here.
"""

from .storage_backend import StorageBackend


class ObjectStoreBackend(StorageBackend):
    """Object store backend placeholder."""

