# 高效复核：复用未改变的证据，不重复求“通过”

## review-cycle 用法

首轮运行 `python scripts/material_dataset.py review-cycle --prepared <目录> --policy <策略JSON> --settings <execution-settings JSON> --output-dir <全新周期目录> --render-pdf-regions`。修订轮改用 `--prior-cycle <上一周期目录>`，沿用已验证的原页。只发送周期目录中的 `pending-requests.json`，不得发送 `held-requests.json`。收到回答后运行 `python scripts/material_dataset.py review-cycle-finish --cycle <周期目录> --results <本轮新回答JSON> --output-dir <全新暂存目录>`。原有 `prepare-review`、`reuse-review`、`stage` 分步命令仍可使用。

## 执行规则

新批次使用 `prepare-review --request-binding bundle-v1`。旧默认、旧请求、正式库和领域最低复核强度不变；严格配置仍要求数值盲提取、字段核查及覆盖核查各自有证据。“一轮”是必要步骤各执行一次，不是把不同职责冒充同一次独立核查。

1. 提取时一次带齐作者样品标签、条件、单位、表头倍率、相关正文及冲突；原始事实不补猜。
2. 新协议先使用既有程序门禁检查必需条件。缺关键字段时在页图渲染、生成请求之前停止，列出记录与字段；非关键 null 不因此循环补问。
3. 必要原页只生成一次，单次最多渲染 8 页（144dpi、每页 40MiB）。首份包保存 `source-regions.json`；修订包用 `--source-regions <已有manifest>`，核对 PDF、页码、图像指纹后使用同一文件。与 `--render-pdf-regions` 互斥。不要另做“证明截图”，主会话不重复打开指纹未变且已经看过的同页。
4. 冻结后先运行 `reuse-review`。只有 `pending-requests.json` 是新增待执行工作；`held-requests.json` 已被条件、覆盖或预算门禁阻塞，不能发送。复用的原回答在 `reused-results.json`，不改 ID、数值或结论。
5. conflict/insufficient 也保留，不自动重问；应定位原文、隔离或经授权升级，不能反复提问挑一个“通过”。
6. 原、新回答按原 request_id 合并后，交给原 `stage`/`commit` 做本地门禁。缓存报告不是入库许可，不代替单位、来源、失败事件及覆盖要求。

## 复用边界

### 程序化 coverage 协议

`--programmatic-coverage` 参与计划指纹；切换协议后，blind/verify 请求若 payload 相同，仍可按原 request_id 复用，因为这两项判定与 coverage 模式无关。

`bundle-v1` 保留整包冻结指纹，但每个请求绑定自己的既有记录束。修改其他束的草稿，不再仅因全局 records_sha256 改变而让本束失效。

复用要求原请求 ID、完整 payload、记录集合、图片内容及证据 ID、模型、推理强度、服务档位、执行器版本、外围提示词和输出 schema 指纹一致。旧、新包均检查实际来源及原回答绑定，只认完整原回答。

- 不是逐字段认证切片。同一束中一个字段变化，整束仍重查；不要为了缓存命中把所有记录强制拆成单条，导致首轮调用增加。
- 整个证据清单、领域配置、策略和复核选项保守失效。覆盖请求仍含整包观测，局部修改不会自动保留全局覆盖结论。
- 同字节来源移到其他本地目录可复用；内容、清单或解析器指纹变化不可。
- 旧全局协议不能追溯拆开复用；切换到新协议首次有新请求，之后才可束级复用。
- 页图缓存不是模型记忆。不同独立复核请求如需看原页，仍须实际送图并保存输入回执；不能据另一个请求看过来伪造交付。
- 模型设置是调用者声明，不是宿主认证；fixture 回执仍为 fixture，不成为真实模型证据。

## CLI

以下为路径占位示例，需使用实际目录。首份包：

```powershell
python scripts/material_dataset.py prepare-review --prepared <prepared-dir> --policy <policy.json> --request-binding bundle-v1 --render-pdf-regions --output-dir <review-v1>
```

修订包复用原页；还应传入原有显式 `--review-options`、`--blind-locator`、`--blind-target-keys-only` 等选项，不因效率协议丢失它们：

```powershell
python scripts/material_dataset.py prepare-review --prepared <revised-prepared-dir> --policy <policy.json> --request-binding bundle-v1 --source-regions <review-v1/source-regions.json> --output-dir <review-v2>
```

准备复用与待执行清单（不运行模型）：

```powershell
python scripts/material_dataset.py reuse-review --prepared <revised-prepared-dir> --review-plan <review-v2/review-plan.json> --prior-prepared <original-prepared-dir> --prior-plan <review-v1/review-plan.json> --prior-results <original-results.json> --settings <current-settings.json> --prior-settings <original-settings.json> --output-dir <reuse-v2>
```

settings 为固定键 JSON，禁止凭据。下列两个 SHA-256 必须填真实外围提示词及输出 schema 的指纹，不能填虚构占位值：

```text
schema_version: material-review-execution-settings/1.0
model: 实际模型标识
reasoning_effort: 实际推理强度
service_tier: 实际服务档位
runner_version: 实际执行器版本
prompt_sha256: 64位小写十六进制SHA-256
response_schema_sha256: 64位小写十六进制SHA-256
```

报告逐项列出复用、待执行或阻塞原因及原回答指纹。record_outcomes 只反映当前已有回答，不表示发布；pending 存在时仍可能为 false。同尺度单位/表头倍率策略仍需绑定目标计划，显式传给 `stage`；工具不会擅自转移旧策略，因此缓存报告可能比最终显式策略结果更保守。

不自动重试、不启动额外模型/插件、不修改原 PDF、正式库或历史认证。无真实模型计量时，只报告离线协议行为，不宣称某个百分比的 token、费用或人工时间收益。
