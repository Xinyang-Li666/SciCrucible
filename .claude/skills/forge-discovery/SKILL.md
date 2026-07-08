---
description: 主动文献发现 — SciMaster 检索 → 去重 → 用户勾选 → 下载 → 摄入
---

# /forge-discovery — 主动文献发现

用户输入关键词 → 多角度 SciMaster 检索 → 去重 → 用户勾选 → 下载。下载后手动触发 `/forge-ingest` 摄入。

> 每周自动速递请用 `/forge-weekly`

---

## 铁律

> 所有文献内容必须来自本次 `sci search` 的真实返回。搜不到就如实报告"未检索到相关文献"，那本身就是结论——**绝不从记忆或训练数据填补**。

---

## 证据账本规则

- **查询编号**: q1, q2, q3… — 每条查询的 query 原文、mode、返回数、采用数
- **证据编号**: E1, E2, E3… — 每篇入选文献的 title, authors, year, doi, abstract, query_id, 采用理由
- 输出中的每条结论能回指到证据编号（如「E1 ← q2」表示 E1 来自查询 q2）

### 去重规则

1. DOI 完全相同 → 同一篇
2. DOI 缺失 → 标题归一化后相同 → 同一篇
3. 标题高度相似（>90%）但年份/作者不同 → 保留，标注为可能相关版本

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

**目的**：不让完整 JSON 进上下文（50 篇完整 JSON ≈ 57,000 tokens）。只提取必要字段：

```bash
PYTHONIOENCODING=utf-8 python -c "
import json, glob, os
files = sorted(glob.glob('raw/search-results/json/search-results-*.json'), key=os.path.getmtime)
# 取本轮检索生成的所有新文件（按时间倒序取最近 N 个）
new_files = files[-3:] if len(files) >= 3 else files
all_papers = []
for f in new_files:
    data = json.load(open(f, encoding='utf-8'))
    papers = data if isinstance(data, list) else data.get('results', data.get('data', []))
    all_papers.extend(papers)

for i, p in enumerate(all_papers):
    abs_zh = (p.get('abstract') or '')[:200]
    venue = p.get('venue') or 'N/A'
    print(f'E{i+1} | {p.get(\"selectScore\",0):3d} | {p.get(\"year\",\"?\")} | {p.get(\"doi\",\"\")} | {venue} | {(p.get(\"title\") or \"\")[:120]}')
    if abs_zh:
        print(f'    摘要: {abs_zh}')
"
```

输出约 3,000-5,000 tokens（含摘要截断），可控。

### Step B4 — 去重

```bash
cd D:/科研/kb
python .claude/skills/forge-discovery/scripts/dedup.py raw/search-results/json/search-results-*.json --index wiki/literature_index.json --wiki-dir wiki/literature/
```

- 索引存在 → O(1) 查找（快）
- 索引不存在 → 自动 fallback 到实时正则解析 `wiki/literature/*.md`
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

用户输入 E 编号后，生成临时 DOI 列表并批量下载：

```python
PYTHONIOENCODING=utf-8 python -c "
import json, glob, os

# 读取去重后的结果
files = sorted(glob.glob('raw/search-results/json/search-results-*.json'), key=os.path.getmtime)
all_papers = []
for f in files[-3:]:
    data = json.load(open(f, encoding='utf-8'))
    papers = data if isinstance(data, list) else data.get('results', data.get('data', []))
    all_papers.extend(papers)

# 用户勾选的 E 编号（从 1-indexed 转换）
selected = [E1, E3, E5]  # ← 替换为实际用户输入
dois = []
for idx in selected:
    p = all_papers[idx - 1]
    doi = p.get('doi', '')
    if doi:
        dois.append(doi)

with open('raw/search-results/dois.txt', 'w') as f:
    f.write('\n'.join(dois))
print(f'已写入 {len(dois)} 个 DOI')
"
```

```bash
# 默认策略：仅合法渠道
scansci-pdf batch raw/search-results/dois.txt --output D:/科研/SciCrucible/raw/new-papers/ --strategy legal_only

# 如果用户传了 --allow-scihub，用 fastest（含 Sci-Hub 兜底）
scansci-pdf batch raw/search-results/dois.txt --output D:/科研/SciCrucible/raw/new-papers/ --strategy fastest
```

