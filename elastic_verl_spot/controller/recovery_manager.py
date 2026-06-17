"""Recovery orchestration for rollout and training failures.

Rollout failures should retry unfinished requests. Training rank failures
should abort the current unsafe step, rebuild the gang group, and restore from
the most recent complete checkpoint.
"""


class RecoveryManager:
    """Placeholder for role-specific recovery flows."""

    def recover_rollout_worker(self, worker_id: str) -> str:
        """Return the planned rollout recovery action for a failed worker."""
        return f"retry_unfinished_requests:{worker_id}"

    def recover_training_group(self, checkpoint_path: str) -> str:
        """Return the planned training recovery action."""
        return f"rebuild_from_checkpoint:{checkpoint_path}"

