# SciMaster CLI 参考手册

> 最后更新: 2026-07-06
> 用途: `/forge-discovery` 和 `/forge-weekly` skill 的检索后端参考

---

## 安装与初始化

```bash
sci --version          # 检查 CLI 版本
sci init               # 首次配置 API Key（交互式输入）
```

---

## search 命令

```bash
sci search "<query>" [--limit N] [--mode <mode>] [--year-from YYYY] [--year-to YYYY]
```

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `query` | str | 必填 | 检索关键词（支持英文自然语言） |
| `--limit N` | int | 20 | 返回结果数上限 |
| `--mode` | str | `low` | 检索模式（见下表） |
| `--year-from` | int | 不限 | 起始年份 |
| `--year-to` | int | 不限 | 截止年份 |

### 检索模式

| 模式 | 费用 | LLM 排序 | 适用场景 |
|------|------|:--:|------|
| `ultra_low` | **免费** | ❌ | 初扫锁定方向、宽网撒 |
| `low` | 消耗额度 | ✅ | 精选排序（默认），精度高 |
| `mid` | 更多额度 | ✅ | low 结果不理想时升级 |
| `high` | 最多额度 | ✅ | 最高精度需求 |

### 模式策略（借鉴 bear-research 成本阶梯）

| 阶段 | 模式 | 理由 |
|------|------|------|
| 初扫锁定方向 | `ultra_low` | 免费，宽网撒 |
| 精选排序 | `low` | LLM 排序，精度高 |
| low 结果不理想 | `mid`（升级前告知用户） | 更深评估 |

---

## 输出文件

每次 `sci search` 在同目录下生成两个文件：

| 文件 | 说明 |
|------|------|
| `search-results-<timestamp>.json` | JSON 完整结果（含所有字段） |
| `search-results-<timestamp>.bib` | BibTeX 格式引用 |

**注意**：文件生成在**当前工作目录**，不是固定输出目录。skill 流程中先 `cd` 到 `raw/search-results/`，JSON 放入 `json/`，BibTeX 放入 `bib/`。

---

## JSON 输出字段

| 字段 | 类型 | 说明 | 是否必有 |
|------|------|------|:--:|
| `title` | str | 论文标题 | ✅ |
| `authors` | list[str] | 作者列表 | ✅ |
| `year` | int | 发表年份 | ✅ |
| `doi` | str | DOI（部分文献可能缺失） | ⚠️ |
| `venue` | str | 期刊/会议名 | ⚠️ |
| `abstract` | str | 摘要全文 | ⚠️ |
| `selectScore` | int | 相关度评分（0-100，仅 low+ 模式） | ⚠️ |
| `reason` | str | LLM 排序理由（仅 low+ 模式，token 占比 ~46%） | ❌ |
| `description` | str | 论文详细描述（仅 low+ 模式，token 占比 ~23%） | ❌ |
| `citationCount` | int | 引用次数 | ❌ |
| `isOpenAccess` | bool | 是否 OA | ❌ |

> ⚠️ = 可能缺失，skill 中用 `.get()` 容错

---

## usage 命令

```bash
sci usage              # 查看剩余额度
```

输出示例：
```
Monthly quota: 666 searches
Used: 23 (3.5%)
Remaining: 643
Resets in: 24 days
```

---

## 错误码与处理

| 返回码 | 含义 | skill 行为 |
|:--:|------|------|
| 0 | 成功 | 继续流程 |
| 1 | 参数错误 | 检查 query 语法，重试 |
| 2 | 认证失败 (401) | 提示用户运行 `sci init` + 停止 |
| 3 | 额度耗尽 | 显示 `sci usage` + 建议充值或降级 |
| 4 | 网络超时 | 建议换 `ultra_low` 或检查网络 |

---

## Token 消耗参考

| 场景 | 结果数 | 完整 JSON | 预过滤后 | 压缩比 |
|------|:--:|------:|------:|:--:|
| ultra_low 扫描 | 10 | ~5,000 | ~800 | 6:1 |
| low 精选 | 20 | ~24,000 | ~2,000 | 12:1 |
| low 大范围 | 50 | ~57,000 | ~4,000 | 14:1 |

> `reason` + `description` 占完整 JSON 的 ~69%（46% + 23%）。预过滤只提取 `title/doi/score/venue/year/abstract[:200]`，显著压缩。
