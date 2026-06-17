"""Rollout resume policy.

Decides whether a failed rollout should restart from the prompt, continue from
partial tokens after prefill replay, or be discarded and resampled.
"""


class ResumePolicy:
    """Default conservative rollout resume strategy."""

    def choose(self, request: dict) -> str:
        """Return a resume mode for a failed request."""
        return "replay_from_prompt"

