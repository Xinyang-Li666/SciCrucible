---
description: 通用实验数据提取框架 — 首次 Q&A 配置向导 → 小规模试点验证 → 全量检索提取入库。跨领域通用：材料科学、化学、物理等任意实验数据。当用户想从文献中构建实验数据集、提取结构化数据、建 ML 训练数据库时触发，即使用户没有说 /extract。
---

# /forge-extract — 通用实验数据提取

> **SciCrucible 根目录**: `D:\科研\SciCrucible\`

从文献中提取实验数据，构建结构化 JSON 数据库。**跨领域通用** — 不限于烧蚀，可用于氧化、力学、热学、电化学等任意实验类型。

## 核心设计

**配置文件 = 提取器的"领域知识"**。不预编码任何领域知识：

```
首次运行 → Q&A 深度引导 → 自动生成配置 → 小规模试点 → 全量提取
    ↑                                                          │
    └──── 已有配置可直接复用（多数据集并行）─────────────────────┘
```

每条命令的完整流程：

```
Phase 0: 配置发现与选择
  ↓
Phase 1: Q&A 深度引导 (首次/新建配置)
  ↓
Phase 2: 小规模试点验证 (3-5 篇)
  ↓
Phase 3: 全量检索 → 筛选 → 下载 → 提取 → 标准化 → 入库
  ↓
