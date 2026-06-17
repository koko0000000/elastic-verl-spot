"""Separated placement policy.

Rollout replicas and actor training gang workers occupy different GPUs or
nodes. This is the easiest policy for early rollout elasticity experiments.
"""

from .placement_policy import PlacementPolicy


class SeparatePolicy(PlacementPolicy):
    """Plan separated rollout and training placement."""

