"""通用实验数据 — 增量合并 + DOI 追踪（forge-extract Step 5 + Step 5.5）

读取数据集配置文件，将 raw/extract/json/*.json 中的新数据合并到目标数据库。
合并规则（方案A）:
  - (doi, material.label) 无匹配 → 追加为新 material
  - (doi, material.label) 匹配 → 对比 tests[]:
      - 新测试条件（method + surface_temperature + duration_s 三元组）→ 追加
      - 已有测试条件 → 跳过（不覆盖）
  - 更新 quality 字段（若新提取更完整）

DOI 追踪:
  - 合并完成后自动更新 processed_dois.json
  - 供后续检索时自动过滤已入库文献

用法: python merge_to_db.py raw/extract/json/ --config database/configs/<dataset>.yaml
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime


def load_config(config_path: Path) -> dict:
    try:
        import yaml
        with open(config_path, encoding='utf-8') as f:
            return yaml.safe_load(f)
    except ImportError:
        print("⚠️ PyYAML 未安装，运行: pip install pyyaml")
        sys.exit(1)


def load_db(db_path: Path) -> dict:
    if not db_path.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return {
            "meta": {"version": "1.0", "updated": "", "total_materials": 0},
            "materials": []
        }
    return json.loads(db_path.read_text(encoding="utf-8"))


def save_db(db: dict, db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db["meta"]["updated"] = datetime.now().isoformat()
    db["meta"]["total_materials"] = len(db["materials"])
    db_path.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")


def load_doi_log(doi_log_path: Path) -> dict:
    if not doi_log_path.exists():
        doi_log_path.parent.mkdir(parents=True, exist_ok=True)
        return {
            "description": "已处理DOI记录",
            "updated": "",
            "dois": {}
        }
    return json.loads(doi_log_path.read_text(encoding="utf-8"))


def save_doi_log(doi_log: dict, doi_log_path: Path):
    doi_log_path.parent.mkdir(parents=True, exist_ok=True)
    doi_log["updated"] = datetime.now().isoformat()
    doi_log_path.write_text(json.dumps(doi_log, ensure_ascii=False, indent=2), encoding="utf-8")


def update_doi_log(doi_log: dict, doi: str, materials_count: int, tests_count: int):
    doi_key = doi.lower().strip()
    if doi_key in doi_log["dois"]:
        existing = doi_log["dois"][doi_key]
        doi_log["dois"][doi_key] = {
            "processed_at": datetime.now().strftime("%Y-%m-%d"),
            "materials_count": existing.get("materials_count", 0) + materials_count,
            "tests_count": existing.get("tests_count", 0) + tests_count
        }
    else:
        doi_log["dois"][doi_key] = {
            "processed_at": datetime.now().strftime("%Y-%m-%d"),
            "materials_count": materials_count,
            "tests_count": tests_count
        }


def test_signature(test: dict) -> tuple:
    """生成测试条件的唯一签名：(method, surface_temp, duration)"""
    return (
        test.get("method", ""),
        test.get("surface_temperature_C") or test.get("surface_temperature_K"),
        test.get("duration_s")
    )


def merge_material(existing: dict, new: dict) -> tuple[dict, int]:
    """将新提取的 material 合并到已有条目，返回 (merged_dict, new_tests_added)"""
    existing_sigs = {test_signature(t) for t in existing.get("tests", [])}
    new_tests_added = 0

    for test in new.get("tests", []):
        sig = test_signature(test)
        if sig not in existing_sigs:
            existing.setdefault("tests", []).append(test)
            existing_sigs.add(sig)
            new_tests_added += 1

    # 更新 quality
    new_conf = new.get("quality", {}).get("confidence", "低")
    old_conf = existing.get("quality", {}).get("confidence", "低")
    conf_order = {"高": 3, "中": 2, "低": 1}
    if conf_order.get(new_conf, 0) > conf_order.get(old_conf, 0):
        existing["quality"] = new["quality"]
        if not existing["quality"].get("reviewer_notes"):
            existing["quality"]["reviewer_notes"] = f"更新于 {datetime.now().strftime('%Y-%m-%d')}"

    return existing, new_tests_added


def main():
    parser = argparse.ArgumentParser(description="通用实验数据增量合并 + DOI 追踪")
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
    db_config = config.get("database", {})
    db_path = Path(db_config.get("output_file", "database/data.json"))
    doi_log_path = Path(db_config.get("processed_dois_file", str(db_path.with_suffix("")) + "_dois.json"))

    display_name = config.get("meta", {}).get("display_name", config_path.stem)
    print(f"数据集: {display_name}")
    print(f"数据库: {db_path}")

    db = load_db(db_path)
    doi_log = load_doi_log(doi_log_path)

    existing_index = {}
    for i, mat in enumerate(db.get("materials", [])):
        doi = mat.get("doi", "").lower().strip()
        label = mat.get("material", {}).get("label", "").lower().strip()
        existing_index[(doi, label)] = i

    stats = {"new_materials": 0, "merged_tests": 0, "skipped": 0}

    doi_new_materials: dict[str, int] = {}
    doi_new_tests: dict[str, int] = {}

    for json_file in sorted(input_dir.glob("*.json")):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        for mat in data.get("materials", []):
            doi = mat.get("doi", "").lower().strip()
            label = mat.get("material", {}).get("label", "").lower().strip()
            key = (doi, label)

            if key in existing_index:
                idx = existing_index[key]
                db["materials"][idx], added = merge_material(db["materials"][idx], mat)
                if added > 0:
                    stats["merged_tests"] += added
                    doi_new_tests[doi] = doi_new_tests.get(doi, 0) + added
                else:
                    stats["skipped"] += 1
            else:
                db["materials"].append(mat)
                existing_index[key] = len(db["materials"]) - 1
                stats["new_materials"] += 1
                doi_new_materials[doi] = doi_new_materials.get(doi, 0) + 1
                n_tests = len(mat.get("tests", []))
                doi_new_tests[doi] = doi_new_tests.get(doi, 0) + n_tests

    save_db(db, db_path)

    # 更新 DOI 追踪
    all_dois = set(list(doi_new_materials.keys()) + list(doi_new_tests.keys()))
    for doi in all_dois:
        m_count = doi_new_materials.get(doi, 0)
        t_count = doi_new_tests.get(doi, 0)
        update_doi_log(doi_log, doi, m_count, t_count)

    save_doi_log(doi_log, doi_log_path)

    json_count = len(list(input_dir.glob("*.json")))
    print(f"合并完成: {stats['new_materials']} 个新材料, "
          f"{stats['merged_tests']} 条新测试合并, "
          f"{stats['skipped']} 条跳过")
    print(f"数据库: {db_path} ({db['meta']['total_materials']} 个材料)")
    print(f"DOI 追踪: {doi_log_path} (累计 {len(doi_log['dois'])} 篇)")
    print(f"处理: {stats['new_materials'] + stats['merged_tests'] + stats['skipped']} 条目, {json_count} 文件")


if __name__ == "__main__":
    main()
