# 材料研究任务数据流程（实施中）

本文件只记录已经接通的本地接口；A–D尚未全部完成，不能据此宣称自主研究、材料发现或计算闭环已验收。

## 输入与责任边界

研究任务使用`research-task/1.0`。`config/research/tasks/uhtc-oxyacetylene.draft.json`只是超高温块体陶瓷氧乙炔烧蚀示例，两个目标为线烧蚀速率与质量/时间速率；元素范围、条件容差、计量基准及授权均未获真实试点批准。面积归一化质量通量是另一物理量。

来源清单使用`research-source-list/1.0`，每条来源显式指定`source_id`、`kind`、本机`local_path`、`expected_content_sha256`、`mapping_ref`。支持已注册`materials-dataset/1.0`库及已有`prepared_literature`结果；注册库使用catalog语义摘要，prepared使用文件字节SHA256。映射引用相对于来源清单所在目录。未复核prepared只能按任务政策用于探索；不自动升级为量化事实。正式库使用既有门禁，不通过此入口写入。

映射例子为`config/research/mappings/material-dataset-v1.example.json`，是字段映射而非领域标准。暴露区间的秒单位必须由原文/具体任务确认；方法别名映射默认标记未核验，不能仅凭文本映射认定方法相同。解析/转换不执行用户表达式。

## 已接通的本地入口

以下尖括号是需由执行者替换的路径，不代表已批准真实科研运行：

```text
python -B scripts/research_materials.py validate-task --task <任务JSON>
python -B scripts/research_materials.py compile --task <任务JSON> --sources <来源清单JSON> --derivations <派生数组JSON> --output-dir <全新输出目录>
python -B scripts/research_materials.py build-view --package <任务包目录> --spec <视图JSON> --max-records 50 --max-chars 10000 --output-dir <全新输出目录>
```

命令只做本地处理，不调用模型、外部API或LLM-MC。输出目录不得与输入源、正式库、wiki、raw或其祖先重叠；不得覆盖已有目录。输入、输出和错误中不得包含凭据。`validate-task`返回合法仅说明契约检查，不授予执行权。

任务包按manifest绑定工件字节哈希，保留来源记录、条件、用途、来源关联及映射；派生规则、输入记录、符号/面积依据另绑定哈希。来源哈希或程序检查通过不等于论文原文内容和物理结果已经核验。

任务要求的必要条件如果为空、明确标记缺失，或点值／区间缺少有效数值、单位及有序边界，不会进入定量用途；依据任务政策只能保留为探索或排除，不能把未知条件视作已满足。

当前内置派生仅支持声明的线速率/质量率单位换算、同记录质量变化除以暴露时间、同记录质量率按受蚀面积归一化。质量变化必须提供符号依据，面积必须有对应证据，时间和面积必须为正。内置算式目前只支持无不确定度的有限点值；不自动修正温标。`research-derivation-rule/1.0`规则须绑定`input_record_sha256`；外部插补/校准只校验已有脚本和结果工件，不运行脚本，符合记录契约的不确定度会原样保留。

视图通过封闭测试集输出限制、用途标签、按条数/字符数截断。训练视图只包含train组定量标签；其他缺失字段以null、单位及原因单独记录。`sealed`不是宿主文件访问隔离；若被测会话能够读取完整源包，则不能声称真正盲测。未知来源/样品分组保守留在train，不能称为独立留出样本。

可选特征采用`research-feature-index/1.0`索引：`row_ids`、`columns`及指向包内数据的`data_ref`。索引与数据工件均须在manifest中，声明的行ID须与返回视图一致；数据内容保持不透明，哈希与声明行映射匹配不证明数据实际行顺序。当前输出不自动生成任何描述符，也不运行训练。

## 候选、方法、评价和选择

```text
python -B scripts/research_materials.py candidate-add --task <任务JSON> --candidate <候选JSON> --output-dir <全新目录>
python -B scripts/research_materials.py method-record --package <任务包目录> --attempt <方法记录JSON> --output-dir <全新目录>
python -B scripts/research_materials.py evaluate --task <任务JSON> --package <任务包目录> --candidates <候选数组JSON> --methods <方法包manifest引用数组JSON> --assessments <逐项判断JSON> --policy <策略JSON> --output-dir <全新目录>
python -B scripts/research_materials.py select --task <任务JSON> --evaluation <评价包目录> --selection <选择JSON> --output-dir <全新目录>
```

候选的组成点或范围使用明确基准与任务范围；化学式标签不自动证明元素组成或实际结构。结构为provided时需要真实工件和哈希。方法尝试只记录现有视图、脚本、输入、输出和日志，不会执行脚本；文件和哈希匹配不证明宿主实际运行。

`config/research/policies/uhtc-evaluation.draft.json`的0.5/0.5权重仅为合成示例，不代表用户选择，也不能因文件存在而运行真实实验。加权评价需要各criterion/method的`research-normalization/1.0`工件、输入引用和`research-normalized-output/1.0`候选结果；结果必须与已冻结方法输出及逐项判断一致。缺项不重归一化，相关方法须声明组权重上限；优先级不是校准的成功概率。