质量报告
```

## 核心原则

1. **配置驱动**：所有搜索关键词、筛选标准、数据 schema、单位规则均来自配置文件，无硬编码
2. **一次到位**：每个 PDF 只处理一次，LLM 提取时尽可能完整
3. **溯源可回溯**：所有数据保留原始值和标准化值，误换算可追溯
4. **质量透明**：每行标注 confidence 和 flags，不确定的字段宁可标"缺失"也不编造
5. **增量不覆盖**：已有数据绝不覆盖，新数据追加或合并
6. **已入库不重复**：已导入数据库的 DOI 自动过滤

---

## Phase 0 — 配置发现与选择

### 0a — 扫描已有配置

```bash
ls database/configs/*.yaml 2>$null
```

- **有已有配置** → 展示列表，用户选择：
  ```
  已有数据集配置:
    1. uhtc-ablation      — UHTC 烧蚀实验数据库 (47 材料/12 DOI)
    2. oxidation-kinetics  — 高温氧化动力学数据库 (空)
  
  输入编号选择已有配置，或输入 n 新建配置:
  ```
- **无配置** → 直接进入 Phase 1 Q&A 向导

### 0b — 选择后分流

| 用户选择 | 动作 |
|---------|------|
| 选择已有配置 | 加载配置 → 跳到 Phase 3（全量检索追加） |
| 新建配置 | 进入 Phase 1 Q&A |
| 首次运行（无配置） | 进入 Phase 1 Q&A |

---

## Phase 1 — Q&A 深度引导

> **目标**：通过 8 个问题确定用户需求，自动生成 3 个配置文件。

### 问答原则

1. **一次一问**，不要连珠炮
2. 每个问题附带**具体示例**帮助用户理解
3. 用户的自然语言回答由 LLM 解析为结构化字段
4. 每轮回答后，LLM 复述理解 → 用户确认再继续

### Q1 — 研究领域与数据集名称

> "这个数据集叫什么名字？属于哪个学科领域？"

**生成**: `meta.name`, `meta.display_name`, `meta.domain`

**示例回答**: "UHTC 烧蚀实验数据库，属于材料科学/超高温陶瓷"

**LLM 自动生成**:
- `name`: `uhtc-ablation`（kebab-case slug）
- 数据库文件名: `database/uhtc-ablation.json`

### Q2 — 测试方法与实验类型

> "你要提取什么实验/测试类型的数据？有哪些常见的方法变体或别名？（比如中文/英文、全称/缩写）"

**生成**: `test_methods` 枚举值 + `test_method_aliases`

**示例回答**: "氧乙炔火焰烧蚀和等离子体烧蚀两种。氧乙炔也叫 oxyacetylene、O₂+C₂H₂；等离子也叫 plasma、arc-jet"

**LLM 自动生成**:
```yaml
test_methods:
  - name: "氧乙炔火焰"
    aliases: ["oxyacetylene", "氧乙炔", "O2+C2H2", "GJB 323A"]
  - name: "等离子体火焰"
    aliases: ["plasma", "等离子", "arc-jet", "电弧风洞"]
```

### Q3 — 关键测量量

> "每个实验/测试要提取哪些核心指标？各自的物理含义是什么？是否必填？"

**生成**: `measurements[]` — 字段名、显示名、物理含义、是否必填

**示例回答**: "质量烧蚀率（衡量质量损失的速率）和线烧蚀率（衡量厚度损失的速率），两者都必填"

**LLM 自动生成**:
```yaml
measurements:
  mass_loss_rate:
    display: "质量烧蚀率"
    description: "单位时间单位面积的质量损失"
    required: true
  linear_loss_rate:
    display: "线烧蚀率"
    description: "单位时间的厚度/长度损失"
    required: true
```

### Q4 — 单位与标准化

> "这些测量量常见的原始单位有哪些？你希望统一到什么标准单位？有没有常见的单位换算陷阱？"

**生成**: `measurements[].standard_unit` + `measurements[].raw_units[]`

**示例回答**: "质量烧蚀率常见 mg/s 和 g/s，统一用 mg/cm²·s；线烧蚀率常见 µm/s 和 mm/s，统一用 mm/s。注意 mg/s 需要除以样品面积才能换算"

**LLM 自动生成**:
```yaml
measurements:
  mass_loss_rate:
    standard_unit: "mg/cm²·s"
    raw_units: ["mg/s", "g/s", "μg/s", "mg/cm²·s", "g/cm²·s"]
    conversion_notes:
      - "mg/s → mg/cm²·s: 需除以样品受测面积(cm²)"
      - "g/s → mg/cm²·s: ×1000 ÷ 面积"
  linear_loss_rate:
    standard_unit: "mm/s"
    raw_units: ["μm/s", "mm/s", "mm/min", "cm/s"]
```

### Q5 — 样品/材料描述字段

> "每个样品需要记录哪些属性？比如材料组分、制备工艺、形貌特征等。哪些是必填的？"

**生成**: `sample_fields[]` — 样品层的 JSON schema

**示例回答**: "必填：材料体系名称、材料类型（块体/薄膜/涂层）、金属元素成分、烧结工艺。可选：掺杂元素、增强相、相对密度"

**LLM 自动生成** sample_fields schema，包含每个字段的类型、必填/可选、描述。

### Q6 — 文献筛选标准

> "什么样的文献应该入选？什么样的应该排除？（比如：必须含实验数据、排除纯计算、排除综述等）"

**生成**: `screening.include[]` + `screening.exclude[]`

**示例回答**: "入选：有定量实验数据 + {test_method} 测试的。排除：纯 DFT/MD 计算、综述、TGA 热分析、涂层/复合材料的（我只关注块体陶瓷）"

**LLM 自动生成**:
```yaml
screening:
  include:
    - "摘要明确提及{test_method}方法 + 定量{measurements}数值"
    - "实验研究（非纯计算/综述）"
  exclude:
    - "纯DFT/MD计算无实验验证"
    - "综述/review/article"
    - "TGA/DSC热分析（非{test_method}）"
    - "涂层/C-C复合材料/碳纤维复合材料"
```

### Q7 — 检索关键词

> "提供 3-5 组检索关键词，覆盖不同角度（直接匹配、材料体系、方法视角等）。也可以指定年份范围。"

**生成**: `search.queries[]` + `search.year_from` + `search.year_to`

**示例回答**: "角度1 'UHTC ablation oxyacetylene plasma'；角度2 'HfC ZrC TaC carbide ablation resistance'；角度3 'ultra-high temperature ceramic mass loss rate'。2016-2026"

**LLM 自动生成** 3 组检索词 + 年份配置。

### Q8 — 数据质量判据

> "什么情况算高/中/低置信度？有哪些常见的质量问题需要标记 flag？"

**生成**: `confidence_rules` + `quality_flags[]`

**示例回答**: "高=核心数据全+方法明确+组分明确。中=缺辅助信息。低=只有定性描述。常见问题：单位换算、成分推测、图表估算"

**LLM 自动生成** 三级判据 + flag 标签表。

### 1.1 — 自动生成配置文件

Q&A 完成后，LLM 自动生成 3 个文件：

```
database/configs/<dataset-name>.yaml       ← 搜索+筛选+提取规则（人类可编辑）
database/configs/<dataset-name>-schema.json ← JSON Schema（validate_schema.py 读取）
database/configs/<dataset-name>-fields.md   ← 字段填写指南（LLM 提取时参考）
```

生成后展示摘要：
```
✅ 配置已生成: database/configs/uhtc-ablation.yaml

   数据集: UHTC 烧蚀实验数据库
   测试方法: 氧乙炔火焰, 等离子体火焰
   核心测量量: mass_loss_rate, linear_loss_rate
   检索关键词: 3 组 × 20 篇/组
   筛选标准: 实验 + 有定量数值, 排除纯计算/综述/TGA/涂层

   下一步: 运行小规模试点验证（Phase 2）
   输入 y 开始试点，或输入 e 手动编辑配置文件:
```

用户可以选择：
- **y** → 直接进入 Phase 2
- **e** → 打开配置文件手动编辑 → 编辑完成后进入 Phase 2
- **n** → 保存配置，下次直接 `/forge-extract --config uhtc-ablation` 进入 Phase 3

---

## Phase 2 — 小规模试点验证

> **目标**：用 3-5 篇文献测试配置是否合理，迭代修改配置，确认后锁定进入全量。

### 2a — Mini 检索

用配置中的关键词 + `--limit 5` 做精简检索：

```bash
cd D:/科研/SciCrucible/raw/search-results
sci search "<queries[0]>" --limit 5 --mode ultra_low --year-from <year_from> --year-to <year_to>
sci search "<queries[1]>" --limit 5 --mode ultra_low --year-from <year_from> --year-to <year_to>
sci search "<queries[2]>" --limit 5 --mode ultra_low --year-from <year_from> --year-to <year_to>
```

### 2b — 摘要筛选

用配置中的 `screening` 标准筛选，输出：

```
🔍 试点检索: 3组 × 5篇 = 15篇 → 去重后 13篇

入选试点 (5篇):
  ✅ P1  Author et al. 2025 — "Title..." J Eur Ceram Soc
  ✅ P2  Author et al. 2024 — "Title..." Corros Sci
  ...

跳过 (8篇):
  ❌ P3  综述 — "A review of..."
  ❌ P7  纯DFT计算 — "First-principles study..."
  ...

是否下载这 5 篇进行提取测试？[y/n]:
```

### 2c — 下载 + 提取试点

```bash
# 下载 (同 Phase 3 Step 2)
scansci-pdf batch ... --output raw/extract/papers/

# PDF → MD (同 Phase 3 Step 3)
python .claude/skills/forge-extract/scripts/extract_pdf_to_md.py --input raw/extract/papers/ --output raw/extract/md/

# LLM 逐篇提取 (同 Phase 3 Step 4)
# 用 database/configs/<dataset>-fields.md 作为填写指南
# 用 database/configs/<dataset>-schema.json 作为输出结构
```

### 2d — 逐篇审阅

每篇展示：**论文标题 + 摘要片段 + 提取结果摘要**。用户逐条反馈：

```
📄 P1: Author et al. 2025 — "Ablation behavior of HfC-SiC composite"
   提取到 2 个材料, 3 条测试
   - HfC-SiC: MAR=0.45 mg/cm²·s, LAR=0.012 mm/s (置信度: 高)
   - HfC: MAR=1.2 mg/cm²·s, LAR=0.031 mm/s (置信度: 中, ⚠️缺热流密度)

   审阅问题:
   1. Schema 字段是否合理？有遗漏/多余的吗？
   2. 筛选标准是否需要调整？（入选/排除边界）
   3. 单位换算是否正确？
   4. 置信度判据是否合适？

   输入: y(通过) / e(修改配置) / s(跳过这篇) / d(查看详细提取内容)
```

### 2e — 迭代 + 锁定

根据用户反馈修改配置，重新提取有问题的篇目。用户满意后：

```
✅ 试点验证通过 (5/5 篇提取成功)

   配置文件已锁定: database/configs/uhtc-ablation.yaml
   下一步: Phase 3 全量检索（预计 3×20 = 60 篇）

   输入 y 开始全量检索，或输入 q 保存配置稍后继续:
```

---

## Phase 3 — 全量检索与提取

> 以下 Step 0-6 的参数全部从配置文件读取，不再硬编码。

### Step 0 — sci search 检索

#### 0a — 前置检查

```bash
sci --version
sci usage
```

额度不足时告知用户。读取配置中的 `search.mode`（默认 `ultra_low`）。

#### 0b — 多角度检索

读取 `search.queries[]`，逐条检索：

```bash
cd D:/科研/SciCrucible/raw/search-results
# 对每条 query:
sci search "<query>" --limit <search.limit_per_query> --mode <search.mode> --year-from <search.year_from> --year-to <search.year_to>
```

#### 0c — Python 预过滤（token 控制）

```bash
PYTHONIOENCODING=utf-8 python -c "
import json, glob, os
files = sorted(glob.glob('raw/search-results/json/search-results-*.json'), key=os.path.getmtime)
new_files = files[-3:] if len(files) >= 3 else files
all_papers = []
for f in new_files:
    data = json.load(open(f, encoding='utf-8'))
    papers = data if isinstance(data, list) else data.get('results', data.get('data', []))
    all_papers.extend(papers)
for i, p in enumerate(all_papers):
    abs_text = (p.get('abstract') or '')[:300]
    print(f'E{i+1} | {p.get(\"year\",\"?\")} | {p.get(\"doi\",\"\")} | {(p.get(\"title\") or \"\")[:150]}')
    if abs_text.strip():
        print(f'  {abs_text}')
"
```

### Step 0.5 — 已入库 DOI 过滤

```bash
PYTHONIOENCODING=utf-8 python -c "
import json
from pathlib import Path
doi_file = Path('<config.database.processed_dois_file>')
if doi_file.exists():
    data = json.loads(doi_file.read_text(encoding='utf-8'))
    processed = set(data.get('dois', {}).keys())
    print(f'已入库 DOI: {len(processed)} 篇')
    for doi in sorted(processed):
        info = data['dois'][doi]
        print(f'  {doi} — {info.get(\"processed_at\", \"?\")} | {info.get(\"materials_count\", 0)} 材料, {info.get(\"tests_count\", 0)} 测试')
else:
    print('已入库 DOI: 0 篇（首次运行）')
    processed = set()
print(f'\nDOI_SET={json.dumps(list(processed))}')
"
```

### Step 1 — LLM 读摘要二次筛选

用配置中的 `screening.include[]` + `screening.exclude[]` 逐篇判定：

| 标记 | 动作 |
|------|------|
| ✅ **[实验]** | 满足所有 `include` 条件，DOI 不在已入库列表 → 进入下载队列 |
| ⚠️ **[待确认]** | 部分条件不明确，但可能符合 → 列出供用户决定 |
| ⏭️ **[已入库]** | DOI 已存在于 processed_dois.json → 自动跳过 |
| ❌ **[跳过]** | 命中任意 `exclude` 条件 → 排除 |

### Step 2 — 下载 PDF

```bash
# 提取已确认的 DOI → 批量下载
scansci-pdf batch raw/search-results/dois_extract.txt --output D:/科研/SciCrucible/raw/extract/papers/ --strategy legal_only
```

输出成功/失败清单。

### Step 3 — PyMuPDF4LLM 提取全文

```bash
python .claude/skills/forge-extract/scripts/extract_pdf_to_md.py --input raw/extract/papers/ --output raw/extract/md/
```

### Step 4 — LLM 从全文提取数据

#### 4a — 读取提取指南

提取前先读取：
- `database/configs/<dataset>-schema.json` — 数据结构
- `database/configs/<dataset>-fields.md` — 字段判据、枚举值、常见陷阱
- `database/configs/<dataset>.yaml` — 全局配置（测试方法、测量量、单位规则）

#### 4b — 逐篇提取

对每篇 Markdown 文件：

1. **定位实验段落**：搜索配置中 `test_methods[].aliases` + `measurements[].display`
2. **识别样品组分**：确定论文研究了几种不同组分
3. **为每个组分创建 material 对象**，填充 `sample_fields` 定义的字段
4. **为每个测试条件创建 tests[] 条目**，填充条件+结果
5. **评估质量**：按配置中的 `confidence_rules` 判定置信度，添加 flags

#### 4c — 输出格式

每篇 PDF 输出一个 `<doi-slug>.json`，结构遵循 `<dataset>-schema.json`，暂存于 `raw/extract/json/`。

### Step 5 — Python 标准化 + 去重 + 合并

```bash
python .claude/skills/forge-extract/scripts/normalize_units.py raw/extract/json/ --config database/configs/<dataset>.yaml
python .claude/skills/forge-extract/scripts/normalize_composition.py raw/extract/json/
python .claude/skills/forge-extract/scripts/validate_schema.py raw/extract/json/ --schema database/configs/<dataset>-schema.json
python .claude/skills/forge-extract/scripts/dedup_check.py raw/extract/json/ --db <config.database.output_file>
python .claude/skills/forge-extract/scripts/merge_to_db.py raw/extract/json/ --config database/configs/<dataset>.yaml
```

### Step 6 — 质量报告

```
📊 提取完成 · 2026-07-21

  数据集: UHTC 烧蚀实验数据库
  配置: database/configs/uhtc-ablation.yaml
  检索: 52篇 → 已入库过滤: 3篇 → 筛选: 15篇 → 下载成功: 14篇
  提取: 14篇 → 新增材料: 18个 → 新增测试: 31条

  数据库: database/uhtc-ablation.json (总计: 47个材料, 78条测试)
  已入库 DOI: database/uhtc-ablation_dois.json (累计 17篇)

  置信度分布:
    高: 11个材料 (61%)
    中: 5个材料 (28%)
    低: 2个材料 (11%)

  需关注的质量标记:
    ⚠️ {measurement}未报道: 3条
    ⚠️ 单位换算: 8条
```

---

## 特殊参数

| 参数 | 功能 |
|------|------|
| `/forge-extract` | 进入 Phase 0 配置选择（无配置时自动进入 Q&A） |
| `/forge-extract --config <name>` | 直接用已有配置进入 Phase 3 全量检索（跳过 Phase 1-2） |
| `/forge-extract --new` | 强制新建配置（跳过 Phase 0 已有配置列表） |
| `/forge-extract --pilot` | 用已有配置进入 Phase 2 试点验证（用于配置调优） |
| `/forge-extract --from extract/papers/` | 跳过检索，直接处理已有 PDF |
| `/forge-extract --pdf <path>` | 处理单个 PDF，不移文件 |
| `--overwrite <id>` | 强制覆盖指定 material id |
| `--year-from YYYY` | 覆盖配置中的年份起始 |
| `--year-to YYYY` | 覆盖配置中的年份结束 |
| `--allow-scihub` | 下载时启用 Sci-Hub 兜底 |

---

## 配置文件结构参考 (`database/configs/<name>.yaml`)

```yaml
# 由 /forge-extract Phase 1 自动生成 · 可手动编辑
meta:
  name: "uhtc-ablation"
  display_name: "UHTC 烧蚀实验数据库"
  domain: "材料科学"
  schema_version: "1.0"
  created_at: "2026-07-21"

search:
  queries:
    - "UHTC ablation oxyacetylene plasma experimental"
    - "HfC ZrC TaC carbide ablation resistance"
    - "ultra-high temperature ceramic mass loss rate linear recession"
  year_from: 2016
  year_to: 2026
  limit_per_query: 20
  mode: "ultra_low"

screening:
  include:
    - "摘要明确提及{test_method}方法 + 定量{measurements}数值"
  exclude:
    - "纯DFT/MD计算无实验验证"
    - "综述/review/article"
    - "TGA/DSC热分析（非{test_method}）"
    - "涂层/C-C复合材料"

test_methods:
  - name: "氧乙炔火焰"
    aliases: ["oxyacetylene", "氧乙炔", "O2+C2H2", "GJB 323A"]
  - name: "等离子体火焰"
    aliases: ["plasma", "等离子", "arc-jet", "电弧风洞"]

measurements:
  mass_loss_rate:
    display: "质量烧蚀率"
    description: "单位时间单位面积的质量损失"
    standard_unit: "mg/cm²·s"
    raw_units: ["mg/s", "g/s", "μg/s", "mg/cm²·s"]
    required: true
  linear_loss_rate:
    display: "线烧蚀率"
    description: "单位时间的厚度损失"
    standard_unit: "mm/s"
    raw_units: ["μm/s", "mm/s", "mm/min"]
    required: true

sample_fields:
  - name: "system"
    display: "材料体系"
    type: "string"
    required: true
  - name: "type"
    display: "材料类型"
    type: "enum"
    values: ["块体陶瓷", "薄膜", "涂层", "复合材料"]
    required: true
  - name: "base_elements"
    display: "主元素原子比"
    type: "object"
    required: true
  - name: "dopant_elements"
    display: "掺杂元素"
    type: "object"
    required: false
  - name: "sintering"
    display: "制备工艺参数"
    type: "object"
    required: true

confidence_rules:
  high: "{核心测量量}至少一个有明确数值 + 测试方法明确 + 样品信息完整"
  medium: "核心数据有但缺少辅助信息（热流密度/气氛等）"
  low: "仅有定性描述无定量值；或数据来自图表估算"

quality_flags:
  - "单位换算"
  - "成分推测"
  - "图表估算"
  - "缺样品尺寸"
  - "仅相对值"
  - "需人工核查"

database:
  output_file: "database/uhtc-ablation.json"
  processed_dois_file: "database/uhtc-ablation_dois.json"
```

---

## 向后兼容：已有 ablation.json 迁移

首次运行 `/forge-extract` 时，若检测到 `database/ablation.json` 存在但无对应配置文件，LLM 自动：

1. 从 `ablation.json` 反向推断配置参数
2. 生成 `database/configs/uhtc-ablation.yaml`
3. 生成 `database/configs/uhtc-ablation-schema.json`
4. 生成 `database/configs/uhtc-ablation-fields.md`
5. 提示：
   ```
   🔄 检测到已有 ablation.json (47 材料)，已自动生成配置:
      database/configs/uhtc-ablation.yaml
   
   后续运行 /forge-extract 将使用此配置。可手动编辑配置后重新提取。
   ```

## 边界条件

- **sci 未安装/未认证**：给出安装命令，停止
- **sci search 返回空**：如实报告，建议扩大关键词或取消年份限制
- **无配置文件首次运行**：自动进入 Phase 1 Q&A
- **processed_dois 不存在**：首次运行，跳过过滤步骤
- **摘要筛选后 0 篇入选**：报告"检索未发现符合条件的文献（已入库 X 篇已自动跳过）"
- **全部命中已入库 DOI**：报告"检索到的文献均已入库"，停止
- **PDF 下载全部失败**：保留 DOI 列表，建议手动下载后用 `--from extract/papers/` 重新提取
- **PyMuPDF4LLM 提取乱码**：标记 `flags: ["PDF提取失败"]`
- **LLM 无法识别任何目标数据**：标记 `confidence: "低"`，`flags: ["无目标数据"]`，仍记录 DOI
- **配置文件损坏**：提示用户检查 YAML 语法，或删除后重新运行 Q&A
- **磁盘空间不足**：下载前检查，<1GB 时警告

## 前置依赖

```bash
# 首次运行前检查
pip list 2>$null | Select-String -Pattern "pymupdf4llm"
pip list 2>$null | Select-String -Pattern "pyyaml"
# 如果未安装：
pip install pymupdf4llm pyyaml
```

`sci` CLI 需已配置（同 forge-discovery 的前置条件）。

## 关联 Skill

| Skill | 关系 |
|-------|------|
| `/forge-discovery` | 独立路径：文献发现 → 手动摄入 wiki。extract 专注于数据提取入库 |
| `/forge-ingest` | 独立路径：PDF → wiki 文献页。extract 跳过 wiki 直接出 JSON |
| `/forge-health` | extract 产生的数据库会被 health 检查纳入知识库统计 |
