"""通用实验数据 — 成分原子比归一化（forge-extract Step 5）

确保 base_elements 以主元素=1 归一化，anion_elements 与金属主元素对齐。
适用于材料科学领域的数据集（如需用于非材料领域，此脚本可跳过）。

用法: python normalize_composition.py raw/extract/json/
"""
import sys
import json
from pathlib import Path


def normalize_elements(elements: dict) -> dict:
    """归一化元素原子比：找到最大值，除以最大值"""
    if not elements:
        return {}
    max_val = max(elements.values())
    if max_val == 0 or max_val == 1.0:
        return elements
    return {k: round(v / max_val, 4) for k, v in elements.items()}


def normalize_anions(anions: dict, metal_factor: float) -> dict:
    """将阴离子系数调整到与金属主元素=1 对应的尺度"""
    if not anions or metal_factor == 1.0:
        return anions
    return {k: round(v * metal_factor, 4) for k, v in anions.items()}


def process_file(json_path: Path) -> dict:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    for mat in data.get("materials", []):
        mi = mat.get("material", {})

        # 归一化金属元素
        base = mi.get("base_elements", {})
        if base and max(base.values()) != 1.0:
            factor = max(base.values())
            mi["base_elements"] = normalize_elements(base)
        else:
            factor = 1.0

        # 掺杂元素保持不变（已经是相对主元素的比值，不应再归一化）
        # dopant_elements 直接保留原值

        # 对齐阴离子
        anions = mi.get("anion_elements", {})
        if anions and factor != 1.0:
            mi["anion_elements"] = normalize_anions(anions, factor)

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
        print(f"  {json_file.name}: 成分已归一化")
        count += 1
    print(f"完成: {count} 文件")


if __name__ == "__main__":
    main()
