# -*- coding: utf-8 -*-
"""人工下载辅助：把缺失文献逐篇打开在 Edge 标签页里，接管浏览器下载并自动命名归档。

用法：
    python -B scripts/manual_assist.py                 # 打开所有缺失文献
    python -B scripts/manual_assist.py --only <doi,...> # 只开指定文献

做的事：
  1. 用带 CF 通行记录的 Edge 配置打开缺失文献标签页（每篇一个，DOI 解析进站）；
  2. 你在标签页里点 PDF / SI 时，浏览器下载事件被接管：
       - 正文 → <目标目录>/<DOI>.pdf（已存在则加序号，不覆盖）
       - 补充材料 → <目标目录>/SI/<DOI>__SI<n>.<ext>
  3. 窗口一直开着，日志实时打到 stdout；全部到齐或你建了 .manual-done 文件就退出。

浏览器操作遵循宿主实际权限，按需审批。
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DOIS_FILE = ROOT / "dois.txt"
OUT = ROOT / "raw" / "new-papers"
STATE = ROOT / "outputs" / "downloads"
PROFILE = ROOT / ".browser-profile"
SI_DIR = OUT / "SI"
STOP_FILE = STATE / ".manual-done"
LOG = STATE / "manual-assist.jsonl"


def safe_name(doi: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", doi).strip("_")


def missing_dois() -> list[str]:
    dois = [l.strip() for l in DOIS_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [d for d in dois if not (OUT / f"{safe_name(d)}.pdf").exists()
            or (OUT / f"{safe_name(d)}.pdf").stat().st_size < 20000]


def looks_like_si(name: str, url: str) -> bool:
    s = (name + " " + url).lower()
    return any(k in s for k in ("supp", "mmc", "esm", "supinfo", "si_", "_si", "supporting"))


def main() -> None:
    global DOIS_FILE, STATE, PROFILE, OUT, SI_DIR, STOP_FILE, LOG
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default="")
    ap.add_argument("--max-minutes", type=int, default=120)
    ap.add_argument("--dois", default=str(DOIS_FILE))
    ap.add_argument("--state", default=str(STATE))
    ap.add_argument("--profile", default=str(PROFILE))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    DOIS_FILE, STATE, PROFILE = Path(args.dois), Path(args.state), Path(args.profile)
    OUT = Path(args.out)
    SI_DIR, STOP_FILE, LOG = OUT / "SI", STATE / ".manual-done", STATE / "manual-assist.jsonl"

    dois = missing_dois()
    if args.only:
        want = {d.strip() for d in args.only.split(",")}
        dois = [d for d in dois if d in want]
    if not dois:
        print("没有缺失文献，无需人工下载")
        return

    OUT.mkdir(parents=True, exist_ok=True)
    SI_DIR.mkdir(parents=True, exist_ok=True)
    STATE.mkdir(parents=True, exist_ok=True)
    PROFILE.mkdir(parents=True, exist_ok=True)
    STOP_FILE.unlink(missing_ok=True)

    print(f"待人工下载 {len(dois)} 篇，窗口保持打开：")
    for i, d in enumerate(dois, 1):
        print(f"  {i:2d}. {d}")
    print(f"\n下载会自动存到：{OUT}")
    print(f"完成后可建 {STOP_FILE} 或直接关闭窗口 / 告诉我即可。\n", flush=True)

    page_doi: dict[int, str] = {}
    saved: list[dict] = []

    def on_download(dl):
        page = dl.page
        doi = page_doi.get(id(page), "")
        name = dl.suggested_filename or "download"
        try:
            if doi and looks_like_si(name, dl.url):
                ext = Path(name).suffix or ".bin"
                n = 1
                while (SI_DIR / f"{safe_name(doi)}__SI{n}{ext}").exists():
                    n += 1
                target = SI_DIR / f"{safe_name(doi)}__SI{n}{ext}"
            elif doi:
                target = OUT / f"{safe_name(doi)}.pdf"
                if target.exists() and target.stat().st_size > 20000:
                    target = OUT / f"{safe_name(doi)}__dup{int(time.time())}.pdf"
            else:
                target = OUT / name
            dl.save_as(str(target))
            size = target.stat().st_size
            rec = {"doi": doi, "file": str(target), "bytes": size, "url": dl.url[:160],
                   "ts": datetime.now().isoformat(timespec="seconds")}
            saved.append(rec)
            with LOG.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"[SAVED] {doi or name} -> {target.name} ({size / 1048576:.2f} MB)", flush=True)
        except Exception as e:
            print(f"[ERR] save {name}: {type(e).__name__} {str(e)[:70]}", flush=True)

    deadline = time.time() + args.max_minutes * 60
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), channel="msedge", headless=False,
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
            viewport={"width": 1440, "height": 950}, locale="en-US", accept_downloads=True,
        )
        ctx.on("page", lambda pg: pg.on("download", on_download))

        for doi in dois:
            try:
                pg = ctx.new_page()
                page_doi[id(pg)] = doi
                pg.goto(f"https://doi.org/{doi}", wait_until="domcontentloaded", timeout=90000)
            except Exception as e:
                print(f"[TAB] {doi} 打开失败：{type(e).__name__}", flush=True)

        first = ctx.pages[0] if ctx.pages else None
        if first is not None:
            try:
                first.close()
            except Exception:
                pass
        print("标签页已全部打开，等你手动下载……\n", flush=True)

        last_n = 0
        while time.time() < deadline:
            time.sleep(5)
            if STOP_FILE.exists():
                print("检测到 .manual-done，收工。", flush=True)
                break
            if len(saved) != last_n:
                last_n = len(saved)
            if all((OUT / f"{safe_name(d)}.pdf").exists() and
                   (OUT / f"{safe_name(d)}.pdf").stat().st_size > 20000 for d in dois):
                print("全部到齐，收工。", flush=True)
                break
        ctx.close()

    got = [d for d in dois if (OUT / f"{safe_name(d)}.pdf").exists()]
    print(f"\n本次保存 {len(saved)} 个文件；这批 {len(got)}/{len(dois)} 已有正文。")


if __name__ == "__main__":
    main()
