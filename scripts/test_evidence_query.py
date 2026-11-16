"""Behavior tests for bounded, local SciCrucible evidence lookup."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_query


class EvidenceQueryTests(unittest.TestCase):
    def test_configured_stopwords_override_default(self):
        self.assertNotIn('ablation', evidence_query._terms('ablation tensile'))
        self.assertEqual(['ablation'], evidence_query._terms('ablation tensile', {'stopwords': ['tensile']}))
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "wiki" / "UHTC").mkdir(parents=True)
        (self.root / "database").mkdir()
        (self.root / "wiki" / "UHTC" / "ablation.md").write_text(
            "# 等离子体烧蚀\n\nHfC-SiC 氧化层与烧蚀测试条件总结。\n\n其它材料。",
            encoding="utf-8",
        )
        (self.root / "database" / "ablation.json").write_text(
            json.dumps({"materials": [
                {"id": "HfC-1", "material": {"label": "HfC", "system": "HfC"},
                 "tests": [{"method": "等离子体火焰", "duration_s": 90,
                            "results": {"linear_loss_rate": {"value": 0.0035, "unit": "mm/s"}}}]},
                {"id": "ZrC-1", "material": {"label": "ZrC-W", "system": "ZrC-W",
                                                          "dopant_elements": {"W": 0.2}},
                 "tests": [{"method": "氧乙炔", "duration_s": 120,
                            "results": {"linear_loss_rate": {"value": 0.001, "unit": "mm/s"}}}]},
            ]}, ensure_ascii=False), encoding="utf-8"
        )
        self.config = {"roots": ["wiki", "database"], "max_candidates": 5,
                       "max_chars": 1600, "aliases": {"plasma": ["等离子体火焰"]}}
        self.catalog = evidence_query.build_catalog(self.root, self.config)

    def tearDown(self):
        self.temp.cleanup()

    def test_catalog_keeps_metadata_not_full_document(self):
        serialized = json.dumps(self.catalog, ensure_ascii=False)
        self.assertNotIn("HfC-SiC 氧化层与烧蚀测试条件总结", serialized)
        self.assertEqual(len(self.catalog["sources"]), 2)

    def test_cli_emits_utf8_even_when_process_defaults_to_gbk(self):
        db = self.root / "database" / "ablation.json"
        data = json.loads(db.read_text(encoding="utf-8"))
        data["materials"][0]["material"]["formula"] = "Ta₀.₈Hf₀.₂C"
        db.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        config_path = self.root / "config.json"
        config_path.write_text(json.dumps(self.config), encoding="utf-8")
        catalog = evidence_query.build_catalog(self.root, self.config)
        cache = self.root / ".kiro" / ".evidence_cache"
        cache.mkdir(parents=True)
        (cache / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
        source_id = next(s["id"] for s in catalog["sources"] if s["kind"] == "database")
        result = subprocess.run(
            [sys.executable, str(Path(evidence_query.__file__)), "--root", str(self.root),
             "--config", str(config_path), "expand", "--source-id", source_id,
             "--record-id", "HfC-1", "--columns", "material.formula"],
            capture_output=True, env={**os.environ, "PYTHONIOENCODING": "gbk"}, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(payload["status"], "ok")
        self.assertIn("Ta₀.₈Hf₀.₂C", result.stdout.decode("utf-8"))

    def test_natural_question_finds_acronyms_across_wiki_lines(self):
        note = self.root / "wiki" / "UHTC" / "dmft.md"
        note.write_text("# DMFT\n局域电子关联的动态方法。\nDFT+U 是静态局域近似。\n",
                        encoding="utf-8")
        catalog = evidence_query.build_catalog(self.root, self.config)
        result = evidence_query.probe(
            "结合本地已有资料，概括 DMFT 与 DFT+U 在描述局域电子关联方面的区别，并说明各自适用边界。",
            self.root, self.config, catalog)
        self.assertTrue(any(c["path"].endswith("dmft.md") for c in result["candidates"]))

    def test_explicit_record_ids_find_ignored_database_rows(self):
        (self.root / ".gitignore").write_text("database/\n", encoding="utf-8")
        result = evidence_query.probe("比较数据库中 HfC-1 和 ZrC-1 的线烧蚀率及测试条件。",
                                      self.root, self.config, self.catalog)
        self.assertEqual(result["status"], "ok")
        rows = [c for c in result["candidates"] if c["kind"] == "database"]
        self.assertEqual(len(rows), 2)

    def test_unrelated_question_does_not_match_science_filler(self):
        result = evidence_query.probe("请查一下本地资料里有没有关于睡眠剥夺与记忆巩固的研究记录",
                                      self.root, self.config, self.catalog)
        self.assertEqual(result["candidates"], [])

    def _cli(self, args):
        config = self.root / "config.json"
        config.write_text(json.dumps(self.config), encoding="utf-8")
        cache = self.root / ".kiro" / ".evidence_cache"
        cache.mkdir(parents=True, exist_ok=True)
        (cache / "catalog.json").write_text(json.dumps(self.catalog), encoding="utf-8")
        return subprocess.run([sys.executable, str(Path(evidence_query.__file__)),
                               "--root", str(self.root), "--config", str(config), *args],
                              capture_output=True, timeout=15)

    def test_probe_read_args_execute_exact_record_without_json_filter(self):
        result = evidence_query.probe("ZrC-1", self.root, self.config, self.catalog)
        candidate = next(c for c in result["candidates"] if c["kind"] == "database")
        self.assertEqual(candidate["record_id"], "ZrC-1")
        read = self._cli(candidate["read_args"])
        self.assertEqual(read.returncode, 0, read.stderr)
        payload = json.loads(read.stdout.decode("utf-8"))
        self.assertEqual([r["id"] for r in payload["records"]], ["ZrC-1"])

    def test_record_id_selector_excludes_other_material(self):
        source = next(s for s in self.catalog["sources"] if s["kind"] == "database")
        result = evidence_query.expand(source["id"], self.root, self.config, self.catalog,
                                       {"record_ids": ["ZrC-1"], "columns": ["id"]})
        self.assertEqual([r["id"] for r in result["records"]], ["ZrC-1"])

    def test_cli_accepts_repeated_record_ids_and_comma_columns(self):
        source = next(s for s in self.catalog["sources"] if s["kind"] == "database")
        result = self._cli(["expand", "--source-id", source["id"], "--record-id", "HfC-1",
                            "--record-id", "ZrC-1", "--columns", "id,test.duration_s"])
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout.decode("utf-8"))["records"]
        self.assertEqual({r["id"] for r in rows}, {"HfC-1", "ZrC-1"})
        self.assertEqual({r["test.duration_s"] for r in rows}, {90, 120})

    def test_database_expand_requires_selection(self):
        source = next(s for s in self.catalog["sources"] if s["kind"] == "database")
        result = evidence_query.expand(source["id"], self.root, self.config, self.catalog)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"]["code"], "selector_required")

    def test_unknown_record_id_is_not_silent_partial_success(self):
        source = next(s for s in self.catalog["sources"] if s["kind"] == "database")
        result = evidence_query.expand(source["id"], self.root, self.config, self.catalog,
                                       {"record_ids": ["HfC-1", "missing"]})
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"]["missing_record_ids"], ["missing"])

    def test_char_budget_marks_actual_truncation_and_counts_matches(self):
        source = next(s for s in self.catalog["sources"] if s["kind"] == "database")
        result = evidence_query.expand(source["id"], self.root,
                                       {**self.config, "max_expand_chars": 100}, self.catalog,
                                       {"record_ids": ["HfC-1", "ZrC-1"],
                                        "columns": ["id", "material.label"]})
        self.assertTrue(result["truncated"])
        self.assertEqual(result["truncation_reason"], "char_budget")
        self.assertEqual(result["matched_records"], 2)
        self.assertEqual(result["returned_records"], 1)

    def test_exact_record_limit_is_not_false_truncation(self):
        source = next(s for s in self.catalog["sources"] if s["kind"] == "database")
        result = evidence_query.expand(source["id"], self.root, self.config, self.catalog,
                                       {"where": {"id": "HfC-1"}, "limit": 1})
        self.assertFalse(result["truncated"])

    def test_sql_where_returns_actionable_error(self):
        source = next(s for s in self.catalog["sources"] if s["kind"] == "database")
        result = self._cli(["expand", "--source-id", source["id"],
                            "--where", "id contains HfC-1"])
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stderr.decode("utf-8"))
        self.assertEqual(payload["error"]["code"], "invalid_where")
        self.assertIn("--record-id", payload["error"]["message"])

    def test_probe_returns_relevant_bounded_candidates(self):
        result = evidence_query.probe("HfC 等离子体火焰", self.root, self.config, self.catalog)
        self.assertEqual(result["status"], "ok")
        self.assertLessEqual(len(result["candidates"]), 5)
        self.assertTrue(any(c["kind"] == "database" for c in result["candidates"]))
        self.assertLessEqual(sum(len(c["snippet"]) for c in result["candidates"]), 1600)

    def test_probe_ignores_common_english_words_and_requires_specificity(self):
        result = evidence_query.probe("W doping HfC", self.root, self.config, self.catalog)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["candidates"], [])

    def test_short_element_symbol_uses_token_boundary(self):
        result = evidence_query.probe("W plasma", self.root, self.config, self.catalog)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["candidates"], [])

    def test_query_requires_explicit_element_and_dopant_evidence(self):
        result = evidence_query.probe("W dopant ZrC", self.root, self.config, self.catalog)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["candidates"]), 1)
        self.assertIn("ZrC-W", result["candidates"][0]["snippet"])

    def test_database_expand_filters_material_and_columns(self):
        source = next(s for s in self.catalog["sources"] if s["kind"] == "database")
        result = evidence_query.expand(source["id"], self.root, self.config, self.catalog,
                                       selector={"where": {"material.label": "HfC"},
                                                 "columns": ["id", "material.label", "test.method"]})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["records"]), 1)
        self.assertEqual(result["records"][0]["id"], "HfC-1")
        self.assertEqual(result["records"][0]["test.method"], "等离子体火焰")
        self.assertNotIn("results", result["records"][0])
        self.assertIn("materials[0]", result["records"][0]["locator"])

    def test_tampered_source_id_cannot_escape_allowed_roots(self):
        malicious = {"sources": [{"id": "outside", "path": "../secret.txt", "kind": "wiki", "sha256": "x"}]}
        result = evidence_query.expand("outside", self.root, self.config, malicious)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"]["code"], "path_outside_roots")

    def test_stale_catalog_is_reported(self):
        (self.root / "wiki" / "UHTC" / "ablation.md").write_text("# changed\n", encoding="utf-8")
        result = evidence_query.probe("HfC 等离子体烧蚀", self.root, self.config, self.catalog)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["errors"][0]["code"], "stale_catalog")

    def test_corrupt_json_is_an_error_not_a_negative_match(self):
        (self.root / "database" / "ablation.json").write_text("{broken", encoding="utf-8")
        result = evidence_query.probe("HfC 烧蚀", self.root, self.config, self.catalog)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["errors"][0]["code"], "invalid_json")


if __name__ == "__main__":
    unittest.main()
