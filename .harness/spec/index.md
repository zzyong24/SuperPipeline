# Harness Spec 索引

## 必须阅读

所有 Generator 在开始编码前，必须阅读以下文件：

1. `.harness/spec/index.md` — 本文件
2. `.harness/spec/backend.md` — Python/FastAPI 开发规范
3. `.harness/spec/frontend.md` — Next.js 开发规范
4. `.harness/spec/guides/acceptance-writing.md` — 如何写验收标准

## 项目信息

- **项目**：SuperPipeline
- **架构**：Monorepo（server/ Python + web/ Next.js）
- **根目录**：`/Users/zyongzhu/Workbase/SuperPipeline/`
- **Harness 版本**：v1.1

## Pre-Development Checklist

- [ ] 理解当前 feature 的 phase 和 acceptance
- [ ] 阅读对应技术栈的 spec 文档（backend.md 或 frontend.md）
- [ ] 如果是跨层 feature（涉及 server/ 和 web/ 两部分），两份都要读
- [ ] 如果 feature 有 parent，先读完 parent 的 spec
- [ ] 确认 spec 规范后再开始编码

## 技术栈说明

| 目录 | 技术栈 | 主要规范文件 |
|------|--------|-------------|
| server/ | Python + FastAPI | backend.md |
| web/ | Next.js + TypeScript | frontend.md |
| .harness/ | JSON + Markdown | 本文件 + guides/* |

## 相关文档

- 项目 SPEC.md：`.harness/../SPEC.md`
- Server README：`.harness/../server/README.md`
- Web README：`.harness/../web/README.md`
