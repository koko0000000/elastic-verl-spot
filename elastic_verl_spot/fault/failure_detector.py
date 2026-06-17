"""Failure detector.

Converts Ray actor death, heartbeat timeout, node loss, and explicit spot
preemption events into normalized controller events.
"""


class FailureDetector:
    """Failure detection shell."""

