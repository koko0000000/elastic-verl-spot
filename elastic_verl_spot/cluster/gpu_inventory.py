"""GPU resource inventory for H200 nodes.

Tracks GPU availability, memory pressure, and role occupancy. This is the
input used by placement policies to decide rollout, training, or hybrid use.
"""

from dataclasses import dataclass


@dataclass
class GPUInventory:
    """Simple aggregate GPU inventory."""

    total_gpus: int = 0
    free_gpus: int = 0

