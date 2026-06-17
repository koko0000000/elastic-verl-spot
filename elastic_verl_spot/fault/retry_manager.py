"""Retry manager.

Owns retry limits and backoff for rollout requests, worker startup, and
recoverable storage operations.
"""


class RetryManager:
    """Retry decision shell."""

    def should_retry(self, attempts: int, limit: int) -> bool:
        """Return whether another retry is allowed."""
        return attempts < limit

