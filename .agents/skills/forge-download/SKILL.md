---
name: forge-download
description: 按 DOI 清单下载全文与补充材料，生成台账与缺失清单；支持 HTTP、浏览器辅助和手动归位。
---

# forge-download

先读 [下载手册](../../../docs/paper-download.md) 和 [路由参考](references/routes.md)。以用户 DOI 清单为范围，先 dry-run 分组；真实联网前确认授权和环境凭据。工具只下载，不自动摄入。

依赖、路径和参数以 scripts 下六个下载工具的 --help 为准。HTTP 使用 download_papers，浏览器使用 download_browser，人工文件归位使用 adopt_downloads，台账使用 download_ledger；机构认证和人工辅助分别由 setup_carsi、manual_assist 完成。遵循宿主实际权限按需审批，不要求全局放宽。

仅使用 OA 和用户有权访问的机构来源。缺凭据、无权限、验证拦截、异常文件如实记录；持续验证停止并转用户手动下载或文献传递，不无限重试。浏览器登录由用户亲自完成，.browser-profile 不上传。不对不同机构或未来站点承诺成功率。

交付正文、SI 子目录、manifest、台账和缺失原因；不上传私人报告。凭据只从环境变量读取，不写入日志。完成后简报实际到手数、SI数和待补项。
