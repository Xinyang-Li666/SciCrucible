"""烧蚀数据库 — 增量合并 + DOI 追踪（forge-extract Step 5 + Step 5.5）

将 raw/extract/json/*.json 中的新数据合并到 database/ablation.json，
并将成功入库的 DOI 记录到 database/processed_dois.json。

合并规则（方案A）:
  - (doi, material.label) 无匹配 → 追加为新 material
  - (doi, material.label) 匹配 → 对比 tests[]:
      - 新测试条件（method + surface_temperature + duration_s 三元组不同）→ 追加到 tests[]
      - 已有测试条件 → 跳过（不覆盖）
  - 更新 quality.confidence 和 flags（若新提取更完整）

DOI 追踪:
  - 合并完成后自动更新 database/processed_dois.json
  - 记录每个 DOI 的处理时间、材料数、测试数
  - 供后续检索时自动过滤已入库文献

用法: python merge_to_db.py raw/extract/json/
"""
import sys
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path("database/ablation.json")
DOI_LOG_PATH = Path("database/processed_dois.json")


def load_db() -> dict:
    if not DB_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        return {
            "meta": {"version": "1.0", "updated": "", "total_materials": 0},
            "materials": []
        }
    return json.loads(DB_PATH.read_text(encoding="utf-8"))


def save_db(db: dict):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db["meta"]["updated"] = datetime.now().isoformat()
    db["meta"]["total_materials"] = len(db["materials"])
    DB_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")


def load_doi_log() -> dict:
    """加载已处理 DOI 记录"""
    if not DOI_LOG_PATH.exists():
        DOI_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        return {
            "description": "已处理DOI记录 — forge-extract 导入过 ablation.json 的文献",
            "updated": "",
            "dois": {}
        }
    return json.loads(DOI_LOG_PATH.read_text(encoding="utf-8"))


def save_doi_log(doi_log: dict):
    """保存已处理 DOI 记录"""
    DOI_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    doi_log["updated"] = datetime.now().isoformat()
    DOI_LOG_PATH.write_text(json.dumps(doi_log, ensure_ascii=False, indent=2), encoding="utf-8")


def update_doi_log(doi_log: dict, doi: str, materials_count: int, tests_count: int):
    """更新单条 DOI 记录（增量：若已存在则追加新材料/测试计数）"""
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
        test.get("surface_temperature_C"),
        test.get("duration_s")
    )


def merge_material(existing: dict, new: dict) -> dict:
    """将新提取的 material 合并到已有条目"""
    existing_sigs = {test_signature(t) for t in existing.get("tests", [])}
    new_tests_added = 0

    for test in new.get("tests", []):
        sig = test_signature(test)
        if sig not in existing_sigs:
            existing.setdefault("tests", []).append(test)
            existing_sigs.add(sig)
            new_tests_added += 1

    # 更新 quality（若新提取更完整）
    new_conf = new.get("quality", {}).get("confidence", "低")
    old_conf = existing.get("quality", {}).get("confidence", "低")
    conf_order = {"高": 3, "中": 2, "低": 1}
    if conf_order.get(new_conf, 0) > conf_order.get(old_conf, 0):
        existing["quality"] = new["quality"]
        # 保留 reviewer_notes
        if not existing["quality"].get("reviewer_notes"):
            existing["quality"]["reviewer_notes"] = f"更新于 {datetime.now().strftime('%Y-%m-%d')}"

    return existing, new_tests_added


def main():
    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("raw/extract/json/")
    if not input_dir.is_dir():
        print(f"⚠️ 目录不存在: {input_dir}")
        sys.exit(1)

    db = load_db()
    doi_log = load_doi_log()

    existing_index = {}
    for i, mat in enumerate(db.get("materials", [])):
        doi = mat.get("doi", "").lower().strip()
        label = mat.get("material", {}).get("label", "").lower().strip()
        existing_index[(doi, label)] = i

    stats = {"new_materials": 0, "merged_tests": 0, "skipped": 0}
    extracted_count = 0

    # 按 DOI 聚合本次入库统计
    doi_new_materials: dict[str, int] = {}
    doi_new_tests: dict[str, int] = {}

    for json_file in sorted(input_dir.glob("*.json")):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        for mat in data.get("materials", []):
            extracted_count += 1
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
                # 新材料必然有新测试
                n_tests = len(mat.get("tests", []))
                doi_new_tests[doi] = doi_new_tests.get(doi, 0) + n_tests

    save_db(db)

    # 更新 DOI 追踪
    all_dois = set(list(doi_new_materials.keys()) + list(doi_new_tests.keys()))
    for doi in all_dois:
        m_count = doi_new_materials.get(doi, 0)
        t_count = doi_new_tests.get(doi, 0)
        update_doi_log(doi_log, doi, m_count, t_count)

    save_doi_log(doi_log)

    print(f"合并完成: {stats['new_materials']} 个新材料, "
          f"{stats['merged_tests']} 条新测试合并, "
          f"{stats['skipped']} 条跳过")
    print(f"数据库: {DB_PATH} ({db['meta']['total_materials']} 个材料)")
    print(f"DOI 追踪: {DOI_LOG_PATH} (累计 {len(doi_log['dois'])} 篇)")
    print(f"Extracted: {extracted_count} entries from {len(list(input_dir.glob('*.json')))} files")


if __name__ == "__main__":
    main()
