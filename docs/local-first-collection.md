# 本地优先的增量文献收集

对应已批准清单：[2026-11-05实施清单](superpowers/plans/2026-11-05-local-first-document-workers.md)。本页描述实际CLI，不授予外发或发布权限。

## 继承与准备

显式 `plan --extraction-model gpt-6.1-terra|gpt-6.1-sol` 可覆盖默认模型指派，供测量与特批批次使用；不传时默认指派不变。

已入库记录按原ID/内容指纹直接继承，不重审、不迁移。completed/reusable范围必须显式给出既有record_ids，且既有证据的物理PDF SHA与本篇一致；同篇记录完成不代表全文覆盖完成。新增目标使用pending范围；失败与未读图不能标完成。

```text
python scripts/collect_material_documents.py prepare-local --source-manifest <sources.json> --source-root <项目根> --scopes <scopes.json> --existing-dataset <现有库> --output-dir <新准备目录> [--source-regions-map <既有原页清单映射>]
python scripts/collect_material_documents.py plan --packets <准备目录/packets.json> --profile <科学profile> --mapping <mapping> --output-dir <新计划目录>
```

新增来源任务可显式增加`plan --typed-input`，启用`material-collection-typed-input/1.0`。模型直接返回`input_data`对象和固定的`input_contract`，不再把记录塞入无法约束内部键的`input_json`字符串。schema按科学profile、实际mapping性质和本次证据ID生成，固定字段、来源路径、来源枚举与单位；未知仍可为null，缺关键事实仍由原门禁拒收。只允许分组字段及已映射性质对应的来源路径，不因critical_fields含更深路径就额外生成来源键。

这是输出格式约束，不是来源语义复核、科学换算或自动补条件。旧字符串请求/原回答原样保留，默认接口不变；新请求必须重新冻结并按新ID实际执行，不能改旧回答或重编号套用。准入重新生成schema并核对。schema增加输入体积，尚不能据此宣称节省token或费用；它首先解决真实输出因格式失配而被拒的问题。

scopes为`material-collection-scopes/1.0`，scopes数组逐项包含document_id、物理pages及status；可选record_ids、new_targets、requires_image。source manifest包含sources数组，复用现有source.json字段：document_id、source_paths、source_sha256、text_path/text_sha256、pages_path、page_offsets数组、parser_name/parser_version/parser_options。以prepare-local验证为准，不猜路径。source-regions-map为document_id到已冻结source-regions.json路径的对象；必须通过原来源及原图指纹校验，不重新截图。

缓存绑定PDF、解析文本、解析器选项和页范围；改动失效，不重写旧缓存。数字/单元候选不是科学事实。必要上下文过大或原页缺失阻塞，不截断冒充完整。

## 授权与执行

```text
python scripts/collect_material_documents.py run --plan <计划/tasks.json> --authorization <授权.json> --ledger <累计账本.json> --output-dir <新执行目录> --max-workers 3
python scripts/collect_material_documents.py summarize --plan <计划/tasks.json> --run-dir <执行目录> --output-dir <新汇总目录>
```

authorization为`material-collection-authorization/1.0`，包含approval、measurement_kind(real/fixture)、allowed_sources(document_id到PDF SHA)、ledger_path、max_cumulative_calls、max_workers、models。real还要求source_grant_path及其source_grant_sha256，绑定保存的用户授权原文。固定Terra/medium；原图/符号/冲突用Sol/medium；Fast。测试使用显式`--fixture-results`且只允许fixture授权，不能冒充真实效果。

主进程预占额度；最多3个独立原生会话；工作进程不读改共享账本或写正式库。失败扣预占，不自动重试；断点复用原回执，未决预占不重放。未知锁不删除。账本、请求/回答/图片回执属于审计协议，不是宿主全局硬控或反恶意伪造机制；不同会话不能证明统计错误独立。

## 分级准入与唯一提交

