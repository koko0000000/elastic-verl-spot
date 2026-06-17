"""Spot-aware role reallocation policy.

This is the main algorithmic module for the paper. It decides whether new or
remaining H200 spot instances should be used for rollout replicas, training
gang capacity, or hybrid workers, and whether reconfiguration should happen now
or be deferred to a safe point.
"""


class RoleReallocationPolicy:
    """Heuristic shell for role reallocation decisions."""

    def decide(self, cluster_state: dict, role_state: dict, phase: str) -> dict:
        """Return a placement action plan."""
        return {"action": "defer", "phase": phase}

