```markdown
# Rollout Worker 状态机

## 1. 目标

每个 rollout worker / rollout replica 维护一个状态，用于统一管理：

- 是否可以接收新的 rollout request
- 是否存在未完成 request
- 是否可以参与 `sleep / wake / update_weights`
- 是否需要从系统中移除或重建

该状态机是后续实现 request retry、trajectory buffer、spot 退出恢复和 rollout group 重建的基础。

## 2. 状态定义

| 状态 | 含义 | 是否可调度 | 是否参与 checkpoint / weight sync |
|---|---|---|---|
| `ALIVE` | 正常运行 | 是 | 是 |
| `DRAINING` | 正在排空，准备移除 | 否 | 通常否 |
| `DEAD` | worker 已失效 | 否 | 否 |
| `REMOVED` | 已从控制面移除 | 否 | 否 |
| `REBUILDING` | 正在重建或重新加入 | 否 | 完成后再参与 |

### ALIVE

正常运行状态。

- 可以接收新 request
- 可以参与 rollout generation
- 可以参与 checkpoint manager 的 `sleep / wake / update_weights`
- load balancer 可以调度到该 worker

### DRAINING

排空状态，通常用于主动缩容或 spot 即将回收。

- 不再接收新 request
- 已经分配的 request 尽量继续完成
- 完成后进入 `REMOVED`
- 如果中途失败，则进入 `DEAD`

### DEAD

失效状态。

- worker 进程或节点已经不可用
- 不再接收新 request
- 未完成 request 需要重新入队或标记失败
- 不再参与 `sleep / wake / update_weights`

### REMOVED

已从控制面移除。

- 从 load balancer 中移除，不再被调度
- 从 checkpoint manager 中移除，不再参与权重同步和 `sleep / wake`
- 后续训练流程不再访问该 worker

### REBUILDING

重建状态。

- 新 worker 正在启动或重新加入
- 需要加载模型或同步权重
- 暂时不可调度
- 准备完成后进入 `ALIVE`

## 3. 当前短期实验流程

当前实验主要验证被动故障场景：

```text
ALIVE -> DEAD -> REMOVED
```

流程如下：

1. rollout server 正常运行，状态为 `ALIVE`。
2. 故障注入通过 `ray.kill` 杀掉一个 rollout server。
3. load balancer 将该 server 从可调度列表中移除。
4. checkpoint manager 将对应 replica 移除，避免后续 `sleep / wake / update_weights` 访问死亡 actor。
5. trainer 跳过本轮 rollout 权重同步，并唤醒剩余 rollout replicas。
6. 剩余 rollout server 继续完成后续训练 step。

## 4. 未来正式系统流程

### Spot 主动退出

如果云平台提前通知 spot instance 将被回收，可以采用更平滑的流程：

```text
ALIVE -> DRAINING -> REMOVED
```

含义：

1. 不再给该 worker 分配新 request。
2. 尽量等待已有 request 完成。
3. 完成后从 load balancer 和 checkpoint manager 中移除。

### Worker 突然故障

如果节点突然掉线：

```text
ALIVE -> DEAD -> REMOVED -> REBUILDING -> ALIVE
```

含义：

1. 检测到 worker 死亡。
2. 未完成 request 进入 retry。
3. 移除 dead worker。
4. 如有新实例可用，重建 rollout worker。
5. 完成模型加载和权重同步后重新加入调度。

## 5. 与 Load Balancer 的关系

load balancer 负责判断 worker 是否可以接收新 request。

| 状态 | 调度策略 |
|---|---|
| `ALIVE` | 可以调度 |
| `DRAINING` | 不再接收新 request |
| `DEAD` | 不可调度 |
| `REMOVED` | 不可调度 |
| `REBUILDING` | 暂不可调度 |

## 6. 与 Checkpoint Manager 的关系

checkpoint manager 负责 rollout worker 的 `sleep / wake / update_weights`。

| 状态 | checkpoint / weight sync 策略 |
|---|---|
| `ALIVE` | 可以参与 |
| `DRAINING` | 通常不再参与新的 `update_weights` |
| `DEAD` | 不能参与 |
| `REMOVED` | 已移除 |
| `REBUILDING` | 完成后再参与 |

## 7. 当前实验结论

当前短期实验已经证明：

- rollout server 被 kill 后可以从 load balancer 移除
- 对应 checkpoint replica 可以被移除
- trainer 可以跳过故障后的 `update_weights`
- 剩余 rollout replicas 可以继续完成后续 rollout
- 训练主流程可以在 rollout worker 退出后继续运行

当前尚未完成：

- request-level retry
- partial response 保存
- trajectory buffer 持久化
- rollout group 重建
- 故障后严格的权重重新同步

后续功能需要基于该状态机继续实现。
```
