# SciCrucible 用户手册

> 基于 LLM 增量编译模式构建 · 从文献摄入到学术写作的全闭环

---

## 零、环境准备与安装

### 0.1 你需要什么

| 组件 | 用途 | 必需？ |
|------|------|:---:|
| **Claude Code** | LLM 驱动核心（所有 /forge-* 命令） | ✅ 必需 |
| **Python 3.9+** | PDF 文本提取、去重脚本、预过滤 | ✅ 必需 |
| **Bash**（Git Bash / WSL / macOS Terminal） | `forge-ingest.sh`、`forge-health.sh` | ✅ 必需 |
| **SciMaster CLI**（`sci`） | `/forge-discovery` 和 `/forge-weekly` 文献检索 | 主动发现需要 |
| **scansci-pdf MCP Server** | 论文 PDF 下载 | 主动发现需要 |
| **期刊评级表**（`journal-ratings.xlsx`） | 期刊质量评估 | 推荐 |

**操作系统**：Windows（Git Bash 或 WSL）、macOS、Linux 均可。本手册以 Windows + Git Bash 为例。

### 0.2 安装 Claude Code

参考 [Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code) 安装：

```bash
# npm 全局安装（推荐）
npm install -g @anthropic-ai/claude-code

# 验证
claude --version
```

启动 Claude Code 后，它会自动读取项目根目录的 `CLAUDE.md` 作为项目指令。

### 0.3 获取 SciCrucible

```bash
# 方式一：Git 克隆（推荐）
git clone <你的仓库地址> <你的项目根目录>
cd <你的项目根目录>

# 方式二：直接下载解压到项目根目录
```

**目录布局**：确保 `CLAUDE.md` 在项目根目录，`SciCrucible/` 为子目录（参见下方 §一 的完整目录树）。

### 0.4 安装 Python 依赖

```bash
pip install openpyxl   # 读取期刊评级表 Excel
```

### 0.5 验证安装

```bash
# 检查必需组件
claude --version        # Claude Code 可用？
python --version        # Python 3.9+ 可用？
bash --version          # Bash 可用？

# 检查 skills 存在
ls SciCrucible/.claude/skills/forge-ingest/SKILL.md
ls SciCrucible/.claude/skills/forge-health/SKILL.md
```

全部通过后，继续下一节的配置。

---

## 一、知识库是什么

这是一个由 LLM 维护的**增量编译式**个人知识库。不同于传统的文件夹归档（你手动整理），也不同于 RAG（每次查询才处理），它的核心理念是：

> **每次摄入新知识时，LLM 自动编译成结构化 wiki 页面。每次查询后，有价值的见解回流到 wiki。知识库越用越聪明。**

类比：
- `raw/` = 图书馆书库（原始 PDF，不可变）
- `wiki/` = 维基百科（LLM 维护的结构化知识）
- `brainstorming/` = 实验笔记本（想法、待办、探索）
- `manuscripts/` = 发表成果（完成的手稿 PDF）
- `projects/` = 你的实际科研目录（数据、图表、手稿草稿）

你的角色是**策展人和提问者**，LLM 做所有整理、交叉引用、格式维护的劳动者。

---

## 二、知识库结构

