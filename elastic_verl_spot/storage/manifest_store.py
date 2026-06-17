"""Global manifest store.

Records global step, model version, checkpoint paths, role topology, placement
plans, and committed trajectory sets so restart and analysis can reconstruct
the system state.
"""

from dataclasses import dataclass


@dataclass
class Manifest:
    """Minimal global manifest."""

    global_step: int
    model_version: int
    checkpoint_path: str

