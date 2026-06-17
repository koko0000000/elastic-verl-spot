"""ElasticGangGroup implementation shell.

Gang groups represent workers that must be scheduled and restarted together,
such as FSDP or Megatron actor training ranks that share a fixed NCCL process
group and world size.
"""


class ElasticGangGroup:
    """Manage safe-point rebuild semantics for training-style roles."""

    def request_reconfigure(self) -> None:
        """Mark the group for rebuild at the next safe point."""
        return None

    def rebuild(self, checkpoint_path: str) -> None:
        """Recreate the gang group from a checkpoint."""
        return None

