# SuperPipeline 进化规格书 — source_documents + document_synthesizer + 审核自纠正闭环

> 状态：已实现（审核闭环）
> 目标：解决 material_collector 胡编 + content_generator 图片全靠 AI 生成的问题 + 审核自纠正闭环

---

## 0. 背景与问题

### 问题 1：material_collector 胡编素材
- **现象**：用户喂入文章后，material_collector 完全忽略，自己去 web 搜索并编造假来源
- **根因**：material_collector 的 prompt 只接收 `selected_topic`，从不看 UserBrief 里的 `topic` 字段是否有原始文档；web search 无文档约束必然发散
- **影响**：内容基于假素材写成，完全不可用

### 问题 2：图片全靠 AI 生成，质量差
- **现象**：所有图片都是 image_prompts → MiniMax 生成，效果不稳定
- **根因**：content_generator 不知道源文档里有真实图片，无法选择是否复用
- **影响**：生成的图信息量低，风格和内容不匹配

### 问题 3：素材和内容生成割裂
- 素材阶段（material_collector）和内容阶段（content_generator）没有关联：素材是素材，内容是内容，AI 只是在 prompt 里拼接，没有真正"基于文档重新组织关联"

### 问题 4：审核不严格，形同虚设
- **现象**：抖音要求 2000 字 + 3张图，审核没检查；AI 生成内容带 emoji 表情包，一眼假
- **根因**：douyin.validate() 只有上限检查没有下限；审核结果不反馈给 content_generator
- **影响**：内容永远达不到发布标准，审核变成走过场

---

## 1. 审核规则（抖音硬性条件）

### 1.1 douyin.validate() 硬性检查

```python
# 硬性下限（标红项，任意一项不满足 → 审核失败）
- 正文不得少于 2000 字
- 配图不得少于 3 张

# 软性上限
- 正文不超过 2200 字（警告）
- 标签不超过 20 个（警告）
- 配图不超过 9 张（警告）
```

### 1.2 审核风格规则（get_rules_prompt）
- 禁止使用 emoji 表情包、❌✅⚠️💥🔥 等符号
- 内容要像真人写的，不要像 AI 批量生成
- 所有配图必须是真实图片，不接受全 AI 生成图

---

## 1. State Schema 改动

### 1.1 UserBrief — 新增 `source_documents` 字段

```python
class UserBrief(BaseModel):
    topic: str = Field(description="Main topic or theme")
    keywords: list[str] = Field(default_factory=list)
    platform_hints: list[str] = Field(default_factory=list)
    style: str = Field(default="")
    extra: dict = Field(default_factory=dict)
    # 新增
    source_documents: list[SourceDocument] = Field(
        default_factory=list,
        description="原始文档：本地文件路径 + 内容"
    )
```

### 1.2 SourceDocument — 新数据模型

```python
class SourceDocument(BaseModel):
    """随 UserBrief 一起传入的原始文档"""
    path: str = Field(description="文件路径或 URL")
    content: str = Field(description="文档正文（已提取）")
    title: str = Field(default="")
    source_type: Literal["local", "url", "article"] = Field(default="local")
    # 从文档中提取的图片
    images: list[ExtractedImage] = Field(default_factory=list)


class ExtractedImage(BaseModel):
    """从文档中提取的真实图片"""
    url: str = Field(description="图片 URL 或本地路径")
    alt: str = Field(default="", description="图片描述/alt text")
    caption: str = Field(default="", description="图片标题/来源说明")
    source_node: str = Field(
        default="",
        description="来源节点 ID（graphify 知识图谱节点标识），用于追溯"
    )
```

### 1.3 Material — 扩展 `source_type`

```python
class Material(BaseModel):
    source: str
    title: str = ""
    snippet: str = ""
    # 原来: web | local_kb | manual
    # 新增: document (来自 source_documents 的 AI 再组织结果)
    source_type: Literal["web", "local_kb", "manual", "document"] = "web"
    # document 来源时，标注来源文档路径
    document_path: str = Field(default="", description="来源文档路径")
    # graphify 节点 ID（如果是从知识图谱关联得出）
    source_node: str = Field(default="")
```

### 1.4 PipelineState — 新增字段

```python
class PipelineState(TypedDict, total=False):
    # ... 现有字段 ...

    # 新增：原始文档（Engine 注入，从 UserBrief.source_documents 来）
    source_documents: list[dict]  # serialized list[SourceDocument]

    # 新增：文档综合结果（document_synthesizer 输出）
    synthesized_materials: list[dict]  # serialized list[Material], source_type="document"

    # 新增：从文档提取的真实图片
    source_images: list[dict]  # serialized list[ExtractedImage]
```

### 1.5 PlatformContent — 扩展 `image_paths` 语义

