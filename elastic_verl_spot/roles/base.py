"""Base role abstractions.

Roles are logical units such as rollout, actor training, reference policy, and
reward. The concrete elasticity behavior is implemented by replica and gang
group subclasses.
"""

from dataclasses import dataclass


@dataclass
class RoleSpec:
    """Desired properties of one role group."""

    name: str
    elastic_kind: str
    min_workers: int = 1
    max_workers: int = 1


@dataclass
class RoleState:
    """Observed runtime state of one role group."""

    name: str
    healthy_workers: int = 0
    desired_workers: int = 0

