# SciCrucible 公共 Agent 指令模板

将本模板按宿主约定复制或合并到项目指令文件；它不覆盖本机 AGENTS.md。

- 尽量使用中文。先读 MANUAL.md、docs/agent-quickstart.md 和 docs/release-status.md，确认公开工具与本地扩展的边界。
- 科研问题先用 evidence_query.py probe 轻量查询本地证据，再按候选 read_args 定向展开；不可无条件展开数据库，错误不等于无记录。
- 优先项目 .agents/skills 中存在的版本，否则读公开兼容技能。不猜未安装脚本的能力或参数。
- 不伪造来源、原文、数值和验证结果；缺失、冲突与截断如实说明。私人文献、笔记、数据库不得发往外部插件。
- 建库扩展可用时，主代理审计并冻结计划，子代理执行，主代理独立验收。正式入库、真实模型调用和门禁放宽遵守独立授权。
- 批次只发送 pending 请求，held 不发送；失败不自动重试，conflict/insufficient 不自动重问。每批新授权与账本，核对来源哈希、模型、额度；固定来源 grant 仅在已批准范围内复用。
- 一篇或一个小批次一会话；完成后写 session_handoff，下一批全新会话先 check 再按 next_command 读取。响应超过 150 次或单次输入超过 150k tokens 时到安全节点交接。
- 不发布 raw、wiki、database、outputs、评测答案、凭据或授权账本；框架提交只选择明确可公开文件，不自动添加 AI 联合署名。
