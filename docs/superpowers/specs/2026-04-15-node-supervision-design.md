# SuperPipeline 第二轮迭代：节点级监督系统

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:writing-plans to create implementation plan from this spec.

## 目标

将 SuperPipeline 从"配置好一键跑"升级为"每个节点可观测、可编辑、可重跑"的多 Agent 监督系统。核心使用场景：Claude Code agent 通过 CLI 逐节点调试优化内容管线。

## 核心概念

### 节点快照（Stage Snapshot）

每个节点执行后自动保存完整快照：输入、输出、配置、状态。支持多版本（重跑时 version 递增）。这是整个系统的数据基础。

### 节点配置动态化

每个节点的模型、提示词、参数在运行时可覆盖。配置优先级：CLI/API 传入 > YAML 默认值。提示词支持内联覆盖（直接传字符串替代 Jinja2 模板）。

### 级联重跑

从某个节点开始重跑：读取该节点的输入快照，用新配置执行，然后依次重跑所有后续节点。每次重跑产生新版本快照。

## 架构变更

### 1. 新增 stage_snapshots 存储

```sql
CREATE TABLE stage_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL,          -- completed | failed
    config_json TEXT NOT NULL,     -- 完整执行配置
    inputs_json TEXT NOT NULL,     -- 输入数据
    outputs_json TEXT,             -- 输出数据 (失败时为 NULL)
    error TEXT,                    -- 错误信息
    duration_ms INTEGER,           -- 执行耗时
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(run_id, agent, version)
);
```

`config_json` 包含：
```json
{
  "model": "MiniMax-M2.5",
  "model_provider": "minimax",
  "prompt_template": "generate.j2",
  "prompt_override": null,
  "params": {"platform": "xiaohongshu", "format": "image_text", "temperature": 0.7}
}
```

### 2. Orchestrator 改造

在 `_wrap_agent()` 中，每个节点执行前后保存快照：

```python
async def node_fn(state):
    # 1. 提取 inputs（agent.consumes 对应的 state 字段）
    # 2. 构建 effective_config（合并 YAML + stage_overrides + model_override + prompt_override）
    # 3. 保存 "执行前" 快照 (inputs + config, status=running)
    # 4. 执行 agent.run()
    # 5. 保存 "执行后" 快照 (outputs, status=completed/failed, duration)
    # 6. 返回 outputs 合并到 state
```

快照存储需要访问 StateStore，orchestrator 构造时传入。

### 3. Agent 配置动态化

扩展 `StageConfig`：

```python
class StageConfig(BaseModel):
    agent: str
    config: dict = {}
    on_error: str = "halt"
    retry_count: int = 1
    # 新增
    model_override: str | None = None        # 覆盖此节点使用的模型名
    model_provider: str | None = None        # 覆盖模型提供商
    prompt_override: str | None = None       # 直接覆盖提示词（不走 Jinja2 模板）
```

在 orchestrator 的 `_wrap_agent()` 中：
- 如果 `stage.model_override` 有值，为该节点创建独立的 ModelAdapter
- 如果 `stage.prompt_override` 有值，注入到 agent 的 run 方法（通过 config 传递，agent 内部检查）

BaseAgent.run() 的 config 中新增可选字段 `_prompt_override`，agent 实现中检查此字段：有则直接用，无则走 load_prompt()。

### 4. CLI 新增命令

```
sp stage list <run_id>
    列出某次运行所有节点的快照（最新版本）
    输出：agent | version | status | duration | output_preview

sp stage show <run_id> <agent>
    查看某节点最新版本的完整快照
    输出：config + inputs + outputs（JSON）
    --version N  查看指定版本
    --field outputs.contents  只看某个字段

sp stage edit <run_id> <agent>
    编辑某节点输出，保存为新版本
    --set "outputs.contents.xiaohongshu.title=新标题"  设置字段值
    --file outputs.json  从文件加载完整输出
    --field outputs.contents.xiaohongshu.body  只编辑某字段（写入 stdin 或 --value）

sp stage rerun <run_id> <agent>
    从该节点开始级联重跑（该节点 + 所有后续节点）
    --config '{"count": 3}'  覆盖该节点的 config 参数
    --model "MiniMax-M2.7"  覆盖该节点的模型
    --prompt "你是一个..."  覆盖该节点的提示词
    --prompt-file prompt.txt  从文件读取提示词
    --only  只重跑此节点，不级联

sp stage history <run_id> <agent>
    查看某节点的所有版本历史
    输出：version | status | duration | created_at
```

**设计原则**：所有命令支持 `--format json`，让 agent 能结构化地读取和处理结果。

### 5. API 新增端点

```
GET  /api/runs/{run_id}/stages           — 列出快照
GET  /api/runs/{run_id}/stages/{agent}   — 查看快照详情 (?version=N)
PUT  /api/runs/{run_id}/stages/{agent}   — 编辑输出
POST /api/runs/{run_id}/stages/{agent}/rerun  — 重跑（支持 cascade/only）
GET  /api/runs/{run_id}/stages/{agent}/history — 版本历史
```

### 6. Web UI 增强

Run Detail 页面新增"节点详情"视图：
- 点击 PipelineProgress 中的某个节点 → 展开该节点面板
- 面板显示：配置、输入摘要、输出（可展开完整 JSON）、版本历史
- 输出区域可编辑（textarea 编辑 JSON）
- "重跑"按钮（可修改配置参数）
- 版本切换下拉

### 7. 重跑流程（级联模式）

```
用户调用: sp stage rerun <run_id> content_generator --config '{"style":"深度"}'

后端流程:
1. 从 stage_snapshots 读取 content_generator 的最新版本的 inputs
2. 合并新 config 到原 config
3. 执行 content_generator.run(inputs, new_config)
4. 保存新快照 (version+1)
5. 更新 pipeline state 中的 contents 字段
6. 识别后续节点: [reviewer, analyst]
7. 对每个后续节点:
   a. 从当前 state 构建 inputs（因为上游 outputs 已经变了）
   b. 用原始 config 执行
   c. 保存新快照
   d. 更新 state
8. 更新 run 的 state_json
```

## 不在此次范围

- 管道拓扑变更（加节点/删节点/改顺序）— 后续迭代
- 并行节点执行 — 后续迭代
- SSE 实时推送节点执行进度 — 后续迭代
- 图片生成工具集成 — 单独迭代

## 文件变更清单

### 后端新增/修改
- `server/src/storage/state_store.py` — 新增 stage_snapshots 表 CRUD
- `server/src/core/orchestrator.py` — 节点快照保存 + 动态模型/提示词
- `server/src/core/state.py` — StageConfig 新增 model_override/prompt_override 字段
- `server/src/agents/base.py` — BaseAgent 支持 _prompt_override
- `server/src/agents/*/agent.py` — 5 个 agent 支持 prompt_override
- `server/src/core/engine.py` — 新增 rerun_stage() 方法
- `server/src/api/routes/stages.py` — 新增 5 个端点
- `server/src/api/schemas.py` — 新增请求/响应模型
- `server/src/api/app.py` — 注册 stages router
- `server/src/cli/commands/stage.py` — 新增 sp stage 子命令
- `server/src/cli/app.py` — 注册 stage 子命令

### 前端修改
- `web/src/lib/api-client.ts` — 新增 stages API 方法
- `web/src/lib/types.ts` — 新增 StageSnapshot 类型
- `web/src/app/runs/[runId]/page.tsx` — 节点详情面板
- `web/src/components/runs/StageDetail.tsx` — 新增节点详情组件
