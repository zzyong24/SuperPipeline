# SuperPipeline Dark Factory 改进规格书

> 状态：规划中
> 目标：借鉴 Claude Code Dark Factory 全自动逻辑，打造真正无人值守的 Pipeline
> 参考：Claude Code 电子书 & AI 全自动开发系统实战（数字游牧人懒人包）

---

## 0. 核心理念对比

| Claude Code Dark Factory 理念 | SuperPipeline 当前状态 | 改进方向 |
|-------------------------------|----------------------|---------|
| **三不原则**：不让人写、不让人 review、不让人 test | reviewer 审核失败后停住等人 | 审核失败自动打回重写，有次数上限 |
| **干完一部分就记录日志** | 只在 agent 跑完才快照，无中间步骤 | 每完成子步骤写 progress.log |
| **progress.txt 实时可见** | 只能 pipeline 结束看结果 | 实时写 progress.log，用户随时 tail |
| **task.json 持久化任务** | pipeline 状态内存传递，断连丢失 | 任务文件化，可断点续跑 |
| **feedback loop 自愈** | reviewer 只标记失败，不反馈修复 | 验证失败 → 自动分析根因 → 修复 → 再验证 |
| **claude.md 上下文记忆** | 无跨 session 记忆机制 | 可选的 session context 文件 |

---

## 1. 实时进度日志系统（Progress Logger）

### 1.1 目标
每个 agent 的每个子步骤完成时立即写入日志文件，用户可以随时 `tail -f` 看到 pipeline 在哪个步骤卡住。

### 1.2 文件结构

```
outputs/{run_id}/
├── progress.log          # 实时进度日志（追加写入）
├── task.json             # 任务描述文件（pipeline 启动时生成）
├── state/                # 中间状态快照
│   ├── stage_{agent}_v{version}.json
│   └── final_state.json
└── content/              # 最终输出
    └── {platform}_content.json
```

### 1.3 progress.log 格式

```
[2026-04-17T14:30:01+08:00] [run_a1b2c3] [PENDING] pipeline_started | pipeline=douyin_image_text_v2
[2026-04-17T14:30:02+08:00] [run_a1b2c3] [RUNNING] agent_topic_generator | step=invoke
[2026-04-17T14:30:05+08:00] [run_a1b2c3] [RUNNING] agent_topic_generator | step=generate_topics | topics=5
[2026-04-17T14:30:06+08:00] [run_a1b2c3] [COMPLETED] agent_topic_generator | duration=4.2s | topics_count=5
[2026-04-17T14:30:07+08:00] [run_a1b2c3] [RUNNING] agent_document_synthesizer | step=invoke
[2026-04-17T14:30:12+08:00] [run_a1b2c3] [RUNNING] agent_document_synthesizer | step=extract_entities | count=23
[2026-04-17T14:30:15+08:00] [run_a1b2c3] [COMPLETED] agent_document_synthesizer | duration=8.1s | materials=12
[2026-04-17T14:30:16+08:00] [run_a1b2c3] [FAILED] agent_content_generator | step=validate | error=body_too_short (1850 < 2000)
[2026-04-17T14:30:17+08:00] [run_a1b2c3] [RETRY] agent_content_generator | attempt=1/3 | reason=body_too_short
[2026-04-17T14:30:22+08:00] [run_a1b2c3] [COMPLETED] agent_content_generator | attempt=2 | duration=5.0s | body_chars=2150
```

### 1.4 实现要求

**ProgressLogger 类：**
```python
class ProgressLogger:
    def __init__(self, run_id: str, output_dir: str = "outputs"):
        self.run_id = run_id
        self.log_path = Path(output_dir) / run_id / "progress.log"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, agent: str, status: str, step: str, **kwargs):
        """追加写入一行日志，status: PENDING/RUNNING/COMPLETED/FAILED/RETRY"""
        line = f"[{datetime.now().isoformat()}] [{self.run_id}] [{status}] {agent} | step={step}"
        if kwargs:
            detail = " | ".join(f"{k}={v}" for k, v in kwargs.items())
            line += f" | {detail}"
        with open(self.log_path, "a") as f:
            f.write(line + "\n")
```

**调用时机：**
- `engine.py` run_pipeline() 开始时写 `pipeline_started`
- `orchestrator.py` 每个 agent 调用前写 `RUNNING`
- agent 内部关键子步骤完成时写 `step=xxx`
- agent 完成时写 `COMPLETED` + duration
- 失败时写 `FAILED` + error
- 重试时写 `RETRY` + attempt count

