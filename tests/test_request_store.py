"""Tests for rollout request retry state."""

from elastic_verl_spot.rollout.request_store import InMemoryRequestStore, RequestStatus


def test_request_retry_with_partial_tokens() -> None:
    """A running request can save partial output and move back to retrying."""

    store = InMemoryRequestStore()
    store.submit("req-1", prompt="hello", model_version=1)
    running = store.mark_running("req-1", worker_id="rollout-0")
    assert running.status == RequestStatus.RUNNING
    assert running.attempt == 1

    store.save_partial("req-1", [1, 2, 3])
    retrying = store.mark_retrying("req-1", error="worker_lost")
    assert retrying.status == RequestStatus.RETRYING
    assert retrying.partial_tokens == [1, 2, 3]

    running_again = store.mark_running("req-1", worker_id="rollout-1")
    assert running_again.attempt == 2
    assert running_again.retried

    done = store.mark_done("req-1", [1, 2, 3, 4])
    assert done.status == RequestStatus.DONE
    assert done.response_tokens == [1, 2, 3, 4]
