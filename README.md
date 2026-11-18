# SciCrucible v2.0.1 — 科学智能知识库

> 科学智能知识库：从文献摄入—知识分析—科学讨论—学术写作的全闭环。

[![License](https://img.shields.io/badge/license-GPL%20v3-blue.svg)](LICENSE)

## 这是什么

SciCrucible 是科学智能知识库框架，也提供其他 Agent 可读取的技能与操作契约。它帮助你构建自己的知识库，串联文献摄入、知识分析、科学讨论与学术写作。你只需提供 PDF 论文和配置，SciCrucible 自动完成：

- 文献元数据提取 → 结构化笔记（组分-条件-性质-机制闭环）
- 概念自动聚合（中颗粒度：共享同一物理机制的合并）
- DOI 去重 + 文献索引缓存
- 多角度主动文献发现
- 每周文献速递（自动扫描 → 精选 → 下载 → 摄入）
- 知识库健康检查（断链、过期、缺口、DOI 覆盖率）
- 文献锚定型学术写作

**核心思路**：你负责阅读和思考，LLM 负责编译和组织。知识库越用越聪明。

## 四阶段使用路由

文献摄入使用 `forge-ingest`，将原始论文编译为可追溯笔记；知识分析使用 `forge-search`，先查本地证据再综合；科学讨论使用 `forge-think`，围绕机制、假设与开放问题展开；学术写作使用 `forge-writing`，以文献证据和大纲推进段落起草。其他 Agent 可直接读取对应技能，遵守相同来源与授权边界。

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
| 构建实验数据库（如烧蚀/氧化） | `/forge-extract` 检索→筛选→下载→提取→结构化 JSON 数据库 |

版本更新见 [CHANGELOG.md](CHANGELOG.md)。

## 本次更新与发布边界

新增有界本地证据查询、PDF 摄入预检与可验证的会话交接工具，并补充跨 Agent 接入说明。入口分别为 `scripts/evidence_query.py`、`scripts/ingest_prepare.py` 和 `scripts/session_handoff.py`。

**进阶材料建库与复核管线仍在本地验证和发布审计中，本次未完整公开。** 下文旧版 `/forge-extract` 命令不代表已具备本地最新版的全部能力。克隆公开仓库后，请以 [发布状态](docs/release-status.md) 判断入口是否可用；不可将未发布脚本当作已安装依赖。

其他 Agent 从 [接入指南](docs/agent-quickstart.md) 开始，并按需采用 [公共指令模板](AGENTS.public.md)。当前测试结果与限制见发布状态，不宣称全量测试通过。

## 快速开始

### 0. 前置条件

- 能读取项目技能与执行本地脚本的 Agent；项目技能位于 `.agents/skills/`，Agent 接入方式见 [接入指南](docs/agent-quickstart.md)
- [SciMaster CLI](https://scimaster.ai)（可选，用于文献发现功能）
- Python 3.11+

### 1. 克隆仓库

```bash
git clone git@github.com:Xinyang-Li666/SciCrucible.git
cd SciCrucible
```

### 2. 按需配置

详细的安装和配置指南见 **[MANUAL.md](./MANUAL.md)**。核心步骤：

- **SciMaster CLI**：配置 `sci` 命令（文献检索）
- **期刊评级表**：仓库已包含 `journal-ratings.xlsx`（社区整理的期刊评级参考，非官方数据）
- **AGENTS.public.md**：将课题名称替换为你自己的研究方向

### 3. 开始使用

```bash
# 下载 PDF 放入暂存区
mkdir -p raw/new-papers
cp ~/Downloads/paper.pdf raw/new-papers/

# 在支持技能的 Agent 中打开项目，输入：
/forge-ingest

# 知识库自动生长（按课题分层）
# - wiki/<课题>/literature/ ← 文献笔记（组分-条件-性质-机制闭环）
# - wiki/<课题>/concepts/   ← 概念页（自动聚合，中颗粒度）
# - wiki/通用/              ← 跨课题共享的通用概念/方法（DFT/MD/热力学…）
# - wiki/index.md           ← 全局索引（自动更新）
# - literature_index.json   ← DOI 去重缓存（自动维护）
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
| `/forge-extract` | 通用实验数据提取 — 检索→筛选→下载→提取→标准化→入库 |

## 目录结构

```
SciCrucible/
├── README.md                    ← 本文件
├── MANUAL.md                    ← 详细使用手册
├── LICENSE                      ← GNU GPL v3
├── AGENTS.public.md             ← 公共 Agent 指令模板
├── .gitignore                   ← Git 忽略规则
├── .mcp.json                    ← MCP 配置模板
├── .agents/skills/              ← Agent skill 定义
│   ├── forge-ingest/            ←   /forge-ingest（文献摄入）
│   ├── forge-search/            ←   /forge-search（知识库查询）
│   ├── forge-think/             ←   /forge-think（协作思考）
│   ├── forge-todo/              ←   /forge-todo（待办管理）
│   ├── forge-health/            ←   /forge-health（健康检查）
│   ├── forge-writing/           ←   /forge-writing（学术写作）
│   │   ├── SKILL.md             ←     IMRD 四段独立路由 + 三阶深挖
│   │   ├── references/          ←     语言规则
│   │   └── evals/
│   ├── forge-extract/            ←   /forge-extract（通用实验数据提取）
│   │   ├── SKILL.md             ←     6 步 pipeline 完整流程
│   │   ├── scripts/             ←     normalize_units, validate_schema, merge_to_db...
│   │   ├── references/          ←     ablation-schema.json, field-guidelines
│   │   └── evals/
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
│   ├── extract/                  ←   forge-extract 工作目录（运行时生成）
│   │   ├── papers/              ←     待提取 PDF
│   │   ├── md/                  ←     PyMuPDF4LLM 转换输出
│   │   └── json/                ←     LLM 提取的结构化 JSON
│   └── references.bib           ←   全局 BibTeX 库（自动生成）
├── database/                     ← 结构化实验数据库（运行时生成）
│   ├── ablation.json             ←   烧蚀实验数据
│   └── processed_dois.json       ←   已处理 DOI 追踪
├── wiki/                        ← 第 2 层：LLM 维护的结构化知识（运行时生成，按课题分层）
│   ├── index.md                 ←   全局索引入口
│   ├── literature_index.json    ←   DOI→标题 索引缓存
│   ├── <课题A>/                 ←   如「超高温陶瓷」
│   │   ├── concepts/            ←     概念页（中颗粒度，80-250 行）
│   │   ├── literature/          ←     文献笔记
│   │   ├── methods/             ←     课题专用方法页
│   │   └── projects/            ←     项目综述（8 章框架）
│   ├── <课题B>/                 ←   如「锂离子电池正极材料」（同上四类）
│   └── 通用/                    ←   跨课题共享
│       ├── concepts/            ←     通用概念（掺杂/热力学/氧化理论…）
│       └── methods/             ←     通用方法（DFT/MD/机器学习势…）
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

1. **修改 `AGENTS.public.md`**：替换课题名称和研究方向
2. **修改 `weekly.yaml`**：替换检索关键词
3. **检查期刊评级表**：仓库已含 `journal-ratings.xlsx`，如需更新请自行替换
4. **配置 SciMaster**：运行 `sci init`（如需文献发现功能）

## DOI 全文与补充材料下载

使用 `/forge-download`，或由 Agent 读取 `.agents/skills/forge-download/SKILL.md`。安装 HTTP/PDF 依赖：`python -m pip install requests pymupdf`；浏览器功能另需 `python -m pip install playwright`。默认使用本机 Edge；未安装时自行安装 Edge，或按 Playwright 文档配置浏览器。

`python -B scripts/download_papers.py --dois <清单.txt> --dry-run` 仅列计划；`--check` 会联网检查出口与订阅权限，不能与 dry-run 合用。实际下载前确认访问授权。默认正文到 `raw/new-papers/`，日志到 `outputs/downloads/`，SI 单独放入正文目录下的 `SI/`。支持 `--out`、`--state` 自定义路径。

Elsevier 仅从环境变量 `ELSEVIER_API_KEY` 读取密钥，无内嵌回退；Unpaywall 需要 `UNPAYWALL_EMAIL`，未配置时跳过并说明。浏览器会话 `.browser-profile/` 含登录态，必须留在本地。浏览器功能按宿主实际权限审批，不要求放宽整个会话。详细 CLI 与路由见 [下载手册](docs/paper-download.md)。

## 完整文档

### 可溯源材料数据集与Materials Project

以下为本地进阶扩展设计，完整实现尚未随本次公开发布。文献数据按领域配置经过prepare→复核→stage→显式commit→按用途export，兼容烧蚀、热力学和金属力学等方向。MP计算数据独立保存，不作为实验值，也不按相同化学式自动匹配样品。公开可用范围与后续发布条件见[发布状态](docs/release-status.md)。

MP客户端可读取显式本地配置中的external_services.materials_project.api_key；未指定配置时读取MP_API_KEY环境变量。不要把Key写入命令、仓库或导出文件。支持旧数字MPID与官方AlphaID的确定性别名校验，保留提供方原始返回身份。请求有材料数/次数上限，不重试、不自动翻页、不自动入库。

并非每个材料都有能量或弹性性质。没有记录、字段未返回、提供方null、数值0和请求失败分别留痕；分页完整性未知时不能通过来源暂存。结构JSON及指纹只针对实际返回内容，不代表弛豫、物理稳定或与性质计算任务同结构。复核夹具通过不代表真实科研准确率或训练适用性通过。

本地实测记录属于私人评测产物，未随本次发布；离线夹具不能代替联网验收。

详见 **[MANUAL.md](./MANUAL.md)** —— 包含安装配置、场景化工作流、维护指南。

## 致谢

SciCrucible 深度依赖以下项目：

- **[SciMaster](https://scimaster.ai)** —— 学术文献检索
- **[OpenAlex](https://openalex.org/)** · **[Semantic Scholar](https://semanticscholar.org/)** —— 开放学术数据

## 许可

GNU General Public License v3.0 — 自由使用、修改、分发，但衍生作品必须同样开源。

详见 [LICENSE](./LICENSE)。
