---
name: forge-db
description: 以主代理模式构建或继续 SciCrucible 材料数据库。用于新领域建库、继续批次、提取复核与可读数据库交付。
---

# /forge-db — 主代理模式建库

目标是交付有原始来源、复核状态和关键条件的组分-性质主表。本技能是操作入口，不构成真实模型调用、门禁放宽或入库授权。

## 按任务状态进入

1. **新领域或新库**：审计领域 profile、mapping、来源和既有数据库契约；先计划配置与离线验证，再进入首个小批次。
2. **继续批次**：先做下文的 handoff check，仅据 `next_command` 读取必要文件。交接无效时审计当前工件并立新计划，不猜上批状态。
3. **已有批次验收或交付**：核对现存 prepared、cycle、授权、账本和导出产物；只补缺失的离线验收与报告，不重复发送已完成请求。
4. **只审计或修技能/脚本**：按用户范围完成该工作。没有真实批次就不虚构调用数、记录、主表或交接文件。

按 `docs/orchestrator-playbook.md` 与 `docs/agent-collaboration-protocol.md` 工作：主代理据文件和行号审计范围、来源、门禁和实测基线 → 写计划（`docs/superpowers/plans/`，写死根因、禁改范围、阶段验收线、回滚和授权停点）→ 按篇或独立小批次给子代理自包含指令（路径、允许操作、检查、停止条件）→ 独立重跑适用检查/测试、离线重放并核对导出记录、哈希和账本 → 超出既有授权范围时停点请示。主代理不亲自执行批量改动，不采信子代理自称通过；`uncataloged` 先诊断再升级。启动参考见 `docs/superpowers/prompts/db-build-bootstrap.md`。

## 单篇增量审计

按 [建库单篇增量审计](../../../docs/db-incremental-audit.md) 一篇只建一次审计包：冻结源指纹、目标范围、逐字段原文定位、内部标签来源分类、源内冲突和人工例外。来源及候选哈希未变时复用定位，人工深读仅针对新增、变更、无证据或矛盾字段；失效条件触发局部或整篇重审。常规篇计划可引用已冻结领域背景，只写本篇差异与停止条件，仍须保存计划文件。主代理独立验收保留对应 `batch_check`、哈希/账本和程序化逐行主表对照；人工复看不一致及抽样行。不得以增量审计替代真实复核或正式入库门禁。

## 执行要求

1. 对存在的对应工件在步骤边界运行 `python -B scripts/batch_check.py`：准备/计划后 `check-prepared <prepared目录>`，冻结后 `check-cycle <周期目录>`，发送前 `check-auth --ledger <账本> <授权JSON>`，渲染后 `check-regions --source-root <项目根> <source-regions.json>`。`cataloged` 按提示自行修复一次并重跑；`uncataloged` 或 `checker_failed` 立即停报主代理，不得绕过。该检查器不验证 SKILL.md。
2. 代码改动后主代理运行 `python -B -m unittest discover -s scripts -p "test_*.py"`，与执行前实测基线对比；新增失败须修复，不能修复则停下请示。不能把历史基线当作永久通过标准。
3. 固定来源集的常驻 grant 经用户明确批准后可跨篇复用：每批新授权文件和账本绑定 grant 指纹并核对来源哈希、模型和额度；范围内不逐篇请示，超范围再请示。宿主审批和入库授权仍单独遵守。
   首次真实发送前对领域共用 profile/mapping 做一次零调用 adapter 小样本检查，指纹未变则跨篇复用。document-021 曾因 mapping 缺 `field_provenance` 且 profile 把未报告的 `quench_method` 列为 critical，使 10/10 提取值无法准入；配置预检应拦截此类问题。
4. 会话纪律：一篇/一个小批次一会话；批次完成写 `session_handoff.py write` 并结束。下一批开全新会话，不 resume/fork；先运行 `python -B scripts/session_handoff.py check --handoff <路径>`，再只读取 `next_command` 所需文件。响应超过 150 次或单次输入超过 150k tokens 时，到安全节点交接。
5. 复核仅发送 `review-cycle` 生成的 `pending-requests.json`；`held-requests.json` 不发；回答用 `review-cycle-finish` 合并暂存。模型调用不自动重试，conflict/insufficient 不重问；不能确认则查原文或隔离。不修改历史运行目录，未获单独授权不入库。
6. 硬规则同 playbook 第 5 节（不同模型臂分账本、收集流下游输出目录放项目外、`--prepared` 传目录、参数写全、复用 source_regions、SI 版本字符串、验收带口径）。

## 交付物（每批完成必备）

1. **可读数据库**：批次完成且有真实导出产物时，从 `material_dataset.py export` / `collect_material_documents.py deliver` 产物程序化生成 `main-table.md` 和 `records-view.json`，默认放 `outputs/database-reports/<批次日期>/`；收集流 source_root 为项目根时下游输出改放项目外。导出缺失或校验未过则标「未交付」，不得从复核摘要手填记录。
   - `main-table.md` 每条记录一行，列含 **记录 ID | 组分 | 性质 | 关键条件 | 复核状态 | 来源**。组分取 composition.nominal.formula，measured 有则并列；性质逐项保留全部已报告名称、原值与原单位；条件按 profile 列方法、暴露时间、热流/温度等适用字段；状态写 accepted/quarantined/excluded 及逐条原因；来源写 DOI/文档 ID 和可追溯定位。缺失标「未报告」，不补猜；不同方法、条件、量纲不自动混合或排序。
   - `records-view.json` 保留原 record_id、字段原文和来源定位，使主表可逐行回查；质量筛选视图不是可直接回灌记录或训练标签。
   - 验收逐行比对 ID、组分、性质原值/原单位、条件、状态、来源与导出产物，核对记录数和状态统计口径。
2. **批次结论**：每篇 accepted/quarantined/excluded 的计数与逐条原因、调用数与 token、held 未发送清单、未完成项；所有数字标明统计口径。
3. **交接文件**：`session_handoff.py write`，next_command 指向下一批或收尾。

## 结束汇报

≤20 行：改动/工件路径、检查与测试结果、可读数据库位置、批次结论表。然后停止，等用户抽查验收。
