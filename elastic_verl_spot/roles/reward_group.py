"""Reward or verifier role group.

Holds rule-based rewards, model rewards, or external verifiers. This should be
modeled as a replica group when requests can be retried independently.
"""

from .replica_group import ElasticReplicaGroup


class RewardGroup(ElasticReplicaGroup):
    """Reward/verifier replica group shell."""

