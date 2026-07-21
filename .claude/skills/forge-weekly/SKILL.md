---
description: 每周文献速递 — 多课题自动扫描 → 精选 → 下载 → 自动摄入，近 3 月文献。当用户想要文献更新、说"这周有什么新论文"、"帮我追踪最新文献"、定期文献速递时触发
---

# /forge-weekly — 每周文献速递

自动扫描多个课题的最新文献，精选后自动摄入。

| | `/forge-discovery` | `/forge-weekly` |
|------|:--:|:--:|
| 触发 | 用户随时输入关键词 | 用户输入 `/forge-weekly` |
| 检索范围 | 不限时间窗口 | 近 3 月 |
| 结果数 | 默认 20 篇/角度 | 10 篇 ultra_low 初扫 → 精选 3-5 篇/课题 |
| 下载后 | 手动触发 `/forge-ingest` | **自动逐篇摄入** |

---

## 共享规则

> **铁律、证据账本规则、去重规则、Python 预过滤/下载/批次脚本、错误处理、额度管理、版权声明** 详见 `../forge-discovery/references/shared-rules.md`（与 forge-discovery 共用）。以下仅列出 weekly 特有流程，共享部分不再重复。

---

## 触发

```
/forge-weekly
```

可选参数：
- `--topic <课题名>`（仅检索指定课题，如 `超高温陶瓷`）
- `--allow-scihub`

---

## Step 1 — 前置检查

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

---

## Step 2 — 读取关键词配置

从 `D:/科研/SciCrucible/.claude/skills/forge-discovery/config/weekly.yaml` 读取各课题关键词。

如果 `weekly.yaml` 不存在或为空：
1. 从 `wiki/index.md` 和项目页中自动提炼各课题关键词
2. 列出提炼结果，提示用户确认后写入 `weekly.yaml`
3. 用户确认后继续

如果用户传了 `--topic`，仅读取指定课题的关键词组。

---

## Step 3 — 多关键词扫描（ultra_low，免费）

每个课题的每个关键词 → `sci search --limit 10 --mode ultra_low`。

```bash
cd D:/科研/SciCrucible/raw/search-results

# 课题1: 超高温陶瓷
sci search "UHTC oxidation resistance" --limit 10 --mode ultra_low
sci search "HfC-SiC composite ablation" --limit 10 --mode ultra_low
# ... (更多关键词)

# 课题2: 锂离子电池正极材料
sci search "high nickel cathode degradation" --limit 10 --mode ultra_low
# ...
```

查询编号 q1, q2, q3…

目的：宽扫，锁定本周有潜力的方向。`ultra_low` 免费，不消耗额度。

---

## Step 4 — 精选复跑（low，消耗额度）

分析 Step 3 中所有 ultra_low 结果，选出最有前景的 2-3 个方向（跨课题），用 `low` 模式高精度复跑：

```bash
sci search "<最有前景方向1>" --limit 20 --mode low
sci search "<最有前景方向2>" --limit 20 --mode low
sci search "<最有前景方向3>" --limit 20 --mode low
```

---

## Step 5 — Python 预过滤 + 去重

### 5a — Python 预过滤

执行 `../forge-discovery/references/shared-rules.md` §Python 预过滤 中的脚本。

### 5b — 去重

```bash
cd D:/科研/SciCrucible
python .claude/skills/forge-discovery/scripts/dedup.py raw/search-results/json/search-results-*.json --index wiki/literature_index.json --wiki-dir wiki
```

- 索引存在 → O(1) 查找（快）
- 索引不存在 → 自动 fallback 到实时正则解析 `wiki/**/literature/*.md`（递归覆盖各课题）
- 输出：去重报告（stderr）+ 去重后 JSON（stdout）

---

## Step 6 — 质量筛选

对去重后的结果进行质量筛选：

| 维度 | 阈值 | 操作 |
|------|------|------|
| 期刊评级 | 优先 评级1/Top | 低评级期刊仅无更好文献时纳入 |
| 相关度 | 标题+摘要 ≥2 个课题核心词 | 排除仅关键词命中但实质不相关 |
| 去重 | DOI 与已有文献比对 | 完全排除 |
| 期刊黑名单 | MDPI 预警期刊 | 排除（待维护黑名单） |

最终精选 **3-5 篇/课题**。每篇分配 E 编号（E1, E2, E3…）。

---

## Step 7 — 推送报告，等待用户确认

终端精简列表：

