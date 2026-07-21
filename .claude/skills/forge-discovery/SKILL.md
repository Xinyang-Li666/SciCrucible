---
description: 主动文献发现 — SciMaster 检索 → 去重 → 用户勾选 → 下载 → 摄入。当用户想搜新文献、说"帮我找X方向的论文"、"最近有什么关于Y的研究"、需要文献调研时触发，即使用户没有说/discovery
---

# /forge-discovery — 主动文献发现

用户输入关键词 → 多角度 SciMaster 检索 → 去重 → 用户勾选 → 下载。下载后手动触发 `/forge-ingest` 摄入。

> 每周自动速递请用 `/forge-weekly`

---

## 共享规则

> **铁律、证据账本规则、去重规则、Python 脚本、错误处理、额度管理、版权声明** 详见 `references/shared-rules.md`。以下仅列出 discovery 特有流程，共享部分不再重复。

---

## 触发

### 触发

```
/forge-discovery "关键词/课题描述"
```

可选参数：
- `--limit N`（默认 20）
- `--year-from YYYY`
- `--year-to YYYY`
- `--allow-scihub`（启用 Sci-Hub 兜底下载）

### Step B1 — 前置检查

```bash
sci --version
```

如果 `sci` 未安装，给出安装命令并停止。

```bash
sci usage
```

如果额度不足，告知用户剩余额度，建议：
- 全部用 `ultra_low` 模式
- 减少检索角度
- 充值

### Step B2 — 多角度检索

将用户输入分解为 3 个检索角度（同义词、上下位概念、不同侧重）。每个角度运行一次检索：

```bash
cd D:/科研/SciCrucible/raw/search-results
sci search "<角度1>" --limit <N> --mode low
sci search "<角度2>" --limit <N> --mode low
sci search "<角度3>" --limit <N> --mode low
```

查询编号 q1, q2, q3。如果额度紧张（剩余 <10 次），先用 `ultra_low` 扫描一轮再决定。

如果用户传了 `--year-from` 或 `--year-to`，追加到每个 `sci search` 命令中。

### Step B3 — Python 预过滤

执行 `references/shared-rules.md` §Python 预过滤 中的脚本，提取必要字段，控制 token 消耗。

### Step B4 — 去重

```bash
cd D:/科研/SciCrucible
python .claude/skills/forge-discovery/scripts/dedup.py raw/search-results/json/search-results-*.json --index wiki/literature_index.json --wiki-dir wiki
```

- 索引存在 → O(1) 查找（快）
- 索引不存在 → 自动 fallback 到实时正则解析 `wiki/**/literature/*.md`（递归覆盖各课题）
- 输出：去重报告（stderr）+ 去重后 JSON（stdout）

### Step B5 — 展示结果 + 等待用户勾选

终端精简列表（一行一篇）：

```
🔍 检索主题: "high entropy ceramic oxidation resistance"
   检索时间: 2026-07-06 14:30
   检索角度: q1 "high entropy carbide oxidation" (20篇·low)
             q2 "multi-component ceramic ablation" (20篇·low)
             q3 "HEC oxidation resistance high throughput" (20篇·low)

结果: 60篇 → 去重 5篇 → 有效 55篇

 E1  Chen et al. 2025 — "High entropy carbide oxidation..."  Acta Mater (评级1/顶级)  score:92  ← q1/q2
 E2  Wang et al. 2026 — "..."  J Am Ceram Soc (评级2/顶级)  score:85  ← q1
 E3  ...

─────────────────────────────────────────────
待下载: 请输入 E 编号 (如 "E1 E3 E5 E7") 或输入 "all" 全部下载
```

**标注规则**：
- 每篇标注分数、期刊、发表年份
- 如果期刊在已有知识库中有期刊评级数据，标注评级
- 标注来源查询（← q1/q2/…），跨查询命中的标注多个

### Step B6 — 下载选中文献

用户输入 E 编号后，执行 `references/shared-rules.md` §DOI 提取 + 批量下载 中的脚本。

下载完成后：输出成功/失败清单，删除临时 `dois.txt`，PDF 留在 `raw/new-papers/`，提醒用户手动 `/forge-ingest` 摄入。

### Step B7 — 写入详细报告

自动生成 Markdown 报告：`raw/search-results/reports/discovery-{topic-slug}-{date}.md`

报告结构（完整版，终端不显示这些细节）：

```markdown
---
date: 2026-07-06
mode: discovery
topic: <用户搜索词>
queries: [{q1: "...", mode: "low", returned: 20, accepted: 3}, ...]
---

## 一眼结论
在 XX 方向发现 N 篇潜在相关文献，其中 E1 (Author Year) 最值得关注…

## 候选文献

### E1 | Authors Year | [DOI](https://doi.org/…)
- **期刊**: Journal Name (评级, IF X.X)
- **score**: 95
- **摘要**: 中文翻译摘要（200 字以内）
- **采用理由**: 为什么推荐这篇（与检索主题的关联）
- **来源查询**: q2

### E2 | …

## 检索透明度
- q1: "query text" — low, 20篇, 采用 3篇
- q2: "query text" — low, 20篇, 采用 5篇
- q3: "query text" — low, 20篇, 结果为空（无相关文献）

## 已排除
- 去重排除 N 篇 (DOI 已存在于 wiki/**/literature/)
- 评级过滤 N 篇（低评级期刊）

## 下载结果
- 成功: N 篇
- 失败: N 篇（列出失败原因）

## 下一步
- 输入 `/forge-ingest` 手动摄入 PDF
```

### Step B8 — 写入批次状态

执行 `references/shared-rules.md` §批次状态写入 中的脚本，mode 设为 `discovery`。

---

## 共享规则

以下规则详见 `references/shared-rules.md`：
- **会话级缓存** — 同会话复用结果
- **额度管理** — 余额检查 + 降级建议
- **错误处理** — 11 种异常情况的行为表
- **版权免责声明** — Sci-Hub 使用警告

---

## 报告输出物

| 输出物 | 位置 | 说明 |
|--------|------|------|
| 终端列表 | stdout | 精简一行一篇（E编号+标题+期刊+score） |
| Markdown 报告 | `raw/search-results/reports/` | 完整版（含摘要翻译、检索透明度、采用理由） |
| 批次状态 | `raw/search-results/batches/` | `.batch-state.json` |
| 下载 PDF | `raw/new-papers/` | 走原有 `/forge-ingest` 摄入入口 |

---

## 关联脚本与配置

| 文件 | 用途 |
|------|------|
| `scripts/dedup.py` | 去重脚本（--index 缓存 + --wiki-dir fallback） |
| `config/weekly.yaml` | 周报模式关键词配置 |
| `references/sci-cli.md` | SciMaster CLI 参考手册 |
