"""Hybrid colocated role group.

Represents one physical worker pool that can serve rollout in rollout phase and
actor training in training phase. The placement policy decides whether this
logical hybrid maps to the same GPUs as rollout and training groups.
"""


class HybridGroup:
    """Shell for colocated or semi-sync hybrid workers."""

    def activate_rollout(self) -> None:
        """Switch the colocated worker into rollout-serving mode."""
        return None

    def activate_training(self) -> None:
        """Switch the colocated worker into training mode."""
        return None

