"""verl RayWorkerGroup adapter.

Creates, destroys, and rebuilds verl Ray worker groups. This is where future
code should bridge ElasticReplicaGroup/ElasticGangGroup to verl's worker group
mechanisms.
"""


class VerlWorkerGroupAdapter:
    """Worker-group lifecycle shell."""

    def create(self, spec: dict) -> object:
        """Create a worker group from a spec."""
        return spec

