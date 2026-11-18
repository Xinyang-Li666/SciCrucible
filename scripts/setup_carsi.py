# -*- coding: utf-8 -*-
"""一次性机构登录（CARSI / 校园 SSO），登录态存进 .browser-profile，后续浏览器批次直接复用。

流程：
  阶段 A  打开 CARSI 门户 + 两家出版商样本页，你在窗口里点
          "Access through your institution" → 选 用户所属机构 → 统一身份认证 登录
  阶段 B  脚本轮询等待，直到出现哨兵文件 <state>/.carsi-done（我会在你确认登录后创建）
  阶段 C  逐家探测 7 个出版商，判定 entitled / no_access / blocked，写 login-status.json

用法：
    python -B scripts/setup_carsi.py                     # 阶段 A+B（窗口一直开着）
    python -B scripts/setup_carsi.py --probe-only        # 只做阶段 C（用已有登录态复测）

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
PROFILE = ROOT / ".browser-profile"
STATE = ROOT / "outputs" / "downloads"
DOIS_FILE = ROOT / "dois.txt"
SENTINEL = STATE / ".carsi-done"

CARSI_ENTRY = "https://www.carsi.edu.cn/"
PUBLISHERS = {
    "acs": "https://pubs.acs.org/doi/{doi}",
    "tandf": "https://www.tandfonline.com/doi/full/{doi}",
    "ieee": "https://doi.org/{doi}",
    "aps": "https://link.aps.org/doi/{doi}",
    "rsc": "https://doi.org/{doi}",
    "science": "https://www.science.org/doi/{doi}",
    "iop": "https://iopscience.iop.org/article/{doi}",
}
PREFIX2GROUP = {"10.1021": "acs", "10.1080": "tandf", "10.1109": "ieee", "10.1103": "aps",
                "10.1039": "rsc", "10.1126": "science", "10.1088": "iop"}

NO_ACCESS_MARKERS = ("access through your institution", "get access", "sign in to access",
                     "buy article", "purchase access", "subscribe to view", "log in to view")


def sample_dois() -> dict[str, str]:
    """从其他清单里给每家挑一个真实 DOI 作探针。"""
    picked: dict[str, str] = {}
    base = DOIS_FILE.parent
    for f in [DOIS_FILE]:
        for line in f.read_text(encoding="utf-8").splitlines():
            d = line.strip()
            if not d.startswith("10."):
                continue
            grp = PREFIX2GROUP.get(d.split("/")[0].lower())
            if grp and grp not in picked:
                picked[grp] = d
    return picked


def classify(page) -> tuple[str, str]:
    try:
        title = (page.title() or "").lower()
    except Exception:
        title = ""
    if "just a moment" in title or "一个片刻" in title:
        return "blocked", "cloudflare"
    try:
        html = page.content()
    except Exception:
        return "unknown", "no_html"
    low = html.lower()
    if any(m in low for m in NO_ACCESS_MARKERS):
        return "no_access", "付费墙标记"
    has_pdf = bool(re.search(r'citation_pdf_url', html, re.I))
    return ("entitled", "有PDF链接且无付费墙标记") if has_pdf else ("unknown", "无判据")


def main() -> None:
    global DOIS_FILE, STATE, PROFILE, SENTINEL
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--probe-only", action="store_true", help="只跑阶段 C")
    ap.add_argument("--wait-minutes", type=int, default=40)
    ap.add_argument("--dois", default=str(DOIS_FILE))
    ap.add_argument("--state", default=str(STATE))
    ap.add_argument("--profile", default=str(PROFILE))
    args = ap.parse_args()
    DOIS_FILE, STATE, PROFILE = Path(args.dois), Path(args.state), Path(args.profile)
    SENTINEL = STATE / ".carsi-done"

    STATE.mkdir(parents=True, exist_ok=True)
    samples = sample_dois()
    if not samples:
        raise SystemExit("没从清单里找到 7 家出版商的样本 DOI")

    PROFILE.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), channel="msedge", headless=False,
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
            viewport={"width": 1440, "height": 950}, locale="zh-CN", accept_downloads=True,
        )

        if not args.probe_only:
            SENTINEL.unlink(missing_ok=True)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            for url in (CARSI_ENTRY, PUBLISHERS["acs"].format(doi=samples["acs"])):
                try:
                    pg = page if url == CARSI_ENTRY else ctx.new_page()
                    pg.goto(url, wait_until="domcontentloaded", timeout=90000)
                except Exception as e:
                    print(f"[TAB] {url[:60]} 打开失败：{type(e).__name__}", flush=True)

            print("\n请在打开的 Edge 窗口里登录（只需一次）：", flush=True)
            print("  1) 在 ACS 页面点 “Access through your institution”", flush=True)
            print("  2) 搜 / 选 用户所属机构（Beijing University of Science and Technology）", flush=True)
            print("  3) 跳到学校统一身份认证后完成登录，回到 ACS 能看到 PDF 即可", flush=True)
            print("  4) 对 Taylor & Francis / IEEE 重复一次同样的动作（各站 Cookie 独立）", flush=True)
            print(f"\n登录完告诉我，我会创建哨兵 {SENTINEL.name} 让它继续；", flush=True)
            print(f"最长等 {args.wait_minutes} 分钟。\n", flush=True)

            deadline = time.time() + args.wait_minutes * 60
            while time.time() < deadline:
                time.sleep(5)
                if SENTINEL.exists():
                    print("收到哨兵，开始探测登录态……\n", flush=True)
                    break
            else:
                print("等待超时，直接进入探测阶段（可能未登录完全）。\n", flush=True)

            try:
                ctx.storage_state(path=str(STATE / "carsi-storage.json"))
                print(f"登录态已保存：{STATE / 'carsi-storage.json'}\n", flush=True)
            except Exception as e:
                print(f"保存登录态失败：{type(e).__name__}\n", flush=True)

        # 阶段 C：逐家探测
        results = {}
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for grp, doi in samples.items():
            url = PUBLISHERS[grp].format(doi=doi)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=90000)
                time.sleep(2)
                verdict, why = classify(page)
            except Exception as e:
                verdict, why = "error", type(e).__name__
            results[grp] = {"doi": doi, "url": url, "verdict": verdict, "why": why}
            print(f"  {grp:8s} {verdict:10s} {doi}  ({why})", flush=True)

        (STATE / "login-status.json").write_text(
            json.dumps({"ts": datetime.now().isoformat(timespec="seconds"), "publishers": results},
                       indent=1, ensure_ascii=False), encoding="utf-8")
        ent = [g for g, r in results.items() if r["verdict"] == "entitled"]
        print(f"\n判定 entitled：{len(ent)}/{len(results)} -> {ent}")
        print(f"明细：{STATE / 'login-status.json'}")
        ctx.close()


if __name__ == "__main__":
    main()
