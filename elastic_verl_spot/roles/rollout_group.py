"""GRPO rollout role group.

This group owns rollout replicas, request assignment, retry behavior, and
model-version-aware generation. It should use rollout scheduler and stores
rather than keeping correctness-critical state only in worker memory.
"""

from .replica_group import ElasticReplicaGroup


class RolloutGroup(ElasticReplicaGroup):
    """Replica group specialized for GRPO response generation."""

