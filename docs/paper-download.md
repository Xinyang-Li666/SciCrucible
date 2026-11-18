# DOI 全文与补充材料下载

工具只下载和生成台账，不自动摄入。先确认 OA 或机构订阅权限；认证失败、付费墙或持续验证时停止并报告，转用户手动操作或文献传递。

## 配置

安装 `requests`、`pymupdf`；浏览器工具另需 `playwright` 及本机 Edge。PDF 检查通过 fitz 懒加载 PyMuPDF。环境变量 `ELSEVIER_API_KEY` 提供 Elsevier 凭据；`UNPAYWALL_EMAIL` 提供 Unpaywall 邮箱，缺失则跳过该路线并留因。不要把凭据写入命令、报告或 Git。

## 计划与执行

从仓库根目录运行，DOI 文本一行一个。默认清单 dois.txt，正文 raw/new-papers，状态 outputs/downloads，可传 --dois/--out/--state。实际权限遵循宿主配置，必要时仅审批具体操作。

```bash
python -B scripts/download_papers.py --dois <清单.txt> --dry-run
python -B scripts/download_papers.py --dois <清单.txt> --check
python -B scripts/download_papers.py --dois <清单.txt> --select elsevier,springer --out <正文目录> --state <状态目录>
python -B scripts/download_papers.py --dois <清单.txt> --si --out <正文目录> --state <状态目录>
python -B scripts/download_browser.py --dois <清单.txt> --groups wiley,aip --limit 2 --out <正文目录> --state <状态目录>
python -B scripts/adopt_downloads.py --from <用户下载目录> --out <正文目录> --dois <清单.txt> --dry-run
python -B scripts/download_ledger.py --dois <清单.txt> --out <正文目录> --state <状态目录>
```

--check 会联网，dry-run 不联网；两者不能合用。浏览器运行默认使用 .browser-profile，含 Cookie 的配置与状态不得上传。机构登录用 setup_carsi.py --dois <清单.txt> --state <状态目录>，用户选择自己的机构并亲自认证；manual_assist.py 提供人工下载事件辅助。参数细节以各脚本 --help 为准。

## 路由与停止条件

Elsevier 使用 API 元数据/attachment-eid 和 SI 索引；Springer SI 可从文章页链接发现；OA 可用 Unpaywall、Semantic Scholar 等来源。出版商 URL 与授权可变化，这些是候选策略，不保证可达性或成功率。浏览器遇持续验证时不无限重试，改由用户在自己的浏览器手动下载，再用 adopt_downloads 按 DOI 复制归位。不要自动绕过付费墙。

校验包括 PDF 魔数、体积、页数与可提取文本；单页或小文件可能被判异常，必须核对原文，不能把它们一律当作无全文。SI 放 <out>/SI，避免作为独立文献摄入。HTTP、浏览器与 SI manifest 分别留痕；台账包含 download-summary.md、ILL-list.md 和 ledger.json。只汇报实际统计，缺失明确区分无权限、拦截、缺凭据、无可得副本与解析异常。站点失败后停止或报告，不自动扩大访问范围。