```python
class PlatformContent(BaseModel):
    platform: str
    title: str
    body: str
    tags: list[str] = Field(default_factory=list)
    image_paths: list[str] = Field(
        default_factory=list,
        description="图片路径列表"
    )
    # image_paths 中的每张图必须标注来源类型
    image_sources: list[ImageSource] = Field(
        default_factory=list,
        description="与 image_paths 一一对应，标注每张图的来源"
    )
    image_prompts: list[str] = Field(
        default_factory=list,
        description="AI 生成图片的 prompt（仅当没有合适真实图片时使用）"
    )
    # 创作过程中自己生成的图片（架构图 / canvas 等 skill 生成）
    inline_images: list[InlineImage] = Field(
        default_factory=list,
        description="内容创作过程中 AI 自建的图片（SVG截图、canvas截图等）"
    )


class ImageSource(BaseModel):
    """标注 image_paths 中每张图的来源"""
    path: str = Field(description="图片路径/URL，与 image_paths 对应")
    type: Literal[
        "real_document",     # 文档自带图片
        "real_extracted",     # 从文档图片分析提取
        "ai_generated",       # MiniMax 文生图
        "skill_screenshot",   # AI 用 skill 造的图（架构图/canvas等）截图
    ] = Field(description="图片来源类型")
    source: str = Field(
        default="",
        description="来源描述，如文档路径、URL、'MiniMax image-01'、'architecture-diagram skill' 等"
    )
    caption: str = Field(default="", description="图片说明（用于图文正文）")
    # skill_screenshot 专用
    skill_used: str = Field(
        default="",
        description="使用的 skill 名称，如 'architecture-diagram'、'obsidian-canvas'、'excalidraw-diagram'"
    )


class InlineImage(BaseModel):
    """AI 在内容创作过程中自建的图片（用 skill 生成后截图）"""
    skill: str = Field(
        description="使用的 skill 名称"
    )
    prompt: str = Field(
        description="传递给 skill 的 prompt/指令内容"
    )
    screenshot_path: str = Field(
        description="截图保存路径（相对于 outputs 目录）"
    )
    caption: str = Field(default="", description="图片说明")
    # 生成时机描述：AI 在写哪部分内容时决定创建这张图
    context: str = Field(
        default="",
        description="创建时机，如 '写到核心循环对比时决定插一张流程图'"
    )
```

---

## 2. Agent 改动

### 2.1 document_synthesizer（新增）

**定位**：读取 source_documents，对文档内容做深度理解 + 跨文档关联，输出结构化 Material 列表。

**consumes**: `["selected_topic", "source_documents"]`
**produces**: `["synthesized_materials"]`
**config**:

```python
class DocumentSynthesizerConfig(BaseModel):
    temperature: float = 0.3  # 偏低，更依赖文档内容而非发散
    max_materials: int = 10
    # 是否启用 graphify 知识图谱辅助关联
    use_graph: bool = True
    # graphify 图谱路径（可选）
    graph_path: str = "graphify-out/graph.json"
```

**prompt 策略**：
- 不是简单的 RAG retrieval，是 AI 主动理解文档结构
- 提取关键实体、时间线、因果关系
- 识别文档间的矛盾点和共性
- 生成的 Material.snippet 是 AI 重新组织的，不是原文复制

**输出示例**：

```json
{
  "source_type": "document",
  "document_path": "/path/to/article.md",
  "source_node": "hermes_agent_self_evolution_repo",  // graphify 节点 ID
  "title": "Evolver 核心循环 vs Hermes 核心循环对比",
  "snippet": "Evolver 的核心循环是 Scan→Select→Mutate→Validate→Solidify...（AI 重新组织）",
  "source": "/path/to/article.md"
}
```

### 2.2 material_collector — 降级为 fallback

**改动**：新增 `mode` 配置项

```python
class MaterialCollectConfig(BaseModel):
    sources: list[str] = Field(default=["web"])
    max_items: int = 8
    temperature: float = 0.7
    # 新增
    mode: Literal["always_web", "web_if_no_documents"] = "web_if_no_documents"
```

**行为**：
- `mode="web_if_no_documents"`：如果 PipelineState 中存在 `source_documents`，跳过 web 搜索，直接返回空（或仅做补充搜索）
- `mode="always_web"`：保持原有行为，强制 web 搜索

### 2.3 image_extractor（新增）

**定位**：从 source_documents 中提取真实图片，输出 `source_images` 到 PipelineState。

**consumes**: `["source_documents"]`
**produces**: `["source_images"]`

**行为**：
- 扫描文档中的图片 URL/本地路径
- 调用 Vision API 分析图片内容，生成 alt 和 caption
- 去重 + 按文档位置排序
- 输出 list[ExtractedImage]

