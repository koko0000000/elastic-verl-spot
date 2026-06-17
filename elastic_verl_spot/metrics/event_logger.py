"""Elastic event logger.

Persists node joins, node exits, preemption notices, retries, safe points, and
reconfiguration actions so experiments can be audited and reproduced.
"""


class EventLogger:
    """Event logger shell."""

