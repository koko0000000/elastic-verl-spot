"""Top-level elastic system configuration.

This file should define whether elasticity is enabled, checkpoint cadence,
safe-point policy, maximum retries, stale rollout limits, and whether training
gang reconfiguration is allowed after new spot capacity appears.
"""

from dataclasses import dataclass


@dataclass
class ElasticConfig:
    """Global knobs for the elastic controller."""

    enable_elasticity: bool = True
    checkpoint_every_iteration: bool = True
    allow_training_reconfigure: bool = True
    max_rollout_retries: int = 3
    max_stale_model_versions: int = 0

