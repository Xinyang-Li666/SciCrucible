# 共享规则

> 被 forge-discovery 和 forge-weekly 共同引用。在此维护一份，两处生效。

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

## Python 预过滤（Step B3 / Step 5a）

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

---

## DOI 提取 + 批量下载（Step B6 / Step 8a）

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

先由 `/forge-download` 读取 DOI 清单并 dry-run；确认访问授权后执行下载，详见 `docs/paper-download.md`。

```bash
python -B scripts/download_papers.py --dois raw/search-results/dois.txt --dry-run
python -B scripts/download_papers.py --dois raw/search-results/dois.txt --out raw/new-papers/ --state outputs/downloads/
```

下载完成后：
1. 输出成功/失败清单
2. 删除临时 `dois.txt`
3. PDF 留在 `raw/new-papers/`

下载结果格式：
```
✅ 下载成功 (N/M):
   - File1.pdf
   - ...

❌ 下载失败 (N/M):
   - DOI: 10.1016/... (原因: 付费墙，未登录)
   - DOI: 10.1016/... (原因: 网络超时)
```

---

## 批次状态写入（Step B8 / Step 8c）

```python
PYTHONIOENCODING=utf-8 python -c "
import json, os
from datetime import datetime

# 确保目录存在
os.makedirs('raw/search-results/batches', exist_ok=True)

batch = {
    'batch_id': '<batch-id>',
    'created': '<timestamp>',
    'mode': '<discovery | weekly>',
    'papers': {
        'E1': {'doi': '...', 'status': 'downloaded', 'pdf': '...'},
        'E2': {'doi': '...', 'status': 'download_failed', 'reason': '付费墙'},
        'E3': {'doi': '...', 'status': 'filtered'},
    }
}
path = 'raw/search-results/batches/<batch-id>.json'
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

---

## 额度管理

- 批量检索超过 5 次前，先运行 `sci usage`
- 余额不足时：
  - 告知用户剩余额度
  - 建议降级方案：全部 `ultra_low` / 减少检索角度 / 充值
- 不自动决定——等待用户选择

---

## 错误处理

| 情况 | 行为 |
|------|------|
| `sci` 未安装 | 给出安装命令 + 停止 |
| 认证失败 (401) | 提示 `sci init` + 停止 |
| 网络超时 | 建议换 `ultra_low` 或检查网络 |
| **返回空结果** | **如实报告，这是结论本身**，不伪造 |
| 额度耗尽 | 显示 `sci usage` + 建议充值，不伪造 |
| sci search JSON 格式变化 | `.get()` 容错，缺失字段显示 "N/A" |
| 下载依赖或凭据缺失 | 按下载手册配置依赖与环境变量，停止该路线并报告 |
| 下载 PDF 是摘要页 | 检查文件大小（<100KB 可能为摘要），提示用户 |
| 下载被拦截或无权限 | 停止重复尝试，转用户手动下载或文献传递 |
| 磁盘空间不足 | 周报中提示磁盘使用情况 |
| E 编号输入错误 | 验证 E 编号范围，提示有效范围 |

---

## 访问范围

下载工具仅处理 OA 或用户有权访问的机构来源，不内置绕过付费墙的路线。缺失或拦截如实记录并提供文献传递清单。
