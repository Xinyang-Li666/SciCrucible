# -*- coding: utf-8 -*-
"""下载台账：校验 PDF、汇总逐条状态、生成缺失清单（文献传递用）。

读三类东西：
  - DOI 清单（一行一个）
  - <state>/manifest.jsonl、manifest-browser.jsonl、manifest-si.jsonl
  - <out>/ 下按 DOI 命名的 PDF（以及 <out>/SI/）

输出：
  - <state>/download-summary.md   逐条台账 + 按出版商统计
  - <state>/ILL-list.md           缺失清单（题名 + 原因，可直接提交文献传递）
  - <state>/ledger.json           机器可读版本

用法：
    python -B scripts/download_ledger.py --dois dois.txt --out <PDF目录> --state <台账目录>
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


def safe_name(doi: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", doi).strip("_")


GROUP = {"10.1016": "Elsevier", "10.1111": "Wiley", "10.1002": "Wiley", "10.1007": "Springer",
         "10.1023": "Springer", "10.1134": "Springer/Pleiades", "10.1063": "AIP", "10.3390": "MDPI",
         "10.1177": "SAGE", "10.1115": "ASME", "10.1093": "OUP", "10.21236": "DTIC", "10.2172": "OSTI",
         "10.2497": "J-STAGE", "10.2978": "J-STAGE", "10.26083": "TUprints", "10.26599": "SciOpen",
         "10.4191": "KCERS"}


def read_jsonl(path: Path) -> list[dict]:
    out = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def page_count(path: Path) -> int | None:
    try:
        import fitz
        with fitz.open(str(path)) as doc:
            return doc.page_count
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dois", required=True, help="DOI 清单文件")
    ap.add_argument("--out", required=True, help="PDF 输出目录")
    ap.add_argument("--state", required=True, help="manifest 与台账所在目录")
    ap.add_argument("--meta", default="", help="可选：probe-metadata.json（取题名）")
    args = ap.parse_args()

    out, state = Path(args.out), Path(args.state)
    dois = [l.strip() for l in Path(args.dois).read_text(encoding="utf-8").splitlines() if l.strip()]

    titles: dict[str, str] = {}
    meta = Path(args.meta) if args.meta else state / "probe-metadata.json"
    if meta.exists():
        for r in json.loads(meta.read_text(encoding="utf-8")):
            if r.get("doi") and r.get("title"):
                titles[r["doi"]] = r["title"]

    routes: dict[str, dict] = {}
    for name in ("manifest.jsonl", "manifest-browser.jsonl"):
        for r in read_jsonl(state / name):
            if r.get("doi"):
                routes[r["doi"]] = r

    si_count: Counter = Counter()
    si_bytes: Counter = Counter()
    for r in read_jsonl(state / "manifest-si.jsonl"):
        doi = r.get("doi")
        if not doi:
            continue
        files = r.get("files") or []
        if files:
            si_count[doi] = len(files)
            si_bytes[doi] = sum(f.get("bytes", 0) for f in files)
    for doi, r in routes.items():
        if r.get("si"):
            si_count[doi] = max(si_count[doi], len(r["si"]))
            si_bytes[doi] = max(si_bytes[doi], sum(f.get("bytes", 0) for f in r["si"]))

    rows, bad = [], []
    for doi in dois:
        f = out / f"{safe_name(doi)}.pdf"
        ok = f.exists() and f.stat().st_size > 20_000
        pages = None
        if ok:
            if f.open("rb").read(5) != b"%PDF-":
                bad.append(str(f))
                ok = False
            else:
                pages = page_count(f)
                if pages is not None and pages < 2:
                    bad.append(f"{f} ({pages}p)")
        rec = routes.get(doi, {})
        rows.append({"doi": doi, "group": GROUP.get(doi.split("/")[0], "其他"), "ok": ok,
                     "mb": (f.stat().st_size / 1048576) if ok else 0.0, "pages": pages,
                     "route": rec.get("route") or rec.get("source") or "",
                     "reason": rec.get("reason", ""),
                     "si": si_count.get(doi, 0), "si_mb": si_bytes.get(doi, 0) / 1048576,
                     "title": titles.get(doi, "")})

    got = [r for r in rows if r["ok"]]
    miss = [r for r in rows if not r["ok"]]
    total_mb = sum(r["mb"] for r in got)
    si_total_mb = sum(r["si_mb"] for r in rows)

    lines = ["# 全文下载台账", "",
             f"生成时间：{datetime.now().isoformat(timespec='seconds')}　|　目标目录：`{out}`", "",
             f"- 主文到手 **{len(got)}/{len(rows)}**，合计 {total_mb:.0f} MB，"
             f"{sum(r['pages'] or 0 for r in got)} 页",
             f"- 带 SI **{sum(1 for r in rows if r['si'])}** 篇，合计 {si_total_mb:.1f} MB",
             ""]
    if bad:
        lines += [f"- ⚠️ 校验异常 {len(bad)} 个：{', '.join(bad)}", ""]
    lines += ["## 按出版商", "", "| 出版商 | 目标 | 到手 |", "|---|---|---|"]
    for g in sorted({r["group"] for r in rows}):
        sub = [r for r in rows if r["group"] == g]
        lines.append(f"| {g} | {len(sub)} | {sum(1 for r in sub if r['ok'])} |")
    lines += ["", "## 逐条台账", "", "| # | DOI | 出版商 | 页 | MB | SI | 状态 |", "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        lines.append(f"| {i} | `{r['doi']}` | {r['group']} | {r['pages'] or ''} | {r['mb']:.1f} | "
                     f"{r['si'] or ''} | {'✅' if r['ok'] else '❌'} |")
    (state / "download-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    ill = ["# 文献传递 / 待补清单", "", f"缺失 {len(miss)} 条。", ""]
    for r in miss:
        ill.append(f"- `{r['doi']}` — {r['group']} — {r['reason'] or '未下载'}")
        if r["title"]:
            ill.append(f"  - {r['title'][:140]}")
    reasons = Counter(r["reason"] or "未下载" for r in miss)
    ill += ["", "## 缺失原因分布", ""] + [f"- {k}: {v}" for k, v in reasons.most_common()]
    (state / "ILL-list.md").write_text("\n".join(ill) + "\n", encoding="utf-8")

    (state / "ledger.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"到手 {len(got)}/{len(rows)} | {total_mb:.0f} MB | 带SI {sum(1 for r in rows if r['si'])} 篇"
          f" | 缺失 {len(miss)}")
    if bad:
        print(f"校验异常: {bad}")


if __name__ == "__main__":
    main()
