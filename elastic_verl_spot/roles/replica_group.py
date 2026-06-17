"""ElasticReplicaGroup implementation shell.

Replica groups are independently scalable services. Rollout workers, reward
services, and some reference-policy services fit this pattern because one
worker can fail without forcing all replicas to restart.
"""


class ElasticReplicaGroup:
    """Manage add/remove/retry semantics for replica-style roles."""

    def add_replica(self) -> None:
        """Add a new replica when capacity appears."""
        return None

    def remove_replica(self, replica_id: str) -> None:
        """Remove or mark a replica unavailable."""
        return None

