"""Registry of Ray nodes and their elastic role assignments.

This module records node IDs, IPs, GPU counts, spot/on-demand status,
preemption state, and the roles currently placed on each node.
"""

from dataclasses import dataclass, field


@dataclass
class NodeRecord:
    """A compute node known to the elastic controller."""

    node_id: str
    address: str
    gpu_count: int
    is_spot: bool = True
    roles: set[str] = field(default_factory=set)

