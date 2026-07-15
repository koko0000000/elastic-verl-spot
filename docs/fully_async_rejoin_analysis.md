# Fully Async Rollout Rejoin Patch Analysis

Date: 2026-07-15

This document analyzes the fully async rollout patch stored under
`experiments/fully_async_rejoin_reference/`. The goal of this step is not to
merge the patch into the main elastic rollout path directly, but to identify
which capabilities should be reused and how they should be integrated with the
existing `elastic_verl_spot` rollout state, request store, trajectory store, and
event log design.

## 1. Reference Files

The collaborator-provided files are archived here:

```text
experiments/fully_async_rejoin_reference/add_trace.20260708.patch
experiments/fully_async_rejoin_reference/control_rollouter.py
experiments/fully_async_rejoin_reference/test.txt
experiments/fully_async_rejoin_reference/run_script_reference.txt
```

The patch was written against upstream verl `v0.7.1` and targets the
`verl.experimental.fully_async_policy` entrypoint.

## 2. Main Capabilities In The Patch

### 2.1 Named Ray Actors

Files:

```text
verl/experimental/fully_async_policy/fully_async_main.py
```

The patch names the fully async rollouter and trainer actors:

```text
fully_async_rollouter
fully_async_trainer
```

This enables an external control script to find them at runtime through Ray.

### 2.2 External Rollout Control CLI

File:

```text
control_rollouter.py
```

Supported operations:

```text
status
global --enabled true|false
replica --id N --enabled true|false
scale-up --num-replicas N
```

This provides an operational control plane for fully async rollout workers.

### 2.3 Active Replica Routing Update

Files:

```text
verl/experimental/agent_loop/agent_loop.py
```

Added or modified methods:

```text
GlobalRequestLoadBalancer.update_servers()
AsyncLLMServerManager.update_servers()
AgentLoopWorker.update_servers()
AgentLoopManager.update_active_replicas()
AgentLoopManager.add_replicas()
```

These methods update the active rollout server set without recreating all
agent-loop workers. Sticky request mappings to removed servers are cleared.

### 2.4 Runtime Replica Enable / Disable

File:

```text
verl/experimental/fully_async_policy/fully_async_rollouter.py
```

Added methods:

```text
set_rollout_enabled()
set_rollout_replica_enabled()
get_rollout_control_state()
scale_up_replicas()
```

The rollouter can pause generation, disable one replica, resume a replica, and
refresh request routing to active replicas.

### 2.5 Scale-Up And Weight Sync

File:

```text
verl/experimental/fully_async_policy/fully_async_trainer.py
```

Added method:

```text
scale_up_rollout_replicas()
```

Flow:

```text
rollouter.scale_up_replicas()
-> trainer obtains new rollout replicas
-> checkpoint_manager.add_replicas(new_replicas)
-> checkpoint_manager.update_weights(current_param_version)
```

This is important because a newly added rollout replica must receive current
model weights before it is allowed to serve rollout requests.

### 2.6 Trace Fields

Files:

```text
verl/experimental/agent_loop/agent_loop.py
verl/experimental/agent_loop/single_turn_agent_loop.py
verl/experimental/agent_loop/tool_agent_loop.py
verl/workers/rollout/vllm_rollout/vllm_async_server.py
```

The patch adds trace identifiers:

```text
rollout_trace_id
rollout_server_id
rollout_request_id
rollout_backend_request_id
```

These overlap conceptually with the local elastic rollout fields:

```text
request_id = uid:sample-x
engine_request_id = backend vLLM request id
worker_id / server_id = rollout server identity
```

The final integration should reuse one naming scheme instead of keeping both.

## 3. Difference From Current Local Elastic Rollout Work

Current local work focuses on request-level fault tolerance inside the current
GRPO / `main_ppo.py` experimental path:

```text
runtime fault injection
request retry events
partial response logging
request store
trajectory store
event replay
rollout replica state machine
```

The fully async patch focuses on replica-level lifecycle control in the
`fully_async_policy` path:

```text
disable / enable rollout replica
active rollout server routing update
dynamic scale-up
new replica checkpoint weight sync
external control CLI
```

In short:

```text
local elastic rollout work: request and trajectory consistency
fully async patch: rollout replica lifecycle and rejoin mechanics
```

These two tracks are complementary.

## 4. Integration Target

The final architecture should avoid long-term direct logic accumulation inside
verl source files.

Target split:

```text
verl source:
  thin hooks for runtime integration

elastic_verl_spot:
  state machine
  request store
  trajectory store
  retry policy
  partial response persistence
  rollout replica lifecycle manager
  checkpoint / load-balancer adapters
```

## 5. Capability Mapping

