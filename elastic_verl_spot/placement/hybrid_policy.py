"""Hybrid placement policy.

Combines colocated workers with extra standalone rollout replicas. This is the
natural policy for semi-sync execution and for absorbing short-lived spot
capacity without always rebuilding training topology.
"""

from .placement_policy import PlacementPolicy


class HybridPolicy(PlacementPolicy):
    """Plan mixed colocated and standalone rollout placement."""

