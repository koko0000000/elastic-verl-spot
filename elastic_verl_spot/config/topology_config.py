"""H200 and distributed-training topology configuration.

This file should hold node-level GPU counts, tensor/pipeline/data parallel
constraints, and rules such as whether tensor parallel may cross node
boundaries on the current compute platform.
"""

from dataclasses import dataclass


@dataclass
class TopologyConfig:
    """Training topology constraints."""

    gpus_per_node: int = 2
    tensor_parallel_size: int = 1
    pipeline_parallel_size: int = 1
    allow_cross_node_tp: bool = False