```text
python scripts/material_dataset.py prepare-collection-review --prepared <汇总/prepared/task_id> --extraction-proof <原extraction-proof.json> --mapping <mapping> --publication-grant <发布授权.json> --output-dir <新准入目录>
python scripts/collect_material_documents.py plan --admission <准入/admission.json> --output-dir <新复核计划目录>
```

用同一run/summarize执行复核；汇总输出updated-admission.json，随后：

```text
python scripts/material_dataset.py stage-collection --prepared <准备目录> --admission <updated-admission.json> --output-dir <新暂存目录>
python scripts/material_dataset.py commit --batch <暂存目录> --dataset <明确授权的现有库> --expected-catalog-sha256 <当前指纹>
```

publication grant为`material-collection-publication-grant/1.0`，包含approval、dataset_path/id/profile_version、scientific_profile_sha256、review_policy=`local-first-risk-review/1.0`、allowed_sources、measurement_kind。测试授权只能写系统临时库。旧科学profile不降低minimum_review_mode，新协议单独验证来源/类型/必要条件/失效/风险/抽样/原响应。

用户明确只要求已登记内容清楚时，可在`prepare-collection-review`显式传`--field-scope <JSON>`，按[字段隔离补充](superpowers/plans/2026-11-05-requested-field-isolation.md)执行。策略为`material-collection-field-scope/1.0`，含approval、reason、omitted_paths。只能隔离可空、非关键的post_test阶段字段；目标性质、组成、条件、failure/裂纹安全字段及critical_fields的父/子路径均不可隔离。

该入口生成新的prepared.json和field-isolation-log.json，保留完整原提取响应和被隔离原值，不重新提取全文、不更改原单位数值符号。空值在质量侧车标为`outside_requested_scope_not_author_absence`，不是“作者未报道”。新的事实范围要重新冻结复核，不能将旧回答换ID使用；复核只审定保留断言与必要条件，不要求无关后验物相争议先得到解决。原风险信号保留；新范围任务中的未分类失效在调用前隔离，提交前另有失效保护，模型给supported也不能当普通标签发布。

普通项20%向上取整、至少2条，由来源与记录指纹固定抽取；高风险逐条定向复核。抽查失败仅升级受影响实验范围，失败原回答保留，不重复求通过。program_checked记录review_state=partial；sampled_supported/targeted_supported为completed，质量侧车始终区分，human_verified=false。与旧strict共同导出不会升级等级。

完整准入包含既有实验时，不能按化学式/数值自动合并。可显式选择新增项：

```text
python scripts/material_dataset.py select-collection --batch <完整暂存目录> --dataset <现有库> --record-id <新增已准入ID> --omissions <显式处置.json> --output-dir <新选择目录>
```

每条未选中的已准入项必须有处置：`{record_id,status:"held_unresolved",basis}`保留未决，不代表已合并/全文完成；或`{record_id,status:"existing_exact",existing_record_id,basis}`明确同一原文事件，对除ID和复核状态外的所有科学字段做精确比较。完整原准入与失败项保留。commit再次校验目标、目录指纹、旧对应记录及来源/样品/事件碰撞；碰撞只阻塞，不自动判为同一实验。目录改变只需重建选择包，不重跑模型。旧select-certified不变。

## 交付

```text
python scripts/collect_material_documents.py deliver --dataset <现有库> --source-manifest <sources.json> --output-dir <新交付目录> [--collection-summary <汇总目录>] [--staged-batch <暂存目录>]
```

输出主表、辅助指标、争议/缺失、逐篇覆盖四份JSON与Markdown；records.json保留原记录，quality-index.json可筛选新旧等级。历史隔离项的当前状态未知时为null，不能拿历史问题条数冒充剩余篇数。原文辅助候选始终candidate_not_reviewed，不因父记录通过而升级。绑定页和提取者覆盖声明不等于全文验证；未读图仍未完成。未知总token、费用、人工时间为null；机器耗时不代替人工时间。

本地夹具验证不证明节省比例、领域召回完整性或科学准确率。真实收集仍须逐篇有来源处置和未完成范围，不能仅凭软件测试通过宣称建库结束。
