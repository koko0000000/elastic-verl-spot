"""Storage configuration for request state, trajectories, and checkpoints.

The first version should keep request metadata in a stable CPU-side store,
trajectories in memory plus durable flushes, and checkpoints in object storage
or a stable shared filesystem rather than on preemptible local disks only.
"""

from dataclasses import dataclass


@dataclass
class StorageConfig:
    """Locations for elastic runtime data."""

    request_backend: str = "memory"
    trajectory_backend: str = "memory"
    checkpoint_uri: str = "checkpoints/"
    response_cache_uri: str = "cache/responses/"

