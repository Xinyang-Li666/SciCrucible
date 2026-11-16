"""烧蚀数据库 — JSON Schema 校验（forge-extract Step 5）

对每个 raw/extract/json/*.json 做结构校验，报告不符合 schema 的字段。

用法: python validate_schema.py raw/extract/json/
"""
import sys
import json
from pathlib import Path

# 简化校验：不依赖 jsonschema 库，做结构性检查
REQUIRED_TOP = ["id", "doi", "source", "material", "tests", "quality"]
REQUIRED_MATERIAL = ["label", "system", "type", "base_elements", "anion_elements", "sintering"]
REQUIRED_SOURCE = ["file", "extracted_at"]
REQUIRED_TEST = ["method", "duration_s", "results"]
REQUIRED_RESULTS = ["mass_loss_rate", "linear_loss_rate"]
REQUIRED_QUALITY = ["confidence", "flags"]
VALID_TYPES = ["块体陶瓷", "碳纤维复合材料", "C/C复合材料", "涂层"]
VALID_METHODS = ["氧乙炔", "等离子", "激光", "风洞", "发动机尾焰", "其他"]
VALID_CONFIDENCE = ["高", "中", "低"]


def check_required(obj: dict, required: list, prefix: str) -> list[str]:
    errors = []
    for key in required:
        if key not in obj or obj[key] is None:
            errors.append(f"{prefix} 缺少必填字段: {key}")
    return errors


def check_enum(value, valid: list, field_name: str) -> list[str]:
    if value is not None and value not in valid:
        return [f"{field_name}: '{value}' 不在枚举值 {valid} 中"]
    return []


def validate_material(mat: dict) -> list[str]:
    errors = []
    errors.extend(check_required(mat, REQUIRED_TOP, f"[{mat.get('id', '?')}]"))
    errors.extend(check_required(mat.get("source", {}), REQUIRED_SOURCE, f"[{mat.get('id', '?')}].source"))
    errors.extend(check_required(mat.get("material", {}), REQUIRED_MATERIAL, f"[{mat.get('id', '?')}].material"))
    errors.extend(check_enum(mat.get("material", {}).get("type"), VALID_TYPES, f"[{mat.get('id', '?')}].material.type"))

    tests = mat.get("tests", [])
    if not tests:
        errors.append(f"[{mat.get('id', '?')}].tests 不能为空")
    for i, test in enumerate(tests):
        prefix = f"[{mat.get('id', '?')}].tests[{i}]"
        errors.extend(check_required(test, REQUIRED_TEST, prefix))
        errors.extend(check_required(test.get("results", {}), REQUIRED_RESULTS, prefix + ".results"))
        errors.extend(check_enum(test.get("method"), VALID_METHODS, prefix + ".method"))

    errors.extend(check_required(mat.get("quality", {}), REQUIRED_QUALITY, f"[{mat.get('id', '?')}].quality"))
    errors.extend(check_enum(mat.get("quality", {}).get("confidence"), VALID_CONFIDENCE, f"[{mat.get('id', '?')}].quality.confidence"))

    return errors


def main():
    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("raw/extract/json/")
    if not input_dir.is_dir():
        print(f"⚠️ 目录不存在: {input_dir}")
        sys.exit(1)

    total_errors = 0
    for json_file in sorted(input_dir.glob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"❌ {json_file.name}: JSON 解析失败 — {e}")
            total_errors += 1
            continue

        errors = []
        for mat in data.get("materials", []):
            errors.extend(validate_material(mat))

        if errors:
            print(f"⚠️ {json_file.name}: {len(errors)} 个校验问题")
            for e in errors:
                print(f"    {e}")
            total_errors += len(errors)
        else:
            print(f"✅ {json_file.name}: 校验通过")

    if total_errors == 0:
        print("全部文件校验通过")
    else:
        print(f"\n共 {total_errors} 个问题需修复")


if __name__ == "__main__":
    main()
