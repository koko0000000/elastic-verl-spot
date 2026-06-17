"""Smoke tests for the scaffold package."""

from elastic_verl_spot.metrics.ettr import effective_training_time_ratio


def test_ettr() -> None:
    """ETTR should be useful time divided by total time."""
    assert effective_training_time_ratio(5.0, 10.0) == 0.5

