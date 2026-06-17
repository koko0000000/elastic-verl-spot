"""Checkpoint coordination.

Saves and restores actor model weights, optimizer state, scheduler state, RNG
state, global step, model version, and placement metadata through verl's native
checkpoint mechanisms where possible.
"""


class CheckpointCoordinator:
    """Checkpoint save/restore shell."""

    def save(self, step: int) -> str:
        """Return a placeholder checkpoint path."""
        return f"checkpoints/step_{step}"

    def load(self, checkpoint_path: str) -> dict:
        """Return placeholder checkpoint metadata."""
        return {"checkpoint_path": checkpoint_path}

