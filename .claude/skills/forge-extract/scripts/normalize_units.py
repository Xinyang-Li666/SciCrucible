"""通用实验数据 — 单位标准化（forge-extract Step 5）

读取配置文件中的 measurements 定义，将原始单位转换为标准单位。
支持: 简单因子换算、SI前缀换算、质量流量→质量通量(需面积)、时间单位换算。

用法: python normalize_units.py raw/extract/json/ --config database/configs/<dataset>.yaml
"""
import sys
import json
import argparse
from pathlib import Path

# ---- SI 前缀映射 ----
SI_PREFIX = {
    "p": 1e-12, "n": 1e-9, "μ": 1e-6, "u": 1e-6, "m": 1e-3,
    "c": 1e-2, "d": 1e-1, "": 1.0,
    "da": 1e1, "h": 1e2, "k": 1e3, "M": 1e6, "G": 1e9
}

# ---- 时间单位换算到秒 ----
TIME_TO_S = {"s": 1.0, "min": 60.0, "h": 3600.0, "day": 86400.0}

# ---- 面积单位换算到 cm² ----
AREA_TO_CM2 = {"mm²": 0.01, "mm2": 0.01, "cm²": 1.0, "cm2": 1.0, "m²": 10000.0, "m2": 10000.0}


def _parse_unit_parts(unit: str) -> dict:
    """将单位字符串拆解为分子/分母的 (prefix, base, power) 元组列表。
    例如 'mg/cm²·s' → num=[('m','g',1)], den=[('','cm',2), ('','s',1)]
    返回 {'num': [...], 'den': [...]}
    """
    unit = unit.replace("·", "*").replace("/", " / ").strip()
    parts = unit.split("/")
    num_str = parts[0].strip() if len(parts) > 0 else ""
    den_str = parts[1].strip() if len(parts) > 1 else ""

    def _parse_group(s: str) -> list:
        result = []
        if not s:
            return result
        # 按 * 或 · 分隔
        for token in s.replace("*", " ").replace("  ", " ").split():
            token = token.strip()
            if not token:
                continue
            # 尝试解析: prefix + base + power
            # 简单处理: 识别已知前缀
            prefix = ""
            rest = token
            for pfx in sorted(SI_PREFIX.keys(), key=len, reverse=True):
                if pfx and rest.startswith(pfx):
                    prefix = pfx
                    rest = rest[len(pfx):]
                    break
            # 尝试提取末尾的数字作为幂
            power = 1
            base = rest
            # 简单的幂提取 (如 cm2, mm²)
            if rest.endswith("²") or rest.endswith("2"):
                power = 2
                base = rest.rstrip("²2")
            elif rest.endswith("³") or rest.endswith("3"):
                power = 3
                base = rest.rstrip("³3")
            result.append((prefix, base.lower(), power))
        return result

    return {"num": _parse_group(num_str), "den": _parse_group(den_str)}


def _unit_factor(raw_unit: str, std_unit: str, needs_area: bool, area_cm2: float | None) -> float | None:
    """计算从 raw_unit 到 std_unit 的换算因子，无法计算时返回 None。"""
    if raw_unit == std_unit:
        return 1.0

    # ---- 简单 SI 前缀 / 时间换算 ----
    # 策略: 对比 raw 和 std 的差异部分

    # 处理仅前缀差异的情况 (如 µm/s → mm/s)
    # 提取: 值 × raw_factor / std_factor × time_correction
    raw_parts = _parse_unit_parts(raw_unit)
    std_parts = _parse_unit_parts(std_unit)

    # 如果结构不匹配 (分子/分母的 base 不同)，尝试用简单映射
    raw_str = raw_unit.lower().replace("²", "2").replace("³", "3")
    std_str = std_unit.lower().replace("²", "2").replace("³", "3")

    # ---- 手动常规映射表 (跨量纲) ----
    CONVERSION_MAP = {
        # 质量流量 → 质量通量 (需面积)
        ("mg/s", "mg/cm2*s"): lambda: (1.0 / area_cm2) if area_cm2 else None,
        ("g/s", "mg/cm2*s"): lambda: (1000.0 / area_cm2) if area_cm2 else None,
        ("μg/s", "mg/cm2*s"): lambda: (0.001 / area_cm2) if area_cm2 else None,
        ("ug/s", "mg/cm2*s"): lambda: (0.001 / area_cm2) if area_cm2 else None,
        ("mg/s", "mg/cm²*s"): lambda: (1.0 / area_cm2) if area_cm2 else None,
        ("g/s", "mg/cm²*s"): lambda: (1000.0 / area_cm2) if area_cm2 else None,
        # 仅时间单位差异
        ("mm/min", "mm/s"): lambda: 1.0 / 60.0,
        ("μm/s", "mm/s"): lambda: 1.0 / 1000.0,
        ("um/s", "mm/s"): lambda: 1.0 / 1000.0,
        ("cm/s", "mm/s"): lambda: 10.0,
        # 仅前缀差异
        ("g/cm2*s", "mg/cm2*s"): lambda: 1000.0,
        ("μg/cm2*s", "mg/cm2*s"): lambda: 0.001,
        ("ug/cm2*s", "mg/cm2*s"): lambda: 0.001,
    }

    key = (raw_str, std_str)
    if key in CONVERSION_MAP:
        result = CONVERSION_MAP[key]()
        return result

    # ---- 回退：尝试仅前缀差异 ----
    # 如果 raw 和 std 差别在数量级上
    if raw_parts["num"] and raw_parts["den"] and std_parts["num"] and std_parts["den"]:
        # 简化：假设换算仅涉及数量级
        pass

    return None