```
<你的项目根目录>/
├── CLAUDE.md                      ← Claude Code 项目指令
├── SciCrucible/
│   ├── README.md                   ← 项目入口
│   ├── MANUAL.md                   ← 本手册
│   ├── journal-ratings.xlsx         ← 期刊评级基准
│   │
│   ├── raw/                       ← 第 1 层：不可变原始素材
│   │   ├── new-papers/            ←    新文献暂存区（待摄入）
│   │   ├── papers/                ←    已摄入 PDF（按课题分文件夹）
│   │   └── search-results/        ←    主动发现输出
│   │       ├── json/              ←      sci search JSON
│   │       ├── bib/               ←      sci search BibTeX
│   │       ├── reports/           ←      检索报告
│   │       └── batches/           ←      批次状态
│   │
│   ├── wiki/                      ← 第 2 层：LLM 维护的结构化知识（按课题分层）
│   │   ├── index.md               ←    全局索引入口
│   │   ├── literature_index.json  ←    DOI 索引缓存（O(1) 去重查重）
│   │   ├── <课题A>/               ←    如「超高温陶瓷」
│   │   │   ├── concepts/          ←      概念页（中颗粒度分组，80-250 行）
│   │   │   ├── literature/        ←      文献笔记（标注期刊评级）
│   │   │   ├── methods/           ←      课题专用方法页
│   │   │   └── projects/          ←      项目综述（8 章框架）
│   │   ├── <课题B>/               ←    如「锂离子电池正极材料」（同上四类）
│   │   └── 通用/                  ←    跨课题共享
│   │       ├── concepts/          ←      通用概念（掺杂/热力学/氧化理论…）
│   │       └── methods/           ←      通用方法（DFT/MD/机器学习势…）
│   │
│   ├── brainstorming/             ← 第 3 层：思考与探索
│   │   ├── ideas/                 ←    设计文档与方法论
│   │   ├── sessions/              ←    协作思考会话记录
│   │   ├── todos.md               ←    待办清单
│   │   └── questions.md           ←    开放问题列表
│   │
│   ├── manuscripts/               ← 第 4 层：手稿定稿 PDF
│   │
│   ├── .kiro/                     ← LLM 行为规则与摄入缓存
│   │   └── .ingest_cache/         ←    摄入临时文件
│   │
│   ├── .claude/skills/            ← Claude Code skill 定义
│   │   ├── forge-discovery/       ←    主动文献发现
│   │   │   ├── SKILL.md
│   │   │   ├── scripts/dedup.py
│   │   │   ├── config/weekly.yaml
│   │   │   └── references/sci-cli.md
│   │   ├── forge-ingest/          ←    文献摄入
│   │   ├── forge-weekly/          ←    每周速递
│   │   ├── forge-search/          ←    知识库查询
│   │   ├── forge-think/           ←    协作思考
│   │   ├── forge-todo/            ←    待办管理
│   │   ├── forge-health/          ←    健康检查
│   │   └── forge-writing/         ←    学术写作
│   │
│   └── scripts/                   ← 辅助脚本
│       ├── extract_pdf.py         ←    PDF 文本提取
│       ├── forge-ingest.sh        ←    摄入流程
│       └── forge-health.sh        ←    链接/孤立检测
│
├── projects/                      ← 你的实际科研目录（与 SciCrucible/ 平级）
│   ├── <课题1>/
│   │   ├── data/                  ← 原始数据与计算结果
│   │   ├── figures/               ← 图表
│   │   ├── draft/                 ← 手稿草稿
│   │   └── notes/                 ← 项目笔记
│   └── <课题2>/
│       └── ...
```

### 数据流（全闭环）

```
┌────────── 被动摄入 ────────────────────────────────┐
│                                                       │
│  PDF 文献 ──→ raw/new-papers/       ← 放这里          │
│                  │                                    │
│                  ▼ /forge-ingest（批量）                  │
│              wiki/<课题>/literature/ ──→ concepts/    │
│                  │                                    │
│                  ▼ 摄入完成后                          │
│              PDF 移至 raw/papers/    ← 已归档          │
│                  │                                    │
│                  ▼                                    │
│              wiki/index.md + literature_index.json    │
│                  │                                    │
│                  ▼ /forge-search                         │
│              用户查询 ──→ 综合回答 + 引用来源           │
│                  │                                    │
│                  ▼ (有价值时归档)                      │
│              brainstorming/                           │
│                                                       │
└───────────────────────────────────────────────────────┘

┌────────── 主动发现 ────────────────────────────────┐
│                                                       │
│  /forge-discovery "关键词"                               │
│       │                                               │
│       ▼ sci search（多角度检索）                       │
│   raw/search-results/json/*.json                      │
│       │                                               │
│       ▼ dedup.py（DOI 去重 + literature_index 查重）   │
│   [新文献列表]                                         │
│       │                                               │
│       ▼ 用户勾选 → scansci-pdf 下载                    │
│   raw/new-papers/                                     │
│       │                                               │
│       ▼ /forge-ingest（手动触发或 /forge-weekly 自动）       │
│   wiki/<课题>/literature/ + concepts/                 │
│                                                       │
└───────────────────────────────────────────────────────┘

┌────────── 学术写作（输出）────────────────────────────┐
│                                                       │
│  /forge-writing "写LNO掺杂的Introduction"                 │
│       │                                               │
│       ▼ 三阶深挖（KB摸底 + 文献锚定 + 创新锚定）       │
│   [结构化写作摘要]                                     │
│       │                                               │
│       ▼ 用户确认大纲 → 逐段起草（一段一审）            │
│   draft/*.md                                          │
│                                                       │
└───────────────────────────────────────────────────────┘
```

---

