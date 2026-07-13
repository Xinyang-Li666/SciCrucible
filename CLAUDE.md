# 科学知识库

> 替换为你的研究方向

## 知识库结构

```
SciCrucible/
├── raw/
│   ├── new-papers/      ← 新文献暂存区（待摄入）
│   └── papers/           ← 已摄入文献 PDF（按课题分文件夹）
│       ├── 课题A/
│       ├── 课题B/
│       └── 其他/
├── wiki/                          ← 按课题分层：wiki 下直接是课题名
│   ├── index.md          ← 全局索引
│   ├── <课题A>/          ← 如 超高温陶瓷
│   │   ├── concepts/     ← 中颗粒度概念页（80-250 行，含机制解释 + [[双链]]）
│   │   ├── literature/   ← 文献笔记（标注期刊评级）
│   │   ├── methods/      ← 课题专用方法页
│   │   └── projects/     ← 项目综述（8 章微型综述 · 含 CAS 过滤文献脉络）
│   ├── <课题B>/          ← 如 锂离子电池正极材料（同上四类）
│   └── 通用/             ← 跨课题共享
│       ├── concepts/     ← 通用概念（掺杂/热力学/氧化理论等，UHTC↔正极共用）
│       └── methods/      ← 通用计算方法（DFT/MD/机器学习势等）
├── brainstorming/        ← 想法、待办、开放问题
├── manuscripts/          ← 手稿定稿 PDF
└── .kiro/                ← LLM 行为规则缓存（skills 定义）
```

## 可用命令

| 命令 | 功能 |
|------|------|
| `/forge-ingest` | 批量摄入 new-papers/ 中所有 PDF，完成后按课题分类移入 papers/ |
| `/forge-ingest <file>` | 摄入单个 PDF 文献 |
| `/forge-search <query>` | 自然语言查询知识库（直接提问即可） |
| `/forge-discovery "<关键词>"` | 主动检索新文献（多角度 sci search → 去重 → 下载，需 SciMaster CLI） |
| `/forge-weekly` | 每周文献速递（自动扫描+精选+下载+摄入，需 SciMaster CLI） |
| `/forge-think` | 围绕材料科学问题协作思考 |
| `/forge-todo` | 待办事项管理 |
| `/forge-health` | 知识库健康检查 |
| `/forge-writing` | 文献锚定型学术写作（Introduction + Discussion），写前梳理大纲，逐段交互起草 |

## 项目目录

课题项目位于 `projects/`（与 SciCrucible/ 平级），每个课题独立目录：
```
projects/<项目名>/
├── data/       ← 原始数据和计算结果
├── figures/    ← 图表
├── draft/      ← 手稿
└── notes/      ← 项目笔记
```

## 工作原则

- 新文献先放入 raw/new-papers/，摄入后自动移入 raw/papers/<课题>/
- **按课题分层**：wiki 下直接是课题名，新摄入文献写入 `wiki/<课题>/literature/`，课题概念/方法写入 `wiki/<课题>/{concepts,methods}/`；跨课题通用概念/方法写入 `wiki/通用/`
- 摄入文献时增量编译，不覆盖已有知识
- **中颗粒度**：概念页按主题分组（共享同一物理机制→合并），不追求一个原子概念一页
- **期刊评级过滤**：文献脉络优先引用 评级1/Top的期刊；低评级期刊正常摄入但不进入脉络
- **项目页 8 章框架**：研究背景→文献脉络→技术路线→阶段进展→核心发现→手稿→开放问题→阅读导航
- 所有 wiki 页面用 [[双链]] 互联
- 手稿定稿后复制 PDF 到 SciCrucible/manuscripts/
- 有价值的新见解归档到 brainstorming/
- 实验/计算记录放在对应项目的 notes/ 中
- 鼓励跨领域类比（如 UHTC ↔ 正极 共享 Ellingham/Wagner/Fick 框架）
