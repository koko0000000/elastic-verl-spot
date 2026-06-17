"""Training topology planner.

Computes world size, rank mapping, and DP/TP/PP layouts for FSDP or Megatron
training groups under current H200 node availability.
"""


class TopologyPlanner:
    """Return training topology candidates."""

    def plan_training_topology(self, available_gpus: int) -> dict:
        """Build a simple topology placeholder."""
        return {"world_size": available_gpus}

