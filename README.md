# Agent Loop Kit

Agent Loop Kit 提供了一套单文件 agent 工作协议，用来在不依赖 supervisor、RPC 服务或自定义 runtime 的前提下，近似复刻 wanman 的“研究 + 改进”循环。

它适用于 Codex、OpenCode 或其他类似 agent 运行器。要求运行器至少具备：

- 能读取 `AGENT.md`
- 能读写仓库文件
- 可选支持子代理或任务委派

## 目录内容

- `AGENT.md`：完整工作协议
- `.agent/mission.md`：长期目标、范围、约束、成功标准
- `.agent/backlog.md`：当前优先级 backlog
- `.agent/context.md`：跨轮次保留的稳定上下文
- `.agent/rounds/`：每轮总结
- `.agent/research/`：研究输出
- `.agent/reviews/`：评审输出
- `.agent/feedback/`：反馈与下一步机会输出

## 使用方式

1. 将这个目录复制到目标仓库，或至少复制 `AGENT.md` 和 `.agent/`
2. 先修改 `.agent/mission.md`，写入真实项目目标
3. 在目标仓库中启动 agent，并给出如下指令：

```text
阅读 AGENT.md，并基于当前 .agent 状态执行工作循环。
```

4. 如果平台支持子代理，让主代理按角色委派执行
5. 如果平台不支持子代理，则让主代理顺序模拟这些角色

## 预期效果

agent 应持续执行以下动作：

- 从代码、文档、配置和仓库信号中发现问题与机会
- 选择当前最有价值的下一步工作
- 实施最小但有用的改进闭环
- 对结果做评审
- 产出下一批 backlog

这是一种 **行为层面的 wanman 复刻**，不是 **runtime 层面的 wanman 复刻**。
