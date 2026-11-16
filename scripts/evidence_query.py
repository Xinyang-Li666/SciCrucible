"""Bounded local search and selective reads for SciCrucible wiki/database evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _allowed_roots(root: Path, config: dict) -> list[Path]:
    roots = []
    for rel in config.get("roots", ["wiki", "database"]):
        candidate = (root / rel).resolve()
        if not candidate.is_relative_to(root.resolve()):
            raise ValueError(f"configured root escapes repository: {rel}")
        roots.append(candidate)
    return roots


def _source_kind(path: Path, roots: list[Path]) -> str:
    for allowed in roots:
        if path.is_relative_to(allowed):
            return "database" if allowed.name == "database" else "wiki"
    raise ValueError("source_outside_roots")


def _title_and_fields(path: Path, kind: str) -> tuple[str, list[str]]:
    if kind == "wiki":
        with path.open("r", encoding="utf-8") as stream:
            for line in stream:
                if line.startswith("# "):
                    return line[2:].strip(), []
        return path.stem, []
    data = json.loads(path.read_text(encoding="utf-8"))
    fields: set[str] = set()

    def visit(value: Any, prefix: str = ""):
        if isinstance(value, dict):
            for key, child in value.items():
                full = f"{prefix}.{key}" if prefix else key
                fields.add(full)
                visit(child, full)
        elif isinstance(value, list) and value:
            visit(value[0], f"{prefix}[]")

    visit(data)
    meta = data.get("meta", {}) if isinstance(data, dict) else {}
    return str(meta.get("display_name") or meta.get("name") or path.stem), sorted(fields)


def build_catalog(root: Path, config: dict) -> dict:
    root = root.resolve()
    roots = _allowed_roots(root, config)
    sources = []
    for allowed in roots:
        if not allowed.exists():
            continue
        patterns = ("*.md",) if allowed.name != "database" else ("*.json",)
        for pattern in patterns:
            for file in sorted(allowed.rglob(pattern)):
                resolved = file.resolve()
                if not any(resolved.is_relative_to(r) for r in roots) or not resolved.is_file():
                    continue
                kind = _source_kind(resolved, roots)
                title, fields = _title_and_fields(resolved, kind)
                relpath = resolved.relative_to(root).as_posix()
                key = hashlib.sha1(relpath.encode("utf-8")).hexdigest()[:12]
                sources.append({
                    "id": f"{kind}:{key}", "path": relpath, "kind": kind,
                    "title": title, "topics": config.get("topics", {}).get(relpath, []),
                    "aliases": config.get("aliases", {}).get(relpath, []),
                    "fields": fields, "sha256": _sha256(resolved),
                })
    return {"schema_version": 1, "built_at": datetime.now(timezone.utc).isoformat(),
            "sources": sources}


def _terms(query: str, config: dict | None = None) -> list[str]:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9._+-]*|[\u3400-\u9fff]{2,}", query)
    stopwords = {"the", "and", "for", "with", "from", "that", "this", "what", "how",
                 "does", "are", "was", "were", "paper", "study", "data", "results",
                 "please", "about", "into", "our", "you", "can", "could", "ablation",
                 "oxidation", "experiment", "test", "tests", "performance", "property",
                 "properties", "mass", "loss", "rate", "linear", "recession", "value",
                 "compare", "comparison", "effect", "influence", "on", "of", "to"}
    stopwords = set((config or {}).get('stopwords', stopwords))
    aliases = {"tungsten": "w", "wolfram": "w", "doping": "dopant", "doped": "dopant"}
    result = set()
    for word in words:
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", word):
            lowered = word.lower()
            if lowered in stopwords or (len(word) == 1 and not word.isupper()):
                continue
            result.add(aliases.get(lowered, lowered))
        if re.fullmatch(r"[\u3400-\u9fff]+", word):
            result.add(word.lower())
            result.update(word[i:i + 2] for i in range(len(word) - 1))
    return sorted(result, key=len, reverse=True)


def _has_term(text: str, term: str) -> bool:
    if re.fullmatch(r"[a-z]", term):
        # Preserve the case-sensitive chemical symbol: C must not match every "c" in prose.
        return re.search(rf"(?<![A-Za-z]){re.escape(term.upper())}(?![a-z])", text) is not None
    if re.fullmatch(r"[a-z]{2}", term) and term.title() in {
        "He", "Li", "Be", "Ne", "Na", "Mg", "Al", "Si", "Cl", "Ar", "Ca", "Sc", "Ti", "Cr",
        "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb",
        "Sr", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn", "Sb",
        "Te", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb",
        "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Hf", "Ta", "Re", "Os", "Ir", "Pt", "Au",
        "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th", "Pa", "U",
        "W", "V", "Y", "B", "C", "N", "O", "F", "P", "S", "K", "I",
    }:
        symbol = term.title()
        return re.search(rf"(?<![A-Za-z]){symbol}(?![a-z])", text) is not None
    return term in text.lower()


def _anchors(query: str) -> set[str]:
    """Prefer explicit acronyms/formulas over conversational Chinese filler."""
    return {word.lower() for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9._+-]*", query)
            if sum(c.isupper() for c in word) >= 2 and len(word) >= 3}


def _mentions_record(query: str, record: dict) -> bool:
    record_id = record.get("id")
    if not isinstance(record_id, str) or not record_id:
        return False
    names = [record_id]
    short = record_id.rsplit("-", 1)[-1]
    if len(short) >= 3 and short.isupper() and any(c.isdigit() for c in short):
        names.append(short)
    return any(re.search(rf"(?<![A-Za-z0-9_-]){re.escape(name)}(?![A-Za-z0-9_-])",
                         query, re.IGNORECASE) for name in names)


def _flatten_records(data: Any, path: str = "$", parent_key: str = ""):
    if isinstance(data, dict):
        if "material" in data and "tests" in data:
            for i, test in enumerate(data.get("tests", [])):
                yield f"{path}.tests[{i}]", {"material": data.get("material"), "id": data.get("id"), "doi": data.get("doi"), "test": test}
        else:
            for key, value in data.items():
                yield from _flatten_records(value, f"{path}.{key}", key)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            yield from _flatten_records(item, f"{path}[{i}]", parent_key)


def _read_source(root: Path, config: dict, source: dict) -> tuple[Path | None, dict | None]:
    try:
        repo = root.resolve()
        path = (repo / source["path"]).resolve()
        roots = _allowed_roots(repo, config)
        if not any(path.is_relative_to(r) for r in roots):
            return None, {"code": "path_outside_roots", "message": "source resolves outside configured roots"}
        if not path.is_file():
            return None, {"code": "source_missing", "message": "source file is missing"}
        try:
            digest = _sha256(path)
        except OSError as exc:
            return None, {"code": "read_failed", "message": str(exc)}
        if digest != source.get("sha256"):
            if path.suffix.lower() == ".json":
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                except (UnicodeError, json.JSONDecodeError) as exc:
                    return None, {"code": "invalid_json", "message": str(exc)}
            return None, {"code": "stale_catalog", "message": "source changed after catalog build"}
        return path, None
    except (KeyError, ValueError, OSError) as exc:
        return None, {"code": "invalid_source", "message": str(exc)}


def probe(query: str, root: Path, config: dict, catalog: dict, limit: int | None = None) -> dict:
    terms = _terms(query, config)
    if not terms:
        return {"status": "ok", "candidates": [], "truncated": False, "errors": []}
    cap = min(max(1, limit or config.get("max_candidates", 5)), 5)
    char_budget = min(max(100, config.get("max_chars", 1600)), 1600)
    found = []
    errors = []
    symbols = {symbol.lower() for symbol in re.findall(r"(?<![A-Za-z])[A-Z][a-z]?(?![A-Za-z0-9])", query)}
    numeric_terms = {term for term in terms if any(character.isdigit() for character in term)}
    generic = {"ablation", "oxidation", "experiment", "test", "tests", "performance", "property",
               "properties", "mass", "loss", "rate", "linear", "recession", "value", "compare",
               "comparison", "effect", "influence"}
    informative = [term for term in terms if term not in generic and not re.fullmatch(r"[a-z]", term)]
    min_specific_hits = len(informative) if len(informative) <= 3 else (len(informative) * 2 + 2) // 3
    anchors = _anchors(query)
    required = anchors | symbols | ({"dopant"} if "dopant" in terms else set())
    for source in catalog.get("sources", []):
        path, error = _read_source(root, config, source)
        if error:
            errors.append({"source_id": source.get("id"), **error})
            continue
        try:
            if source["kind"] == "wiki":
                text = path.read_text(encoding="utf-8")
                lines = text.splitlines()
                # A natural question may describe a page in several sentences;
                # do not require all its filler bigrams in one source line.
                if anchors:
                    if not all(_has_term(text, term) for term in required):
                        continue
                    best = max(range(len(lines)), key=lambda i: sum(_has_term(lines[i], t) for t in required))
                    matched = [term for term in terms if _has_term(text, term)]
                    snippet = "\n".join(lines[max(0, best - 1): min(len(lines), best + 2)])
                    found.append((len(required), {"source_id": source["id"], "path": source["path"],
                                  "kind": "wiki", "title": source["title"], "locator": f"line {best + 1}",
                                  "snippet": snippet[:500], "match_terms": matched[:8]}))
                    continue
                for i, line in enumerate(lines):
                    matched = [term for term in terms if _has_term(line, term)]
                    specific_hits = sum(term in matched for term in informative)
                    if matched and symbols.issubset(set(matched)) and specific_hits >= min_specific_hits:
                        snippet = "\n".join(lines[max(0, i - 1): min(len(lines), i + 2)])
                        found.append((len(matched), {"source_id": source["id"], "path": source["path"],
                                      "kind": "wiki", "title": source["title"], "locator": f"line {i + 1}",
                                      "snippet": snippet[:500], "match_terms": matched[:8]}))
                        break
            else:
                data = json.loads(path.read_text(encoding="utf-8"))
                for locator, record in _flatten_records(data):
                    material_text = json.dumps(record.get("material"), ensure_ascii=False, sort_keys=True)
                    rendered = json.dumps({"material": record.get("material"), "test": record.get("test")},
                                          ensure_ascii=False, sort_keys=True)
                    matched = [term for term in terms if _has_term(rendered, term)]
                    material_matches = {term for term in symbols if _has_term(material_text, term)}
                    specific_hits = sum(term in matched for term in informative)
                    explicit_id = _mentions_record(query, record)
                    if (explicit_id or (matched and symbols.issubset(material_matches)
                            and numeric_terms.issubset(set(matched))
                            and (required.issubset(set(matched)) if anchors else specific_hits >= min_specific_hits))):
                        found.append((len(matched), {"source_id": source["id"], "path": source["path"],
                                      "kind": "database", "title": source["title"], "locator": locator,
                                      "record_id": record.get("id"),
                                      "snippet": json.dumps(record, ensure_ascii=False)[:500], "match_terms": matched[:8]}))
        except (UnicodeError, json.JSONDecodeError, OSError) as exc:
            errors.append({"source_id": source.get("id"), "code": "invalid_json" if path.suffix == ".json" else "read_failed", "message": str(exc)})
    if errors:
        return {"status": "error", "candidates": [], "truncated": False, "errors": errors}
    found.sort(key=lambda item: (-item[0], item[1]["path"], item[1]["locator"]))
    candidates = []
    remaining = char_budget
    for _, candidate in found[:cap]:
        if remaining <= 0:
            break
        candidate["snippet"] = candidate["snippet"][:remaining]
        remaining -= len(candidate["snippet"])
        candidate["read_args"] = ["expand", "--source-id", candidate["source_id"]]
        if candidate["kind"] == "database":
            if isinstance(candidate.get("record_id"), str) and candidate["record_id"]:
                candidate["read_args"] += ["--record-id", candidate["record_id"]]
            else:
                candidate.pop("read_args")
                candidate["read_note"] = "No record ID; provide an explicit JSON --where selector."
        candidates.append(candidate)
    return {"status": "ok", "candidates": candidates,
            "truncated": len(found) > len(candidates), "errors": []}


def _get_path(value: Any, dotted: str) -> Any:
    current = value
    for segment in dotted.split("."):
        if isinstance(current, list) and segment.isdigit():
            current = current[int(segment)]
        elif isinstance(current, dict) and segment in current:
            current = current[segment]
        else:
            return None
    return current


def expand(source_id: str, root: Path, config: dict, catalog: dict, selector: dict | None = None) -> dict:
    source = next((item for item in catalog.get("sources", []) if item.get("id") == source_id), None)
    if not source:
        return {"status": "error", "error": {"code": "source_unknown", "message": "Use source_id or read_args returned by probe; do not invent a source ID."}}
    path, error = _read_source(root, config, source)
    if error:
        return {"status": "error", "error": error}
    selector = selector or {}
    if source["kind"] == "wiki":
        try:
            text = path.read_text(encoding="utf-8")
            max_chars = min(max(100, int(config.get("max_expand_chars", 6000))), 6000)
            return {"status": "ok", "source_id": source_id, "fingerprint": source["sha256"],
                    "locator": "whole-file", "content": text[:max_chars], "truncated": len(text) > max_chars}
        except (UnicodeError, OSError) as exc:
            return {"status": "error", "error": {"code": "read_failed", "message": str(exc)}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        return {"status": "error", "error": {"code": "invalid_json", "message": str(exc)}}
    columns = selector.get("columns", [])
    where = selector.get("where", {})
    record_ids = selector.get("record_ids", [])
    if (not isinstance(columns, list) or not all(isinstance(c, str) and c.strip() for c in columns)
            or not isinstance(where, dict) or not isinstance(record_ids, list)
            or not all(isinstance(r, str) and r for r in record_ids)):
        return {"status": "error", "error": {"code": "invalid_selector", "message": "columns and record_ids must be lists of nonempty strings; where must be a JSON object."}}
    columns = [part.strip() for col in columns for part in col.split(",") if part.strip()]
    if not record_ids and not where:
        return {"status": "error", "error": {"code": "selector_required", "message": "Database reads require --record-id ID (repeat for multiple IDs) or a JSON --where object. Copy read_args from probe; unfiltered reads are disabled."}}
    rows = []
    max_records = min(max(1, int(selector.get("limit", 20))), 100)
    max_chars = min(max(100, int(config.get("max_expand_chars", 6000))), 6000)
    used = 0
    matched_records = 0
    truncation_reason = None
    requested_ids = set(record_ids)
    seen_ids = set()
    for locator, record in _flatten_records(data):
        record_id = record.get("id")
        if isinstance(record_id, str):
            seen_ids.add(record_id)
        if requested_ids and record_id not in requested_ids:
            continue
        material = record.get("material") or {}
        test = record.get("test") or {}
        view = {"id": record.get("id"), "doi": record.get("doi"), "material": material, "test": test}
        if any(_get_path(view, key) != expected for key, expected in where.items()):
            continue
        matched_records += 1
        if truncation_reason:
            continue  # Count remaining matches locally; never send the rest to the model.
        selected = {"locator": locator}
        if columns:
            for column in columns:
                value = _get_path(view, column)
                if value is not None:
                    selected[column] = value
        else:
            selected.update(view)
        row_chars = len(json.dumps(selected, ensure_ascii=False))
        if len(rows) >= max_records:
            truncation_reason = "record_limit"
            continue
        if used + row_chars > max_chars:
            truncation_reason = "char_budget"
            continue
        rows.append(selected)
        used += row_chars
    missing_ids = sorted(requested_ids - seen_ids)
    if missing_ids:
        return {"status": "error", "error": {"code": "record_unknown", "missing_record_ids": missing_ids,
                "message": "Requested record IDs are absent from this source; use record_id returned by probe. No partial success or full-database fallback."}}
    return {"status": "ok", "source_id": source_id, "fingerprint": source["sha256"],
            "records": rows, "matched_records": matched_records, "returned_records": len(rows),
            "truncated": truncation_reason is not None, "truncation_reason": truncation_reason,
            "selection": {"record_ids": sorted(requested_ids), "where": where, "columns": columns}}


def _main() -> int:
    # JSON is a UTF-8 interface regardless of the Windows console code page.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1] / "config" / "evidence-retrieval.json")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    p_probe = sub.add_parser("probe")
    p_probe.add_argument("--query", required=True)
    p_probe.add_argument("--limit", type=int)
    p_expand = sub.add_parser("expand")
    p_expand.add_argument("--source-id", required=True)
    p_expand.add_argument("--record-id", action="append", default=[], help="Exact record ID; repeat to select multiple IDs (OR).")
    p_expand.add_argument("--columns", nargs="*", default=[], help="Space-separated fields; comma-separated fields also accepted.")
    p_expand.add_argument("--where", default="{}", help="JSON object with exact field matches (AND), not SQL; prefer --record-id.")
    p_expand.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        catalog_path = args.root / ".kiro" / ".evidence_cache" / "catalog.json"
        if args.command == "build":
            catalog = build_catalog(args.root, config)
            catalog_path.parent.mkdir(parents=True, exist_ok=True)
            temp = catalog_path.with_suffix(".tmp")
            temp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(catalog_path)
            result = {"status": "ok", "catalog": str(catalog_path), "sources": len(catalog["sources"])}
        else:
            if args.command == "probe":
                # Refresh local metadata on each new top-level lookup so additions are not missed.
                # Only candidate snippets are returned to the model; corpus text stays local.
                catalog = build_catalog(args.root, config)
                catalog_path.parent.mkdir(parents=True, exist_ok=True)
                temp = catalog_path.with_suffix(".tmp")
                temp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
                temp.replace(catalog_path)
                result = probe(args.query, args.root, config, catalog, args.limit)
            else:
                catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
                try:
                    where = json.loads(args.where)
                except json.JSONDecodeError:
                    print(json.dumps({"status": "error", "error": {"code": "invalid_where",
                          "message": "--where requires a JSON object, not SQL. Prefer --record-id ID (repeat for multiple IDs); copy read_args from probe."}}), file=sys.stderr)
                    return 2
                result = expand(args.source_id, args.root, config, catalog,
                                {"columns": args.columns, "where": where, "record_ids": args.record_id, "limit": args.limit})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "ok" else 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": {"code": "command_failed", "message": str(exc)}}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
