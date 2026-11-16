# SciCrucible v2.0.0 用户手册

> 基于 Claude 的科学智能知识库：从文献摄入—知识分析—科学讨论—学术写作的全闭环。

本手册区分公开工具与本地进阶扩展。首先阅读 [发布状态](docs/release-status.md)。

## 安装与目录

```bash
git clone git@github.com:Xinyang-Li666/SciCrucible.git
cd SciCrucible
python --version
```

建议 Python 3.11+。所有命令均从仓库根目录执行；不需要在根目录内再建立一层 SciCrucible。Agent 应能读取 Markdown 技能并调用本地脚本。现有 `.claude/skills/` 是兼容入口，其他 Agent 的配置见 [接入指南](docs/agent-quickstart.md)。

Claude 运行环境可读取现有兼容技能；其他 Agent 按相同来源与授权契约接入，不需要把项目限定为单一宿主。

按实际操作安装依赖：PDF 解析需要 `pymupdf`，期刊评级表读取需要 `openpyxl`。部分进阶扩展另需 `pdfplumber` 等依赖，不能把缺依赖误报成无数据。SciMaster CLI 与 scansci-pdf 为文献发现/下载的可选集成，配置凭据留在本地，不提交到 Git。已有宿主工具可按授权范围使用，不要求所有用户采用同一模型服务。

根目录包含 README、MANUAL、兼容技能与 scripts；运行时知识分别保存在 `raw/`、`wiki/`、`brainstorming/`、`database/` 等本地目录。它们不随框架发布。课题项目目录与知识库平级，使用 `../projects/<课题>/{data,figures,draft,notes}/`。

## 配置研究方向

读取你所用 Agent 的项目指令。可参考 [AGENTS.public.md](AGENTS.public.md) 写入自己的 AGENTS.md；兼容运行环境可读取 CLAUDE.md。替换课题名称与本机路径，保留来源、授权和错误处理规则。按需配置发现技能中的 weekly.yaml、期刊评级表与下载工具。不要上传私人论文、笔记、数据库、API Key、运行账本或评测答案。

## 文献摄入

将新 PDF 放入 `raw/new-papers/`，先做本地预检：

```bash
python -B scripts/ingest_prepare.py raw/new-papers/
```

Windows 可使用 `scripts/forge-ingest.ps1`，Bash 可使用 `scripts/forge-ingest.sh`。预检生成 `.kiro/.ingest_cache/` 中的 manifest、缓存文本与报告。ready 仅表示自动检查完成；needs_review、error 必须核对。DOI 候选、页数与稀疏文本警告不能代替人工确认。预检不会完成 wiki 编译或自动移动原始论文。

随后让 Agent 读取 `forge-ingest/SKILL.md`，执行内容核对、笔记编译、索引维护与归档。文献页写入 `wiki/<课题>/literature/`，共享同一机制的知识合并到中颗粒度概念页，通用机制写入 `wiki/通用/`，用双链互联，增量追加而非覆盖。

## 本地查询与科研讨论

先轻量探测：

```bash
python -B scripts/evidence_query.py probe --query "材料 性质 机制"
```

probe 会刷新轻量目录，无需先 build。最多输出 5 个候选、合计默认 1600 字符；对相关候选优先原样采用其 `read_args`，再运行 expand。数据库只选择所需记录、字段和数量；记录 ID 使用可重复的 `--record-id`，字段使用 `--columns`。`--where` 是 JSON 精确匹配，不是 SQL。先用 `expand --help` 核对参数。

必须区分匹配数、返回数与截断原因。错误不是无记录，空候选只表示本地未匹配。回答给出笔记路径/行号或记录定位。相同问题且证据指纹未变时复用已读证据；新增条件或证据不足才继续检索。私人内容不发送到外部插件。

## 知识分析、科学讨论与学术写作

按对应技能使用 forge-search、forge-think、forge-writing、forge-todo、forge-health。写作先梳理证据与大纲，再逐段起草并核对引用；缺失证据明确标记。主动发现/每周更新依赖可选检索与下载工具，工具失败如实报告，不宣称检索无结果。

## 进阶材料建库：本地扩展工作流

**本节是接入契约，完整管线尚未公开，不是克隆后即可执行的操作教程。** 查看 [发布状态](docs/release-status.md)，确认实现与领域配置可用后才执行。

主入口为 forge-db：审计 → 冻结计划 → 子代理执行 → 主代理独立验收 → 授权停点。forge-extract 负责冻结文献与逐字段证据绑定；领域 profile 定义性质、单位、关键条件和可空性，mapping 绑定原字段。流程为 prepare → gate/复核 → stage → 显式 commit → export。stage 不等于正式入库，离线测试不等于真实科研准确性。

复核由 review-cycle 生成请求，只发送 pending-requests.json；held-requests.json 不发送。用 review-cycle-finish 合并回答并暂存。模型失败不自动重试；conflict/insufficient 不自动重问，查原文或隔离。字段、来源或配置变更要重新核对指纹和复核适用性。

固定来源集的常驻 grant 须经用户明确批准，可在范围内跨篇复用；每批仍需新的授权文件与账本，核对来源哈希、模型、额度和 grant 指纹。宿主审批、门禁放宽与每次正式入库授权分别遵守。进阶批次按适用的 batch_check 子命令检查 prepared、cycle、auth、regions；cataloged 只按提示修复一次，uncataloged/checker_failed 停报。

MP 计算数据使用独立来源适配，不能当作实验事实或按同化学式自动匹配样品。Key 仅从本地凭据或 MP_API_KEY 环境变量读取；缺记录、缺字段、null、0 与失败分别留痕，不自动翻页、重试或入库。

## 会话交接与验证

一篇文献或一个小批次一会话。完成后编写符合脚本 schema 的输入，运行 `python -B scripts/session_handoff.py write --input <输入JSON> --output <新交接文件>`，绑定完成工件哈希、范围、授权引用、阻塞项与 next_command。脚本不推断批次状态。

下一批开启全新会话，不 resume/fork，先运行：

```bash
python -B scripts/session_handoff.py check --handoff <交接文件>
```

通过后只读取 next_command 所需文件。响应超过 150 次或单次输入超过 150k tokens 时到安全节点交接。代码改动后运行相关检查及全量 unittest，与实际基线比较；发布状态已列出当前限制，不将失败隐藏为通过。
