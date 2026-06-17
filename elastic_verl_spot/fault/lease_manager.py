"""Lease manager.

Assigns leases to rollout requests so a request can be returned to the pending
queue if its worker disappears or stops renewing the lease.
"""


class LeaseManager:
    """Lease management shell."""

