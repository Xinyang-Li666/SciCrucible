"""烧蚀数据库 — Rm 单位标准化（forge-extract Step 5）

将 mass_loss_rate 和 linear_loss_rate 的 original_value 转换为标准单位。

标准化目标:
  - mass_loss_rate → mg/cm²·s
  - linear_loss_rate → mm/s

用法: python normalize_units.py raw/extract/json/
"""
import sys
import json
from pathlib import Path


def _sample_area_mm2_to_cm2(sample_size_mm: dict) -> float | None:
    """从样品尺寸估算受烧蚀表面积 (cm²)。假设圆形截面或单面烧蚀。"""
    dia = sample_size_mm.get("diameter")
    if dia:
        return 3.14159 * (dia / 2) ** 2 / 100  # π*(d/2)² → mm² → cm²
    length = sample_size_mm.get("length")
    width = sample_size_mm.get("width")
    if length and width:
        return length * width / 100
    return None


def normalize_mass_loss_rate(result: dict, sample_size_mm: dict | None):
    """将 mass_loss_rate 标准化为 mg/cm²·s"""
    mr = result.get("mass_loss_rate", {})
    if not mr or mr.get("value") is not None and not mr.get("converted"):
        return  # 已经是标准化值

    ov = mr.get("original_value")
    ou = mr.get("original_unit", "")
    if ov is None or ou is None:
        return

    # 已经是标准单位
    if ou == "mg/cm²·s" or ou == "mg/(cm²·s)":
        mr["value"] = ov
        mr["unit"] = "mg/cm²·s"
        mr["converted"] = False
        return

    area_cm2 = None
    if sample_size_mm:
        area_cm2 = _sample_area_mm2_to_cm2(sample_size_mm)

    # mg/s → mg/cm²·s (需要面积)
    if ou == "mg/s" and area_cm2:
        mr["value"] = round(ov / area_cm2, 6)
        mr["unit"] = "mg/cm²·s"
        mr["converted"] = True
    # g/s → mg/cm²·s (需要面积)
    elif ou == "g/s" and area_cm2:
        mr["value"] = round(ov * 1000 / area_cm2, 6)
        mr["unit"] = "mg/cm²·s"
        mr["converted"] = True
    # μg/s → mg/cm²·s (需要面积)
    elif ou == "μg/s" and area_cm2:
        mr["value"] = round(ov / 1000 / area_cm2, 6)
        mr["unit"] = "mg/cm²·s"
        mr["converted"] = True
    elif ou in ("mg/s", "g/s", "μg/s") and not area_cm2:
        # 缺面积，无法换算
        mr["value"] = None
        mr["unit"] = "mg/cm²·s"
        mr["converted"] = False


def normalize_linear_loss_rate(result: dict):
    """将 linear_loss_rate 标准化为 mm/s"""
    lr = result.get("linear_loss_rate", {})
    if not lr or lr.get("value") is not None and not lr.get("converted"):
        return

    ov = lr.get("original_value")
    ou = lr.get("original_unit", "")
    if ov is None or ou is None:
        return

    if ou == "mm/s":
        lr["value"] = ov
        lr["unit"] = "mm/s"
        lr["converted"] = False
    elif ou == "μm/s" or ou == "um/s":
        lr["value"] = round(ov / 1000, 6)
        lr["unit"] = "mm/s"
        lr["converted"] = True
    elif ou == "mm/min":
        lr["value"] = round(ov / 60, 6)
        lr["unit"] = "mm/s"
        lr["converted"] = True


def process_file(json_path: Path) -> dict:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    for mat in data.get("materials", []):
        for test in mat.get("tests", []):
            sample_size = test.get("sample_size_mm")
            results = test.get("results", {})
            normalize_mass_loss_rate(results, sample_size)
            normalize_linear_loss_rate(results)
    return data


def main():
    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("raw/extract/json/")
    if not input_dir.is_dir():
        print(f"⚠️ 目录不存在: {input_dir}")
        sys.exit(1)

    count = 0
    for json_file in sorted(input_dir.glob("*.json")):
        data = process_file(json_file)
        json_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        converted = sum(
            1 for m in data.get("materials", [])
            for t in m.get("tests", [])
            if t.get("results", {}).get("mass_loss_rate", {}).get("converted")
            or t.get("results", {}).get("linear_loss_rate", {}).get("converted")
        )
        print(f"  {json_file.name}: {converted} 条测试的单位已标准化")
        count += 1
    print(f"完成: {count} 文件")


if __name__ == "__main__":
    main()
