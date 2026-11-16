# 当前材料数据接线规范

复核效率与安全复用见[高效复核协议](review-efficiency.md)：新批次显式使用束级依赖绑定、复用已验证原页，并在调用前生成仅含必要请求的清单；旧默认与正式门禁不变。
统一周期入口见[review-cycle 用法](review-efficiency.md#review-cycle-用法)。

两份 forge-extract 技能入口共同遵循本文件。历史工件用于追溯，正式变更经当前版本化准入和发布门禁执行。

已批准的剩余文献本地优先流程见[本地优先收集接口](local-first-collection.md)。它是显式选择的新批次准入协议；旧strict记录、profile和默认stage语义不变。

## 提取路线与协作边界

| 路线 | 选择条件 | 接线与验收 |
|---|---|---|
| 程序规则模板 | 冻结布局稳定，样品、条件及字段锚点可以唯一回放。 | 用 `prepare-local` 构建单来源冻结包，通过 `program_rule_engine.scan_packet` 扫描及校验。注册时锁定模板适用 profile、精确证据与 `rule_hash`，使用 `stage_packet` 后以 `verify_batch` 重放。逐篇核对来源、profile、mapping、规则摘要和目标库。 |
| 通用 admission | 文档版式不稳定、字段需要人工判读，或没有唯一的已注册模板。 | 走 `prepare_collection_records` 或下文 CLI。按 profile 门禁和已批准的复核策略处置，通过的记录进入暂存。缺证、冲突和关键字段不满足的记录隔离。 |

两条路线共用 **prepare → gate → stage → commit → export** 的阶段边界。门禁包含本地证据/字段校验及适用的复核要求。暂存是可回放的候选批次。commit 须单独获批，并重新验证完整 catalog SHA-256 和暂存回执。模型调用和门禁放宽分别授权。新 profile 和模板版本只进入新批次，旧记录按原版本重放。

### 候选入口与定位

现行试点顺序为表格、正文，图内取值暂缓。表格单元格保留原值、原单位、按列倍率和原文定位。正文补缺和旁证，只有样品、处理条件、性质、单位和观测事件对齐才可合并。冻结文本按字符区间 `[start,end)` 回放 quote，物理页、行号与栏位辅助复核。跨行分段，双栏按栏位归属。省略号在原文能唯一确定时展开，倍率缺号时保留原字符和定位。详见[新领域开库手册](superpowers/new-domain-playbook.md)。

### 协作板与检查器

批次协作板在该批次输出目录建立 `BOARD.md`。主代理追加编号指令和验收，执行者只追加自己的报告，写清输入版本、执行状态、产出和停点。文件保留历次指令与结果，用户授权单独记录。交接与停止规则见[协作协议](agent-collaboration-protocol.md)。

| 步骤边界 | 检查 |
|---|---|
| 生成适用的 prepared 工件后 | `python -B scripts/batch_check.py check-prepared <prepared目录>` |
| 冻结复核周期后 | `python -B scripts/batch_check.py check-cycle <周期目录>` |
| 发送前核对授权与账本 | `python -B scripts/batch_check.py check-auth --ledger <账本> <授权JSON>` |
| 生成原文区域后 | `python -B scripts/batch_check.py check-regions --source-root <来源根> <source-regions.json>` |
| 程序模板暂存后 | `verify_batch` 重放规则和批次。`batch_check` 各子命令只检查相应工件。 |

`cataloged` 按提示修复一次再重跑。`uncataloged`、`checker_failed`、来源或规则哈希错配、无法唯一回放、未授权操作及旧记录回归均为停点。复核只发送 pending 请求，held 不发送。冲突或证据不足保留原状态。

### 准召回归

冻结金标准、目标口径和候选定位规则，分别报告表、正文及布局不确定的精确率、召回率、定位正确率。保留误报、漏检、非目标与重复片段的逐条对账。每次调整按 **基线 → 归因 → 修复 → 回归** 记录版本变化。候选反向起草的金标准只能提供本集合的召回上限。独立覆盖评估采用新篇先人工标注、再扫描。

## 来源和授权

先确定研究目标、字段、单位/基准、关键条件、复核强度与预算；已有配置可复用，不要求每次重复回答。烧蚀、热力学和金属力学示例在config/datasets/，example_only=true不代表领域验收完成。领域不限这三类，可显式添加profile，不复制核心流程。

文献检索与下载继续使用已有工具，但只在获授权范围内执行；依赖缺失不自动安装，检索错误不写作没有文献，全文不可得保留缺失状态。不加载整个知识库、不上传私有PDF到外部插件。提取模型/客户端中立，不要求OpenAI Key。

实验观测保存样品、条件、观测事件和引用。MP计算性质另走material_mp.py与MP来源适配，不当实验事实，不用同化学式自动匹配实验样品；Key只在本地凭据提供器内读取。MP已通过单材料身份与热力学/弹性性质简单真实测试，不能泛化为所有材料的覆盖率或物理准确性验证。

## 文献实际操作

配置与映射示例配对使用：config/datasets/<领域>.example.json和<领域>.mapping.example.json。映射所列缺失字段应显式为null，不能从另一来源填入猜值；example不是已经校准的领域标准。

1. 从提取结果生成待适配JSON。mapping只使用JSON pointer，不执行任意转换表达式；原始输入全量保留于准备包，未映射信息不是已接受事实。
2. 提供research_review现有evidence契约（documents、parse_snapshots、evidence、coverage_scopes）。quote必须与冻结文本一致，原PDF/解析文本各自哈希。每条来源snapshot ID必须存在。
3. 运行：

```text
python scripts/material_dataset.py prepare --input <提取JSON> --profile <领域JSON> --mapping <映射JSON> --evidence <证据JSON> --source-root <来源根> --output-dir <全新准备目录>
```

准备目录包含prepared.json和review-request.json，不调用模型。profile定义allowed_properties和critical_fields；缺关键条件即使模型给supported也不能入库。

4. 获单独模型执行授权后，在不含评估参考的上下文提交完整review-request。模型只返回request_id、payload_sha256、answers，逐问题/目标给supported/conflict/insufficient、evidence_ids和简短理由。保存为reviews.json数组，每项为request和response；必须与冻结请求完全一致。不得模拟真实调用。
5. 运行：

```text
python scripts/material_dataset.py stage --prepared <准备目录> --reviews <reviews.json> --output-dir <全新暂存目录>
```

没有--reviews时全部留待复核。accepted、quarantined、excluded分别计数；阶段成功不等于所有记录通过。stage保存batch.json和receipt.json。引用、profile、数据或来源改变必须重新准备/复核，不能仅改完成标签。

6. 获正式写入授权后显式初始化新的database/datasets/<名称>，不覆盖旧库；先确认不是正式既有目录。

```text
python scripts/material_dataset.py init --dataset <新库根> --dataset-id <名称> --profile-version <版本>
python scripts/material_dataset.py commit --batch <暂存目录> --dataset <库根> --expected-catalog-sha256 <init或前次提交返回的指纹>
python scripts/material_dataset.py export --dataset <库根> --requirements <任务要求JSON> --output-dir <全新导出目录>
```

commit重新验证来源、receipt和响应，遇过期catalog/锁冲突拒绝，不覆盖其他进程锁。缺关键条件、冲突和未决记录不会因同批其他记录通过而放行。导出requirements为JSON pointer→精确值的对象，例如按review_state、来源类别或方法/基准筛选；不进行跨方法数值聚合。无要求导出不代表可训练。

## 显式关联（不自动匹配）

关系输入为JSON数组，每项包含left_record_id、right_record_id、relation_type、status、basis、evidence_ids。两端必须是同一已注册库中存在的不同记录；依据引用须对应有效的research_review证据。类型为candidate_match、same_structure或asserted_correspondence，状态为pending或asserted；候选匹配只能pending。asserted是显式声明，不代表自动科学验证。same_structure的asserted还要求两端记录已保存相同structure_sha256，以及basis.kind=exact_structure_content_identity、basis.structure_sha256匹配；同化学式或同material_id均不能替代这些条件。原始内容指纹不等于晶体学等价分析。

```text
python scripts/material_dataset.py stage-relations --input <关系JSON> --dataset <库根> --evidence <证据JSON> --source-root <来源根> --output-dir <全新暂存目录>
python scripts/material_dataset.py commit --batch <关系暂存目录> --dataset <库根> --expected-catalog-sha256 <当前指纹>
python scripts/material_dataset.py export-relations --dataset <库根> --output-dir <全新导出目录>
```

关系独立保存到relations.jsonl，不覆盖性质、不合并实验。提交时重验依据与两端内容指纹；修改来源、未知目标或未知引用均拒绝。普通export只导出性质记录，需关系时显式export-relations。

## 旧格式只读与适配

旧库只读导出：`python scripts/material_dataset.py legacy-export --input <旧JSON> --output-dir <全新导出目录>`。输出保留原数据并标记not_reviewed；不修改原文件，不表示通过新门禁。

旧materials[].tests[]适配须在prepare命令额外指定`--legacy-materials --snapshot-id <已有解析快照ID>`，使用针对material/test嵌套字段的显式mapping。来源定位保留原行路径。不得直接将旧库记录视作已核验数据。

## MP本地接口

定向获取：`python scripts/material_mp.py --credential-config <本地配置路径> --material-ids mp-149 --categories summary thermo elasticity --max-materials 1 --max-requests 3 --output-dir <全新目录>`。

有界发现：改用`--query-file <JSON文件> --fields material_id formula_pretty`，query只允许formula、chemsys、elements；与--material-ids互斥。服务返回截断时明确标记，不自动翻页扩大预算。

获取成功后：`python scripts/material_dataset.py stage-mp --snapshot <snapshot.json> --profile config/datasets/mp-properties.example.json --output-dir <全新暂存目录>`；随后使用同一commit/export命令。失败、截断或无支持性质的快照不可提交。snapshot有来源校验不等于物理准确验证；浮点数和弹性张量不能混作实验值。结构仍保存在来源快照中；没有任务级关联依据时same_structure_verified=false。

真实身份定位已确认MPID/AlphaID等价拼写兼容问题并修复，细节见docs/mp-field-mapping.md；后续获单独授权的2次请求取得4条性质记录，并通过临时入库与导出。API Key不在命令中传值，不再使用已耗尽的请求额度。结果见evals/research-workflow/mp-properties/runs/authorized-properties-smoke-20261102/report.md。

获取目录另存structure-manifest.json及实际返回结构的原生JSON文件；结构缺失/非法不产生假指纹，也不证明与性质任务同结构。逐字段缺失原因保存在snapshot.missing_fields中。字段、单位、基准和结构指纹含义详见docs/mp-field-mapping.md。

兼容入口：--query接受有界JSON对象（与--query-file、--material-ids互斥）；--profile仅用于显式材料fetch的确定性适配，另存adapted.json，不stage或commit。配置文件优先；省略--credential-config时读取MP_API_KEY。Python接口保留request注入，并支持client_factory返回同协议的请求函数以做离线边界测试，两者不得同时传入；正常CLI不初始化额外SDK客户端。

小型授权验收可显式使用--capture-responses（要求--max-requests不超过2），在下游校验前保存脱敏data/meta。失败仍扣预算，禁止重启已有capture预算目录；不保存HTTP headers或密钥。此开关不授予联网权限，真实请求仍需明确授权。

新流程禁止调用旧merge_to_db.py写库；其CLI现返回迁移提示和失败码，旧数据库原样保留，旧记录不自动升级。不得用旧normalization脚本原地改写冻结证据，应在显式副本中转换并保留依据。

同一论文可有多个样品/条件/时间段，不能按DOI或相同数值吞并实验。程序通过只说明契约和定位成立；模型支持不是人工金标准，既有漏检案例仍适用。真实语义准确率、全文完整性、跨领域效果需分别验证。

存储/门禁的本地契约与临时库闭环已具备；只在临时夹具中测试过的步骤不能标生产全量已验证。缺API权限或请求预算时保留进度，不自动重试或替换服务。

## 分级复核与字段扩展接线（显式选择的新接口）

新显式协议 `--programmatic-coverage` 将 coverage 判定改为程序清点结果，不生成模型 coverage 请求；旧默认不变。依据是历史 41/41 次 coverage 回答均为 supported，且程序已有精确清点门禁。

旧profile 1.0、旧review-request和stage --reviews保持原有含义；不要将历史strict回答改ID套入它们。新增profile 1.1仅在显式选择时启用，外层record_kind和materials-dataset/1.0不变。完整配置见`config/datasets/ablation-production.json`及配套mapping；example_only=true表示配置不是已校准科学标准，不表示它不执行程序检查。

1. `template --profile <1.1配置> --snapshot-id <已有解析ID> --output-dir <新目录>`生成空表和field-catalog。空值/单位均不猜，ambiguous不是“作者未报道”。填值时同步填写material_identity.field_provenance：每个结构化分组和性质单独列证据ID及origin（reported/read_from_figure）；缺失填origin=missing及明确missing_reason。转换、派生、预测走现有独立变换/研究层，不能伪装reported。
2. 按原命令prepare。1.1声明field_rules（递归object/array/text/enum/number/quantity）、property_rules（基准、逐性质条件、可用阶段）、publication门禁和views。组成、工艺、样品状态、事件、测试、后验机制均保留类型；未知字段留在完整原始包，不静默当已审核事实。缺失性质可以unit=null，仅1.1允许，不改变1.0；未知非空单位仍拒绝。质量率、面积通量、总质量变化、线率和总厚度变化是不同性质。
3. `prepare-review --prepared <准备目录> --policy <已有research_review策略JSON> --output-dir <新目录> [--render-pdf-regions]`生成review-plan.json、field-audit.json及中文核对表。来源先复验；计划绑定完整记录/证据/领域配置/复核策略。最终绑定后的载荷重新按字符限制稳定拆包；必要上下文不截断，单项仍过大则阻塞。这里不运行模型、不授予执行额度。
4. 将计划中每个可执行请求的**原始payload及绑定信息**送入另获授权的客户端。verify/coverage原响应仍为request_id、payload_sha256、answers，每个问题/目标必须完整回答。回答支持的是payload.field_targets明列的全部字段；组内另一个记录冲突不自动污染已支持记录。不同请求/策略/来源的历史响应拒绝，不做编号转换。
5. strict盲提取只接收精确原始文本或冻结原PDF页图，返回request_id、payload_sha256、records。每行字段见该请求response_contract（sample_label、quantity_key、shape、raw_value、unit、evidence_ids；同名不同事件另有event_context）。程序按样品/性质/事件上下文匹配，不按行序、同数值或同化学式合并。只比较原值/原单位，不把单位别名或符号不明自动修好。没有匹配、重复歧义、符号/单位不同仍隔离；模型的盲提取不等于独立科学金标准。
6. `--render-pdf-regions`仅本地调用已有pdftoppm渲染PDF物理页，最多8页、144dpi、每页40MiB；缺工具只报告，不安装。手工转写的PDF quote不会进入盲载荷。请求attachments列实际原页路径/指纹，发送客户端必须真的附图；仅发描述不算附图。结果有附件时另需input_receipt={payload_sha256,attachment_sha256:[按请求顺序],method:fixture/external_recorded/real}。该receipt是审计协议，不是具有宿主隔离或反恶意伪造能力的证明；本地夹具只能标fixture。图片不自动上传。
7. strict覆盖另需独立清点、完整解析、无未解决区、shared_parser=false且有来源人的inventory。该标记不能证明统计独立。expected_targets使用sample_label、quantity_key；同名不同事件加event_context（与请求中的critical字段路径一致）。程序对照非缺失观测精确清点，未支持格式、重复、缺漏均阻塞，不只相信模型“覆盖完整”。1.1逐字段证据用于限定所属scope。首批配置最低strict；不能用弱策略或旧--reviews绕过。
8. 将结果保存为JSON数组，每项`{request_id,response}`（有附件再加input_receipt），然后：`stage --prepared <准备目录> --review-plan <review-plan.json> --review-results <结果JSON> --output-dir <新暂存目录>`。不与旧--reviews混用。缺请求/被阻塞/预算延后/冲突保持隔离；已知缺任务关键条件或破碎样品排除该用途。stage和commit都重新生成计划、验证来源/附件/响应/receipt；不得从completed标签推断通过。
9. commit仍需正式发布授权，仅向已注册新库显式写入。本地测试不授予正式写权限。`export --dataset <库根> --view design_inputs|as_made|post_test|all --output-dir <新目录>`按可用阶段投影；design_inputs不带目标率、实测组成、烧蚀后机制或其provenance。每种性能有独立property_context，不能把同一测量温度/方法套给所有性质。投影标projection_only/not_ingestion_records，不能重新作为完整入库记录提交。无筛选导出仍不等于可训练；氧乙炔/等离子须按任务条件分开。

新typed quantity可通过现有research-source-map将condition pointer指向完整{value,unit,basis}节点，unit=null表示保留原单位；若声明的单位不同则拒绝，不把min悄悄标s。标量老映射保持不变。后续任务编译、分组防泄漏、派生追溯、候选及LLM-MC可选适配继续复用research_materials.py，不复制算法/调度器。

### 已认证修订包的显式子集发布（可选）

同一输入包修改一个样品时，旧适配器会使其他未变化样品的生成ID一起变化；新ID不代表新实验。不能直接删改原认证包的accepted列表。获发布授权后，可用以下独立命令保留完整认证，只选择实际新增记录：

```text
python scripts/material_dataset.py select-certified --batch <完整已暂存认证目录> --dataset <目标库> --record-id <新增且已认证ID> --existing-links <显式修订关联JSON> --output-dir <全新选择目录>
```

`--record-id`可重复。existing-links为数组，每项仅有certified_record_id、existing_record_id、basis；每个未选择的已接纳条目必须明确关联到既有记录并说明同一原文事件的修订依据。除生成ID外的全部事实（含来源快照、原记录定位、组成、条件、性质、逐字段证据等）必须完全一致；相同化学式或相同速率不能代替此依据，也不自动寻找/合并实验。没有既有对应项时此命令拒绝，不提供任意删除或绕过门禁的能力。

生成的material-certified-selection/1.0暂存封装保存完整原认证、原认证指纹、选择项、既有完整记录及显式关联；record_kind与profile语义不变。随后仍用原commit/export命令。stage及commit重新验证完整原认证门禁、选择事实与目标库既有记录；目录或catalog变化会阻塞并要求重新准备选择包（不需重跑模型）。已提交的同一选择包按原commit协议返回already_committed。隔离/排除结果保留在原认证中，绝不因选择而升级。核心不会将此接口解释为通用科学去重或独立实验判定。

## 独立元素／单质相／化合物相参考包

参考属性不另造实验record_kind，也不凭同化学式填实验缺值。`prepare-reference --input <参考catalog JSON> --evidence <既有证据> --source-root <来源根> --output-dir <新目录>`支持material-reference-catalog/1.0；顶层catalog_id/version/resource(name/version/无凭据公开uri或null)/entries。条目含reference_id、entity(kind=element/elemental_phase/compound_phase,label,material_id或null)、name、definition、数值value(shape/raw_value/unit/basis，缺失另含missing_reason)、method/temperature/pressure/reference_state（缺失为null）、source_snapshot_id、evidence_ids。抽象element不能带MP晶体ID；有材料ID也不证明结构一致。

来源验证通过只生成原始复核请求。获授权运行后，`stage-reference --prepared <参考准备目录> [--reviews <原响应数组>] --output-dir <新目录>`逐条验证association/units/provenance/conflict/applicability；无响应或缺值留隔离。`export-reference --packet <暂存目录> --output-dir <新目录>`再次核验，输出reference-records.json与manifest，始终source_layer=reference、human_verified=false、same_structure_verified=false，不加入实验标签或自动建立物相对应。参考包与实验库、MP快照分开交付；LLM/特征插件可按明确reference_id和定义选用，自动任务混合和新资源的真实值校准需显式配置，不隐式启用。

上一个本地优化批次（production-completion-20261104-01）未重新运行真实模型/API、全语料提取、人工计时或正式发布；其历史状态不代表后续正式批次状态。详细验收见evals/research-workflow/material-dataset-wiring/runs/production-completion-20261104-01/。

## 正式首批与显式复核选项（2026-11-04）

后续正式批次production-20261104-01已按用户授权建立`database/datasets/ablation-bulk-carbide-carbonitride-v1`：3篇来源中6条观测通过门禁入库，1条MMC记录因原文密度冲突隔离，4条碎裂事件排除普通样品标签并保留来源。只有选定速率及必要条件的有界范围被复核，不代表全文、所有字段或全语料完成。GPT-6 Astra/high的5条展示项抽查是模型复核，不是人工金标准；其中只有3条属于最终6条接纳记录。人工核验、人工计时及费用未知，不能记为零。执行与证据见`raw/search-results/ablation-production/runs/production-20261104-01/`。

以下选项均为显式启用；省略时旧默认行为不变：

- `prepare-review --review-options <JSON>`接受`material-review-context/1.0`。规则`scientific_criteria_without_workflow_recursion`区分原文科学支持与随后程序执行的复核/覆盖门禁，不循环要求本次尚未结束的复核已经完成。保留关键字段、来源、覆盖、冲突和用途排除门禁；非关键null仍未知，不能补成零、室温或n=1。隔离备注必须绑定同来源证据，指向真实缺失字段，不能把已有值改称缺失来绕过检查。选项参与计划指纹，改动后必须重新冻结并复核。
- `stage --comparison-policy <JSON>`只与`--review-plan/--review-results`配套使用。契约`material-review-unit-notation/1.0`绑定原计划、授权记录和固定规则版本，仅允许`mg s⁻¹ ↔ mg/s`、`μm s⁻¹ ↔ μm/s`两组同尺度写法等价；不换算数值、正负号、尺度或面积通量。原请求和响应不改写；暂存包保存comparison_audit，提交时重新比对并校验。未知符号仍隔离；缺此显式选项仍逐字匹配单位。

新库中的`accepted-search-view.json`是仅含已接纳记录的旧检索兼容投影，不是旧库迁移，也不是独立事实来源。其元数据绑定正式catalog指纹，当前已实际验证probe和按ID定向expand；后续新增提交后须显式刷新投影，不得把旧投影当作最新全量。隔离和排除记录不能从此视图混入普通实验标签。`published-views`中的design_inputs等任务投影与完整入库记录仍分开。

用户后续单独授权的`material-review-table-header/1.0`仅适用于DOI `10.1016/j.jeurceramsoc.2023.01.018`这一既有PDF指纹的物理第2页Table 1。策略绑定冻结计划、原PDF及页图指纹，仅在比对副本中展开明确的`10^-3 mm·s^-1`线率和`10^-4 g·s^-1`质量率表头倍率，使用十进制定值运算并逐项记录原系数、倍率和展开值。未知倍率、乱码、面积通量和其他表不适用，默认关闭；原请求及回答不改。该策略不能覆盖逐字段复核中的conflict/insufficient，不能据倍率一致自动入库。真实执行与红绿测试见`raw/search-results/ablation-production/runs/remainder-20261104-01/`。

随后获明确授权的`material-review-si-typography/1.0`可显式传入同一`stage --comparison-policy`入口。工厂`material_data.si_typography.si_policy(plan, approval)`绑定冻结计划，只接受mg、g、mm、μm、µm、um及每秒的已批准排版（空格/·/⋅/*与s-1/s−1/s⁻¹）；微米别名统一表示为μm/s，不改变数值或尺度。日志保留原字符串，原回答不改。mg/s与g/s、mm/s与μm/s不作尺度转换；面积通量、乱码和带未核实倍率的单位仍不适用。该策略与特定Table 1倍率策略是两种独立、显式选择的策略，不自动合并，不改变默认精确比较行为。

后续单独授权的`material-review-source-multiplier/1.0`通过同一显式比较入口使用；旧默认和上述两种策略不变。Python工厂`material_data.source_multipliers.source_multiplier_policy(plan, declarations, approval)`要求每个声明逐项指定request_id、source_snapshot_id、source_pdf_sha256、page_no、image_sha256、table_id、sample_labels、quantity_key和header_unit（如`10^-4 g/s`）。来源/原页必须在冻结计划及对应盲请求中；样品/性质必须唯一对应同一来源的记录，重名多事件应先分包，不猜映射。table_id和表头必须经原页核对：程序只能校验契约和指纹，不能自动证明表头语义或授权文字真实性。

只接受明确10的整数幂（指数范围−12至12）的mg/g或mm/μm每秒速率；已批准SI排版可等价匹配，但不换mg与g或mm与μm的尺度，不接受面积量纲、未知字符或任意算式。十进制运算仅用于比对副本，日志保留原系数、单位、明确倍率、展开十进制值和源页指纹。原回答、请求、科学记录不改；逐字段conflict/insufficient仍不能通过。已展开的同尺度值可按SI写法核对，未展开值不能冒充已展开值。新准备包若采用展开表达，必须在可复核字段中保留原系数/表头及展开依据，不能以此比较策略掩盖来源或转换链缺失；程序日志不替代模型的科学来源复核。stage与commit重新验证策略和日志。针对性夹具与临时入库结果见`raw/search-results/ablation-production/runs/remainder-20261104-01/source-bound-multiplier-repair-20261105/`，不属于真实效果测量或全套回归。

### 显式盲提取目标键约束

`prepare-review --blind-target-keys-only`仅在显式启用时生成`material-blind-target-keys/1.0`响应契约：`allowed_quantity_keys`来自本请求已经登记的目标性质，不包含候选数值或通过结论。执行客户端可使用`material_data.blind_targets.quantity_key_schema(request)`生成对应enum约束，避免把原文±不确定度、误差棒等另造未请求的性质行。此选项参与计划和请求指纹；必须重新冻结并使用新请求实际复核，旧回答不得改ID套用。默认旧请求与语义不变，额外行、漏项、单位/符号错误及科学冲突仍由原门禁拒收；程序不会过滤或改写旧模型响应。来源不确定度仍应在原文和候选上下文保留，限制输出键不表示不确定度已完成科学审核，也不表示全文完整。

独立原单位兼容配置可显式为mass_rate增加`μg/s`、`µg/s`，应使用新profile_id并保留旧配置。经单独授权的`material-review-si-typography/2.0`由`material_data.si_typography.microgram_policy(plan, approval)`生成；它保留1.0的同尺度能力并仅增加μg/µg每秒排版等价。旧1.0规则与默认逐字比较不变。微克不换算为毫克或克，不接受ASCII ug、面积通量、乱码或未知倍率。新准备包及策略须重新冻结并经过原严格门禁；补录同一实验的另一性质时应显式关联既有观测，不把两条性质记录当两次独立实验。

### 显式原文条件定位（数值盲，不是条件盲）

后续单独授权的`prepare-review --blind-locator <JSON>`接受`{"schema_version":"material-blind-locator/1.0","paths":["/material_identity/test/method","/material_identity/test/heat_flux","/material_identity/test/exposure"],"approval":"明确授权记录"}`。paths可选非空子集；只允许氧乙炔/等离子方法、已知正热流和暴露时长。来源必须由该记录的test逐字段来源绑定支持；不允许未知条件、温度响应、候选性质、失效、重复数或任意自由文本。数量单位及basis也使用固定白名单，不能夹带答案。这里的绑定只证明引用契约成立，不代替来源语义复核。

新盲请求向每个target附加`locator_conditions`查询条件，仍不提供dataset_records、候选速率、参考答案、原真实记录ID或通过结论。返回每行需包含与查询完全一致的`locator_conditions`，同时保持原值/原单位及原页证据；同化学式另一热流/时长不得混入。当前显式接口按一个作者条件范围分包，同包同名多事件应继续拆分，不能按行序匹配；旧event_context协议及覆盖清点要求不变。旧默认不提供这些条件，省略参数时原请求和默认语义不变。

条件定位是被授权提供的检索问题，不是从盲上下文独立发现的实验条件；只能称“候选速率数值盲提取”，不能据此宣称完全条件盲、独立盲测或统计错误独立。新选项参与冻结计划和请求指纹；旧回答不得改ID套入新请求，stage/commit重新生成并校验计划。来源原文可能包含实际数值，这是提取证据而不是另给参考答案。科学条件不一致、单位/符号冲突、缺关键字段及发布排除仍照常阻塞。针对性证据位于`raw/search-results/ablation-production/runs/remainder-20261104-01/blind-locator-repair-20261105/`，不是全套回归或人工金标准。
### 新领域接入清单

1. 建立完整 profile：声明 `field_rules`、`property_rules`、`allowed_properties`、`critical_fields`；按需设置 `extraction_scope` 和 `domain_label`。
2. 建立从提取记录到领域字段的 mapping。
3. 选用通用 review policy，或显式建立新策略。
4. 期刊评级沿用现有评级表。

领域差异优先落在 profile、mapping、策略与示例配置中。可回放的版式差异由注册模板承载。共享契约扩展需显式声明并做旧版本回归，既有批次按其冻结配置重放。
