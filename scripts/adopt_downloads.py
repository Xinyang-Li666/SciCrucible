# -*- coding: utf-8 -*-
"""把手动下载的 PDF 按 DOI 归位到目标目录。

用人自己的浏览器下载时文件名千奇百怪（`jace.12893.pdf`、`1-s2.0-...-main.pdf`、
`文章名.pdf`），但 PDF 首页几乎都带 DOI。这个脚本读首页文本、抽出 DOI，
再按 `<DOI>.pdf` 命名复制进目标目录，已存在的跳过。

用法：
    python -B scripts/adopt_downloads.py --from ~/Downloads --out <目标> --days 3 --dry-run
    python -B scripts/adopt_downloads.py --from ~/Downloads --out <目标> --days 3
    python -B scripts/adopt_downloads.py --from <目录> --out <目标> --dois <清单.txt>

注意：默认只**复制**不移动，原件留在下载目录里。
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path

DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>,;()\[\]]+")
SI_HINTS = ("supp", "mmc", "esm", "supinfo", "supporting", "_si", "si-")


def safe_name(doi: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", doi).strip("_")


def first_pages_text(path: Path, pages: int = 2) -> str:
    try:
        import fitz
        with fitz.open(str(path)) as doc:
            return "".join(doc[i].get_text() for i in range(min(pages, doc.page_count)))
    except Exception:
        return ""


def doi_from_meta(path: Path) -> str:
    try:
        import fitz
        with fitz.open(str(path)) as doc:
            meta = doc.metadata or {}
        blob = " ".join(str(v) for v in meta.values())
        m = DOI_RE.search(blob)
        return m.group(0) if m else ""
    except Exception:
        return ""


def find_doi(path: Path, want: set[str] | None = None) -> tuple[str, str]:
    """返回 (doi, 来源说明)。首页文本 → PDF 元数据 → 文件名正则 → 与清单后缀互含匹配。"""
    m = DOI_RE.search(first_pages_text(path))
    if m:
        return m.group(0).rstrip(".,);"), "首页"
    d = doi_from_meta(path)
    if d:
        return d.rstrip(".,);"), "元数据"
    m = DOI_RE.search(path.stem)
    if m:
        return m.group(0), "文件名"
    # 出版商的文件名经常只留后缀，例如 sciadv.abn8241.pdf → 10.1126/sciadv.abn8241
    if want:
        stem = path.stem.lower()
        for w in want:
            suffix = w.split("/", 1)[-1].lower()
            if len(suffix) >= 8 and (suffix in stem or stem in suffix):
                return w, "清单后缀匹配"
    return "", ""


def looks_like_si(name: str) -> bool:
    s = name.lower()
    return any(k in s for k in SI_HINTS)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="src", required=True, help="下载目录（如 C:\\Users\\<you>\\Downloads）")
    ap.add_argument("--out", required=True, help="目标目录")
    ap.add_argument("--days", type=int, default=7, help="只看最近 N 天修改的文件")
    ap.add_argument("--dois", default="", help="可选：只接受清单里的 DOI")
    ap.add_argument("--state", default="", help="manifest 目录，默认与 --out 同级")
    ap.add_argument("--move", action="store_true", help="复制后删除原件（默认保留）")
    ap.add_argument("--dry-run", action="store_true", help="只报告，不写文件")
    args = ap.parse_args()

    src, out = Path(args.src).expanduser(), Path(args.out)
    if not src.is_dir():
        raise SystemExit(f"下载目录不存在：{src}")
    want = set()
    if args.dois:
        want = {l.strip() for l in Path(args.dois).read_text(encoding="utf-8").splitlines() if l.strip()}

    cutoff = datetime.now() - timedelta(days=args.days)
    files = [p for p in src.rglob("*.pdf") if p.is_file() and datetime.fromtimestamp(p.stat().st_mtime) >= cutoff]
    print(f"扫描 {src}：最近 {args.days} 天的 PDF {len(files)} 个")
    if not args.dry_run:
        out.mkdir(parents=True, exist_ok=True)
        (out / "SI").mkdir(exist_ok=True)
    state = Path(args.state) if args.state else out.parent / "_adopt"
    if not args.dry_run:
        state.mkdir(parents=True, exist_ok=True)

    taken, skipped, unknown = [], [], []
    for f in files:
        doi, how = find_doi(f, want or None)
        if not doi:
            unknown.append(f.name)
            continue
        if want and doi.lower() not in {w.lower() for w in want}:
            skipped.append((f.name, f"不在清单：{doi}"))
            continue
        if looks_like_si(f.name):
            target = out / "SI" / f"{safe_name(doi)}__{f.name}"
        else:
            target = out / f"{safe_name(doi)}.pdf"
        if target.exists() and target.stat().st_size > 20000:
            skipped.append((f.name, f"{target.name} 已存在"))
            continue
        if args.dry_run:
            taken.append((f.name, target.name, how))
            continue
        shutil.copy2(f, target)
        if args.move:
            f.unlink(missing_ok=True)
        rec = {"doi": doi, "from": str(f), "file": str(target), "bytes": target.stat().st_size,
               "how": how, "ts": datetime.now().isoformat(timespec="seconds")}
        with (state / "manifest-adopt.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        taken.append((f.name, target.name, how))

    print(f"\n{'将归位' if args.dry_run else '已归位'} {len(taken)} 个：")
    for a, b, how in taken:
        print(f"  {a[:46]:46s} -> {b:52s} ({how})")
    if skipped:
        print(f"\n跳过 {len(skipped)} 个：")
        for a, why in skipped:
            print(f"  {a[:46]:46s} {why}")
    if unknown:
        print(f"\n抽不出 DOI {len(unknown)} 个：{', '.join(unknown[:6])}{' …' if len(unknown) > 6 else ''}")


if __name__ == "__main__":
    main()
