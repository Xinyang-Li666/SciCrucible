# v2.0.0 公开同步状态（2026-11-16）

本次为文档与独立工具同步；进阶材料数据管线尚未完整公开。

## 已发布范围
- 项目 Agent 技能入口（`.agents/skills/`），通用 Agent 启动说明与使用手册。
- 有界本地证据查询、摄入预处理、跨平台摄入入口、批次交接。
- 仅发布代码与通用配置，不包含个人 wiki、PDF、数据库、授权文件和运行结果。

## 尚未公开的本地扩展
`forge-db` / `forge-extract` 的完整材料数据管线、复核发送器、批次检查器及 MP 适配器仍需本地扩展代码。技能文档介绍契约，不代表克隆此版本即可运行所有高级命令。执行前检查文件是否存在；缺失时停止并说明，不能伪造执行结果。

发布审计发现 `scripts/material_collection/program_rule_prose_five.py` 含约十万行逐篇规则、论文引文和数据。该管线需要将公开通用实现与私有来源绑定规则拆分，完成依赖闭包检查后再发布。本次不上传这些源码及其私人来源。

## 验证
- 发布工具定向测试：evidence_query 22 项、ingest_prepare 4 项、session_handoff 1 项，全部通过。
- 现有完整本地工作区基线：970 项测试，1 failure、3 errors、5 skipped。此结果不等于公开分支测试结果。
- 已知问题：缺少 pdfplumber；recover_completed_claims 导入失败；collection selection 的 risk_flags 查询 KeyError；Al–Cu controller 新任务调用断言失败。
- 未执行科研模型调用、论文下载或数据库入库。

本轮按用户授权发布 v2.0.0，并在备份后移除历史提交中的历史联合署名，保留真实作者、日期和代码内容；不变更 GitHub 协作者访问权限。历史重写与远端同步由主代理执行并验收，完成情况以最终发布结果为准。GitHub Contributors 统计可能缓存，署名移除后页面显示可能延迟更新。

