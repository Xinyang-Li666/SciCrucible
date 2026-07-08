# SciCrucible — 科学智能知识库框架

> 一套 Claude Code skills + 脚本 + 行为规则，LLM 增量编译式个人知识库 —— 从文献摄入到学术写作的全闭环

[![License](https://img.shields.io/badge/license-GPL%20v3-blue.svg)](LICENSE)

## 这是什么

SciCrucible 是一套**框架**——不是成品知识库，而是帮你**构建自己知识库**的工具链。你只需提供 PDF 论文和配置，SciCrucible 自动完成：

- 文献元数据提取 → 结构化笔记（组分-条件-性质-机制闭环）
- 概念自动聚合（中颗粒度：共享同一物理机制的合并）
- DOI 去重 + 文献索引缓存
- 多角度主动文献发现
- 每周文献速递（自动扫描 → 精选 → 下载 → 摄入）
- 知识库健康检查（断链、过期、缺口、DOI 覆盖率）
- 文献锚定型学术写作

**核心思路**：你负责阅读和思考，LLM 负责编译和组织。知识库越用越聪明。

## 它能做什么

| 场景 | 命令 |
|------|------|
| 新论文太多，读完就忘 | `/forge-ingest` 自动提取元数据 → 生成文献页 → 按课题分类归档 |
| 想快速了解某个材料问题 | `/forge-search <问题>` 遍历概念页+文献→综合回答，附文献出处 |
| 主动发现领域新文献 | `/forge-discovery "<关键词>"` 多角度 sci search → 去重 → 下载 → 待摄入 |
| 每周文献速递 | `/forge-weekly` 自动扫描+精选+下载+摄入，推送 3-5 篇/课题 |
| 设计新材料成分 / 分析机制 | `/forge-think` 基于已有知识跨领域类比思考 |
| 知识库质量下降 | `/forge-health` 全面检查断链/过期/缺口/DOI覆盖率/概念页健康评分 |
| 写论文 Introduction / Discussion | `/forge-writing` 文献锚定型写作，逐段交互起草 |

## 快速开始

### 0. 前置条件

- [Claude Code](https://claude.ai/code)（通过 CLI 或 IDE 扩展）
- [SciMaster CLI](https://scimaster.ai)（可选，用于文献发现功能）
- [scansci-pdf](https://github.com/nick-cn/scansci-pdf)（可选，用于文献下载功能）
- Python 3.10+

### 1. 克隆仓库

```bash
git clone git@github.com:Xinyang-Li666/SciCrucible.git
cd SciCrucible
```

### 2. 按需配置

详细的安装和配置指南见 **[MANUAL.md](./MANUAL.md)**。核心步骤：

- **Claude Code MCP**：配置 `scansci-pdf`（文献下载）
- **SciMaster CLI**：配置 `sci` 命令（文献检索）
- **期刊评级表**：仓库已包含 `journal-ratings.xlsx`（社区整理的期刊评级参考，非官方数据）
- **CLAUDE.md**：将课题名称替换为你自己的研究方向

### 3. 开始使用

```bash
# 下载 PDF 放入暂存区
cp ~/Downloads/paper.pdf SciCrucible/raw/new-papers/

# 在 Claude Code 中打开项目，输入：
/forge-ingest

# 知识库自动生长
# - wiki/literature/   ← 文献笔记（组分-条件-性质-机制闭环）
# - wiki/concepts/     ← 概念页（自动聚合，中颗粒度）
# - wiki/index.md      ← 全局索引（自动更新）
# - literature_index.json ← DOI 去重缓存（自动维护）
```

### 其他常用操作

```bash
# 查询知识库（直接提问即可）
"掺杂如何影响高镍正极的 H2→H3 相变？"

# 主动发现新文献
/forge-discovery "高熵碳化物抗氧化烧蚀"

# 每周文献速递
/forge-weekly

# 学术写作
/forge-writing 写LNO掺杂抑制H2-H3相变的Introduction
```

## 可用命令

| 命令 | 功能 |
|------|------|
| `/forge-ingest` | 批量摄入 `raw/new-papers/` 中所有 PDF |
| `/forge-ingest <file>` | 摄入单个 PDF |
| `/forge-search <query>` | 自然语言查询知识库（直接提问即可） |
| `/forge-discovery "<关键词>"` | 主动检索新文献（多角度 sci search → 去重 → 下载） |
| `/forge-weekly` | 每周文献速递（自动扫描+精选+下载+摄入） |
| `/forge-think` | 材料科学协作思考 |
| `/forge-todo` | 待办管理 |
| `/forge-health` | 知识库健康检查 |
| `/forge-writing` | 文献锚定型学术写作（Introduction + Discussion） |

## 目录结构

```
SciCrucible/
├── README.md                    ← 本文件
├── MANUAL.md                    ← 详细使用手册
├── LICENSE                      ← GNU GPL v3
├── CLAUDE.md                    ← 项目指令（Claude Code 自动读取）
├── .gitignore                   ← Git 忽略规则
├── .mcp.json                    ← MCP 配置模板
├── .claude/skills/              ← Claude Code skill 定义
│   ├── forge-ingest/            ←   /forge-ingest（文献摄入）
│   ├── forge-search/            ←   /forge-search（知识库查询）
│   ├── forge-think/             ←   /forge-think（协作思考）
│   ├── forge-todo/              ←   /forge-todo（待办管理）
│   ├── forge-health/            ←   /forge-health（健康检查）
│   ├── forge-writing/           ←   /forge-writing（学术写作）
│   ├── forge-discovery/         ←   /forge-discovery（主动文献发现）
│   │   ├── SKILL.md             ←     完整流程定义
│   │   ├── scripts/dedup.py     ←     DOI 去重脚本
│   │   ├── config/weekly.yaml   ←     周报关键词配置模板
│   │   └── references/sci-cli.md←     SciMaster CLI 参考
│   └── forge-weekly/            ←   /forge-weekly（每周速递）
├── scripts/                     ← 辅助脚本
│   ├── extract_pdf.py           ←   PDF 文本提取
│   ├── forge-ingest.sh          ←   批量摄入入口
│   └── forge-health.sh          ←   健康检查入口
├── raw/                         ← 第 1 层：不可变原始素材（运行时生成）
│   ├── new-papers/              ←   待摄入暂存区
│   ├── papers/                  ←   已摄入 PDF（按课题分文件夹）
│   ├── search-results/          ←   检索结果
│   │   ├── json/                ←     JSON 原始数据
│   │   ├── bib/                 ←     BibTeX 引用
│   │   ├── reports/             ←     检索报告
│   │   └── batches/             ←     批次状态
│   └── references.bib           ←   全局 BibTeX 库（自动生成）
├── wiki/                        ← 第 2 层：LLM 维护的结构化知识（运行时生成）
│   ├── index.md                 ←   全局索引入口
│   ├── literature_index.json    ←   DOI→标题 索引缓存
│   ├── concepts/                ←   概念页（中颗粒度）
│   ├── literature/              ←   文献笔记
│   ├── methods/                 ←   方法页
│   └── projects/                ←   项目综述（8 章框架）
├── brainstorming/               ← 第 3 层：想法与探索（运行时生成）
└── manuscripts/                 ← 第 4 层：完成的手稿 PDF（运行时生成）
```

> **注意**：`wiki/`、`raw/`、`brainstorming/`、`manuscripts/` 的内容是**用户个人知识**，不在仓库中。使用时这些目录由脚本和 skills 自动创建和填充。

## 设计理念

### 中颗粒度
概念页不追求一个原子概念一页，也不全部塞进一页。**共享同一物理机制的合并为一页**，用 `###` 子标题区分。页面规模 80-250 行。

### 期刊评级过滤
构建文献脉络时按期刊评级过滤：优先评级 1和顶级期刊，低评级期刊仍摄入但不进入脉络。评级表 `journal-ratings.xlsx` 已包含在仓库中（社区整理的期刊评级参考，非官方数据）。

### 增量编译
每次摄入追加新知识，不覆盖已有内容。概念页增量补充，文献索引自动维护。

### 双链互联
所有 wiki 页面 `[[双向链接]]`，鼓励跨领域类比（如 UHTC ↔ 正极共享 Ellingham/Wagner/Fick 框架）。

### 闭环
摄入 → 编译 → 查询 → 发现 → 写作 → 再摄入。知识库越用越聪明。

### 8 章项目框架
每个研究课题统一结构：研究背景 → 文献脉络 → 技术路线 → 阶段进展 → 核心发现 → 手稿 → 开放问题 → 阅读导航。

## 个人化

Fork 后你需要做的：

1. **修改 `CLAUDE.md`**：替换课题名称和研究方向
2. **修改 `weekly.yaml`**：替换检索关键词
3. **检查期刊评级表**：仓库已含 `journal-ratings.xlsx`，如需更新请自行替换
4. **配置 MCP**：在 Claude Code 中启用 `scansci-pdf`
5. **配置 SciMaster**：运行 `sci init`（如需文献发现功能）

## 完整文档

详见 **[MANUAL.md](./MANUAL.md)** —— 包含安装配置、场景化工作流、维护指南。

## 致谢

SciCrucible 深度依赖以下项目：

- **[scansci-pdf](https://github.com/nick-cn/scansci-pdf)** —— 学术文献智能下载引擎，感谢作者的开源贡献
- **[Claude Code](https://claude.ai/code)** —— LLM 运行时
- **[SciMaster](https://scimaster.ai)** —— 学术文献检索
- **[OpenAlex](https://openalex.org/)** · **[Semantic Scholar](https://semanticscholar.org/)** —— 开放学术数据

## 许可

GNU General Public License v3.0 — 自由使用、修改、分发，但衍生作品必须同样开源。

详见 [LICENSE](./LICENSE)。
