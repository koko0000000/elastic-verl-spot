"""Effective Training Time Ratio metric.

ETTR measures the fraction of wall-clock time spent doing useful training work
rather than recovery, waiting, reconfiguration, or failed work replay.
"""


def effective_training_time_ratio(useful_seconds: float, total_seconds: float) -> float:
    """Compute ETTR with zero-division protection."""
    if total_seconds <= 0:
        return 0.0
    return useful_seconds / total_seconds

