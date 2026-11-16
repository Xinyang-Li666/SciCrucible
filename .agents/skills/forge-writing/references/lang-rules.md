# 语言层自检规则库

> 被 SKILL.md §2.3b（中文）和 §2.6（英文）引用。按需读取，不需要每次加载到上下文。

---

## 1. 中文语言自检（§2.3b）

### 1.1 AI 高频虚词

| 虚词 | 替换建议 |
|------|---------|
| 值得注意的是 | 删除，直接从论点开始 |
| 众所周知 | 删除（如果确实众所周知，不需要说） |
| 毋庸置疑 | 删除（学术写作不需要修辞强调） |
| 综上所述 | → "以上结果表明" / 删除 |
| 由此可见 | → "这表明" / 删除 |
| 不难发现 | → 直接陈述发现 |
| 具有重要意义 | → 具体说明意义 |
| 引起了广泛关注 | → 说明为什么被关注 |
| 为其提供了新的思路 | → 具体说是什么思路 |
| 扮演着至关重要的角色 | → 删除"至关重要"，直接说作用 |
| 近年来，随着…的快速发展 | → 给出具体年份区间 + 具体驱动力 |
| 在…领域中 | → 删除"领域中"（冗余限定） |

### 1.2 模板化开篇

| 模式 | 处理 |
|------|------|
| "本节将讨论/介绍/阐述…" | 删除整句，直接从论点开始 |
| "如前所述…" | 删除或用具体内容替代 |
| "上一节中我们讨论了…" | 删除 |
| "在这一部分中…" | 删除 |
| "首先，我们需要明确…" | 删除"首先，我们需要明确"，直接陈述 |

### 1.3 段落节奏单一

- 连续 3 段以上句数完全相同 → 标记
- 连续 5 句以上句长差距 < 5 字 → 标记

### 1.4 引文堆砌

- 一个角标 `[1-6]` 引用 > 3 篇 → 建议拆分

### 1.5 修复原则

| 级别 | 类型 | 行为 |
|------|------|------|
| **L1 自动修复** | 黑名单词汇替换、模板化开篇删除 | 直接执行，不需用户确认 |
| **L2 建议修复** | 段落节奏调整、句式变异度 | 给出建议，由用户决定 |
| **L3 仅标记** | 引文堆砌 | 用户自行拆分 |

**绝不修改**：专业术语、引文格式、作者宣称强度、原文未出现的实质内容。

---

## 2. 英文语言自检（§2.6）

### 2.1 中→英转换陷阱

| 中文源模式 | AI 直译产物 | 地道改写 |
|-----------|------------|---------|
| 通过…实现了… | Through/By… achieving… | 改用主动语态 |
| 在…条件下 | Under the condition of… | At/When/With… |
| 随着…的增加/减小 | With the increase/decrease of… | As X increases/decreases… |
| 表现出/呈现出 | exhibits/displays/presents | 改用更具体的动词或直接陈述 |
| 结果表明 | The results show/indicate that… | X was observed to… |
| 这是由于 | This is because/due to… | reflecting/suggesting/indicating that… |
| 具有重要的…意义 | has important significance for… | 重构 |
| 对…产生影响 | has an influence/impact on… | affects / influences / shapes… |
| …的存在 | the existence/presence of… | 直接陈述，避免 of-stacking |
| 起到…作用 | plays a… role in… | serves as / acts as / 直接动词 |
| 为了…而… | In order to… | To… |
| 不仅…而且… | Not only… but also… | 用 and 或拆分 |

### 2.2 英文 AI 高频虚词

| 虚词 | 替换建议 |
|------|---------|
| delve into | investigate, probe, examine, explore |
| shed light on | reveal, clarify, explain, uncover |
| notably | 删除或用 "in particular" |
| moreover / furthermore | 删除 |
| underscore | demonstrate, show, indicate, emphasize |
| crucial (滥用) | critical, essential, key（只在确实必要时使用） |
| pivotal | central, critical, key |
| paramount | critical, essential, fundamental |
| robust (滥用) | 只在描述统计/算法稳定性时使用 |
| holistic | comprehensive, integrated |
| multifaceted | complex, multi-factor |
| showcase (用于非展示场景) | demonstrate, present, illustrate |
| highlight (滥用) | show, demonstrate, reveal, note |
| remarkable / unprecedented | 只在确实非凡时使用 |
| it is important to note that | 删除，直接陈述 |
| it should be noted that | 删除 |
| it is worth noting that | 删除 |
| it is imperative that | 删除 |
| plays a crucial role in | 改为具体作用：controls, drives, mediates, enables… |
| has garnered significant attention | 删除或改为"has been studied extensively because…" |
| a testament to | 改为"reflects" / "demonstrates" / "confirms" |

### 2.3 模板化开篇

| 模式 | 处理 |
|------|------|
| "In this section, we discuss/introduce/present…" | 删除整句 |
| "This section is devoted to…" | 删除 |
| "As aforementioned…" | 删除 |
| "First and foremost…" | → "First," |
| "Herein, we…" | → "We…" |

### 2.4 格式检查

- em dash `—` > 2 个/页 → 替换为逗号、括号、或分号
- 连续 3 段以上句数完全相同 → 标记
- 连续 5 句以上句长差距 < 5 词 → 标记
- 同一括号内引用 > 3 篇 → 建议拆分

### 2.5 修复原则

与中文规则相同（L1 自动修复 / L2 建议 / L3 标记）。额外规则：
- ❌ 不改变专业术语
- ❌ 不修改作者宣称的强度
- ❌ 不添加原文未出现的实质内容