def _sample_area_cm2(sample_size_mm: dict | None) -> float | None:
    """从样品尺寸估算受测表面积 (cm²)。"""
    if not sample_size_mm:
        return None
    dia = sample_size_mm.get("diameter")
    if dia:
        return 3.14159 * (dia / 2) ** 2 / 100
    length = sample_size_mm.get("length")
    width = sample_size_mm.get("width")
    if length and width:
        return length * width / 100
    return None


def load_config(config_path: Path) -> dict:
    """加载 YAML 配置文件。优先用 yaml 库，回退到手动解析。"""
    try:
        import yaml
        with open(config_path, encoding='utf-8') as f:
            return yaml.safe_load(f)
    except ImportError:
        pass
    # 回退: JSON 格式的配置 (yaml 是 JSON 超集，简单情况可手解)
    # 实际上这里我们预期用户已安装 pyyaml
    print("⚠️ PyYAML 未安装，运行: pip install pyyaml")
    sys.exit(1)


def normalize_measurement(result: dict, field_name: str, meas_config: dict,
                          sample_size_mm: dict | None):
    """根据配置标准化单个测量量。"""
    mr = result.get(field_name, {})
    if not mr or not isinstance(mr, dict):
        return

    # 已经标准化过的跳过
    if mr.get("value") is not None and mr.get("converted") is False and mr.get("unit") == meas_config.get("standard_unit"):
        return

    ov = mr.get("original_value")
    ou = mr.get("original_unit", "")
    if ov is None or ou is None:
        return

    std_unit = meas_config.get("standard_unit", "")
    if not std_unit:
        return

    # 已经是标准单位
    if ou == std_unit:
        mr["value"] = ov
        mr["unit"] = std_unit
        mr["converted"] = False
        return

    # 尝试自动识别是否需要面积
    raw_str = ou.lower()
    needs_area = ("/s" in raw_str or "/min" in raw_str) and "cm2" not in raw_str and "cm²" not in raw_str and "m2" not in raw_str and "mm2" not in raw_str

    area_cm2 = _sample_area_cm2(sample_size_mm) if needs_area else None

    factor = _unit_factor(ou, std_unit, needs_area, area_cm2)

    if factor is not None:
        mr["value"] = round(ov * factor, 6)
        mr["unit"] = std_unit
        mr["converted"] = True
    elif needs_area and area_cm2 is None:
        # 需要面积但无法获取
        mr["value"] = None
        mr["unit"] = std_unit
        mr["converted"] = False
        mr["conversion_note"] = "⚠️非标准单位: 缺少样品尺寸无法换算面积"
    else:
        # 无法换算，保留原值
        pass


def process_file(json_path: Path, config: dict) -> dict:
    """处理单个 JSON 文件，按配置标准化所有测量量。"""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    measurements = config.get("measurements", {})

    for mat in data.get("materials", []):
        for test in mat.get("tests", []):
            sample_size = test.get("sample_size_mm")
            results = test.get("results", {})
            for field_name, meas_config in measurements.items():
                if isinstance(meas_config, dict):
                    normalize_measurement(results, field_name, meas_config, sample_size)

    return data


def main():
    parser = argparse.ArgumentParser(description="通用实验数据单位标准化")
    parser.add_argument("input_dir", type=str, nargs="?", default="raw/extract/json/",
                        help="JSON 文件目录")
    parser.add_argument("--config", type=str, required=True,
                        help="数据集配置文件 (YAML)")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    config_path = Path(args.config)

    if not input_dir.is_dir():
        print(f"⚠️ 目录不存在: {input_dir}")
        sys.exit(1)
    if not config_path.exists():
        print(f"⚠️ 配置文件不存在: {config_path}")
        sys.exit(1)

    config = load_config(config_path)
    measurements = config.get("measurements", {})
    print(f"配置: {config.get('meta', {}).get('display_name', config_path.stem)}")
    print(f"标准化 {len(measurements)} 个测量量: {', '.join(measurements.keys())}")

    count = 0
    for json_file in sorted(input_dir.glob("*.json")):
        data = process_file(json_file, config)
        json_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        converted = 0
        for m in data.get("materials", []):
            for t in m.get("tests", []):
                for field_name in measurements:
                    mv = t.get("results", {}).get(field_name, {})
                    if isinstance(mv, dict) and mv.get("converted"):
                        converted += 1
        print(f"  {json_file.name}: {converted} 条测量值已标准化")
        count += 1

    print(f"完成: {count} 文件")


if __name__ == "__main__":
    main()