### 1.5 用户体验

```bash
# 用户可以随时查看进度
tail -f outputs/run_a1b2c3/progress.log

# 或者查看当前卡在哪
tail -5 outputs/run_a1b2c3/progress.log
```

---

## 2. 审核失败自动重写机制（Auto-Retry）

### 2.1 目标
reviewer 审核失败时，不要停住等人，而是自动将失败原因反馈给 content_generator 重写，直到通过或达到重试上限。

### 2.2 流程对比

**改进前（当前）：**
```
content_generator → reviewer.validate() → 失败 → pipeline 暂停等人介入
```

**改进后（Dark Factory）：**
```
content_generator → reviewer.validate() → 失败 → 分析失败原因 → 打回 content_generator 重写 → 再审核
     ↑                                                                                              ↓
     ←←←←←←←←←←←←←←← 达到重试上限仍失败 → 记录 error + 标记 failed，pipeline 继续往下游走 ←←←←←←←←←←
```

### 2.3 配置项

```python
class ReviewConfig(BaseModel):
    rules: list[str] = Field(default_factory=list)
    min_score: float = 7.0
    # 新增：自动重试配置
    auto_retry: bool = Field(default=True, description="审核失败是否自动打回重写")
    max_retries: int = Field(default=3, description="最大重试次数")
    retry_on: list[str] = Field(
        default_factory=list,
        description="需要重试的错误类型，如 ['body_too_short', 'images_insufficient', 'has_emoji']"
    )
```

### 2.4 ReviewResult 扩展

```python
class ReviewResult(BaseModel):
    passed: bool
    score: float
    failures: list[FailureDetail] = Field(default_factory=list)
    # 新增：是否可重试
    retryable: bool = Field(default=False)
    retry_hint: str = Field(default="", description="给 content_generator 的修改建议")

class FailureDetail(BaseModel):
    rule: str
    severity: Literal["error", "warning"]
    message: str
    field: str = Field(default="", description="出问题的字段，如 body/image_paths/tags")
    current: str = Field(default="", description="当前值")
    expected: str = Field(default="", description="期望值")
```

### 2.5 重试循环实现（engine.py）

```python
async def _run_content_with_retry(
    self,
    agent: Agent,
    config: ReviewConfig,
    state: dict,
    review_result: ReviewResult,
    attempt: int = 1,
) -> dict:
    """审核失败时自动打回 content_generator 重写"""

    if not review_result.passed and config.auto_retry and attempt < config.max_retries:
        # 构建重试提示
        retry_prompt = self._build_retry_prompt(review_result)
        state["retry_context"] = {
            "attempt": attempt,
            "max_retries": config.max_retries,
            "failures": [f.dict() for f in review_result.failures],
            "hint": retry_prompt,
        }
        logger.log(agent.name, "RETRY", f"attempt={attempt}/{config.max_retries}", reason=review_result.failures[0].message if review_result.failures else "review_failed")

        # 重新调用 content_generator（注入重试上下文）
        new_state = await self._invoke_agent(agent, state)

        # 再次审核
        new_result = await self._run_reviewer(new_state, config)
        if new_result.passed:
            logger.log(agent.name, "COMPLETED", f"retry_passed_after_{attempt}", score=new_result.score)
            return new_state

        # 继续重试
        return await self._run_content_with_retry(
            agent, config, new_state, new_result, attempt + 1
        )

    # 达到上限或不可重试，记录最终状态
    if not review_result.passed:
        logger.log(agent.name, "FAILED", "max_retries_exceeded", score=review_result.score)
        state["_review_final_failure"] = review_result.dict()

    return state
```

### 2.6 重试提示示例（给 content_generator 的 hint）

```
你生成的内容在审核时被检测到以下问题，请针对性修改后重新生成：

失败项 1：
- 规则：body_min_length
- 问题：正文 1850 字，少于最低要求 2000 字
- 当前：1850 字
- 期望：>= 2000 字
- 修改建议：扩充内容，增加案例或分析深度

失败项 2：
- 规则：no_emoji
- 问题：检测到 emoji 表情符号 ❌✅⚠️
- 当前：包含 ❌✅⚠️💥
- 期望：不包含任何 emoji
- 修改建议：删除所有 emoji，用文字替代（如 ✓ → 可以，✗ → 不能）

失败项 3：
- 规则：images_min_count
- 问题：配图 2 张，少于最低要求 3 张
- 当前：2 张
- 期望：>= 3 张
- 修改建议：从 source_images 补充 1 张，或生成 1 张 AI 图片

请基于以上反馈重新生成内容，只修改有问题的部分，其他保持不变。
```