下载完成后：
1. 输出成功/失败清单（格式见下方）
2. 删除临时 `dois.txt`
3. PDF 留在 `raw/new-papers/`，提醒用户手动 `/forge-ingest` 摄入

```
✅ 下载成功 (7/10):
   - Smith2025_CRISPR.pdf
   - ...

❌ 下载失败 (3/10):
   - DOI: 10.1016/... (原因: 付费墙，未登录)
   - DOI: 10.1016/... (原因: 网络超时)
   - DOI: 10.1016/... (原因: DOI 无效)
```

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
- 去重排除 N 篇 (DOI 已存在于 wiki/literature/)
- 评级过滤 N 篇（低评级期刊）

## 下载结果
- 成功: N 篇
- 失败: N 篇（列出失败原因）

## 下一步
- 输入 `/forge-ingest` 手动摄入 PDF
```

### Step B8 — 写入批次状态

```python
PYTHONIOENCODING=utf-8 python -c "
import json, os
from datetime import datetime

# 确保目录存在
os.makedirs('raw/search-results/batches', exist_ok=True)

batch = {
    'batch_id': 'discovery-{topic_slug}-{date}',
    'created': '{timestamp}',
    'mode': 'discovery',
    'papers': {
        'E1': {'doi': '...', 'status': 'downloaded', 'pdf': '...'},
        'E2': {'doi': '...', 'status': 'download_failed', 'reason': '付费墙'},
        'E3': {'doi': '...', 'status': 'filtered'},
    }
}
path = 'raw/search-results/batches/discovery-{topic_slug}-{date}.json'
with open(path, 'w', encoding='utf-8') as f:
    json.dump(batch, f, ensure_ascii=False, indent=2)
print(f'批次状态已保存: {path}')
"
```

状态流转：`filtered → download_queued → downloaded → ingested`（或 `download_failed` / `ingest_failed`）

---

## 会话级缓存

- 同一会话（当天）内，相同 query + mode → 复用结果，不重复调用 `sci search`
- 跨会话 / 不同日期 → 重新检索（文献索引在变，旧结果可能过时）

## 额度管理

- 批量检索超过 5 次前，先运行 `sci usage`
- 余额不足时：
  - 告知用户剩余额度
  - 建议降级方案：全部 `ultra_low` / 减少检索角度 / 充值
- 不自动决定——等待用户选择

## 错误处理

| 情况 | 行为 |
|------|------|
| `sci` 未安装 | 给出安装命令 + 停止 |
| 认证失败 (401) | 提示 `sci init` + 停止 |
| 网络超时 | 建议换 `ultra_low` 或检查网络 |
| **返回空结果** | **如实报告，这是结论本身**，不伪造 |
| 额度耗尽 | 显示 `sci usage` + 建议充值，不伪造 |
| sci search JSON 格式变化 | `.get()` 容错，缺失字段显示 "N/A" |
| scansci-pdf 版本不兼容 | 捕获异常，提示检查版本 |
| 下载 PDF 是摘要页 | 检查文件大小（<100KB 可能为摘要），提示用户 |
| 批量下载中断 | scansci-pdf 支持断点续传，重新运行 batch 即可 |
| 磁盘空间不足 | 周报中提示磁盘使用情况 |
| E 编号输入错误 | 验证 E 编号范围，提示有效范围 |

---

## 版权免责声明

⚠️ **Sci-Hub 使用警告**：本工具内置 Sci-Hub 下载能力，但：

- **默认关闭**：所有下载默认使用 `--strategy legal_only`（Elsevier API + WebVPN/CARSI + OpenAlexOA）
- **用户自主决策**：需用户显式传入 `--allow-scihub` 才启用 Sci-Hub 兜底
- **仅限个人研究**：下载的论文仅用于个人学术研究，不得再分发
- **建议优先使用合法渠道**：完善 CARSI / WebVPN / 校园网等机构订阅渠道
- 使用者应遵守所在机构的电子资源使用协议和当地著作权法

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
