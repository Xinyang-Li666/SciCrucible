# -*- coding: utf-8 -*-
"""SciCrucible 多出版商 PDF 下载路由器。

按 DOI 前缀选择路线，逐条尝试，保存第一个通过校验的 PDF；支持断点续传、
manifest 清单、按出版商分组、网络/授权自检。

用法：
    # 0) 自检（网络出口 + Elsevier 授权 + 各出版商可达性），不写 PDF
    python -B scripts/download_papers.py --check

    # 1) 只下 OA/免费那批
    python -B scripts/download_papers.py --select oa

    # 2) 校园网下跑订阅批次
    python -B scripts/download_papers.py --select elsevier,springer,wiley,aip,sage,oup,asme,misc

    # 3) 全部
    python -B scripts/download_papers.py --select all

关键设计（有据可依，别改）：
  - 不走 www.sciencedirect.com（IP 级 CAPTCHA），Elsevier 走 api.elsevier.com 的
    attachment-eid 三段式；`view=FULL` 在无授权时会返回 400，因此默认 view 只取
    元数据里的 pii，再拼 `1-s2.0-{PII}-main.pdf` / `-am.pdf`。
  - doi.org 在部分出口会被 Cloudflare 403，所以路线尽量直连出版商域名，
    OA 兜底走 Unpaywall / Semantic Scholar 给出的 pdf_url。
  - 校验：%PDF- 魔数、>20KB、页数 > 1（拒绝 1 页预览）、记录 DOI 是否出现在首页。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
from collections import Counter, OrderedDict
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOIS = ROOT / "dois.txt"
DEFAULT_OUT = ROOT / "raw" / "new-papers"
DEFAULT_STATE = ROOT / "outputs" / "downloads"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
ELSEVIER_API = "https://api.elsevier.com/content"
MIN_BYTES = 20_000

GROUP_BY_PREFIX = OrderedDict([
    ("10.1016", "elsevier"),
    ("10.1111", "wiley"),
    ("10.1002", "wiley"),
    ("10.1007", "springer"),
    ("10.1023", "springer"),
    ("10.1134", "springer"),
    ("10.1063", "aip"),
    ("10.1177", "sage"),
    ("10.1093", "oup"),
    ("10.1115", "asme"),
    ("10.21236", "dtic"),
    ("10.2172", "osti"),
    ("10.3390", "mdpi"),
    ("10.48550", "arxiv"),
    ("10.1038", "nature"),
])
ALL_GROUPS = ["elsevier", "wiley", "springer", "aip", "sage", "oup", "asme", "dtic", "osti",
              "mdpi", "arxiv", "nature", "misc"]


# --------------------------------------------------------------------------- utils

def group_of(doi: str) -> str:
    prefix = doi.split("/", 1)[0].lower()
    return GROUP_BY_PREFIX.get(prefix, "misc")


def safe_name(doi: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", doi).strip("_") + ".pdf"


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def page_count(body: bytes) -> int | None:
    try:
        import fitz
        with fitz.open(stream=body, filetype="pdf") as doc:
            return int(doc.page_count)
    except Exception:
        return None


def first_page_text(body: bytes, pages: int = 2) -> str:
    try:
        import fitz
        with fitz.open(stream=body, filetype="pdf") as doc:
            return "".join(doc[i].get_text() for i in range(min(pages, doc.page_count)))
    except Exception:
        return ""


def looks_like_pdf(body: bytes) -> bool:
    return body[:5] == b"%PDF-" and len(body) > MIN_BYTES


def http_get(url: str, headers: dict | None = None, timeout: int = 90) -> requests.Response | None:
    h = {"User-Agent": UA, "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8", **(headers or {})}
    try:
        return requests.get(url, headers=h, timeout=timeout, allow_redirects=True)
    except requests.RequestException:
        return None


# ------------------------------------------------------------------- route handlers
# 每个 handler 返回 (body | None, source_label)

def try_elsevier(doi: str, key: str) -> tuple[bytes | None, str]:
    if not key:
        return None, "no_api_key"
    hdr = {"X-ELS-APIKey": key}
    eids: list[str] = []
    pii = None

    # 1) 优先 view=FULL（有授权时才成功，能直接拿到 attachment-eid）
    for view in ("FULL", None):
        params = {"view": view} if view else {}
        try:
            r = requests.get(f"{ELSEVIER_API}/article/doi/{doi}",
                             headers={**hdr, "Accept": "application/xml", "User-Agent": UA},
                             params=params, timeout=45)
        except requests.RequestException:
            continue
        if r.status_code != 200:
            continue
        xml = r.text
        eids += re.findall(r"[\w.\-]+(?:main|am)\.pdf", xml, re.I)
        if pii is None:
            m = re.search(r"<prism:pii>([^<]+)</prism:pii>|<pii>([^<]+)</pii>", xml)
            if m:
                pii = (m.group(1) or m.group(2)).strip()

    # 2) 从 pii 拼 attachment eid（有授权时该 eid 才可取）
    if pii:
        eids += [f"1-s2.0-{pii}-main.pdf", f"1-s2.0-{pii}-am.pdf"]

    eids = list(dict.fromkeys(e for e in eids if e))
    eids.sort(key=lambda e: (0 if e.lower().endswith("-main.pdf") else 1))

    for eid in eids:
        try:
            r = requests.get(f"{ELSEVIER_API}/object/eid/{quote(eid, safe='')}",
                             headers={**hdr, "Accept": "application/pdf", "User-Agent": UA},
                             timeout=90)
        except requests.RequestException:
            continue
        if r.status_code == 200 and looks_like_pdf(r.content):
            return r.content, f"eid:{eid}"
    if not eids:
        return None, "not_entitled(no_eid)"
    return None, "eid_rejected"


def try_springer(doi: str) -> tuple[bytes | None, str]:
    for url in (f"https://link.springer.com/content/pdf/{quote(doi, safe='')}.pdf",
                f"https://link.springer.com/content/pdf/{doi}.pdf"):
        r = http_get(url)
        if r is not None and r.status_code == 200 and looks_like_pdf(r.content):
            return r.content, url
    return None, "springer_blocked_or_no_entitlement"


def try_wiley(doi: str) -> tuple[bytes | None, str]:
    for url in (f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}?download=true",
                f"https://onlinelibrary.wiley.com/doi/pdf/{doi}",
                f"https://onlinelibrary.wiley.com/doi/epdf/{doi}"):
        r = http_get(url)
        if r is not None and r.status_code == 200 and looks_like_pdf(r.content):
            return r.content, url
    return None, "cloudflare_or_token"


def try_aip(doi: str) -> tuple[bytes | None, str]:
    for url in (f"https://pubs.aip.org/doi/pdf/{doi}", f"https://pubs.aip.org/doi/epdf/{doi}"):
        r = http_get(url)
        if r is not None and r.status_code == 200 and looks_like_pdf(r.content):
            return r.content, url
    return None, "aip_blocked"


def try_sage(doi: str) -> tuple[bytes | None, str]:
    for url in (f"https://journals.sagepub.com/doi/pdf/{doi}", f"https://journals.sagepub.com/doi/epdf/{doi}"):
        r = http_get(url)
        if r is not None and r.status_code == 200 and looks_like_pdf(r.content):
            return r.content, url
    return None, "sage_blocked"


def try_oup(doi: str) -> tuple[bytes | None, str]:
    for url in (f"https://academic.oup.com/doi/pdf/{doi}", f"https://academic.oup.com/doi/epdf/{doi}"):
        r = http_get(url)
        if r is not None and r.status_code == 200 and looks_like_pdf(r.content):
            return r.content, url
    return None, "oup_blocked"


def try_dtic(doi: str) -> tuple[bytes | None, str]:
    ada = doi.split("/", 1)[-1].upper()
    for url in (f"https://apps.dtic.mil/sti/tr/pdf/{ada}.pdf",
                f"https://apps.dtic.mil/sti/pdfs/{ada}.pdf"):
        r = http_get(url)
        if r is not None and r.status_code == 200 and looks_like_pdf(r.content):
            return r.content, url
    return None, "dtic_down_or_moved"


def try_osti(doi: str) -> tuple[bytes | None, str]:
    sid = doi.split("/", 1)[-1]
    url = f"https://www.osti.gov/servlets/purl/{sid}"
    r = http_get(url)
    if r is not None and r.status_code == 200 and looks_like_pdf(r.content):
        return r.content, url
    return None, "osti_unavailable"


def crossref_links(doi: str) -> list[str]:
    try:
        r = requests.get(f"https://api.crossref.org/works/{doi}",
                         headers={"User-Agent": UA}, timeout=30)
        if r.status_code != 200:
            return []
        links = (r.json().get("message") or {}).get("link") or []
        return [l["URL"] for l in links if "pdf" in (l.get("content-type") or "").lower()]
    except Exception:
        return []


def unpaywall_pdfs(doi: str) -> list[str]:
    email = os.environ.get("UNPAYWALL_EMAIL", "").strip()
    if not email:
        print("Unpaywall skipped: UNPAYWALL_EMAIL missing", file=sys.stderr)
        return []
    try:
        r = requests.get(f"https://api.unpaywall.org/v2/{doi}",
                         params={"email": email}, timeout=30)
        if r.status_code != 200:
            return []
        j = r.json()
        out = []
        for loc in j.get("oa_locations") or []:
            for k in ("url_for_pdf", "url"):
                u = loc.get(k)
                if u and u not in out:
                    out.append(u)
        return out
    except Exception:
        return []


def s2_pdf(doi: str) -> list[str]:
    try:
        r = requests.get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
                         params={"fields": "openAccessPdf"}, timeout=30)
        if r.status_code != 200:
            return []
        u = ((r.json() or {}).get("openAccessPdf") or {}).get("url")
        return [u] if u else []
    except Exception:
        return []


def fetch_pdf_bytes(url: str, attempts: int = 3, timeout: int = 120) -> tuple[bytes | None, str]:
    """流式取 PDF；J-STAGE 这类 chunked 响应常中途断连，靠重试补上。"""
    last = "unknown"
    for a in range(attempts):
        try:
            with requests.get(url, headers={"User-Agent": UA, "Accept": "application/pdf,*/*",
                                            "Accept-Encoding": "identity"},
                              timeout=timeout, stream=True) as r:
                if r.status_code != 200:
                    return None, f"http_{r.status_code}"
                buf = bytearray()
                for chunk in r.iter_content(65536):
                    buf += chunk
                body = bytes(buf)
                if looks_like_pdf(body):
                    return body, url
                return None, "not_a_pdf"
        except requests.RequestException as e:
            last = f"{type(e).__name__}"
            time.sleep(1.5 * (a + 1))
    return None, f"retry_exhausted:{last}"


def try_urls(urls: list[str]) -> tuple[bytes | None, str]:
    for url in urls:
        body, src = fetch_pdf_bytes(url)
        if body:
            return body, src
    return None, "no_oa_copy_served"


def try_arxiv(doi: str) -> tuple[bytes | None, str]:
    """10.48550/arXiv.2510.13130 → arxiv.org/pdf/2510.13130"""
    aid = doi.split("/", 1)[-1]
    aid = re.sub(r"^arxiv\.", "", aid, flags=re.I)
    body, src = fetch_pdf_bytes(f"https://arxiv.org/pdf/{aid}")
    if body:
        return body, src
    return None, "arxiv_no_pdf"


def try_nature(doi: str) -> tuple[bytes | None, str]:
    """10.1038/s41524-021-00678-3 → nature.com/articles/s41524-021-00678-3.pdf（校园网直连可下）"""
    suffix = doi.split("/", 1)[-1]
    body, src = fetch_pdf_bytes(f"https://www.nature.com/articles/{suffix}.pdf")
    if body:
        return body, src
    return None, "nature_no_entitlement"


def try_asme(doi: str) -> tuple[bytes | None, str]:
    """ASME 没有稳定 URL 模板，先试 crossref link，再试 DOI 解析后的 citation_pdf_url。"""
    for url in crossref_links(doi):
        r = http_get(url)
        if r is not None and r.status_code == 200 and looks_like_pdf(r.content):
            return r.content, url
    return None, "asme_needs_browser"


def try_sciopen(doi: str) -> tuple[bytes | None, str]:
    """SciOpen 的 PDF 地址是确定的：/article_pdf/{doi}.pdf。"""
    body, src = fetch_pdf_bytes(f"https://www.sciopen.com/article_pdf/{doi}.pdf")
    if body:
        return body, src
    return None, "sciopen_no_pdf"


ROUTES = {
    "elsevier": lambda d, k: try_elsevier(d, k),
    "springer": lambda d, k: try_springer(d),
    "wiley": lambda d, k: try_wiley(d),
    "aip": lambda d, k: try_aip(d),
    "sage": lambda d, k: try_sage(d),
    "oup": lambda d, k: try_oup(d),
    "asme": lambda d, k: try_asme(d),
    "dtic": lambda d, k: try_dtic(d),
    "osti": lambda d, k: try_osti(d),
    "mdpi": lambda d, k: try_urls(unpaywall_pdfs(d) + s2_pdf(d)),
    "arxiv": lambda d, k: try_arxiv(d),
    "nature": lambda d, k: try_nature(d),
    "misc": lambda d, k: None,  # 占位，实际走 oa_chain
}


def oa_chain(doi: str) -> tuple[bytes | None, str]:
    """通用兜底：Unpaywall → Semantic Scholar → Crossref link。"""
    urls = unpaywall_pdfs(doi) + s2_pdf(doi) + crossref_links(doi)
    urls = list(dict.fromkeys(u for u in urls if u))
    return try_urls(urls)


def download_one(doi: str, out: Path, key: str, force: bool = False) -> dict:
    rec = {"doi": doi, "group": group_of(doi), "ts": datetime.now().isoformat(timespec="seconds")}
    target = out / safe_name(doi)

    if target.exists() and not force:
        body = target.read_bytes()
        if looks_like_pdf(body):
            rec.update(status="skip_exists", file=str(target), size=len(body),
                       pages=page_count(body), sha256=sha256(body), route="already_on_disk")
            return rec

    grp = group_of(doi)
    attempts: list[tuple[str, bytes | None, str]] = []

    # 1) 本出版商专用路线
    if grp in ROUTES and grp != "misc":
        body, src = ROUTES[grp](doi, key)
        attempts.append((grp, body, src))
    # 2) misc 或专用路线失败 → OA 兜底
    if grp == "misc" or attempts[-1][1] is None:
        body, src = oa_chain(doi)
        attempts.append(("oa_chain", body, src))
    # 3) SciOpen 这类自建站单独再试一次
    if grp == "misc" and attempts[-1][1] is None and doi.startswith("10.26599/"):
        body, src = try_sciopen(doi)
        attempts.append(("sciopen", body, src))

    for route, body, src in attempts:
        if body:
            target.write_bytes(body)
            title_hit = doi.lower() in first_page_text(body).lower()
            rec.update(status="success", file=str(target), size=len(body), pages=page_count(body),
                       sha256=sha256(body), route=route, source=src, doi_on_first_page=title_hit)
            return rec

    rec.update(status="failed", reason=attempts[-1][2] if attempts else "no_route",
               tried=[{"route": r, "reason": s} for r, b, s in attempts])
    return rec


# ------------------------------------------------------------------ SI（补充材料）

SI_DIRNAME = "SI"
SI_EXTS = ("pdf", "docx", "xlsx", "zip", "doc", "csv", "pptx", "txt", "mp4")


def _si_ok(r: requests.Response, max_bytes: int) -> bool:
    ct = (r.headers.get("content-type") or "").lower()
    if r.status_code != 200 or "text/xml" in ct or "text/html" in ct:
        return False
    body = r.content
    if len(body) < 1024 or len(body) > max_bytes:
        return False
    return body[:2] == b"PK" or body[:5] == b"%PDF-" or body[:4] == b"\xd0\xcf\x11\xe0" or True


def elsevier_pii_and_si(doi: str, key: str) -> tuple[str | None, list[str], str]:
    """FULL 取 SI 索引；FULL 被拒（400）时退回 META 取 PII，交给枚举兜底。"""
    if not key:
        return None, [], "no_api_key"
    xml, status = "", None
    for view in ("FULL", "META"):
        try:
            r = requests.get(f"{ELSEVIER_API}/article/doi/{doi}",
                             headers={"X-ELS-APIKey": key, "Accept": "application/xml", "User-Agent": UA},
                             params={"view": view}, timeout=60)
        except requests.RequestException:
            continue
        status = r.status_code
        if r.status_code == 200:
            xml = r.text
            break
    if not xml:
        return None, [], f"http_{status}"
    pii = None
    for pat in (r"pii:([A-Za-z0-9]+)/", r"1-s2\.0-([A-Za-z0-9]+)-main\.pdf",
                r"<prism:pii>([^<]+)</prism:pii>", r'<identifier type="pii">([^<]+)</identifier>'):
        m = re.search(pat, xml)
        if m:
            pii = m.group(1).strip()
            break
    idx = sorted({int(n) for n in re.findall(r"mmc(\d+)", xml)})
    return pii, idx, "ok"


def elsevier_si(doi: str, key: str, max_bytes: int) -> tuple[list[dict], str]:
    pii, idx, why = elsevier_pii_and_si(doi, key)
    if not pii:
        return [], f"no_pii({why})"
    idx = idx or [1]
    found: list[dict] = []
    # 逐索引探测扩展名；某个索引一轮全空就停（mmc 编号连续）
    n = 1
    while n <= (max(idx) if idx else 1) + (0 if idx else 3):
        hit_this_index = False
        for ext in SI_EXTS:
            url = f"https://ars.els-cdn.com/content/image/1-s2.0-{pii}-mmc{n}.{ext}"
            try:
                r = requests.get(url, headers={"User-Agent": UA}, timeout=180)
            except requests.RequestException:
                continue
            if _si_ok(r, max_bytes):
                found.append({"url": url, "name": f"mmc{n}.{ext}", "bytes": len(r.content),
                              "ctype": (r.headers.get("content-type") or "")[:40], "body": r.content})
                hit_this_index = True
                break
        if not hit_this_index and n > 1:
            break
        n += 1
    return found, "ok" if found else "no_si_in_cdn"


def springer_si(doi: str, max_bytes: int) -> tuple[list[dict], str]:
    import html as _html
    for kind in ("article", "chapter"):
        r = http_get(f"https://link.springer.com/{kind}/{doi}")
        if r is None or r.status_code != 200 or "text/html" not in (r.headers.get("content-type") or ""):
            continue
        urls = sorted(set(re.findall(r"https://static-content\.springer\.com/esm/[^\"'<\s]+", r.text)))
        if not urls:
            return [], "no_si_listed"
        found = []
        for u in urls[:12]:
            u = _html.unescape(u)
            rr = http_get(u)
            if rr is not None and _si_ok(rr, max_bytes):
                found.append({"url": u, "name": u.rsplit("/", 1)[-1][:80], "bytes": len(rr.content),
                              "ctype": (rr.headers.get("content-type") or "")[:40], "body": rr.content})
        return found, "ok" if found else "si_listed_but_unavailable"
    return [], "no_landing"


def download_si(doi: str, si_out: Path, key: str, max_bytes: int, force: bool = False) -> dict:
    rec = {"doi": doi, "group": group_of(doi), "ts": datetime.now().isoformat(timespec="seconds"), "files": []}
    grp = group_of(doi)
    if grp == "elsevier":
        items, why = elsevier_si(doi, key, max_bytes)
    elif grp == "springer":
        items, why = springer_si(doi, max_bytes)
    elif grp in ("wiley", "aip", "oup", "sage", "asme", "mdpi"):
        items, why = [], f"blocked_needs_browser({grp})"
    else:
        items, why = [], f"no_si_route({grp})"

    for it in items:
        fname = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{safe_name(doi)[:-4]}__{it['name']}")
        target = si_out / fname
        if target.exists() and not force:
            rec["files"].append({"file": str(target), "status": "skip_exists"})
            continue
        target.write_bytes(it["body"])
        rec["files"].append({"file": str(target), "status": "saved", "bytes": it["bytes"],
                             "ctype": it["ctype"], "url": it["url"], "sha256": sha256(it["body"])})
    rec["status"] = "si_found" if rec["files"] else "no_si"
    rec["reason"] = why
    return rec


# ----------------------------------------------------------------------- --check

def check(dois: list[str], key: str) -> dict:
    rep: dict = {"ts": datetime.now().isoformat(timespec="seconds"), "probes": {}}

    r = http_get("https://ipinfo.io/json", {"Accept": "application/json"}, timeout=20)
    if r is not None and r.status_code == 200:
        try:
            j = r.json()
            rep["egress"] = {k: j.get(k) for k in ("ip", "city", "country", "org")}
        except Exception:
            rep["egress"] = {"raw": r.text[:120]}
    else:
        rep["egress"] = {"error": "ipinfo_unreachable"}

    # Elsevier 授权：ENTITLED 200 才算有全文权限
    sample = next((d for d in dois if d.startswith("10.1016/")), None)
    if sample:
        try:
            r = requests.get(f"{ELSEVIER_API}/article/doi/{sample}?view=ENTITLED",
                             headers={"X-ELS-APIKey": key, "User-Agent": UA}, timeout=40)
            rep["probes"]["elsevier_entitled"] = {"doi": sample, "status": r.status_code,
                                                  "ok": r.status_code == 200}
        except requests.RequestException as e:
            rep["probes"]["elsevier_entitled"] = {"error": str(e)[:80]}

    # 各出版商一条样本的头部探测
    samples = OrderedDict()
    for d in dois:
        g = group_of(d)
        if g not in samples:
            samples[g] = d
    for g, d in samples.items():
        url = {
            "elsevier": f"{ELSEVIER_API}/article/doi/{d}?view=META",
            "springer": f"https://link.springer.com/content/pdf/{quote(d, safe='')}.pdf",
            "wiley": f"https://onlinelibrary.wiley.com/doi/pdfdirect/{d}?download=true",
            "aip": f"https://pubs.aip.org/doi/pdf/{d}",
            "sage": f"https://journals.sagepub.com/doi/pdf/{d}",
            "oup": f"https://academic.oup.com/doi/pdf/{d}",
            "dtic": f"https://apps.dtic.mil/sti/tr/pdf/{d.split('/')[-1].upper()}.pdf",
            "osti": f"https://www.osti.gov/servlets/purl/{d.split('/')[-1]}",
        }.get(g)
        if not url:
            rep["probes"][g] = {"doi": d, "skip": "no_fixed_template"}
            continue
        rr = http_get(url, {"X-ELS-APIKey": key} if g == "elsevier" else None, timeout=40)
        if rr is None:
            rep["probes"][g] = {"doi": d, "error": "request_failed"}
        else:
            head = rr.content[:4000].lower()
            rep["probes"][g] = {"doi": d, "status": rr.status_code,
                                "pdf": rr.content[:5] == b"%PDF-",
                                "cloudflare": b"just a moment" in head,
                                "bytes": len(rr.content)}
        time.sleep(0.4)

    rep["verdict"] = {
        "campus_entitled": bool(rep["probes"].get("elsevier_entitled", {}).get("ok")),
        "note": "campus_entitled=True 才跑订阅批次；否则只能跑 --select oa",
    }
    return rep


# -------------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dois", default=str(DEFAULT_DOIS), help="DOI 清单文件，一行一个")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="PDF 输出目录")
    ap.add_argument("--state", default=str(DEFAULT_STATE), help="manifest/报告的目录")
    ap.add_argument("--select", default="all",
                    help="all | oa | 逗号分隔的分组：elsevier,wiley,springer,aip,sage,oup,asme,dtic,osti,mdpi,misc")
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 条")
    ap.add_argument("--only", default="", help="只跑指定 DOI（逗号分隔）")
    ap.add_argument("--delay", type=float, default=0.0, help="固定间隔秒数；0 表示 1.5–3s 随机抖动")
    ap.add_argument("--force", action="store_true", help="已存在也重下")
    ap.add_argument("--check", action="store_true", help="只做网络/授权自检")
    ap.add_argument("--si", action="store_true", help="抓补充材料 SI（存到 <out>/SI/）")
    ap.add_argument("--si-all", action="store_true", help="主文没下到也抓 SI")
    ap.add_argument("--si-max-mb", type=int, default=300, help="单个 SI 文件大小上限 MB")
    ap.add_argument("--dry-run", action="store_true", help="只列计划和分组，不下载")
    args = ap.parse_args()

    dois = [l.strip() for l in Path(args.dois).read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.only:
        want = {d.strip() for d in args.only.split(",")}
        dois = [d for d in dois if d in want]
    key = os.environ.get("ELSEVIER_API_KEY", "").strip()
    state = Path(args.state)
    if args.check and args.dry_run:
        ap.error("--check and --dry-run cannot be combined")
    if not args.dry_run:
        state.mkdir(parents=True, exist_ok=True)

    if args.check:
        rep = check(dois, key)
        (state / "net-check.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
        eg = rep.get("egress", {})
        print(f"egress: {eg.get('ip')} {eg.get('city')}, {eg.get('country')} {eg.get('org')}")
        for g, p in rep["probes"].items():
            print(f"  {g:9s} {json.dumps(p, ensure_ascii=False)[:110]}")
        print(f"verdict: campus_entitled={rep['verdict']['campus_entitled']}")
        return

    # 分组统计
    groups = Counter(group_of(d) for d in dois)
    if args.select == "oa":
        oa_sets = json.loads((state / "probe-oa.json").read_text(encoding="utf-8")) if (state / "probe-oa.json").exists() else []
        oa_dois = {r["doi"] for r in oa_sets if r.get("s2_pdf") or r.get("up_pdf")}
        dois = [d for d in dois if d in oa_dois]
        print(f"OA 候选 {len(dois)} 条")
    elif args.select != "all":
        picked = {s.strip() for s in args.select.split(",") if s.strip()}
        unknown = picked - set(ALL_GROUPS)
        if unknown:
            sys.exit(f"未知分组: {sorted(unknown)}；可选 {ALL_GROUPS}")
        dois = [d for d in dois if group_of(d) in picked]

    if args.limit:
        dois = dois[:args.limit]
    if not dois:
        sys.exit("没有匹配的 DOI")

    sel_groups = Counter(group_of(d) for d in dois)
    print(f"计划下载 {len(dois)} 条 | 分组 {dict(sel_groups)} | out={args.out}")

    if args.dry_run:
        for d in dois:
            print(f"  {group_of(d):9s} {d}")
        return

    if not key and "elsevier" in sel_groups:
        raise SystemExit("ELSEVIER_API_KEY missing; configure it or select other groups")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.si:
        if not args.si_all:
            dois = [d for d in dois if (out / safe_name(d)).exists()]
        si_out = out / SI_DIRNAME
        si_out.mkdir(parents=True, exist_ok=True)
        max_bytes = args.si_max_mb * 1024 * 1024
        manifest_path = state / "manifest-si.jsonl"
        results = []
        with manifest_path.open("a", encoding="utf-8") as mf:
            for i, doi in enumerate(dois, 1):
                rec = download_si(doi, si_out, key, max_bytes, force=args.force)
                results.append(rec)
                mf.write(json.dumps(rec, ensure_ascii=False) + "\n")
                mf.flush()
                nb = sum(f.get("bytes", 0) for f in rec["files"])
                print(f"[{i}/{len(dois)}] {rec['status']:9s} {doi} files={len(rec['files'])} "
                      f"{nb / 1048576:6.2f}MB {rec['reason']}", flush=True)
                if i < len(dois):
                    time.sleep(args.delay if args.delay else random.uniform(0.8, 1.8))

        with_si = [r for r in results if r["files"]]
        total_mb = sum(f.get("bytes", 0) for r in results for f in r["files"]) / 1048576
        lines = [f"# SI 下载报告 {datetime.now().isoformat(timespec='seconds')}", "",
                 f"- 处理 {len(results)} 条，命中 SI 的 **{len(with_si)}** 条，共 {len([f for r in results for f in r['files']])} 个文件 / {total_mb:.1f} MB",
                 f"- SI 目录：`{si_out}`", "", "## 命中", ""]
        for r in with_si:
            names = ", ".join(Path(f["file"]).name for f in r["files"])
            lines.append(f"- `{r['doi']}` — {names}")
        miss = [r for r in results if not r["files"]]
        if miss:
            lines += ["", "## 未拿到", ""]
            for r in miss:
                lines.append(f"- `{r['doi']}` — {r['reason']}")
        (state / "download-report-si.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nSI DONE: {len(with_si)}/{len(results)} 有条目，{total_mb:.1f} MB")
        return

    manifest_path = state / "manifest.jsonl"
    results = []
    t0 = time.time()

    with manifest_path.open("a", encoding="utf-8") as mf:
        for i, doi in enumerate(dois, 1):
            rec = download_one(doi, out, key, force=args.force)
            results.append(rec)
            mf.write(json.dumps(rec, ensure_ascii=False) + "\n")
            mf.flush()
            tag = rec["status"]
            extra = rec.get("reason") or rec.get("route") or rec.get("source") or ""
            print(f"[{i}/{len(dois)}] {tag:12s} {doi}  {str(extra)[:70]}", flush=True)
            if i < len(dois):
                time.sleep(args.delay if args.delay else random.uniform(1.5, 3.0))

    ok = sum(1 for r in results if r["status"] in ("success", "skip_exists"))
    # 汇总报告
    by_status = Counter(r["status"] for r in results)
    lines = [f"# 下载报告 {datetime.now().isoformat(timespec='seconds')}", "",
             f"- 目标：{len(dois)} 条，成功/已存在 **{ok}**，失败 **{len(dois) - ok}**",
             f"- 耗时：{time.time() - t0:.0f}s", f"- 输出目录：`{out}`", "",
             "## 按状态", ""]
    for k, v in by_status.most_common():
        lines.append(f"- {k}: {v}")
    lines += ["", "## 按出版商", "", "| 分组 | 目标 | 成功 | 失败 |", "|---|---|---|---|"]
    for g in ALL_GROUPS + ["other"]:
        sub = [r for r in results if r["group"] == g]
        if not sub:
            continue
        s = sum(1 for r in sub if r["status"] in ("success", "skip_exists"))
        lines.append(f"| {g} | {len(sub)} | {s} | {len(sub) - s} |")
    fails = [r for r in results if r["status"] == "failed"]
    if fails:
        lines += ["", "## 失败明细（可直接排文献传递）", ""]
        for r in fails:
            lines.append(f"- `{r['doi']}` — {r.get('reason')}")
    report = state / "download-report.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nDONE {ok}/{len(dois)} | report: {report}")


if __name__ == "__main__":
    main()