## 三、安装与配置

> **配置顺序**：先配 Claude Code MCP（scansci-pdf），再装 SciMaster CLI。两者独立，可并行进行。

### 3.1 Claude Code MCP 配置（scansci-pdf 文献下载）

scansci-pdf 是一个开源的学术论文下载 MCP Server，支持 13+ 下载源、多所大学 WebVPN、Tor 匿名网络。**`/forge-discovery` 和 `/forge-weekly` 依赖它完成文献下载。**

> 💡 **致谢**：本文献下载功能基于开源项目 **scansci-pdf**。感谢作者为学术界提供了这样一个强大、易用的论文获取工具，免去了手动逐个下载和格式转换的繁琐。如果你觉得有用，欢迎给项目加星 ⭐。

#### Step 1 — 找到 Claude Code 配置文件

Claude Code 的 MCP Server 配置文件位置：

| 操作系统 | 路径 |
|----------|------|
| Windows | `%APPDATA%\.claude\claude-code.json` 或 `%USERPROFILE%\.claude\claude-code.json` |
| macOS | `~/.claude/claude-code.json` |
| Linux | `~/.claude/claude-code.json` |

如果文件不存在，手动创建。以下以 Windows 为例：

```powershell
# 用记事本打开配置文件
notepad "$env:USERPROFILE\.claude\claude-code.json"
```

#### Step 2 — 添加 scansci-pdf MCP Server

在 `mcpServers` 中添加：

```json
{
  "mcpServers": {
    "scansci-pdf": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "scansci-pdf-mcp"
      ],
      "env": {
        "SCANSCI_PDF_OUTPUT_DIR": "D:/科研/SciCrucible/raw/new-papers",
        "SCANSCI_PDF_CACHE_DIR": "D:/科研/SciCrucible/.cache/scansci"
      }
    }
  }
}
```

**字段说明**：

| 字段 | 说明 |
|------|------|
| `type` | 固定为 `"stdio"` |
| `command` | `npx`（Node.js 包运行器，安装 Node.js 后自带） |
| `args` | `["-y", "scansci-pdf-mcp"]`，`-y` 表示自动确认安装 |
| `SCANSCI_PDF_OUTPUT_DIR` | **必填**。PDF 下载目录，指向 `SciCrucible/raw/new-papers/` |
| `SCANSCI_PDF_CACHE_DIR` | **推荐**。缓存目录，避免重复下载 |

> ⚠️ **路径使用正斜杠** `/`，即使 Windows 也要用 `D:/科研/...` 而非 `D:\科研\...`。

#### Step 3 — 重启 Claude Code

配置保存后，**完全退出并重启 Claude Code**。启动后在对话中输入以下命令验证：

```
/scansci-pdf:health_check
```

如果返回各下载源状态，说明配置成功。

#### Step 4 — 下载策略选择

| 策略 | 命令参数 | 说明 |
|------|---------|------|
| **合法渠道**（默认） | `--strategy legal_only` | Elsevier API + OpenAlex OA + WebVPN + CARSI |
| 最快路径 | `--strategy fastest` | 含 Sci-Hub 兜底，需用户显式允许 |
| 仅开放获取 | `--strategy oa_first` | 优先 OA，不触发付费墙 |
| 仅 Sci-Hub | `--strategy scihub_only` | 需用户允许 |

**首次使用建议运行自动检测**：

```
/scansci-pdf:auto_setup
```

这会自动检测 Tor、浏览器、Sci-Hub 可用性，并给出缺失组件的安装建议。

### 3.2 SciMaster CLI 安装与配置

SciMaster CLI（命令行工具 `sci`）是主动文献发现的后端检索引擎，提供多模式学术检索能力。

#### Step 1 — 安装

参考 SciMaster 官方文档安装 `sci` 命令行工具。安装完成后验证：

```bash
sci --version   # 应输出版本号
```

#### Step 2 — 获取并配置 API Key

1. 访问 SciMaster 官网注册账号
2. 在个人设置页面获取 API Key
3. 运行初始化命令：

```bash
sci init
# 按提示粘贴 API Key
```

> ⚠️ **安全提醒**：API Key 存储在 `~/.scimaster/config.json`（用户目录），**不要**将其复制到 SciCrucible 项目目录中，也不要提交到 Git。SciCrucible 的 `.gitignore` 已配置排除相关路径。

#### Step 3 — 验证配置

```bash
sci usage   # 查看剩余额度，确认认证成功
```

