# SuperPipeline — 全媒体内容生产管线设计文档

> 日期：2026-04-15
> 状态：Approved
> 作者：MoonlitClear + Claude

## 1. 项目定位

将选题、素材、生成、编辑、审核、分发、复盘全流程自动化的多 Agent 内容生产系统。

**核心原则**：一次配置、批量产出、全链路可控、多平台分发。

**MVP 范围**：图文内容（个人使用），覆盖完整生产链路。视频和多用户后续扩展。

## 2. 核心决策记录

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 架构模式 | Hub-Spoke 调度器 | 支持多平台并行生成、Agent 独立可测、YAML 配置扩展 |
| Agent 通信 | LangGraph State 驱动 | 原生数据驱动，无需额外 Event Bus 抽象层 |
| 编排框架 | LangGraph | 图编排、状态机、断点续跑、subgraph 原生支持 |
| 技术栈 | Python | AI SDK 生态成熟，开发效率高 |
| 文本/图片模型 | MiniMax（可插拔） | 当前可用，后续通过 Adapter 模式切换 |
| 数据存储 | SQLite + 本地文件 | MVP 轻量，元数据用 SQLite，内容资产用文件 |
| 内容类型 | 参数化（prompt/skill 控制） | 管道是引擎，类型是配方，不硬编码 |
| 触发方式 | 渐进式（MVP 手动触发） | 架构预留调度接口，后续可接 cron/事件驱动 |
| 发布方式 | 手动发布 | 防封控，审核由 Agent 自动完成，发布人工操作 |
| 目标平台 | X、小红书、抖音、B站 | 主流平台，通过平台适配层扩展 |
| 主接口 | CLI（Agent 调用） | 远程 Agent 通过 CLI 驱动管道，性能好、可编排 |
| Web UI | 轻量只读工作台 | 看状态、复制内容、手动分发，不做重交互 |

## 3. 系统架构

### 3.1 协作模式

```
远程电脑 (Agent)                     服务器                        办公电脑/手机
┌──────────────┐    CLI/Skills    ┌─────────────────┐    Web UI    ┌────────────┐
│ Claude Code  │ ──────────────▶ │  SuperPipeline  │ ◀─────────── │  浏览器     │
│ Agent        │  SSH + CLI      │  Server         │   HTTP       │  看状态     │
│              │                 │                 │              │  复制内容   │
└──────────────┘                 └─────────────────┘              │  手动分发   │
  主接口：CLI                      Core + API + DB                └────────────┘
  全自动编排                                                       辅助接口：Web
```

### 3.2 分层架构

```
┌─────────────────────────────────────┐
│  CLI (主接口，Agent 调用)            │
│  sp run / sp status / sp content    │
├─────────────────────────────────────┤
│  Web UI (辅助，人工查看)             │
│  状态监控 / 内容复制 / 手动分发      │
└──────────┬──────────────────────────┘
           │ HTTP REST + SSE (状态推送)
┌──────────▼──────────────────────────┐
│  API Layer (FastAPI)                │
│  CLI 和 Web 共用同一套 API           │
└──────────┬──────────────────────────┘
           │
┌──────────▼──────────────────────────┐
│  Core Engine                        │
│  Orchestrator (LangGraph)           │
│  Registry / State / Models          │
└──────────┬──────────────────────────┘
           │
┌──────────▼──────────────────────────┐
│  Agents (可插拔模块)                 │
│  选题 / 素材 / 生成 / 审核 / 复盘    │
└──────────┬──────────────────────────┘
           │
┌──────────▼──────────────────────────┐
│  Infrastructure                     │
│  Storage / Model Adapters           │
└─────────────────────────────────────┘
```

**CLI 是一等公民**：所有操作都能通过 CLI 完成，远程 Agent 通过 SSH + CLI 驱动整个管道。
**Web UI 是只读窗口**：给人看的，不做复杂交互。

### 3.3 Agent 通信模式

Agent 之间通过 LangGraph 的 State 解耦，不直接调用：

- 每个 Agent 声明 `consumes`（从 State 读什么）和 `produces`（往 State 写什么）
- Orchestrator 根据 YAML 配置决定流转顺序
- Agent 之间零依赖——移除任何一个 Agent，其他 Agent 不受影响

### 3.4 MVP 管道流程

```
用户输入 Brief
       │
       ▼
  选题 Agent ── 生成候选选题，自动或人工选中一个
       │
       ▼
  素材 Agent ── 联网搜索 + 本地知识库采集素材
       │
       ▼
  生成 Agent ── 按平台规范生成图文（可并行多平台）
       │
       ▼
  审核 Agent ── 质量评分 + 平台合规检查
       │
       ▼
  待发布队列 ── 人工确认发布
       │
       ▼
  复盘 Agent ── 分析数据、生成改进建议
```

