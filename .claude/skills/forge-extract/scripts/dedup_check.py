"""通用实验数据 — 去重检查（forge-extract Step 5）

在合并前检查 raw/extract/json/ 中的新提取数据与目标数据库已有数据：
  - DOI + material.label 完全匹配 → 报告重复，比较 tests[] 条数
  - 无匹配 → 标记为新条目

用法: python dedup_check.py raw/extract/json/ --db database/<dataset>.json
"""
import sys
import json
import argparse
from pathlib import Path


def load_existing_db(db_path: Path) -> dict:
    if not db_path.exists():
        return {"meta": {"version": "1.0", "updated": "", "total_materials": 0}, "materials": []}
    return json.loads(db_path.read_text(encoding="utf-8"))


def build_existing_index(materials: list) -> dict:
    """构建 (doi, label) → 索引 的查找表"""
    index = {}
    for i, mat in enumerate(materials):
        doi = mat.get("doi", "").lower().strip()
        label = mat.get("material", {}).get("label", "").lower().strip()
        key = (doi, label)
        if key not in index:
            index[key] = []
        index[key].append(i)
    return index


def main():
    parser = argparse.ArgumentParser(description="通用实验数据去重检查")
    parser.add_argument("input_dir", type=str, nargs="?", default="raw/extract/json/",
                        help="JSON 文件目录")
    parser.add_argument("--db", type=str, required=True,
                        help="目标数据库 JSON 文件路径")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    db_path = Path(args.db)

    if not input_dir.is_dir():
        print(f"⚠️ 目录不存在: {input_dir}")
        sys.exit(1)
    if not db_path.exists():
        print(f"⚠️ 数据库不存在: {db_path}（将全部视为新条目）")

    db = load_existing_db(db_path)
    existing = build_existing_index(db.get("materials", []))
    print(f"数据库: {db_path} ({db['meta']['total_materials']} 个材料)")

    new_count = 0
    dup_count = 0
    merge_count = 0

    for json_file in sorted(input_dir.glob("*.json")):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        for mat in data.get("materials", []):
            doi = mat.get("doi", "").lower().strip()
            label = mat.get("material", {}).get("label", "").lower().strip()
            key = (doi, label)

            if key in existing:
                dup_indices = existing[key]
                existing_mat = db["materials"][dup_indices[0]]
                existing_tests = len(existing_mat.get("tests", []))
                new_tests = len(mat.get("tests", []))

                if new_tests > existing_tests:
                    print(f"  🔀 {mat.get('id')}: 已有 {existing_tests} 条测试，新提取 {new_tests} 条（将合并新测试条件）")
                    merge_count += 1
                else:
                    print(f"  ⏭️ {mat.get('id')}: 已存在且测试条数相同/更多（{existing_tests} ≥ {new_tests}），跳过")
                    dup_count += 1
            else:
                print(f"  🆕 {mat.get('id')}: 新材料条目")
                new_count += 1

    print(f"\n去重结果: {new_count} 新增, {merge_count} 合并, {dup_count} 跳过")
    print(f"数据库当前: {db['meta']['total_materials']} 个材料 → 预计 {db['meta']['total_materials'] + new_count} 个材料")


if __name__ == "__main__":
    main()
