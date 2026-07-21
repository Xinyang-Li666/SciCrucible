"""通用实验数据 — JSON Schema 校验（forge-extract Step 5）

读取数据集配置文件中的 schema 定义，对每个 raw/extract/json/*.json 做结构校验。
不依赖 jsonschema 库，做轻量级结构性检查。

用法: python validate_schema.py raw/extract/json/ --schema database/configs/<dataset>-schema.json
"""
import sys
import json
import argparse
from pathlib import Path


def load_schema(schema_path: Path) -> dict:
    """加载 JSON Schema 文件"""
    return json.loads(schema_path.read_text(encoding="utf-8"))


def extract_required(schema_obj: dict, key: str) -> list:
    """从 schema 的 properties 中提取 required 字段列表"""
    return schema_obj.get("required", [])


def extract_enum_values(schema_obj: dict, field_path: str) -> list | None:
    """从 schema 中提取指定字段的 enum 值。
    field_path 形如 'material.type' 或 'tests[*].method'
    """
    parts = field_path.split(".")
    current = schema_obj
    for part in parts:
        if part == "[*]":
            # items 在 $defs 中引用
            ref = current.get("items", {}).get("$ref", "")
            if ref.startswith("#/$defs/"):
                def_name = ref[len("#/$defs/"):]
                current = schema_obj.get("$defs", {}).get(def_name, {})
            else:
                current = current.get("items", {})
        else:
            current = current.get("properties", {}).get(part, {})
    return current.get("enum", None)


def get_def_schema(schema: dict, def_name: str) -> dict:
    """获取 $defs 中的子 schema"""
    return schema.get("$defs", {}).get(def_name, {})


def check_required(obj: dict, required: list, prefix: str) -> list[str]:
    errors = []
    for key in required:
        if key not in obj or obj[key] is None:
            errors.append(f"{prefix} 缺少必填字段: {key}")
    return errors


def check_enum(value, valid: list, field_name: str) -> list[str]:
    if value is not None and valid and value not in valid:
        return [f"{field_name}: '{value}' 不在枚举值 {valid} 中"]
    return []


def validate_material(mat: dict, schema: dict) -> list[str]:
    """根据 schema 校验单个 material 条目"""
    errors = []
    mid = mat.get('id', '?')

    # 顶层必填
    errors.extend(check_required(mat, extract_required(schema.get("$defs", {}).get("material", {}), ""),
                                 f"[{mid}]"))

    # source 层
    source_schema = get_def_schema(schema, "source")
    errors.extend(check_required(mat.get("source", {}),
                                 extract_required(source_schema, ""),
                                 f"[{mid}].source"))

    # material 层
    mat_schema = get_def_schema(schema, "material_info")
    mat_data = mat.get("material", {})
    errors.extend(check_required(mat_data,
                                 extract_required(mat_schema, ""),
                                 f"[{mid}].material"))
    # 枚举检查: material.type
    type_enum = extract_enum_values(mat_schema, "type")
    errors.extend(check_enum(mat_data.get("type"), type_enum,
                             f"[{mid}].material.type"))

    # tests[] 层
    tests = mat.get("tests", [])
    if not tests:
        errors.append(f"[{mid}].tests 不能为空")

    test_schema = get_def_schema(schema, "test")
    test_required = extract_required(test_schema, "")

    # 获取 method 的枚举值
    method_enum = None
    method_props = test_schema.get("properties", {}).get("method", {})
    if isinstance(method_props, dict):
        method_enum = method_props.get("enum")

    # 获取 results 的 required
    results_schema = test_schema.get("properties", {}).get("results", {})
    if isinstance(results_schema, dict) and "$ref" in results_schema:
        ref = results_schema["$ref"]
        if ref.startswith("#/$defs/"):
            results_schema = schema.get("$defs", {}).get(ref[len("#/$defs/"):], {})
    results_required = results_schema.get("required", [])

    for i, test in enumerate(tests):
        prefix = f"[{mid}].tests[{i}]"
        errors.extend(check_required(test, test_required, prefix))
        errors.extend(check_required(test.get("results", {}), results_required,
                                     prefix + ".results"))
        errors.extend(check_enum(test.get("method"), method_enum,
                                 prefix + ".method"))

    # quality 层
    quality_schema = get_def_schema(schema, "quality")
    errors.extend(check_required(mat.get("quality", {}),
                                 extract_required(quality_schema, ""),
                                 f"[{mid}].quality"))
    # 枚举检查: quality.confidence
    conf_enum = extract_enum_values(quality_schema, "confidence")
    errors.extend(check_enum(mat.get("quality", {}).get("confidence"), conf_enum,
                             f"[{mid}].quality.confidence"))

    return errors


def main():
    parser = argparse.ArgumentParser(description="通用实验数据 Schema 校验")
    parser.add_argument("input_dir", type=str, nargs="?", default="raw/extract/json/",
                        help="JSON 文件目录")
    parser.add_argument("--schema", type=str, required=True,
                        help="数据集 Schema 文件 (JSON)")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    schema_path = Path(args.schema)

    if not input_dir.is_dir():
        print(f"⚠️ 目录不存在: {input_dir}")
        sys.exit(1)
    if not schema_path.exists():
        print(f"⚠️ Schema 文件不存在: {schema_path}")
        sys.exit(1)

    schema = load_schema(schema_path)
    domain = schema.get("title", schema_path.stem)
    print(f"Schema: {domain}")

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
            errors.extend(validate_material(mat, schema))

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