## 4. 项目结构

```
SuperPipeline/
├── docs/                          # 文档
│   ├── architecture.md            # 架构总览
│   ├── agent-dev-guide.md         # 如何写一个新 Agent
│   └── superpowers/specs/         # 设计文档
│
├── server/                        # Python 后端
│   ├── src/
│   │   ├── core/                  # 核心引擎（稳定层）
│   │   │   ├── orchestrator.py    # LangGraph 图构建器
│   │   │   ├── state.py           # PipelineState 定义
│   │   │   ├── registry.py        # Agent 注册表
│   │   │   ├── models.py          # 模型适配器
│   │   │   └── config.py          # 全局配置加载
│   │   │
│   │   ├── agents/                # Agent 模块（每个一个目录）
│   │   │   ├── base.py            # BaseAgent 抽象类
│   │   │   ├── topic_generator/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── agent.py
│   │   │   │   ├── prompts/
│   │   │   │   ├── schemas.py
│   │   │   │   └── README.md
│   │   │   ├── material_collector/
│   │   │   ├── content_generator/
│   │   │   ├── reviewer/
│   │   │   └── analyst/
│   │   │
│   │   ├── platforms/             # 平台适配层
│   │   │   ├── base.py
│   │   │   ├── xiaohongshu.py
│   │   │   ├── x_twitter.py
│   │   │   ├── douyin.py
│   │   │   └── bilibili.py
│   │   │
│   │   ├── cli/                   # CLI 主接口（Agent 调用入口）
│   │   │   ├── app.py             # Click/Typer 入口
│   │   │   ├── commands/
│   │   │   │   ├── run.py         # sp run <pipeline> --brief "..."
│   │   │   │   ├── status.py      # sp status [run_id]
│   │   │   │   ├── content.py     # sp content list / get / approve
│   │   │   │   ├── agent.py       # sp agent list / run <agent>
│   │   │   │   └── pipeline.py    # sp pipeline list / show
│   │   │   └── formatters.py      # 输出格式化（JSON / table / plain）
│   │   │
│   │   ├── api/                   # FastAPI（Web UI 的后端）
│   │   │   ├── app.py
│   │   │   ├── routes/
│   │   │   │   ├── pipelines.py
│   │   │   │   ├── contents.py
│   │   │   │   └── assets.py
│   │   │   ├── sse.py             # SSE 管道状态推送（比 WS 轻量）
│   │   │   └── schemas.py
│   │   │
│   │   └── storage/               # 存储层
│   │       ├── state_store.py
│   │       ├── asset_store.py
│   │       └── models.py
│   │
│   ├── pipelines/                 # 管道配置（YAML）
│   │   ├── xiaohongshu_image_text.yaml
│   │   ├── x_thread.yaml
│   │   └── bilibili_article.yaml
│   │
│   ├── prompts/                   # 全局 prompt 库
│   │   ├── styles/
│   │   └── platforms/
│   │
│   ├── tests/
│   │   ├── agents/
│   │   └── integration/
│   │
│   ├── config.yaml
│   └── pyproject.toml
│
├── web/                           # Next.js 轻量 UI（只读为主）
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # 仪表盘（运行概览）
│   │   │   ├── runs/
│   │   │   │   └── [runId]/
│   │   │   │       └── page.tsx   # 管道状态可视化
│   │   │   └── contents/
│   │   │       └── page.tsx       # 内容列表 + 复制 + 标记已发布
│   │   ├── components/
│   │   │   ├── PipelineGraph.tsx   # 管道流程图（节点状态）
│   │   │   ├── ContentCard.tsx     # 内容卡片（预览 + 一键复制）
│   │   │   └── RunList.tsx         # 运行列表
│   │   └── lib/
│   │       ├── api-client.ts
│   │       └── types.ts
│   ├── package.json
│   └── next.config.ts
│
├── data/                          # 运行时数据（.gitignore）
│   ├── assets/
│   ├── outputs/
│   └── superpipeline.db
│
└── README.md
```

## 5. 核心接口设计

### 5.1 PipelineState（数据契约）

```python
class PipelineState(TypedDict):
    # 运行标识
    run_id: str
    pipeline_config: PipelineConfig
    user_brief: UserBrief

    # 选题阶段
    topics: list[Topic]
    selected_topic: Optional[Topic]

    # 素材阶段
    materials: list[Material]

    # 生成阶段（按平台分）
    contents: dict[str, PlatformContent]

    # 审核阶段
    reviews: dict[str, ReviewResult]

    # 复盘阶段
    analysis: Optional[Analysis]

    # 流转控制
    stage: str
    errors: list[PipelineError]
    metadata: dict
```

### 5.2 BaseAgent（Agent 标准接口）