---

## 3. 任务文件持久化（Task File）

### 3.1 目标
pipeline 启动时将任务信息写入 `task.json`，agent 都从文件读取上下文而非仅靠内存传递。进程崩溃后可从 task.json 恢复。

### 3.2 task.json 格式

```json
{
  "task_id": "run_a1b2c3",
  "pipeline_name": "douyin_image_text_v2",
  "created_at": "2026-04-17T14:30:01+08:00",
  "user_brief": {
    "topic": "AI Agent 发展趋势",
    "keywords": ["Claude Code", "AutoGPT", "自主代理"],
    "platform_hints": ["douyin"],
    "source_documents": [
      {
        "path": "/Users/zyongzhu/Downloads/article.md",
        "title": "AI Agent 深度解析",
        "source_type": "local"
      }
    ]
  },
  "config": {
    "auto_retry": true,
    "max_retries": 3,
    "retry_on": ["body_too_short", "images_insufficient", "has_emoji"]
  },
  "current_stage": "agent_content_generator",
  "current_attempt": 2,
  "status": "running",
  "progress_log": "outputs/run_a1b2c3/progress.log"
}
```

### 3.3 实现要求

**pipeline 启动时：**
```python
# engine.py run_pipeline()
task_file = Path("outputs") / run_id / "task.json"
task_file.parent.mkdir(parents=True, exist_ok=True)
task_file.write_text(json.dumps({
    "task_id": run_id,
    "pipeline_name": pipeline_name,
    "created_at": datetime.now().isoformat(),
    "user_brief": user_brief.model_dump(),
    "config": pipeline_config.dict(),
    "status": "running",
}, ensure_ascii=False, indent=2))

# 顺便创建 progress.log 头
progress_logger = ProgressLogger(run_id, "outputs")
progress_logger.log("pipeline", "PENDING", "pipeline_started", pipeline=pipeline_name)
```

**pipeline 结束时：**
```python
# 更新 task.json status
task_file = Path("outputs") / run_id / "task.json"
data = json.loads(task_file.read_text())
data["status"] = final_status  # completed / failed / partially_completed
data["completed_at"] = datetime.now().isoformat()
task_file.write_text(json.dumps(data, indent=2))
```

**断点恢复（可选，后续实现）：**
```python
async def resume_pipeline(self, run_id: str):
    task_file = Path("outputs") / run_id / "task.json"
    if not task_file.exists():
        raise ValueError(f"Cannot resume: task.json not found for {run_id}")
    task = json.loads(task_file.read_text())
    # 从 task.json 恢复上下文，继续执行未完成的 stage
```

---

## 4. Feedback Loop 自愈机制（Self-Healing）

### 4.1 目标
validator（reviewer）发现错误后，不仅标记失败，还要分析根因并给出具体的修复方案。content_generator 收到修复方案后不是简单重写，而是知道**为什么错**和**怎么改**。

### 4.2 修复策略表

```python
REPAIR_STRATEGY: dict[str, dict] = {
    "body_too_short": {
        "field": "body",
        "action": "expand",
        "method": "add_examples_or_analysis",
        "min_delta_chars": 200,
    },
    "body_too_long": {
        "field": "body",
        "action": "compress",
        "method": "remove_redundancy",
        "max_delta_chars": -200,
    },
    "images_insufficient": {
        "field": "image_paths",
        "action": "add",
        "source": "prefer_source_images_then_ai",
        "count_delta": "+1 or +2",
    },
    "images_excessive": {
        "field": "image_paths",
        "action": "remove",
        "count_delta": "-1 to -3",
    },
    "has_emoji": {
        "field": "body",
        "action": "replace",
        "method": "emoji_to_text",
    },
    "tags_excessive": {
        "field": "tags",
        "action": "truncate",
        "max_count": 20,
    },
    "title_too_long": {
        "field": "title",
        "action": "truncate",
        "max_chars": 30,
    },
}
```

### 4.3 reviewer 的 retry_hint 生成

```python
def _build_retry_hint(self, result: ReviewResult) -> str:
    """根据失败项生成具体的修改提示"""
    hints = []
    for failure in result.failures:
        strategy = REPAIR_STRATEGY.get(failure.rule, {})
        if strategy:
            hint = self._format_hint(failure, strategy)
            hints.append(hint)
        else:
            # 未知规则，直接用 message
            hints.append(f"- {failure.message}")

    return "\n".join([
        "你生成的内容在审核时被检测到以下问题，请针对性修改：",
        *hints,
        "",
        "请基于以上反馈重新生成内容，只修改有问题的部分，其他保持不变。",
    ])
```

