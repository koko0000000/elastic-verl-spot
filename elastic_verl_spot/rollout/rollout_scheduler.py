"""Rollout request scheduler.

Assigns prompt requests to rollout replicas, renews leases, retries timed-out
requests, and keeps generation tied to a specific actor model version.
"""


class RolloutScheduler:
    """Minimal rollout scheduler shell."""

    def submit(self, request: dict) -> str:
        """Submit a rollout request and return its id."""
        return str(request.get("request_id", "unknown"))

