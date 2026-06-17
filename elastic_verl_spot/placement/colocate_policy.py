"""Colocated placement policy.

Rollout and training share the same physical GPUs and switch capabilities by
phase. This requires memory lifecycle controls such as sleep, wake, offload, or
engine teardown before the first production implementation.
"""

from .placement_policy import PlacementPolicy


class ColocatePolicy(PlacementPolicy):
    """Plan colocated rollout/training placement."""

