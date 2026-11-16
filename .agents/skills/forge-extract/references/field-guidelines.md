# 字段填写指南

> LLM 提取数据时逐字段参考。不确定的字段留 null，标记 flag 而非编造。

## material 层

### material.type

| 值 | 判据 |
|----|------|
| **块体陶瓷** | 无纤维/晶须增强，无涂层；直接烧结致密的陶瓷块体 |
| **碳纤维复合材料** | 含 Cf/Csf（短切/连续碳纤维）增强的陶瓷基复材 |
| **C/C复合材料** | 以 C/C 为基体，浸渗/涂覆陶瓷 |
| **涂层** | 在基体（C/C/石墨/Csf-SiC 等）表面制备的陶瓷涂层 |

### base_elements / dopant_elements

- `base_elements`：主金属元素，以主元素=1.0 归一化其他金属系数
- `dopant_elements`：添加量 < 5at% 的微量元素；等摩尔多组分体系不归入 dopant
- 文献仅给质量比 → 计算原子比，标记 `成分推测`

**例**：
- HfC₀.₇₆N₀.₂₄ → base: {Hf: 1.0}, dopant: {}, anion: {C: 0.76, N: 0.24}
- (Hf₀.₂Zr₀.₂Ti₀.₂Ta₀.₂Nb₀.₂)C → base: {Hf: 0.2, Zr: 0.2, Ti: 0.2, Ta: 0.2, Nb: 0.2}, dopant: {}
- HfC + 2wt% Y₂O₃ → base: {Hf: 1.0}, dopant: {Y: <计算>}, flag: `成分推测`

### anion_elements

独立列 C/N/B/Si/O。碳化物陶瓷填 C；碳氮化物填 C+N；硼化物填 B；含 SiC 时填 Si。
全部以主金属=1 为基准归一化。

### sintering

提取论文"实验方法"部分的完整烧结参数。温度/压力/时间至少填一项。

---

## tests[] 层

### method

| 值 | 典型判据 |
|----|---------|
| **氧乙炔** | oxyacetylene, 氧乙炔, O₂+C₂H₂, GJB 323A |
| **等离子** | plasma, 等离子, 电弧风洞, Huels-type |
| **激光** | laser, CO₂ laser, 激光加热 |
| **风洞** | wind tunnel, arc-jet, 电弧风洞 |
| **发动机尾焰** | engine exhaust, rocket plume, 固体/液体火箭发动机 |

### results

**核心规则**：

1. `results.mass_loss_rate` 和 `results.linear_loss_rate` 必须填
2. 论文报了绝对值 → 填入 `original_value` + `original_unit`，标准化后的值填入 `value` + `unit`
3. 论文仅报对比（"比 XX 提高 3 倍"）→ `value` 留 null，填 `compared_to`
4. 论文未报 Rm / Rd → 留 null，标记对应 flag
5. 负 Rm 值（烧蚀后增重）→ 保留负值，是有效数据（氧化增重大于烧蚀损失）

**单位标准化规则**（normalize_units.py 执行，LLM 只需填 original）：

| 量 | 标准化单位 | 常见原始单位 |
|----|-----------|-------------|
| mass_loss_rate | mg/cm²·s | mg/s, g/s, μg/s, mg/cm²·s |
| linear_loss_rate | mm/s | μm/s, mm/s, mm/min |
| mass_loss | mg/cm² | mg, g, mg/cm² |

### oxide_layer

论文没报道氧化层信息 → `oxide_layer` 可整体为 null。
有报道但不全 → 填已知字段，缺失字段留 null。

---

## quality 层

### confidence 判定

| confidence | 条件 |
|-----------|------|
| **高** | Rm 和 Rd 至少一个有明确数值 + 烧蚀方法明确 + 组分化学式明确 + 样品尺寸已知 |
| **中** | 核心数据有但缺少辅助信息（热流密度、背面温度、氧化层厚度等） |
| **低** | 仅有定性描述无定量值；或数据来自间接推断（如从图表估算）；或 Rm 仅报对比值无绝对值 |

### flags 标签表

| flag | 触发条件 |
|------|---------|
| `Rm未报道` | 质量烧蚀率缺失 |
| `Rd未报道` | 线烧蚀率缺失 |
| `单位换算` | Rm 经过了单位变换 |
| `成分推测` | 化学式含推断（质量比→原子比、缺确切含量） |
| `缺样品尺寸` | Rm 报 g/s 或 mg/s 但无法获取样品面积 |
| `缺热流密度` | 烧蚀方法已知但热流未报道 |
| `仅相对值` | 只有 "3× better than XX" 无绝对值 |
| `PDF表格损坏` | PyMuPDF4LLM 未能正确解析数据表格 |
| `PDF提取失败` | 文本提取乱码或内容明显缺失 |
| `无烧蚀数据` | 全文检索后确实不含烧蚀实验定量数据 |
| `图表估算` | 数据来自从论文图表中目测读取 |
| `需人工核查` | LLM 对自己的提取不确定（自动附加，confidence≠高时必加） |