#### Step 4 — 检索模式与费用

| 模式 | 费用 | LLM 排序 | 适用场景 |
|------|------|:--:|------|
| `ultra_low` | **免费** | 否 | 初扫锁定方向、宽网撒 |
| `low` | 消耗额度 | 是 | 精选排序（默认），精度高 |
| `mid` | 更多额度 | 是 | low 结果不理想时升级 |
| `high` | 最多额度 | 是 | 最高精度需求 |

**额度管理建议：**
- `/forge-weekly` 先用 `ultra_low` 宽扫（免费），再精选 2-3 个方向用 `low`
- `/forge-discovery` 默认 `low` 模式，每次消耗约 3×20 次检索
- 定期运行 `sci usage` 查看余额

### 3.3 机构订阅配置（可选，提升下载成功率）

如果有大学/机构订阅，可进一步配置以下渠道。配置后 scansci-pdf 会自动尝试通过这些渠道下载付费论文。

#### CARSI 登录（推荐）

通过机构 SSO 统一认证访问出版社（支持 ScienceDirect、Springer、Wiley、IEEE 等）：

```
/scansci-pdf:carsi_login publisher=sciencedirect
```

首次使用时会打开浏览器，选择你的学校并完成统一认证登录。Cookie 会被自动保存，后续下载自动复用。

#### WebVPN 登录

通过学校 VPN 系统访问：

```
/scansci-pdf:vpnsci_set_school "你的大学名称"
/scansci-pdf:vpnsci_login
```

> 支持国内大多数高校。运行 `/scansci-pdf:vpnsci_schools` 可搜索支持的学校列表。

#### 浏览器 Cookie 导入

如果已有有效的出版社登录状态，可直接导入浏览器 Cookie：

```
/scansci-pdf:import_browser_cookies
```

#### 网络诊断

如果下载持续失败，运行网络诊断：

```
/scansci-pdf:network_diagnose
```

### 3.4 期刊评级表（期刊质量评估）

仓库中已包含 `journal-ratings.xlsx`（期刊评级参考），无需额外下载。

> ⚠️ **免责声明**：此文件为社区整理的期刊评级参考，非任何官方机构数据。评级信息仅供参考，用户需自行核实准确性。该数据按"原样"提供，不附带任何保证。

**文件格式**：
- 列：`期刊名称` | `评级`（1-4, 1 为最高） | `顶级`（是/否） | `Open Access`
- `.xlsx` 格式

如果没有评级表，文献摄入仍可正常进行，但会跳过期刊评级标注和文献脉络过滤。

### 3.5 配置验证清单

全部配置完成后，逐项验证：

| # | 检查项 | 命令 | 通过标准 |
|---|--------|------|---------|
| 1 | Claude Code 可用 | `claude --version` | 输出版本号 |
| 2 | Python 可用 | `python --version` | ≥3.9 |
| 3 | Bash 可用 | `bash --version` | 输出版本号 |
| 4 | Skills 存在 | `ls .claude/skills/forge-ingest/SKILL.md` | 文件存在 |
| 5 | scansci-pdf 配置 | 在 Claude Code 中运行 `/scansci-pdf:health_check` | 显示各源状态 |
| 6 | SciMaster CLI | `sci --version && sci usage` | 版本 + 额度 |
| 7 | 评级表 | `ls journal-ratings.xlsx` | 文件存在 |
| 8 | 目录结构 | `ls raw/new-papers/` | 目录存在（空） |

全部通过 ✅ → 可以开始使用。运行 `/forge-health` 做最终验证。

---

## 四、命令速查

| 命令 | 用途 | 示例 |
|------|------|------|
| `/forge-ingest` | 批量摄入 new-papers/ 中所有 PDF | `/forge-ingest` |
| `/forge-ingest <文件>` | 摄入单个文献 | `/forge-ingest raw/new-papers/xxx.pdf` |
| `/forge-search <查询>` | 查询知识库 | 直接提问即可 |
| `/forge-discovery "<关键词>"` | 主动检索新文献（多角度 sci search → 去重 → 下载） | `/forge-discovery "UHTC oxidation" --limit 20` |
| `/forge-weekly` | 周报模式：自动扫描+精选+下载+摄入 | `/forge-weekly` |
| `/forge-think` | 协作思考（围绕材料科学问题展开讨论） | `/forge-think 为什么 Hf 比 Zr 抗氧化但扩散更慢？` |
| `/forge-todo` | 管理待办 | `/forge-todo 添加待办: ...` |
| `/forge-health` | 健康检查 | `/forge-health` |
| `/forge-writing` | 文献锚定型学术写作 | `/forge-writing 写LNO掺杂的Introduction` |