### 2.4 content_generator — 增强图片策略

**改动**：
- 输入新增 `synthesized_materials` 和 `source_images`
- prompt 中明确告知：优先从 `source_images` 选配图，只有在没有合适图片时才生成 AI 图
- 输出 `image_sources` 标注每张图来源
- `image_prompts` 仅在无合适真实图片时填写

---

## 3. Pipeline YAML 改动

### 3.1 新 pipeline：`douyin_image_text_v2`（完整版）

```yaml
name: "抖音图文 v2"
description: "基于源文档的内容创作，支持真实图片复用"
platforms: ["douyin"]

stages:
  - agent: topic_generator
    config:
      style: "种草"
      count: 5

  - agent: document_synthesizer    # 新增：文档深度理解
    config:
      temperature: 0.3
      max_materials: 10
      use_graph: true

  - agent: image_extractor        # 新增：提取真实图片
    config: {}

  - agent: material_collector     # 降级为补充搜索
    config:
      sources: ["web"]
      max_items: 5
      mode: web_if_no_documents   # 有文档时跳过 web

  - agent: content_generator
    config:
      platform: douyin
      format: image_text
      image_strategy: prefer_real  # 新增配置项

  - agent: reviewer
    config:
      rules: ["platform_compliance", "quality_score"]
      min_score: 7.0

  - agent: analyst
    config:
      metrics: ["engagement", "reach"]
```

### 3.2 兼容旧 pipeline

`douyin_image_text` 等旧 pipeline 保持不变，`source_documents` 为空时所有新节点自动跳过。

---

## 4. Engine 改动

### 4.1 `run_pipeline` — 注入 source_documents 到 PipelineState

```python
# engine.py run_pipeline()
initial_state: dict[str, Any] = {
    "run_id": run_id,
    "pipeline_name": pipeline_config.name,
    "user_brief": user_brief.model_dump(),
    # 新增：原始文档注入
    "source_documents": [d.model_dump() for d in brief.source_documents],
    "synthesized_materials": [],
    "source_images": [],
    # ... 其余字段 ...
}
```

---

## 5. 图片策略流程图

```
source_documents
    │
    ├─→ image_extractor ──→ source_images ──→ content_generator
    │
    ├─→ document_synthesizer ──→ synthesized_materials ──→ content_generator
    │
    └─→ material_collector (web_if_no_documents)
                                                  │
                                          content_generator
                                          写作过程中按需决定：
                                          ① 有合适 source_images → 直接用
                                          ② 需要示意图 → 调用 architecture-diagram skill → 截图
                                          ③ 需要 Canvas 关系图 → 调用 obsidian-canvas skill → 截图
                                          ④ 需要手绘风 → 调用 excalidraw-diagram skill → 截图
                                          ⑤ 以上都没有 → MiniMax 文生图（image_prompts）
                                                  │
                                          输出 image_paths + image_sources + inline_images
```

**图片来源优先级（content_generator 写作时判断）：**

| 优先级 | 来源 | 类型标签 | 说明 |
|--------|------|---------|------|
| 1 | source_images | `real_document` / `real_extracted` | 文档自带或从文档提取的图片 |
| 2 | skill 自建（架构图） | `skill_screenshot` + `skill_used: architecture-diagram` | 需要技术架构/流程图时调用 |
| 3 | skill 自建（Canvas） | `skill_screenshot` + `skill_used: obsidian-canvas` | 需要节点关系/组织图时调用 |
| 4 | skill 自建（手绘风） | `skill_screenshot` + `skill_used: excalidraw-diagram` | 需要草图/示意图时调用 |
| 5 | AI 文生图 | `ai_generated` + `source: MiniMax image-01` | 所有其他情况 |

**inline_images 的创作决策点：**
- content_generator 在写特定段落时自行决定是否需要配图
- 不需要预先在 prompt 里声明，而是在写作过程中按需触发
- 每张自建图的 `context` 字段说明"写到这里时为什么决定要做这张图"
- 截图统一保存到 `outputs/{run_id}/inline/` 目录

### 5.1 inline_images 实现方式

**架构决策：不把 skill 调用能力塞进 content_generator，而是分两步走**

```
content_generator（步骤1）
  └─→ 输出 JSON，含 inline_images specs（skill_name + prompt + caption + context）
                                    │
                    post_processor（步骤2 — 新增节点）
                      ├─→ skill=architecture-diagram → skill_view() → 执行 → playwright 截图
                      ├─→ skill=obsidian-canvas → skill_view() → 执行 → 截图
                      ├─→ skill=excalidraw-diagram → skill_view() → 执行 → 截图
                      └─→ skill=minimax-image → 调用 API → 保存图片
```