```
📰 本周文献速递 · 2026-07-06
═══════════════════════════════════════════

 🔥 超高温陶瓷 (4篇)
 E1  Kim et al. 2026 — "Oxidation kinetics of HfC-SiC..."  J Eur Ceram Soc (评级1/顶级)  score:95
 E2  Zhang et al. 2025 — "Ablation behavior of UHTC..."  Corros Sci (评级1)  score:88
 E3  ...

 ⚡ 锂离子电池正极材料 (3篇)
 E5  Wang et al. 2026 — "High-nickel cathode degradation..."  Adv Energy Mater (评级1/顶级)  score:91
 E6  ...

选择操作: [全部下载] [逐篇勾选 E1 E3 E5] [本周跳过]
```

---

## Step 8 — 下载 + 自动摄入

用户确认后：

### 8a — 下载选中文献

执行 `../forge-discovery/references/shared-rules.md` §DOI 提取 + 批量下载 中的脚本。下载完成后输出成功/失败清单，删除临时 `dois.txt`。

### 8b — 自动逐篇摄入

```
📥 下载完成 (4/4)
📝 开始自动摄入...

[1/4] 摄入 Kim2026_Oxidation.pdf...
  ✅ 新增文献笔记: wiki/超高温陶瓷/literature/Kim2026-Oxidation.md
  ✅ 更新概念页: UHTC优先氧化与多相协同
  ✅ 文献索引缓存: 57 → 58 篇

[2/4] 摄入 Zhang2025_Ablation.pdf...
  ✅ 新增文献笔记: wiki/超高温陶瓷/literature/Zhang2025-Ablation.md
  📝 新建概念页: 超高温烧蚀机理
  ✅ 文献索引缓存: 58 → 59 篇

...

摄入完成: 新增 2 个概念页 · 更新 3 个概念页 · 新增 4 篇文献笔记
```

### 8c — 更新批次状态

执行 `../forge-discovery/references/shared-rules.md` §批次状态写入 中的脚本，mode 设为 `weekly`。

---

## Step 9 — 写入详细报告

自动生成 Markdown 报告：`raw/search-results/reports/weekly-{date}.md`

```markdown
---
date: 2026-07-06
mode: weekly
queries: [{q1: "...", mode: "ultra_low", returned: 10, accepted: 2}, ...]
---

## 一眼结论
本周在 XX、YY 方向发现 N 篇潜在相关文献，其中 E1 (Author Year) 最值得关注…

## 候选文献

### E1 | Authors Year | [DOI](https://doi.org/…)
- **期刊**: Journal Name (评级, IF X.X)
- **score**: 95
- **摘要**: 中文翻译摘要（200 字以内）
- **采用理由**: 为什么推荐这篇（与检索主题的关联）
- **来源查询**: q2

### E2 | …

## 检索透明度
- q1: "query text" — ultra_low, 10篇, 采用 2篇
- q2: "query text" — ultra_low, 10篇, 采用 3篇
- q3: "query text" — low, 20篇, 采用 4篇

## 已排除
- 去重排除 N 篇 (DOI 已存在于 wiki/**/literature/)
- 评级过滤 N 篇（低评级期刊）

## 下载结果
- 成功: N 篇
- 失败: N 篇（列出失败原因）

## 本周反馈
- 推荐: 7 篇
- 下载: 4 篇
- 摄入: 4 篇
- 摄入率: 57%

## 下一步
- 已自动摄入，可查看新增文献笔记
```

---

## 共享规则

以下规则详见 `../forge-discovery/references/shared-rules.md`（与 forge-discovery 共用）：
- **会话级缓存** — 同会话复用结果
- **额度管理** — 余额检查 + 降级建议
- **错误处理** — 11 种异常情况的行为表
- **版权免责声明** — Sci-Hub 使用警告

---

## 报告输出物

| 输出物 | 位置 | 说明 |
|--------|------|------|
| 终端列表 | stdout | 精简一行一篇（E编号+标题+期刊+score） |
| Markdown 报告 | `raw/search-results/reports/` | 完整版（含摘要翻译、检索透明度、采用理由 + 反馈） |
| 批次状态 | `raw/search-results/batches/` | `.batch-state.json` |
| 下载 PDF | `raw/new-papers/` | 自动摄入后按课题移入 `raw/papers/` |

## 关联脚本与配置

| 文件 | 用途 |
|------|------|
| `scripts/dedup.py` | 去重脚本（--index 缓存 + --wiki-dir fallback） |
| `config/weekly.yaml` | 周报模式关键词配置 |
| `references/sci-cli.md` | SciMaster CLI 参考手册 |
