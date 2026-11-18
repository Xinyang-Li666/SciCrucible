# -*- coding: utf-8 -*-
"""用真实 Edge 过 Cloudflare，下载 Wiley / AIP / MDPI / SAGE / ASME 的 PDF 与 SI。

为什么要浏览器：这些站点对纯 HTTP 请求一律 403（Cloudflare 按 TLS 指纹 + IP 判定）。
浏览器能过挑战，但 PDF 不能靠 context.request 取（同样 403），也不能在页面里 fetch
（Wiley 的文章页在 ceramics. 子域，跨域会被 CORS 挡）。可行做法是**导航到 PDF 地址，
接住浏览器原生的下载事件**，再 save_as 落盘。

用法：
    python -B scripts/download_browser.py --groups wiley --limit 2      # 试跑
    python -B scripts/download_browser.py --groups wiley,aip,mdpi,sage,asme
    python -B scripts/download_browser.py --only 10.1111/jace.12893

浏览器操作遵循宿主实际权限，按需审批。
"""
from __future__ import annotations

import argparse
import json
import random
import re
import tempfile
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOIS = ROOT / "dois.txt"
DEFAULT_OUT = ROOT / "raw" / "new-papers"
DEFAULT_STATE = ROOT / "outputs" / "downloads"
PROFILE = ROOT / ".browser-profile"
SI_DIRNAME = "SI"

GROUPS = {
    "10.1111": "wiley", "10.1002": "wiley",
    "10.1063": "aip", "10.3390": "mdpi", "10.1177": "sage",
    "10.1115": "asme", "10.1093": "oup",
    "10.1103": "aps", "10.1039": "rsc", "10.1126": "science", "10.1088": "iop",
    "10.1021": "acs", "10.1080": "tandf", "10.1109": "ieee",
}

# 会识别 Playwright 的站（4b 档）：acs / tandf / ieee / aps / rsc / science / iop。
# 这些组留着是为了留痕与统一入口，实际下载走真人浏览器 + scripts/adopt_downloads.py。

# 同源 fetch 兜底：IOP 这类站点 PDF 直接渲染在查看器里，不触发下载事件；
# 但文章页与 PDF 同源，fetch 不受 CORS 限制（Wiley 那种跨子域的不适用）。
FETCH_JS = """
async (url) => {
  try {
    const r = await fetch(url, {credentials: 'include'});
    if (!r.ok) return {ok: false, status: r.status};
    const b = new Uint8Array(await r.arrayBuffer());
    let s = '';
    const CH = 0x8000;
    for (let i = 0; i < b.length; i += CH) s += String.fromCharCode.apply(null, b.subarray(i, i + CH));
    return {ok: true, b64: btoa(s), bytes: b.length};
  } catch (e) { return {ok: false, err: String(e)}; }
}
"""


def group_of(doi: str) -> str:
    return GROUPS.get(doi.split("/", 1)[0].lower(), "other")


