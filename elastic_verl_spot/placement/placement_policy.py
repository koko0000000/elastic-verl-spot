"""Base placement policy.

Placement maps logical roles to physical Ray nodes and H200 GPUs. The policy
layer is separate from ElasticReplicaGroup and ElasticGangGroup, which describe
elastic semantics rather than physical colocation.
"""


class PlacementPolicy:
    """Base class for role-to-resource mapping."""

    def plan(self, cluster_state: dict, role_state: dict) -> dict:
        """Return a desired placement plan."""
        return {}

