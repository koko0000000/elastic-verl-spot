"""Role configuration for GRPO and future algorithms.

This module describes logical roles such as rollout, actor training, reference
policy, and reward/verifier. Each role declares whether it behaves like an
elastic replica group or a safe-point-rebuilt gang group.
"""

from dataclasses import dataclass


@dataclass
class RoleConfig:
    """Resource and elasticity settings for one logical role."""

    name: str
    gpus_per_worker: int = 1
    min_workers: int = 1
    max_workers: int = 1
    elastic_kind: str = "replica"

