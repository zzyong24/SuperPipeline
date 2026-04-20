# Acceptance 写作规范

> 所有 feature 的 acceptance criteria 必须遵循本规范

## 原则

**Acceptance 必须是可验证的、可观测的、有明确通过/失败标准的。**

不可验证的 acceptance = 无法执行的三层架构。

## 格式模板

每个 acceptance 必须是：

1. **具体**：不模糊描述质量，描述可测量的结果
2. **可测试**：能通过自动化测试或人工检查验证
3. **原子性**：一个 acceptance 只描述一件事

## 好 vs 坏 acceptance

### ❌ 坏的 acceptance（不可验证）

```
- 代码质量好
- 内容看起来自然
- 用户体验流畅
- 没有明显的 bug
```

### ✅ 好的 acceptance（可验证）

```
- content_generator 必须记录每个素材的 source_url
- douyin.validate() 在正文 < 2000 字时返回 False
- 无 emoji 表情包（正则匹配 ^[^\U0001F300-\U0001F9FF]+$ 通过）
- pytest tests/unit/test_audit.py 全部通过
```

## 格式检查清单

写完 acceptance 后，自问：

- [ ] 我能在不知道代码长什么样之前，判断这条 acceptance 通过了吗？
- [ ] 有没有用什么词？（很好、不错、尽量、适当）—— 这些词出现说明不可验证
- [ ] 这条 acceptance 能用自动化测试验证吗？

## SuperPipeline 特定 acceptance 示例

### 素材约束 acceptance

```markdown
# ✅ 可验证
"material_collector 必须记录每个素材的 source_url，且 source_url 不得为空"
"无 source_document 时，material_collector 禁止调用 web search"

# ❌ 不可验证
"素材必须真实可信"
```

### 内容质量 acceptance

```markdown
# ✅ 可验证
"输出内容不包含任何 emoji（匹配正则 ^[\U00000000-\U0001FFFF]+$）"
"正文长度 >= 2000 字（len(content.text) >= 2000）"

# ❌ 不可验证
"内容看起来像真人写的"
```

### 审核闭环 acceptance

```markdown
# ✅ 可验证
"douyin.validate() 返回 False 时，content_generator 收到 audit_feedback 并重新生成"
"连续 3 次 audit 失败后，pipeline 停止并抛出 AuditFailedError"

# ❌ 不可验证
"审核结果有效反馈给生成器"
```

## 多层 acceptance

一个 feature 可以有多层 acceptance：

1. **格式层**：文件存在、格式正确、能被解析
2. **功能层**：函数行为正确、返回值符合预期
3. **集成层**：端到端流程跑通、输出符合业务标准

三层都要写，不能只写功能层。