**为什么这样设计：**
- content_generator 保持纯 LLM JSON 输出，prompt 简单，不依赖 skill 工具定义
- skill 的调用（SVG 生成、Canvas JSON、截图）统一封装在 post_processor
- post_processor 读取 `inline_images` spec 列表，依次执行，截图保存到 `outputs/{run_id}/inline/`
- 生成的图片路径回填到 `PlatformContent.image_paths`

**post_processor（新增节点）：**
```python
class InlineImageProcessorConfig(BaseModel):
    output_dir: str = "outputs/{run_id}/inline"
    screenshot_format: Literal["png", "jpg"] = "png"
```

**post_processor 工具箱（按 skill 分发）：**

| skill | 生成方式 | 截图工具 |
|--------|---------|---------|
| `architecture-diagram` | 调用 skill → 生成 SVG → 保存 | playwright screenshot |
| `obsidian-canvas` | 调用 skill → 生成 .canvas JSON → 保存 | playwright screenshot |
| `excalidraw-diagram` | 调用 skill → 生成 .excalidraw.json → 保存 | playwright screenshot |
| `minimax-image-generation` | 直接调用 MiniMax API | 无需截图，直接保存 URL |

**content_generator prompt 里对 inline_images 的描述（新增章节）：**

```jinja
## 图片策略（按需自决定，不要预先声明）

在写作过程中，如果发现以下情况，可以创建 inline_images：
- 需要技术架构/流程对比图 → 使用 architecture-diagram skill
- 需要节点关系/组织结构图 → 使用 obsidian-canvas skill
- 需要手绘风格示意图 → 使用 excalidraw-diagram skill
- 需要实景/场景图 → 使用 minimax-image-generation

创建图片后，必须在 inline_images 列表中记录：skill名称、prompt内容、截图路径、图片说明、创作时机。

## 输出格式
JSON 对象：
{
  "title": "...",
  "body": "...",
  "tags": [...],
  "image_sources": [...],  // source_images 和 ai_generated 图片
  "inline_images": [        // 创作过程中自己生成的图
    {
      "skill": "architecture-diagram",
      "prompt": "...",
      "screenshot_path": "inline/图1.png",
      "caption": "Evolver vs Hermes 核心循环对比图",
      "context": "写到核心循环对比时，觉得文字不够直观，决定做一张流程对比图"
    }
  ]
}
```

---

## 6. 实施顺序

### Phase 1：State schema（只改 data model）
1. `src/core/state.py` — 新增 SourceDocument, ExtractedImage, ImageSource, ImageMaterial
2. 扩展 UserBrief, Material, PipelineState, PlatformContent
3. **不改动任何 agent 行为**，仅 schema 兼容

### Phase 2：document_synthesizer agent（新增节点）
1. 创建 `src/agents/document_synthesizer/` 目录
2. 实现 agent + schemas + prompts
3. 注册到 `Engine._register_agents()`
4. prompt 实现：深度理解 + 跨文档关联，不做简单 RAG

### Phase 3：image_extractor agent（新增节点）
1. 创建 `src/agents/image_extractor/`
2. 实现从文档提取图片 + Vision 分析
3. 注册到 Engine

### Phase 4：material_collector 降级
1. 扩展 MaterialCollectConfig，新增 `mode` 字段
2. 修改 `collect.j2` prompt，支持 web_if_no_documents 模式

### Phase 5：content_generator 增强 + post_processor（新增节点）
1. 扩展 ContentGenConfig，新增 `image_strategy` 字段
2. 修改 `generate.j2` prompt，支持 image_sources + inline_images 输出
3. 创建 `src/agents/post_processor/`（inline image processor）
4. 注册到 Engine

### Phase 6：Pipeline YAML + Engine 注入
1. 创建 `pipelines/douyin_image_text_v2.yaml`
2. Engine.run_pipeline() 注入 source_documents 到 initial_state
3. 端到端测试（从文档输入 → 内容输出 → 图片生成）

---

## 7. 不做的事

- 不改动现有 5 个 agent 的核心逻辑（只扩展配置项）
- 不改变 LangGraph 图结构（仍然是线性 pipeline）
- 不引入向量数据库（document_synthesizer 用 LLM 直接理解，不做 embedding search）
- 不改变 StateStore schema（新增字段都是 dict 类型，兼容现有存储）

---

## 8. 验收标准

1. 喂入一篇 .md 文章，material_collector 不产生任何 web 搜索
2. document_synthesizer 输出基于原文重新组织的 Material，不是原文复制
3. content_generator 优先使用 source_images 中的真实图片
4. image_sources 正确标注每张图的来源类型
5. 旧 pipeline 不受影响（source_documents 为空时行为完全一致）