```python
class BaseAgent(ABC):
    name: str
    consumes: list[str]            # 从 State 读哪些字段
    produces: list[str]            # 往 State 写哪些字段
    config_schema: type[BaseModel] # 配置 Schema

    @abstractmethod
    async def run(self, inputs: dict, config: BaseModel) -> dict:
        """
        inputs: 从 State 中按 consumes 提取的字段
        config: 从 YAML 加载的运行时配置
        return: 要写回 State 的字段（对应 produces）
        """

    def validate_inputs(self, state: PipelineState) -> bool:
        """自动校验 consumes 字段是否在 State 中且非空"""

    def validate_outputs(self, outputs: dict) -> bool:
        """自动校验 outputs 是否符合 produces 声明"""
```

### 5.3 Agent 注册与发现

```python
@register_agent
class TopicGeneratorAgent(BaseAgent):
    name = "topic_generator"
    consumes = ["user_brief"]
    produces = ["topics"]
    config_schema = TopicGenConfig

    async def run(self, inputs, config):
        brief = inputs["user_brief"]
        prompt = self.load_prompt("generate.j2", brief=brief, **config.dict())
        response = await self.model.generate(prompt)
        return {"topics": self.parse_topics(response)}
```

新增 Agent = 写一个模块 + 注册 + YAML 里加一行。不改 Orchestrator 代码。

### 5.4 模型适配器

```python
class ModelAdapter(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """文本生成"""

    @abstractmethod
    async def generate_image(self, prompt: str, **kwargs) -> bytes:
        """图片生成"""

class MiniMaxAdapter(ModelAdapter):
    """当前默认"""

class OpenAICompatibleAdapter(ModelAdapter):
    """兼容 OpenAI 接口的模型（后续扩展）"""
```

模型配置：

```yaml
models:
  text:
    provider: minimax
    api_key: ${MINIMAX_API_KEY}
    model: abab6.5-chat
  image:
    provider: minimax
    api_key: ${MINIMAX_API_KEY}
    model: abab6.5-image
```

换模型 = 改 YAML + 写一个 Adapter 类。

### 5.5 Orchestrator（动态图构建）

```python
class Orchestrator:
    def build_graph(self, pipeline_config: PipelineConfig) -> StateGraph:
        graph = StateGraph(PipelineState)

        for stage in pipeline_config.stages:
            agent = self.registry.get(stage.agent)
            graph.add_node(stage.agent, self._wrap_agent(agent, stage.config))

        self._build_edges(graph, pipeline_config)
        return graph.compile(checkpointer=self.checkpointer)
```

Orchestrator 不知道任何具体 Agent 的存在。它只认识注册表和 YAML。

### 5.6 Pipeline YAML 配置

```yaml
name: 小红书图文
description: 生成小红书种草图文内容
platforms: [xiaohongshu]

stages:
  - agent: topic_generator
    config:
      style: "种草"
      count: 5
  - agent: material_collector
    config:
      sources: ["web", "local_kb"]
  - agent: content_generator
    config:
      platform: xiaohongshu
      format: image_text
  - agent: reviewer
    config:
      rules: ["platform_compliance", "quality_score"]
      min_score: 7.0
  - agent: analyst
    config:
      trigger: after_publish
      metrics: ["engagement", "reach"]
```

### 5.7 Core 层函数接口（CLI / API / 小程序通用）

```python
async def run_pipeline(config_name: str, brief: UserBrief) -> str:
    """触发管道，返回 run_id"""

async def get_run_status(run_id: str) -> RunStatus:
    """查询运行状态和当前阶段"""

async def get_run_outputs(run_id: str) -> dict[str, PlatformContent]:
    """获取生成的内容"""

async def approve_content(run_id: str, platform: str) -> bool:
    """标记内容为已发布，触发复盘"""
```

## 6. 平台适配层

```python
class BasePlatform(ABC):
    name: str
    max_text_length: int
    image_specs: ImageSpec          # 尺寸、格式、数量限制
    tag_rules: TagRules             # 标签/话题规范
    content_rules: list[str]        # 平台禁忌/合规规则

    @abstractmethod
    def format_content(self, raw_content: str) -> str:
        """按平台规范格式化内容"""

    @abstractmethod
    def validate(self, content: PlatformContent) -> list[str]:
        """校验是否符合平台规范，返回问题列表"""
```

平台规范以配置 + 代码双重定义。审核 Agent 调用 `platform.validate()` 做合规检查。

## 7. 存储设计

### SQLite（元数据 + 状态）

- `pipeline_runs`: 运行记录（run_id, config, status, timestamps）
- `contents`: 内容记录（run_id, platform, content, review_score, publish_status）
- `analytics`: 复盘数据（content_id, metrics, insights）

### 文件系统（内容资产）

