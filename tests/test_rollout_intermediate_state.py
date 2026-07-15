"""Tests for rollout intermediate state persistence."""

from elastic_verl_spot.rollout.response_cache import ResponseCache, ResponseCacheKey
from elastic_verl_spot.rollout.resume_policy import ResumeMode, ResumePolicy
from elastic_verl_spot.rollout.event_replay import RolloutEventStateBuilder
from elastic_verl_spot.rollout.request_store import RequestStatus
from elastic_verl_spot.rollout.trajectory_store import InMemoryTrajectoryStore, TrajectoryStatus


def test_trajectory_store_preserves_partial_and_completed_state() -> None:
    """Partial trajectory data can be updated and then completed."""

    store = InMemoryTrajectoryStore()
    partial = store.upsert_partial(
        "req-1",
        trajectory_id="traj-1",
        model_version=7,
        group_id="group-a",
        prompt_tokens=[101, 102],
        response_tokens=[201],
    )
    assert partial.status == TrajectoryStatus.PARTIAL

    store.append_response_tokens("traj-1", [202, 203])
    done = store.mark_done("traj-1", reward=1.0, logprobs=[-0.1], ref_logprobs=[-0.2])

    assert done.status == TrajectoryStatus.DONE
    assert done.response_tokens == [201, 202, 203]
    assert done.reward == 1.0
    assert done.as_event_fields()["response_tokens"] == 3


def test_response_cache_uses_prompt_model_and_sampling_key() -> None:
    """Completed responses can be cached by stable rollout metadata."""

    cache = ResponseCache()
    key = ResponseCacheKey.build(
        prompt_tokens=[1, 2, 3],
        model_version=2,
        sampling_params={"temperature": 1.0, "top_p": 0.9},
    )
    cache.put(key, response_tokens=[4, 5], response_text="ok")

    cached = cache.get(key)
    assert cached is not None
    assert cached.response_tokens == [4, 5]
    assert cache.contains(key)


def test_resume_policy_prefers_kv_then_partial_then_prompt() -> None:
    """Resume policy chooses the strongest available recovery path."""

    policy = ResumePolicy(max_attempts=3)
    assert policy.choose({"attempt": 1}) == ResumeMode.REPLAY_FROM_PROMPT
    assert policy.choose({"attempt": 1, "partial_tokens": [1]}) == ResumeMode.REPLAY_WITH_PARTIAL_PREFIX
    assert (
        policy.choose({"attempt": 1, "partial_tokens": [1], "kv_cache": {"cache_key": "kv"}})
        == ResumeMode.CONTINUE_FROM_KV_CACHE
    )
    assert policy.choose({"attempt": 3, "partial_tokens": [1]}) == ResumeMode.FAIL


def test_event_replay_links_stable_request_id_to_engine_attempts() -> None:
    """Runtime hook events rebuild request and trajectory state with id mapping."""

    builder = RolloutEventStateBuilder()
    stable_id = "uid-123:sample-0"
    events = [
        {"event_type": "request_submitted", "request_id": stable_id, "model_version": 1},
        {
            "event_type": "request_running",
            "request_id": stable_id,
            "engine_request_id": "engine-a",
            "worker_id": "rollout-0",
            "attempt": 1,
        },
        {
            "event_type": "partial_response_saved",
            "request_id": stable_id,
            "engine_request_id": "engine-a",
            "worker_id": "rollout-0",
            "attempt": 1,
            "partial_tokens": 2,
            "token_ids": [11, 12],
            "reason": "ActorDiedError",
        },
        {
            "event_type": "request_retry_queued",
            "request_id": stable_id,
            "engine_request_id": "engine-a",
            "failed_worker_id": "rollout-0",
            "attempt": 1,
            "next_attempt": 2,
            "error": "ActorDiedError",
        },
        {
            "event_type": "request_running",
            "request_id": stable_id,
            "engine_request_id": "engine-b",
            "worker_id": "rollout-1",
            "attempt": 2,
            "retried": True,
        },
        {
            "event_type": "request_retry_done",
            "request_id": stable_id,
            "engine_request_id": "engine-b",
            "worker_id": "rollout-1",
            "attempt": 2,
            "retried": True,
            "token_count": 3,
            "token_ids": [21, 22, 23],
        },
    ]

    builder.apply_events(events)

    request = builder.request_store.get(stable_id)
    trajectory = builder.trajectory_store.get(stable_id)

    assert request is not None
    assert trajectory is not None
    assert request.status == RequestStatus.DONE
    assert request.engine_request_ids == ["engine-a", "engine-b"]
    assert request.partial_tokens == [11, 12]
    assert request.partial_token_count == 2
    assert request.response_tokens == [21, 22, 23]
    assert request.response_token_count == 3
    assert trajectory.status == TrajectoryStatus.DONE
    assert trajectory.response_tokens == [21, 22, 23]


def test_event_replay_keeps_streamed_partial_when_actor_death_has_no_tokens() -> None:
    """A later ActorDiedError placeholder must not erase already streamed partial tokens."""

    builder = RolloutEventStateBuilder()
    stable_id = "uid-456:sample-0"
    builder.apply_events(
        [
            {"event_type": "request_submitted", "request_id": stable_id},
            {
                "event_type": "request_running",
                "request_id": stable_id,
                "engine_request_id": "engine-a",
                "worker_id": "rollout-0",
                "attempt": 1,
            },
            {
                "event_type": "partial_response_saved",
                "request_id": stable_id,
                "engine_request_id": "engine-a",
                "worker_id": "rollout-0",
                "attempt": 1,
                "partial_tokens": 4,
                "token_ids": [31, 32, 33, 34],
                "finished": False,
                "reason": "stream_update",
            },
            {
                "event_type": "partial_response_saved",
                "request_id": stable_id,
                "engine_request_id": "engine-a",
                "worker_id": "rollout-0",
                "attempt": 1,
                "partial_tokens": 0,
                "token_ids": [],
                "reason": "ActorDiedError",
            },
        ]
    )

    request = builder.request_store.get(stable_id)
    trajectory = builder.trajectory_store.get(stable_id)

    assert request is not None
    assert trajectory is not None
    assert request.partial_tokens == [31, 32, 33, 34]
    assert request.partial_token_count == 4
    assert trajectory.response_tokens == [31, 32, 33, 34]