---

## 五、场景化工作流

### 场景 A：阅读一篇新论文（被动摄入）

```
1. 下载 PDF → 放到 SciCrucible/raw/new-papers/
2. /forge-ingest（批量处理 new-papers/ 中所有 PDF）
3. 阅读 LLM 生成的摘要和关联
4. 摄入完成后 PDF 自动移入 raw/papers/<课题>/
5. 如果有想法：/forge-think 讨论
6. 如有后续行动：/forge-todo 添加待办
```

### 场景 B：写论文时查询某个概念

```
1. 直接提问："掺杂如何影响 NCM 正极的表面氧空位形成能？"
2. LLM 从知识库中综合答案，附文献出处
3. 如果需要更深入：/forge-think 展开讨论
4. 讨论中有价值的部分回写到 wiki
```

### 场景 C：记录实验/计算

```
1. 在 projects/<课题>/notes/ 下创建项目笔记
2. 研究成果（手稿）在 projects/<课题>/draft/ 中撰写
3. 定稿后将编译好的 PDF 复制到 SciCrucible/manuscripts/
```

### 场景 D：写论文 Introduction / Discussion

```
1. 发起写作：/forge-writing 写LNO掺杂抑制H2-H3相变的Introduction
2. LLM 先梳理思路 → 搜索 KB → 提出大纲（每段标注 KB 支撑强度）
3. 你审阅大纲 → 调整段落结构 → 确认
4. LLM 逐段起草（一段一审），每段自动引用文献 + 辩证自检
5. 全部段落完成后综合审校 → 输出 .md 文件
6. 定稿 .md → 导入到 projects/<课题>/draft/ 继续编辑
```

### 场景 E：主动发现新文献（定向检索）

```
1. 发起检索：/forge-discovery "高熵碳化物抗氧化烧蚀" --limit 20
2. LLM 分解为 3 个检索角度 → sci search 多角度检索
3. dedup.py 自动去重（对比 literature_index.json 中已摄入文献）
4. 终端显示精简列表（一行一篇，含期刊、分区、相关度评分）
5. 你勾选感兴趣的文献：E1 E3 E5
6. scansci-pdf 批量下载 PDF → raw/new-papers/
7. 手动 /forge-ingest 摄入下载的 PDF
```

### 场景 F：每周文献速递（周报自动化）

```
1. 周一运行：/forge-weekly
2. LLM 按 weekly.yaml 配置的关键词，多课题 ultra_low 免费初扫
3. 精选 2-3 个最有前景方向 → low 模式高精度复跑
4. 去重 + 质量筛选（期刊评级过滤）
5. 推送精简报告（3-5 篇/课题）
6. 你确认后：自动下载 + 自动逐篇摄入
7. 摄入完成后输出摘要：新增概念、更新概念页、新增文献笔记
```

### 场景 G：协作思考（深入讨论材料科学问题）

当你在研究或阅读中遇到困惑时，直接用自然语言与 LLM 展开讨论：

```
/forge-think 为什么 HfC 比 ZrC 抗氧化，但在高熵碳化物中 Ti 反而扩散最快？
```

LLM 会：
1. 从知识库中检索相关文献和概念页
2. 从热力学（Ellingham 图）和动力学（Fick 扩散、Wagner 氧化理论）两个框架分析
3. 对比碳化物、硼化物、氮化物体系中的异同
4. 提出跨领域类比（如 UHTC 的优先氧化 ↔ 正极的阳离子混排）
5. 识别知识空白并建议下一步实验/计算方向

常见用法：

```
/forge-think 优先氧化能否用 DFT 的氧吸附能来预测？
/forge-think 高熵碳化物的鸡尾酒效应在氧化中有体现吗？
/forge-think 正极的 H2→H3 相变和 UHTC 的氧化层剥落有没有共同的力学根源？
```

讨论中有价值的见解会自动提示你归档到 `brainstorming/`。

---

## 六、核心基础设施

### 文献去重系统

`literature_index.json` 是 DOI → 元数据的索引缓存，支持 O(1) 查重：

