"""Training group adapter interface.

Defines common methods for FSDP and Megatron training groups: create, destroy,
train, save checkpoint, load checkpoint, and rebuild with a new topology.
"""


class TrainingGroupAdapter:
    """Backend-neutral training group interface."""

    def rebuild(self, topology: dict, checkpoint_path: str) -> None:
        """Rebuild a training group from checkpoint and topology."""
        return None

