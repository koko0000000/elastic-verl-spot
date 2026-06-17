"""Preemption response policy.

Defines how to drain rollout requests, stop assigning new work, and request a
training checkpoint or restart when spot preemption notices arrive.
"""


class PreemptionPolicy:
    """Return actions for preempting nodes."""

    def on_preemption_notice(self, node_id: str, roles: list[str]) -> dict:
        """Build a preemption response plan."""
        return {"node_id": node_id, "roles": roles, "action": "drain"}