```
/forge-discovery 检索到新文献
       │
       ▼ dedup.py
  ┌─ 1. 查 literature_index.json（O(1)，优先）
  │     - DOI 命中 → 排除（已摄入）
  │     - DOI 缺失 → 标题归一化比对
  │
  └─ 2. Fallback：实时正则解析 wiki/literature/*.md
        - 索引文件损坏/不存在时自动回退
```

每次 `/forge-ingest` 摄入新文献后，自动更新 `literature_index.json`。

### 期刊质量过滤

基于 `journal-ratings.xlsx`，所有文献摄入时自动标注期刊评级：

| 评级 | 文献脉络策略 |
|------|-------------|
| 评级1/顶级 / 评级1 / 评级2/顶级 / 评级2 | 优先引用，进入项目页文献脉络 |
| 评级3 / 评级4 | 正常摄入，但不进入项目页文献脉络（除非无可替代） |

### 概念页健康评分

`/forge-health` 对每个概念页评估 100 分制健康评分：
- 行数 >300 行：-15 分；>500 行：-15 分
- 关联文献 >15 篇：-10 分
- 超过 6 个月未更新：-20 分；超过 12 个月：-15 分
- 叙述性段落 <3 句：-15 分

---

## 七、维护知识库

### 定期健康检查

建议**每月一次**：`/forge-health`

检查内容：
- 断链、孤立页面、过期内容
- DOI 覆盖率（缺失率 >10% 警告）
- 索引一致性（literature_index.json vs 实际文献页）
- 概念页健康评分（最低分 3 个标红）
- 概念缺失（文献中提到但 concepts/ 中未定义的概念）

### 摄入节奏

- `raw/new-papers/` 支持批量放入多篇 PDF，`/forge-ingest` 一次性处理
- **每批 ≤5 篇**，让 LLM 有足够注意力做深度编译
- 摄入后花几分钟阅读生成的 wiki 页面，确认理解正确
- 在文献笔记的"与我的工作关联"部分手动补充

### 双链文化

- 在 wiki 页面中积极使用 `[[双链]]`
- `[[概念名]]` → `<课题>/concepts/` 或 `通用/concepts/` | `[[文献标题]]` → `<课题>/literature/` | `[[方法名]]` → `<课题>/methods/` 或 `通用/methods/` | `[[projects/项目名]]` → `<课题>/projects/`
- 双链按 basename 解析，与所在课题目录无关；`[[projects/项目名]]` 用路径尾段消歧（概念页与项目页可同名）
- 当你发现两个概念相关但未链接时，手动加上

### 内容质量标准

- 材料科学概念必须有准确定义
- 文献笔记必须包含：研究概述、组分-条件-性质-机制闭环、结构化关键发现（四字段）、分流方法表、与自身工作的关联
- 不确定的内容用 `[待验证]` 标记
- 过时内容用 `[待更新: YYYY-MM-DD]` 标记
- 不覆盖已有内容，增量追加

### weekly.yaml 关键词维护

`skills/forge-discovery/config/weekly.yaml` 控制 `/forge-weekly` 的检索范围。研究方向变化时更新此文件：
- 每个课题 4-8 个关键词
- 覆盖核心方向 + 边缘探索方向
- 连续 4 周摄入率为 0 的关键词 → 考虑替换

---

## 八、自定义研究方向

本知识库默认预置了材料科学方向作为示例。修改为你的研究方向：

1. **编辑 `CLAUDE.md`**：修改标题行和研究领域
2. **编辑 `weekly.yaml`**：替换 `topics` 为你的课题和关键词
3. **编辑 `wiki/index.md`**：修改专题组结构和核心概念
4. **运行 `/forge-health`**：确认所有配置生效

---

## 九、致谢

SciCrucible 建立在以下开源工具和服务之上：

- **[scansci-pdf](https://github.com/nickyoung-hk/scansci-pdf)** — 学术论文下载 MCP Server。支持 13+ 下载源、多所大学 WebVPN、Tor 匿名网络，是本项目文献获取的核心基础设施。感谢作者的杰出工作 🙏
- **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** — Anthropic 的 LLM 编程助手，驱动所有 `/forge-*` 命令的智能行为
- **[SciMaster](https://scimaster.bohrium.com)** — 学术文献检索 API，提供多模式检索与 LLM 排序能力
- **[OpenAlex](https://openalex.org)** — 开放学术图谱，提供 DOI 元数据解析
- **[Semantic Scholar](https://semanticscholar.org)** — 学术搜索引擎，提供文献元数据补充

> 最后更新：2026-07-13（wiki 目录树、数据流图、双链文化同步为「按课题分层」结构）