```
data/
├── assets/{run_id}/           # 素材文件
├── outputs/{run_id}/          # 生成内容（文本 + 图片）
└── superpipeline.db
```

## 8. CLI 接口设计（主接口）

CLI 是整个系统的主操作接口，远程 Agent 通过 SSH + CLI 驱动管道。

### 8.1 命令结构

```bash
sp run <pipeline> --brief "主题描述"    # 触发管道，返回 run_id
sp run <pipeline> --brief-file brief.json  # 从文件读取 brief

sp status                               # 列出所有运行（最近 20 条）
sp status <run_id>                      # 查看单次运行详情（各阶段状态）
sp status <run_id> --stage <agent>      # 查看某阶段的输入/输出

sp content list                         # 列出待发布内容
sp content list --status approved       # 按状态过滤
sp content get <content_id>             # 获取内容详情（文本 + 图片路径）
sp content get <content_id> --copy      # 输出纯文本（方便管道传递）
sp content approve <content_id>         # 标记已发布，触发复盘

sp agent list                           # 列出所有已注册 Agent
sp agent run <agent> --input input.json # 单独运行某个 Agent（调试用）

sp pipeline list                        # 列出所有管道配置
sp pipeline show <name>                 # 查看管道配置详情
```

### 8.2 输出格式

所有命令支持 `--format` 参数，默认 table，Agent 调用时用 json：

```bash
sp status --format json                 # JSON 输出，Agent 解析友好
sp status --format table                # 人类可读表格（默认）
sp content get <id> --format json       # 结构化输出，含所有字段
```

### 8.3 Agent 调用示例

远程 Agent 的典型调用流程：

```bash
# 1. 触发管道
RUN_ID=$(sp run xiaohongshu_image_text --brief "AI 编程工具测评" --format json | jq -r '.run_id')

# 2. 等待完成（轮询或阻塞）
sp status $RUN_ID --wait                # 阻塞直到完成或失败

# 3. 获取生成的内容
sp content list --run $RUN_ID --format json

# 4. 发布后标记
sp content approve <content_id> --publish-url "https://..."
```

### 8.4 退出码约定

- 0: 成功
- 1: 一般错误
- 2: 参数错误
- 3: 管道运行失败（部分 Agent 失败）
- 4: 资源不存在

Agent 可通过退出码判断是否需要重试或告警。

## 9. Web UI 设计（轻量辅助）

Web UI 定位：**给人看的只读窗口**，方便手机/电脑上查看状态和复制内容去发布。

### 9.1 技术栈

- Next.js（App Router），与 MoonOS 技术栈统一
- SSE 替代 WebSocket（更轻量，单向推送够用）

### 9.2 三个页面

**① 仪表盘（/）**
- 最近运行列表 + 状态标签
- 待发布内容数量

**② 管道状态（/runs/[runId]）**
- 管道流程图：节点链 + 状态指示灯（SSE 实时更新）
- 点击节点看该阶段输出摘要
- 错误信息展示

**③ 内容列表（/contents）**
- 按平台 + 状态过滤
- 内容预览卡片
- **一键复制**按钮（复制文本到剪贴板）
- 标记已发布按钮

## 10. 错误处理策略

- Agent 级别：每个 Agent 的错误写入 `state.errors`，不中断管道
- 管道级别：可配置 `on_error: skip | retry | halt`
- 重试：Agent 级别可配置重试次数和退避策略
- 断点续跑：LangGraph checkpointer 支持从失败点恢复

## 11. 扩展路径

| 阶段 | 新增内容 | 改动范围 |
|------|---------|---------|
| 加新平台 | `platforms/` 加一个文件 + YAML | 不改 core |
| 加新 Agent | `agents/` 加一个目录 + YAML | 不改 core |
| 换模型 | `core/models.py` 加 Adapter + 改 config | 不改 agents |
| 加 API 层 | `api/` 目录，调 core 函数 | 不改 core/agents |
| 加视频 | 新 Agent + 新 Pipeline YAML | 不改已有模块 |
| 全自动调度 | 加 scheduler 模块，调 core 函数 | 不改 core/agents |

## 12. MVP 交付物

1. 核心引擎：Orchestrator + Registry + State + ModelAdapter
2. 5 个 Agent：选题、素材、生成、审核、复盘
3. 2 个平台适配：小红书 + X
4. 1 个 Pipeline YAML：小红书图文
5. CLI 完整接口：`sp` 命令，支持 JSON 输出，Agent 可编排
6. API 层：FastAPI REST + SSE 状态推送
7. Web UI：轻量 Next.js（状态查看 + 内容复制 + 标记发布）
8. 文档：架构文档 + Agent 开发指南 + CLI 使用文档
9. 测试：每个 Agent 独立测试 + 一个端到端测试
