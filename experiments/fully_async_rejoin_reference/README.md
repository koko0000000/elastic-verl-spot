# Fully Async Rejoin Reference

This directory archives the collaborator-provided fully async rollout control
patch and the first system-side integration analysis.

Files:

```text
add_trace.20260708.patch
control_rollouter.py
test.txt
run_script_reference.txt
```

The patch is not applied wholesale to this repository. Its reusable concepts are
being migrated into `elastic_verl_spot`, starting with:

```text
elastic_verl_spot/rollout/lifecycle_manager.py
docs/fully_async_rejoin_analysis.md
```

The first merged capabilities are:

```text
replica disable/enable
active replica set updates
scale-up lifecycle bookkeeping
checkpoint weight-sync event semantics
unified lifecycle event names
```

To connect the real verl fully-async runtime controls to these system-side
interfaces, run:

```text
experiments/fully_async_rejoin_reference/install_fully_async_lifecycle_hook.py
```

This hook installer is intended to be run after the collaborator's
`add_trace.20260708.patch`, because it hooks the methods introduced there:

```text
FullyAsyncRollouter.set_rollout_replica_enabled()
FullyAsyncRollouter.scale_up_replicas()
FullyAsyncRollouter.get_rollout_control_state()
FullyAsyncTrainer.scale_up_rollout_replicas()
```

Expected lifecycle events:

```text
rollout_replicas_registered
worker_disabled
checkpoint_replica_removed
worker_rebuilding
checkpoint_weight_synced
worker_rejoined
load_balancer_updated
rollout_replicas_scaled_up
```