### 4.4 修复验证循环

```
content_generator 输出
       ↓
reviewer.validate()
       ↓
  ┌─→ 通过 → 继续下游
  │
  └─→ 失败 + retryable=True
            ↓
      分析根因 + 生成修复提示
            ↓
      打回 content_generator + 注入 retry_context
            ↓
      content_generator 基于修复提示重写
            ↓
      再次 reviewer.validate()
            ↓
      循环直到通过或达到上限
```

---

## 5. 可选的 Session Context 文件（claude.md 等效）

### 5.1 背景
Claude Code 的 `claude.md` 用来在项目目录下存放项目特定的偏好和规则，让每次启动都能继承上下文。

### 5.2 设计决策

> **本版本不实现**（复杂度高，优先级低）
>
> 理由：SuperPipeline 是 server 模式，每次 pipeline 运行是独立的，不存在"下次对话继续这个项目"的需求。如果未来需要跨 pipeline 的上下文共享，可以通过 `source_documents` 注入，而不是文件机制。
>
> 标记为 `future: v2.x`

---

## 6. Edge Node 决策分支（Condition Router）

### 6.1 目标
参考 Claude Code 的 Edge Node 模式，在关键节点增加条件分支，让 pipeline 可以根据状态走不同路径。

### 6.2 应用场景

```
topic_generator
      ↓
  ┌──→ 有 3 个以上 topics → 继续
  │
  └──→ 只有 0-2 个 topics → 降级为 manual 模式（跳过 document_synthesizer）

content_generator
      ↓
  ┌──→ reviewer 通过 → 继续 analyst
  │
  └──→ reviewer 失败（不可重试）→ 跳过 analyst，标记 partial_complete

material_collector
      ↓
  ┌──→ 有 source_documents + synthesized_materials → 跳过 web 搜索
  │
  └──→ 没有文档 → 正常 web 搜索
```

### 6.3 实现方式

在 `engine.py` 的 stage 循环中增加条件判断：

```python
async def _should_skip_stage(self, stage: Stage, state: dict) -> tuple[bool, str]:
    """判断是否跳过当前 stage，返回 (skip, reason)"""
    agent_name = stage.agent

    if agent_name == "document_synthesizer":
        if not state.get("source_documents"):
            return True, "no_source_documents"

    if agent_name == "material_collector":
        if state.get("synthesized_materials") and len(state["synthesized_materials"]) >= 5:
            return True, "sufficient_materials_from_documents"

    if agent_name == "image_extractor":
        if not state.get("source_documents"):
            return True, "no_source_documents"

    return False, ""
```

---

## 7. 错误日志详细化（Error Log）

### 7.1 目标
当前 StateStore 只存最后一条 error。Dark Factory 要求每次错误都要记录，包括：发生了什么、尝试了什么修复、结果如何。

### 7.2 错误日志格式（追加到 progress.log）

```
[2026-04-17T14:30:16+08:00] [run_a1b2c3] [ERROR] agent_content_generator | error=ValidationError
    rule=body_min_length
    message=正文 1850 字，少于最低要求 2000 字
    field=body
    current=1850
    expected=2000
[2026-04-17T14:30:17+08:00] [run_a1b2c3] [RETRY_ATTEMPT] agent_content_generator | attempt=1/3
    planned_fix=expand_body
    method=add_examples_or_analysis
    target_chars=2200
[2026-04-17T14:30:22+08:00] [run_a1b2c3] [RETRY_RESULT] agent_content_generator | attempt=1
    success=false
    new_chars=1920
    still_failing=[body_too_short]
[2026-04-17T14:30:23+08:00] [run_a1b2c3] [RETRY_ATTEMPT] agent_content_generator | attempt=2/3
    planned_fix=expand_body_with_deeper_analysis
    method=add_case_study
    target_chars=2300
[2026-04-17T14:30:28+08:00] [run_a1b2c3] [COMPLETED] agent_content_generator | attempt=2
    success=true
    final_chars=2180
    review_score=8.5
```

### 7.3 实现要求

`ProgressLogger.log()` 支持多行错误：

