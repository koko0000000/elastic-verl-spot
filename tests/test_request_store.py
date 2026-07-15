"""Tests for rollout request retry state."""

from elastic_verl_spot.rollout.request_store import InMemoryRequestStore, RequestStatus


def test_request_retry_with_partial_tokens() -> None:
    """A running request can save partial output and move back to retrying."""

    store = InMemoryRequestStore()
    store.submit("req-1", prompt="hello", prompt_tokens=[10, 11], model_version=1)
    running = store.mark_running("req-1", worker_id="rollout-0", engine_request_id="engine-a")
    assert running.status == RequestStatus.RUNNING
    assert running.attempt == 1
    assert running.engine_request_ids == ["engine-a"]

    store.save_partial("req-1", [1, 2, 3])
    store.append_partial("req-1", [4], text_delta="x")
    store.save_kv_cache(
        "req-1",
        cache_key="kv-req-1",
        token_count=4,
        worker_id="rollout-0",
        location="object-store://kv-req-1",
    )
    retrying = store.mark_retrying("req-1", error="worker_lost")
    assert retrying.status == RequestStatus.RETRYING
    assert retrying.partial_tokens == [1, 2, 3, 4]
    assert retrying.kv_cache is not None
    assert retrying.kv_cache.cache_key == "kv-req-1"

    running_again = store.mark_running("req-1", worker_id="rollout-1", engine_request_id="engine-b")
    assert running_again.attempt == 2
    assert running_again.retried
    assert running_again.engine_request_ids == ["engine-a", "engine-b"]

    store.attach_trajectory("req-1", "traj-1")
    done = store.mark_done("req-1", [1, 2, 3, 4], text="done")
    assert done.status == RequestStatus.DONE
    assert done.response_tokens == [1, 2, 3, 4]
    assert done.response_text == "done"
    assert done.trajectory_id == "traj-1"