Pareto比较仅对具备可比证据的目标进行；存在未知候选时只能称已知集合前沿。外部脚本方法可通过`evaluate`的`--external-inputs`和`--external-output`显式传递工件引用JSON；系统只校验、保存并标记算法未复现，不执行它们。权重、数据、方法或归一化版本变化后需重新评价；可用`--previous-evaluation`及`--change-reason`保留上一轮，缺旧候选时不产生完整排名。

选择包允许性能、稳健性和探索角色，不要求凑齐；未排名或约束未知的候选只能作为探索，硬约束失败不得选入。选择只表示研究优先级，不表示稳定、能量最优或已证实有效。

## 有界运行记录与恢复

```text
python -B scripts/research_materials.py run-init --task <已批准任务JSON> --authorization <范围引用JSON> --output-dir <新运行目录>
python -B scripts/research_materials.py reserve --run <运行目录> --action <动作JSON> --expected-state-sha256 <状态SHA>
python -B scripts/research_materials.py record-action --run <运行目录> --reservation-id <预留ID> --result <结果JSON> --expected-state-sha256 <状态SHA>
python -B scripts/research_materials.py record-round --run <运行目录> --round <轮次JSON> --expected-state-sha256 <状态SHA>
python -B scripts/research_materials.py resume --run <运行目录> --task <相同任务JSON> --expected-state-sha256 <状态SHA>
python -B scripts/research_materials.py status --run <运行目录>
```

运行记录不启动动作。已批准的范围文件须与任务内容哈希一致，但这不是审批人身份认证。动作须预留并匹配工具允许列表，失败计数、不自动重试；中断未结算时，输入字符与活动时间保守计为预留上限和已观测消耗中的较大值。总token或费用部分未知时为null；无法获得宿主计量时不接受有硬token或费用上限的模型/API调用。超额实耗保留并阻止后续预留。发生锁冲突或孤儿事件时不会自动删除或猜测恢复。

轮次的数据包放在运行目录下的`packages/<目录>/`；方法、评价、选择引用指向各包的`manifest.json`并与任务和数据包绑定。报告固定为`report.md`，历史版本按内容哈希归档。进展依据已存在的工件，同一证据重复叙述不算新进展。恢复仅校验记录和汇总未结算预留，不执行、重试或提交计算。程序没有宿主级拦截钩子，故不能声称防止外部绕过记账或全局预算硬控制；工具日志工件匹配也不独立证明宿主确实执行。

恢复非空来源的数据包时须追加 `--sources <原来源清单JSON>`：程序在本地校验来源的当前内容或目录指纹，并与冻结快照对照；缺少清单或来源变更时拒绝恢复，需重新编译并建立新版本。空来源夹具无需此参数。来源路径仅在本地读取，不会作为恢复结果输出。

## 可选计算互操作与反馈

```text
python -B scripts/research_materials.py export-intent --intent <意图JSON> --selection <选择包目录> --output-dir <新目录>
python -B scripts/research_materials.py import-feedback --feedback <反馈JSON> --intent <意图包目录> --artifact-root <反馈工件根目录> --output-dir <隔离反馈集合目录>
python -B scripts/research_materials.py export-llm-mc-context --intent <意图包目录> --output-dir <新目录>
python -B scripts/research_materials.py inspect-llm-mc-package --package <已有包JSON> --workspace-root <已有工作区> --contract-fixture <冻结的离线契约JSON>
```

计算意图仅引用已选择的候选：`selection_ref`指向选择包内的`selection.json`，`candidate_ref`指向其`evaluation/cohort.json`，同时以候选修订确定记录。若提供`resource_scope_ref`，它也必须在选择包清单中并匹配哈希。问题须区分直接目标、代理和机制；代理性质不证明烧蚀速率。组成范围可以保留，下游必须自行实例化结构与输入。意图与上下文均不提供命令或执行许可。

反馈的每项性质格式为`{quantity, output_ref, interpretation}`，输出引用必须在`artifacts`中并能在本地验证。实际输入、方法、后端哈希与状态均原样保留；未知文件放入`missing_outputs`，不伪造本地文件。相同反馈在同一隔离集合内按后端、请求和attempt去重；组合中任一attempt已登记且内容不一致则拒绝。改变组成或已有结构时标明需要新候选修订，未知原始结构不冒充相同结构。

反馈按`llm_mc`计算记录暂存，不是MP计算或实验事实，不写正式库、不自动当作成功标签。可显式使用正式设计中的`calculation_feedback`来源：`local_path`指向反馈包的`manifest.json`，`expected_content_sha256`为该文件字节SHA256，映射采用`research-source-map/1.0`且`source_kind`与来源名一致。为兼容本轮较早的输出，也接受`research_feedback`，两者分别使用同名映射。系统校验并冻结反馈文件；暂存状态默认只允许探索，不自动升级为训练标签。

可选的下游包检查只读已有文件及源码指纹，校验部分字段、引用、输入字节哈希和路径，不运行下游包。结果`prepared_only`表示该本地部分检查通过，不代表完整资源/执行策略、批准真实性、实际准备或提交已验证；`approval_verified`和`execution_authorized`均为false。引用源码不可用或漂移时检查不可用，不影响核心独立使用。实际提交、profile和批准由LLM-MC按其自身权限链处理。
