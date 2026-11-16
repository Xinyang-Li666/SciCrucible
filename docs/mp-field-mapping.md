# MP字段映射与使用限制

以下表格对应本项目当前代码白名单，不表示真实服务已全部验收。实际返回缺字段写入missing_fields，区分not_returned与provider_null；无该材料/类别记录另列missing。不填0、不调用模型补数。

| 来源端点/字段 | 保存属性/元数据 | 单位与基准 | 使用限制 |
| --- | --- | --- | --- |
| thermo.energy_per_atom | energy_per_atom | eV/atom | 不当总能量；修正方式未知时不能跨方法直接比较 |
| thermo.formation_energy_per_atom | formation_energy_per_atom | eV/atom | 不代表有限温度Gibbs自由能；参考态未独立核验 |
| thermo.energy_above_hull | energy_above_hull | eV/atom | 与提供方方法/相图版本绑定，不是实验稳定性判定 |
| thermo.thermo_type/thermo_id | material_identity对应字段 | 原样，无单位 | 缺失为null；不同thermo_type或任务不合并 |
| elasticity.bulk_modulus.{vrh,voigt,reuss} | bulk_modulus_对应后缀 | GPa | Hill、Voigt、Reuss分别保存，不相互覆盖 |
| elasticity.shear_modulus.{vrh,voigt,reuss} | shear_modulus_对应后缀 | GPa | 不混比不同平均约定 |
| elasticity.poisson_ratio | poisson_ratio | 无量纲，unit=1 | 不推断缺失值 |
| elasticity.universal_anisotropy | universal_anisotropy | 无量纲，unit=1 | 不替换为其他各向异性指标 |
| elasticity.elastic_tensor.{ieee_format,raw} | elastic_tensor_对应后缀 | GPa，有限6×6矩阵 | 原数组保留；坐标/Voigt顺序不独立猜测 |
| elasticity.elastic_tensor数组 | elastic_tensor_unspecified_frame | GPa，有限6×6矩阵 | 坐标框架未知，不与已知框架直接比较 |
| summary.structure | structures/下provider JSON | 原提供方晶格/分数坐标 | 仅导出实际收到且通过基本格式检查的结构；不弛豫、不保证物理有效 |
| summary.material_id/formula_pretty/origins | 原始快照 | 原样 | 化学式相同不建same_structure；origins不是自动结构对应证明 |
| 各类别last_updated（如返回） | material_identity.last_updated | 原样 | 更新日期不是数据库冻结版本 |

## 结构指纹

material_mp.py在获取目录保存structure-manifest.json：结构路径、来源pointer、material_id、规范化JSON内容SHA256及实际文件SHA256。指纹只表示内容一致，不代表晶体学等价、计算任务结构一致或物理稳定。结构缺失/非法仅记issue，不产生虚假指纹。默认不生成CIF/POSCAR转换，避免新增依赖及无记录的重构。

## MP身份兼容

MP官方Emmet同时支持旧数字MPID与AlphaID。依据[官方实现](https://github.com/materialsproject/emmet/blob/main/emmet-core/emmet/core/mpid.py)，小写字母采用a=0的26进制，前导a为补位；例如mp-149与mp-aaaaaaft均对应149。客户端只在这一确定性等价关系成立时接收不同拼写，snapshot保留返回原值，并在identity_aliases保存请求ID、返回ID及emmet_alphaid_base26依据。并非接受所有看似相近的ID，不按化学式匹配。重复ID或重复别名在请求前拒绝。

真实身份查询已取得并交叉核验这一对应关系；此前的“意外身份”记录保留原样，不假称恢复了未保存的响应。后续单独授权的2次真实性质请求已取得3条热力学和1条弹性记录，并完成暂存、临时入库、导出和18项原值比对；仅说明这一材料的小型链路验收通过，不代表全部字段/体系覆盖或物理准确性。

## 方法与版本可获性

当前请求字段中thermo_type、thermo_id是可用的方法/身份线索；method/task_id只有快照实际提供时适配器才保留，不能因离线夹具带这些字段就声称实时API已取得。未取得数据库版本、任务关系、修正基准时保留null或明确未知，不默认各项兼容。当前程序不做能量排序、跨源归并或数值聚合；导出可按JSON pointer明确筛选，空要求导出不表示可训练。

客户端允许额外保留提供方实际返回的method、task_id、database_version、energy_type、reference_state、correction、normalization及uncorrected_energy_per_atom白名单元数据，不为了取得它们而擅自扩大请求字段或重试。数据库版本若在响应meta.db_version/database_version中实际返回，按类别保存；缺少则null。分页总数/游标缺失时truncated=null，不记成false，后续stage拒绝未知完整性的快照。

客户端为本项目标准库HTTPS边界，固定官方主机、无重试/重定向，不依赖mp-api执行请求。已安装mp-api仅作为只读参考，不继承其他项目插件权限。运行时和依赖版本应随验收结果保存；数据库版本不能从本地SDK版本推断。