```python
def log_error(self, agent: str, error_type: str, error_details: dict):
    """记录错误，包含详细信息"""
    lines = [f"[{self._ts}] [{self.run_id}] [ERROR] {agent} | error={error_type}"]
    for k, v in error_details.items():
        lines.append(f"    {k}={v}")
    with open(self.log_path, "a") as f:
        f.write("\n".join(lines) + "\n")
```

---

## 8. 实施顺序

### Phase 1：Progress Logger（优先级 P0）
1. 创建 `src/core/progress_logger.py`
2. `engine.py` 导入并初始化 ProgressLogger
3. 在 pipeline 启动、agent 开始/完成/失败时调用 `log()`
4. 验证：运行一个 pipeline，`tail -f outputs/{run_id}/progress.log` 能看到实时输出

### Phase 2：Task File（优先级 P0）
1. pipeline 启动时生成 `task.json`
2. pipeline 结束时更新 `status`
3. 验证：`cat outputs/{run_id}/task.json` 能看到完整任务信息

### Phase 3：Auto-Retry（优先级 P1）
1. 扩展 `ReviewResult` 增加 `retryable` 和 `retry_hint`
2. 修改 `ReviewConfig` 增加 `auto_retry` 和 `max_retries`
3. 在 `engine.py` 实现 `_run_content_with_retry()` 循环
4. 验证：故意让 content_generator 生成过短内容，触发自动重写

### Phase 4：Retry Hint 生成（优先级 P1）
1. 实现 `REPAIR_STRATEGY` 字典
2. `reviewer.py` 增加 `_build_retry_hint()` 方法
3. 验证：看 progress.log 里 retry hint 是否具体

### Phase 5：Edge Node 条件分支（优先级 P2）
1. 实现 `_should_skip_stage()` 判断逻辑
2. 验证：没有 source_documents 时 document_synthesizer 被跳过

### Phase 6：错误日志详细化（优先级 P2）
1. `ProgressLogger.log_error()` 实现
2. auto_retry 循环中记录每次 retry attempt
3. 验证：progress.log 能看到完整的 retry 轨迹

---

## 9. 验收标准

### Phase 1 验收
- [ ] 运行 pipeline 时，progress.log 实时写入
- [ ] 能用 `tail -f` 看到每一步的状态变化
- [ ] pipeline 结束后，能看到完整的执行轨迹

### Phase 2 验收
- [ ] `outputs/{run_id}/task.json` 在 pipeline 启动时创建
- [ ] 包含 user_brief、pipeline_name、created_at
- [ ] pipeline 结束时 status 正确更新

### Phase 3 验收
- [ ] reviewer 失败时自动触发重试（不暂停）
- [ ] 重试次数不超过 max_retries
- [ ] progress.log 显示 `RETRY` 状态

### Phase 4 验收
- [ ] retry_hint 包含具体的修改建议（不只是"失败"）
- [ ] 能根据不同失败类型生成不同提示
- [ ] content_generator 能根据 hint 有效修改

### Phase 5 验收
- [ ] 无 source_documents 时 document_synthesizer 被跳过
- [ ] 无 source_documents 时 image_extractor 被跳过
- [ ] 有足够 synthesized_materials 时 material_collector 被跳过

### Phase 6 验收
- [ ] progress.log 记录每次 ERROR 的详细信息
- [ ] 能看到完整的 retry 轨迹（attempt 1 → 2 → 3）
- [ ] 最终状态（COMPLETED/FAILED）包含最终结果

---

## 10. 不做的事

- 不改动 LangGraph 图结构（仍然是线性 pipeline + 内部循环）
- 不引入向量数据库或 embedding search
- 不实现跨 pipeline 的 session context 文件（claude.md 等效）
- 不改变现有 agent 的核心 prompt 逻辑（只扩展配置项）

---

## 11. 相关文件清单

需要改动或新增的文件：

```
server/src/core/
├── progress_logger.py     [新增] 实时进度日志
└── engine.py              [改动] 集成 ProgressLogger + Auto-Retry 循环

server/src/agents/reviewer/
├── schemas.py             [改动] ReviewResult 增加 retryable/retry_hint
├── config.py             [改动] ReviewConfig 增加 auto_retry/max_retries
├── reviewer.py           [改动] 实现 _build_retry_hint()
└── prompts/
    └── review.j2         [改动] 输出 retry_hint

server/src/storage/
└── state_store.py         [可选改动] 增加 error_log 表（如果需要单独查询）

tests/
├── test_progress_logger.py [新增]
└── test_auto_retry.py      [新增]
```
