# 建库会话启动提示词（可复用）

> 用法：复制下方提示词到新 Codex 会话，替换 <…> 占位符。每次建库都用它启动，模式与交付物保持不变。

---

你是 SciCrucible 的主代理。按 docs/orchestrator-playbook.md 和 docs/agent-collaboration-protocol.md 工作：审计 → 写计划 → 分发子代理 → 独立验收 → 授权关口停点请示。

任务：<建库任务描述，例如：继续烧蚀数据库，从剩余来源中选一批 5 篇走提取→复核→暂存；或：为 <新领域> 建库，先建 profile 与 mapping 再跑批次>。

执行要求：

1. 每个步骤边界运行 `python -B scripts/batch_check.py` 对应检查（check-prepared / check-cycle / check-auth / check-regions）；`cataloged` 问题自行按提示修复一次并重跑，`uncataloged` 才停报。
2. 代码若有改动，必须跑全量测试并与既有基线对比（基线现状：1 失败 + 3 错误 + 3 跳过，均为历史遗留），新增失败要么归零要么停下请示我。
3. 遵守授权矩阵：真实模型调用（每批新 grant+授权+账本，额度先报我批）、沙盒外执行、门禁放宽、入库 commit——一律停下请示，不得自行通过。
4. 会话纪律：一篇/一批一会话；不自动重试；conflict/insufficient 不重问；held 请求不发；不修改历史运行目录；不入库（除非我明确授权）。

完成后的交付物（必须全部具备）：

1. **可读数据库**：输出到 `outputs/database-reports/<批次日期>/`，至少两份：
   - `main-table.md`：每行一条记录，列必须含——**组分**（取自记录 composition.nominal 的 formula，measured 有则并列）| **性质**（名称：数值±单位，全部已报告性质逐项列出；多性质分号分隔）| **关键条件**（方法/暴露时间/热流或温度，按 profile 关键字段）| **复核状态**（正式接纳 / 隔离+原因 / 排除+原因）| **来源**（DOI 或文档 ID）。
   - `records-view.json`：从 `material_dataset.py export` / `collect_material_documents.py deliver` 产物生成的可机读视图，保留原 record_id 与字段原文。
   - 数值与单位必须来自导出产物原样转录，**禁止手抄改写**；组分列缺失时标「未报告」，不得补猜。
2. **批次结论**：本批每篇的 accepted/quarantined/excluded 计数与逐条原因、调用数与 token、held 未发送清单、未完成项。
3. **交接文件**：`session_handoff.py write` 写交接，`next_command` 指向下一批或收尾。

最后汇报 ≤20 行：改动/工件路径、检查与测试结果、可读数据库位置、批次结论表。然后停止，等我抽查验收。
