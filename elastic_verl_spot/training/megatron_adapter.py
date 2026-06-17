"""Megatron training adapter.

Handles Megatron TP/PP/DP topology, checkpoint manifests, shard restoration,
and rank mapping for actor training.
"""

from .training_group_adapter import TrainingGroupAdapter


class MegatronAdapter(TrainingGroupAdapter):
    """Megatron backend shell."""