| Patch capability | Current patch location | Target system location |
|---|---|---|
| Named rollouter/trainer actors | `fully_async_main.py` | Thin verl hook or launch adapter |
| Disable / enable replica | `fully_async_rollouter.py` | `RolloutReplicaStateMachine` + lifecycle manager |
| Update active servers | `agent_loop.py` | load-balancer adapter |
| Add rollout replicas | `AgentLoopManager.add_replicas()` | rollout lifecycle manager |
| Sync weights to new replica | `fully_async_trainer.py` | checkpoint adapter |
| Trace request ids | `agent_loop.py`, agent loops | unified `request_id` / `engine_request_id` event schema |
| vLLM request / response logs | `vllm_async_server.py` | JSONL event logger + event replay |

## 6. Minimal Reproduction Plan

Before integration, reproduce the patch in an isolated vanilla verl checkout.

```bash
git clone https://github.com/volcengine/verl.git verl-v0.7.1-fully-async-test
cd verl-v0.7.1-fully-async-test
git checkout v0.7.1
git apply /path/to/add_trace.20260708.patch
```

Place the control script in the checkout:

```bash
cp /path/to/control_rollouter.py scripts/control_rollouter.py
```

Run the fully async training script from `run_script_reference.txt` after
replacing local model and dataset paths.

During training, verify:

```bash
python3 scripts/control_rollouter.py status
python3 scripts/control_rollouter.py replica --id 0 --enabled false
python3 scripts/control_rollouter.py status
python3 scripts/control_rollouter.py replica --id 0 --enabled true
python3 scripts/control_rollouter.py scale-up --num-replicas 1
python3 scripts/control_rollouter.py status
```

Success criteria:

```text
1. status returns active and disabled replica ids.
2. disabling one replica removes it from active routing.
3. enabling the replica restores routing.
4. scale-up creates a new replica.
5. trainer adds the new checkpoint replica.
6. trainer syncs current weights to the new rollout replica.
7. training continues after each operation.
```

## 7. First Integration Step

Do not directly apply the full patch to the main branch.

Recommended first integration branch:

```bash
git checkout -b integration/fully-async-rejoin-adapter
```

Recommended order:

```text
1. Reproduce the patch on vanilla verl v0.7.1.
2. Record successful logs and command output.
3. Port only active server update APIs into a thin adapter.
4. Connect disable/enable to RolloutReplicaStateMachine.
5. Connect scale-up to checkpoint adapter and current model version.
6. Emit unified JSONL events.
7. Add tests using event replay and state-machine assertions.
```

## 8. Event Schema To Use During Integration

The rejoin work should use the existing elastic event style and add these
events:

```text
worker_draining
worker_disabled
worker_removed
worker_rebuilding
worker_rejoined
worker_alive
load_balancer_updated
checkpoint_replica_added
checkpoint_weight_synced
```

Suggested common fields:

```text
run_id
global_steps
replica_id
server_id
node_id
state_before
state_after
model_version
checkpoint_version
active_replica_ids
```

## 9. Storage Design Note

For multi-node spot/preemptible environments, state should not live only in one
training node's GPU or one rollout node's process memory.

Recommended design:

```text
Redis:
  current control-plane state
  request status
  replica status
  retry queue
  engine-id mapping

S3 / shared object store:
  append-only event logs
  trajectory payloads
  partial response payloads
  checkpoints

Rollout worker local GPU / CPU memory:
  vLLM engine state
  KV cache body
```

Redis should store small, low-frequency metadata. It should not store full KV
cache tensors, model weights, or large trajectory payloads.

## 10. Open Questions Before Merge

1. Does the collaborator patch handle sudden actor death, or mainly controlled
   disable / enable?
2. Does scale-up work when the new replica lands on a newly joined Ray node?
3. Does the new replica receive the latest global step weights before routing?
4. Are in-flight requests drained, aborted, or retried during disable?
5. How should patch trace fields map to `request_id` and `engine_request_id`?
6. Should the first integration target `fully_async_policy` only, or also the
   current `main_ppo.py` GRPO experiment path?

## 11. First Functional Merge

The first functional merge does not apply the full verl patch. Instead, it
extracts the reusable control-plane semantics into:

```text
elastic_verl_spot/rollout/lifecycle_manager.py
tests/test_rollout_lifecycle_manager.py
```

This provides a system-side interface for:

```text
register_replicas()
disable_replica()
enable_replica()
scale_up()
update_model_version()
control_state()
```

Expected event flow for disabling and re-enabling a replica:

```text
rollout_replicas_registered
worker_disabled
checkpoint_replica_removed
load_balancer_updated
worker_rebuilding
checkpoint_weight_synced
worker_rejoined
load_balancer_updated
```

Expected event flow for scale-up:

```text
worker_rebuilding
checkpoint_weight_synced
worker_rejoined
load_balancer_updated
rollout_replicas_scaled_up
```

Local validation:

```powershell
cd "D:\research\elastic verl\elastic-verl-spot"
python -m pytest tests\test_rollout_lifecycle_manager.py -q
python -m pytest tests -q
```

The next integration step is to make the thin verl fully-async hook call this
manager when `set_rollout_replica_enabled()` or `scale_up_rollout_replicas()` is
invoked.
