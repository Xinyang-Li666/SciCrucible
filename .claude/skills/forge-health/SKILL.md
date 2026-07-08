---
description: 知识库健康检查 — 运行脚本 + LLM 专项诊断，覆盖结构完整性、内容质量、文献质量等 9 个维度
---

# /forge-health — 知识库健康检查

运行 forge-health.sh 脚本，并由 LLM 解读和修复发现的问题。

## 流程

1. **运行脚本**：执行 `bash scripts/forge-health.sh`
2. **分析结果**：
   - 断链 → 判断是页面缺失（需创建）还是链接笔误（需修正）
   - 孤立页面 → 判断是概念确实独立，还是缺少入链（需在相关页面添加链接）
3. **逐项修复**：每发现一个问题，询问用户后再修复

## 脚本检查之外的 LLM 专项检查

脚本运行后，LLM 还应检查脚本无法检测的问题：

### 1. 结构完整性
- **概念页覆盖**：index.md 核心概念区的 5 个专题组下的所有页面是否都存在
- **index.md 时效性**：是否存在 `[待建立]` 标记？所有 [[双链]] 目标页面是否都存在？
- **项目页框架**：项目综述是否包含完整的 8 章结构？缺失章节需补建

### 2. 内容质量
- **过期内容**：扫描 wiki/ 中所有标记了 `[待更新]` 或超过 6 个月未编辑的页面
- **提纲化检测**：页面是否只有标题和列表，缺乏实质性叙述（< 3 句连续文字说明）？
- **孤立概念**：concepts/ 中的页面是否至少被 index.md 和 1 个其他页面引用？

### 3. 知识缺口
- **literature/ 中提到但 concepts/ 中未覆盖的概念**：扫描文献页面中的关键术语，检查是否有对应概念页
- **跨领域关联缺失**：UHTC 和正极相关的页面是否缺少跨领域类比链接？

### 4. 一致性
- **矛盾检测**：不同页面中对同一概念/数据的描述是否存在矛盾
- **冗余检测**：内容高度重复的页面（如两个概念页大量讨论同一机制）

### 5. 文献质量
- **分区标注**：literature/ 中的文献页面是否标注了期刊评级？
- **脉络引用**：项目页文献脉络中引用的文献是否均为高评级期刊（评级1-2），排除低评级期刊？

### 6. DOI 字段一致性
- **DOI 覆盖率**：扫描 `wiki/literature/*.md`，检查每页是否存在 `**DOI:**` 字段
- **缺失率统计**：(缺失 DOI 的文献数 / 总文献数)
- 缺失率 > 10% → 报告「⚠️ 文献 DOI 覆盖率不足，可能导致去重漏网」
- **列出所有缺失 DOI 的文献**，供用户手动补充
- DOI 格式校验：检测异常格式（如 URL 而非裸 DOI、包含中文字符等）

### 7. 文献索引缓存一致性
- **对比 `wiki/literature_index.json` 与实际 `wiki/literature/*.md`**：
  - 文件存在但索引缺失 → 报告「索引缺失条目: N」，建议补录
  - 索引指向已删除文件 → 报告「索引悬空条目: N」，建议清理
  - 索引 `count` 与实际文件数不一致 → 报告差异
- **索引不存在** → 提示用户运行 `/forge-ingest` 任意一篇文献触发自动重建
- 索引 JSON 格式校验：是否能被 `json.load()` 正确解析？

### 8. 概念页健康评分

先运行量化统计命令：

```bash
PYTHONIOENCODING=utf-8 python -c "
import os, re
from pathlib import Path
from datetime import datetime

concepts_dir = Path('wiki/concepts')
for f in sorted(concepts_dir.glob('*.md')):
    content = f.read_text(encoding='utf-8')
    lines = content.count('\n')
    refs = len(re.findall(r'\[\[[^]]+\]\]', content))
    mtime = datetime.fromtimestamp(f.stat().st_mtime)
    months_ago = (datetime.now() - mtime).days / 30.44
    short_paras = sum(1 for p in content.split('\n\n') if 10 < len(p) < 80)
    
    score = 100
    if lines > 300: score -= 15
    if lines > 500: score -= 15
    if refs > 15: score -= 10
    if months_ago > 6: score -= 20
    if months_ago > 12: score -= 15
    if short_paras < 3: score -= 15
    
    print(f'{score:3d} | {lines:3d}行 | {refs:2d}引用 | {months_ago:4.1f}月前 | {f.name}')
"
```

然后 LLM 对量化结果逐页评估：
- **行数**：> 300 行 → ⚠️ 建议拆分为子专题
- **关联文献数**：> 15 篇关联文献 → ⚠️ 建议拆分子专题
- **最后更新时间**：> 6 个月未更新 → 标记 `[待更新]`
- **叙述质量**：短段落 < 3 → ⚠️ 标记待补充（提纲化风险）
- 输出：概念页健康评分排名，最低分的 3 个标红

### 9. 期刊预警检查（可选）
- 检查 `wiki/literature/` 中是否有来自 MDPI 预警期刊的文献
- 列出供用户审查
- 注意：此检查依赖期刊黑名单维护，当前为可选功能

### 10. 检索结果清理（自动执行）

清理 `raw/search-results/json/` 和 `raw/search-results/bib/` 中超过 1 个月的旧文件：

```bash
PYTHONIOENCODING=utf-8 python -c "
import os, time
from pathlib import Path

BASE = Path('raw/search-results')
now = time.time()
cutoff = now - 30 * 24 * 3600  # 1 month ago

for sub in ['json', 'bib']:
    d = BASE / sub
    if not d.exists():
        continue
    for f in d.glob('search-results-*'):
        if f.stat().st_mtime < cutoff:
            age_days = (now - f.stat().st_mtime) / 86400
            print(f'  🗑 {f.name} ({age_days:.0f}d old)')
            f.unlink()
    # Remove empty dir
    remaining = list(d.glob('*'))
    if not remaining:
        d.rmdir()
        print(f'  📁 Removed empty dir: {sub}/')

print('Done.')
"
```

- **阈值**: 30 天（1 个月）
- **范围**: `json/` 和 `bib/` 子目录中的所有 `search-results-*` 文件
- **保留**: `batches/`、`reports/`、`search-test.json` 不在此清理范围
- **执行方式**: 自动执行，清理前列出待删文件，需用户确认后执行删除

## 修复原则

- 断链：优先创建缺失页面（即使是占位符），而不是删除链接
- 孤立页面：优先在 index.md 或相关概念页面中添加链接
- 过期内容：标记 `[待更新: YYYY-MM-DD]`，不删除原文
- 提纲化页面：补充 3-5 句机制解释，保持中颗粒度
- 缺失概念：按中颗粒度原则决定是归入已有页面还是新建