def safe_name(doi: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", doi).strip("_")


# APS：`link.aps.org/doi/{doi}` 是死路由（返回 Not Found），必须用期刊页地址，
# 且 DOI 要还原成注册时的大小写（PhysRevB.103.L041203）。DOI 后缀 → 期刊代码。
APS_JOURNALS = {
    "physrevb": ("PhysRevB", "prb"),
    "physrevlett": ("PhysRevLett", "prl"),
    "physrevmaterials": ("PhysRevMaterials", "prmaterials"),
    "physrevapplied": ("PhysRevApplied", "prapplied"),
    "revmodphys": ("RevModPhys", "rmp"),
}


def aps_url(doi: str) -> str:
    suffix = doi.split("/", 1)[-1]
    low = suffix.lower()
    for key, (label, code) in APS_JOURNALS.items():
        if low.startswith(key + "."):
            parts = suffix[len(key) + 1:].split(".")
            if parts and parts[-1] and parts[-1][0].isalpha():
                parts[-1] = parts[-1][0].upper() + parts[-1][1:]
            return f"https://journals.aps.org/{code}/abstract/10.1103/{label}.{'.'.join(parts)}"
    return f"https://doi.org/{doi}"


def article_url(doi: str) -> str:
    g = group_of(doi)
    if g == "wiley":
        return f"https://onlinelibrary.wiley.com/doi/{doi}"
    if g == "aip":
        return f"https://pubs.aip.org/doi/{doi}"
    if g == "sage":
        return f"https://journals.sagepub.com/doi/{doi}"
    if g == "oup":
        return f"https://academic.oup.com/doi/{doi}"
    if g == "aps":
        return aps_url(doi)
    if g == "science":
        return f"https://www.science.org/doi/{doi}"
    if g == "iop":
        return f"https://iopscience.iop.org/article/{doi}"
    if g == "acs":
        return f"https://pubs.acs.org/doi/{doi}"
    if g == "tandf":
        return f"https://www.tandfonline.com/doi/full/{doi}"
    return f"https://doi.org/{doi}"  # mdpi / rsc / asme / ieee：靠 DOI 解析进站


def clear_challenge(page, max_wait=60) -> str:
    deadline = time.time() + max_wait
    title = ""
    while time.time() < deadline:
        try:
            title = page.title() or ""
        except Exception:
            title = ""
        low = title.lower()
        if title and "just a moment" not in low and "attention required" not in low and "access denied" not in low:
            return title
        time.sleep(2)
    return title


def download_via_nav(ctx, url: str, wait: int = 150) -> tuple[bytes | None, str]:
    """开新标签导航到下载地址，接住 download 事件。"""
    page = ctx.new_page()
    got = []
    page.on("download", lambda d: got.append(d))
    try:
        page.goto(url, wait_until="commit", timeout=90000)
    except Exception:
        pass  # 附件响应会让 goto 抛 "Download is starting"，属正常
    deadline = time.time() + wait
    while time.time() < deadline and not got:
        page.wait_for_timeout(1000)
    if not got:
        page.close()
        return None, "no_download_event"
    path = Path(tempfile.gettempdir()) / f"dl_{int(time.time() * 1000)}_{random.randint(100, 999)}.pdf"
    try:
        got[0].save_as(str(path))
        body = path.read_bytes()
    except Exception as e:
        page.close()
        return None, f"save_error:{type(e).__name__}"
    finally:
        page.close()
        path.unlink(missing_ok=True)
    return body, "ok"


def is_pdf(b: bytes) -> bool:
    return b[:5] == b"%PDF-" and len(b) > 20_000


def fetch_same_origin(page, url: str, max_bytes: int = 200 * 1024 * 1024) -> bytes | None:
    import base64
    try:
        res = page.evaluate(FETCH_JS, url)
    except Exception:
        return None
    if not res or not res.get("ok"):
        return None
    try:
        body = base64.b64decode(res["b64"])
    except Exception:
        return None
    return body if len(body) <= max_bytes else None


def grab_pdf(ctx, page, doi: str, pdf_url: str | None) -> tuple[bytes | None, str]:
    urls: list[str] = []
    if group_of(doi) == "wiley":
        urls.append(f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}?download=true")
    if pdf_url:
        urls.append(pdf_url)
    for u in dict.fromkeys(urls):
        body, why = download_via_nav(ctx, u)
        if body and is_pdf(body):
            return body, u
    if page is not None and pdf_url:  # IOP：PDF 在查看器里，只能同源取
        body = fetch_same_origin(page, pdf_url)
        if body and is_pdf(body):
            return body, "same_origin_fetch"
    if pdf_url:  # 最后一招：浏览器上下文的 request（部分站点不绑定 TLS 指纹）
        try:
            r = ctx.request.get(pdf_url, timeout=120000)
            b = r.body() if r.ok else b""
            if is_pdf(b):
                return b, "ctx_request"
        except Exception:
            pass
    return None, "all_methods_failed"


def handle(doi: str, out: Path, page, ctx, si_max_mb: int, cf_wait: int = 60) -> dict:
    rec = {"doi": doi, "group": group_of(doi), "ts": datetime.now().isoformat(timespec="seconds")}
    target = out / f"{safe_name(doi)}.pdf"
    if target.exists() and is_pdf(target.read_bytes()):
        rec.update(status="skip_exists", file=str(target))
        return rec

    try:
        page.goto(article_url(doi), wait_until="domcontentloaded", timeout=90000)
    except Exception as e:
        rec.update(status="failed", reason=f"goto:{type(e).__name__}")
        return rec

    title = clear_challenge(page, cf_wait)
    rec["page_title"] = title[:110]
    if "just a moment" in title.lower() or "access denied" in title.lower():
        rec.update(status="failed", reason="cloudflare_not_passed")
        return rec

    el = page.query_selector("meta[name='citation_pdf_url']")
    pdf_url = el.get_attribute("content") if el else None
    rec["pdf_url"] = pdf_url

    body, src = grab_pdf(ctx, page, doi, pdf_url)
    if not body:
        rec.update(status="failed", reason=src)
        return rec
    target.write_bytes(body)
    pages = None
    try:
        import fitz
        with fitz.open(stream=body, filetype="pdf") as doc:
            pages = doc.page_count
    except Exception:
        pass
    rec.update(status="success", file=str(target), bytes=len(body), pages=pages, source=src)

    # SI：文章页上的补充材料链接，逐个用下载事件取
    try:
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    except Exception:
        hrefs = []
    keys = ("suppdata", "downloadsupplement", "supinfo", "suppl", "_si", "supporting-information", "esm")
    si_links = [u for u in dict.fromkeys(hrefs) if any(k in u.lower() for k in keys)]
    si_files = []
    if si_links:
        si_out = out / SI_DIRNAME
        si_out.mkdir(parents=True, exist_ok=True)
        for k, u in enumerate(si_links[:8], 1):
            b, _ = download_via_nav(ctx, u, wait=90)
            if not b or len(b) < 1024:
                continue
            ext = Path(u.split("?")[0]).suffix or ".bin"
            fname = f"{safe_name(doi)}__SI{k}{ext}"
            (si_out / fname).write_bytes(b)
            si_files.append({"file": str(si_out / fname), "bytes": len(b), "url": u[:160]})
    rec["si"] = si_files
    return rec


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dois", default=str(DEFAULT_DOIS))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--state", default=str(DEFAULT_STATE))
    ap.add_argument("--groups", default="wiley,aip,mdpi,sage,asme,oup,aps,rsc,science,iop")
    ap.add_argument("--only", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--si-max-mb", type=int, default=300)
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--cf-wait", type=int, default=60, help="等 Cloudflare 挑战的最长秒数")
    args = ap.parse_args()

    dois = [l.strip() for l in Path(args.dois).read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.only:
        want = {d.strip() for d in args.only.split(",")}
        dois = [d for d in dois if d in want]
    else:
        picked = {g.strip() for g in args.groups.split(",") if g.strip()}
        dois = [d for d in dois if group_of(d) in picked]
    if args.limit:
        dois = dois[:args.limit]
    if not dois:
        raise SystemExit("没有匹配的 DOI")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    state = Path(args.state)
    state.mkdir(parents=True, exist_ok=True)
    print(f"浏览器批次 {len(dois)} 条 | out={out}")

    PROFILE.mkdir(parents=True, exist_ok=True)
    manifest = state / "manifest-browser.jsonl"
    results = []
    with sync_playwright() as p, manifest.open("a", encoding="utf-8") as mf:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), channel="msedge", headless=args.headless,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1440, "height": 900}, locale="en-US",
            accept_downloads=True,
        )
        page = ctx.new_page()
        for i, doi in enumerate(dois, 1):
            try:
                rec = handle(doi, out, page, ctx, args.si_max_mb, args.cf_wait)
            except Exception as e:
                rec = {"doi": doi, "group": group_of(doi), "status": "error",
                       "reason": f"{type(e).__name__}: {str(e)[:80]}"}
            results.append(rec)
            mf.write(json.dumps(rec, ensure_ascii=False) + "\n")
            mf.flush()
            extra = rec.get("reason") or f"{rec.get('pages')}p {rec.get('bytes')}B"
            si = f" +SI{len(rec.get('si') or [])}" if rec.get("si") else ""
            print(f"[{i}/{len(dois)}] {rec['status']:12s} {doi} {str(extra)[:60]}{si}", flush=True)
            time.sleep(random.uniform(2.0, 3.5))
        ctx.close()

    ok = [r for r in results if r["status"] in ("success", "skip_exists")]
    lines = [f"# 浏览器批次报告 {datetime.now().isoformat(timespec='seconds')}", "",
             f"- 目标 {len(dois)}，成功 **{len(ok)}**", ""]
    for r in results:
        mark = "OK " if r["status"] in ("success", "skip_exists") else "FAIL"
        detail = r.get("reason") or f"{r.get('pages')}p {r.get('bytes')}B"
        suffix = f" +SI{len(r['si'])}" if r.get("si") else ""
        lines.append(f"- {mark} `{r['doi']}` — {detail}{suffix}")
    (state / "download-report-browser.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nDONE {len(ok)}/{len(dois)}")


if __name__ == "__main__":
    main()
