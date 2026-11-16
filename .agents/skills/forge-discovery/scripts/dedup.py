#!/usr/bin/env python3
"""dedup.py — 文献去重工具

两级去重架构:
  1. --index 模式 (推荐): 读取 literature_index.json，O(1) 哈希查找
  2. --wiki-dir 模式 (fallback): 实时正则解析 wiki/**/literature/*.md（递归，兼容按课题分层）

用法:
  python dedup.py <new_results.json> --index <index.json>          # 主路径
  python dedup.py <new_results.json> --wiki-dir <dir>              # 兜底路径
  python dedup.py <new_results.json> --index <index.json> --wiki-dir <dir>  # 完整配置

输出: 去重后的 JSON 到 stdout，去重报告到 stderr

注意: 文献页无 YAML frontmatter——DOI 是 **DOI:** value，标题是 # Title。
"""

import json
import re
import sys
import os
import argparse
from pathlib import Path
from difflib import SequenceMatcher


# ── 路径自动检测 ──────────────────────────────────────

def _has_lit(root) -> bool:
    """判断 root 下是否存在任意 literature 目录（兼容按课题分层结构）。

    分层后文献不再位于 wiki/literature/，而是散落于
    wiki/<课题>/literature/。用 glob('wiki/**/literature') 递归探测。
    """
    return bool(list(Path(root).glob('wiki/**/literature')))


def detect_forge_root() -> str:
    """自动检测 SciCrucible/ 根目录。

    优先级:
      1. 环境变量 FORGE_ROOT
      2. 从脚本位置向上查找含 wiki/**/literature/ 的目录
      3. 当前工作目录
    """
    # 1. 环境变量
    env_root = os.environ.get('FORGE_ROOT')
    if env_root and _has_lit(env_root):
        return env_root

    # 2. 从脚本位置推断
    script_dir = Path(__file__).resolve().parent
    for ancestor in [script_dir] + list(script_dir.parents):
        if _has_lit(ancestor):
            return str(ancestor)

    # 3. 当前工作目录
    if _has_lit(Path.cwd()):
        return str(Path.cwd())

    return '.'


KB_ROOT = detect_forge_root()
DEFAULT_WIKI_DIR = os.path.join(KB_ROOT, 'wiki')
DEFAULT_INDEX = os.path.join(KB_ROOT, 'wiki', 'literature_index.json')


# ── 工具函数 ───────────────────────────────────────────

def normalize_doi(doi: str) -> str:
    """DOI 归一化：小写、去空格、去 URL 前缀"""
    if not doi:
        return ""
    doi = doi.strip().lower()
    doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
    return doi


def normalize_title(title: str) -> str:
    """标题归一化：小写、去标点、去多余空格"""
    if not title:
        return ""
    title = title.lower().strip()
    title = re.sub(r'[^\w\s]', '', title)
    title = re.sub(r'\s+', ' ', title)
    return title


# ── 索引缓存模式（主路径）─────────────────────────────

def load_index(index_path: str) -> dict | None:
    """加载文献索引缓存"""
    if not os.path.exists(index_path):
        return None
    with open(index_path, encoding='utf-8') as f:
        return json.load(f)


def extract_from_index(index: dict) -> tuple[set, set]:
    """从索引缓存提取 DOI 集合和标题集合（O(1)）

    DOI 归一化后入集：索引键可能保留原始大小写（如 10.26599/JAC...），
    而 is_duplicate 对来料 DOI 归一化为小写比对——此处同样归一化，
    避免大写 DOI 去重漏网（DOI 本身大小写不敏感）。
    """
    dois = set()
    titles = set()
    for doi, info in index.get('papers', {}).items():
        dois.add(normalize_doi(doi))
        if info.get('title_normalized'):
            titles.add(info['title_normalized'])
    return dois, titles


# ── 实时正则解析模式（兜底路径）─────────────────────────

def _iter_literature_files(wiki_dir: str):
    """列出待扫描的文献 .md 文件（兼容分层与旧扁平结构）。

    - 传入 wiki/（分层结构根）→ 递归 wiki/**/literature/*.md
    - 传入具体的 wiki/<课题>/literature 或旧 wiki/literature → 直接 *.md
    """
    lit_dir = Path(wiki_dir)
    if not lit_dir.exists():
        return []
    files = list(lit_dir.glob("**/literature/*.md"))
    if not files and lit_dir.name == "literature":
        files = list(lit_dir.glob("*.md"))
    return files


def extract_existing_dois(wiki_dir: str) -> set:
    """从 wiki/**/literature/ 递归提取所有已有 DOI（兜底路径）

    文献页格式: **DOI:** 10.1016/j.actamat.2025.119123
    注意: 没有 YAML frontmatter。
    """
    dois = set()
    for md_file in _iter_literature_files(wiki_dir):
        content = md_file.read_text(encoding='utf-8')
        # 匹配内联字段: **DOI:** <value>
        doi_match = re.search(r'\*\*DOI:\*\*\s*([^\s\n]+)', content)
        if doi_match:
            dois.add(normalize_doi(doi_match.group(1)))
    return dois


def extract_existing_titles(wiki_dir: str) -> set:
    """从 wiki/**/literature/ 递归提取所有已有标题（兜底路径）

    文献页格式: # Title of the Paper
    注意: 没有 YAML frontmatter。
    """
    titles = set()
    for md_file in _iter_literature_files(wiki_dir):
        content = md_file.read_text(encoding='utf-8')
        # 匹配 Markdown H1: # <Title>
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            titles.add(normalize_title(title_match.group(1)))
    return titles


# ── 去重判断 ────────────────────────────────────────────

def is_duplicate(paper: dict, existing_dois: set, existing_titles: set) -> tuple[bool, str]:
    """检查单篇文献是否与已有文献重复。

    三层判断（按优先级）:
      1. DOI 完全匹配（O(1) 哈希查找）
      2. 标题归一化匹配（O(1) 哈希查找）
      3. 标题高度相似（>0.9）但年份/作者不同 → 可能相关版本
         优化：长度预过滤，跳过长度差异 >30% 的标题

    Returns:
        (is_dup, reason) — is_dup=True 表示应排除
    """
    # 1. DOI 完全匹配
    doi = normalize_doi(paper.get('doi', ''))
    if doi and doi in existing_dois:
        return True, f"DOI 已存在: {doi}"

    # 2. 标题归一化匹配
    title = normalize_title(paper.get('title', ''))
    if not title:
        return False, ""
    if title in existing_titles:
        return True, f"标题已存在: {title[:60]}..."

    # 3. 标题高度相似（>0.9）→ 可能相关版本
    #    长度预过滤：跳过长度差异 >30% 的标题
    title_len = len(title)
    for existing_title in existing_titles:
        if not existing_title:
            continue
        if abs(len(existing_title) - title_len) / max(title_len, 1) > 0.3:
            continue
        ratio = SequenceMatcher(None, title, existing_title).ratio()
        if ratio > 0.9:
            return True, f"标题高度相似 ({ratio:.0%}): {existing_title[:60]}..."

    return False, ""


# ── 主入口 ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='文献去重工具 — 支持索引缓存（快）和实时正则解析（兜底）'
    )
    parser.add_argument(
        'input',
        help='sci search 输出的 JSON 文件（或通配符，如 search-results-*.json）'
    )
    parser.add_argument(
        '--index', default=None,
        help='文献索引缓存文件路径 (推荐，O(1) 查找)'
    )
    parser.add_argument(
        '--wiki-dir', default=DEFAULT_WIKI_DIR,
        help=f'已有文献目录，索引不存在时的 fallback (默认: {DEFAULT_WIKI_DIR})'
    )
    parser.add_argument(
        '--output', '-o', default=None,
        help='输出文件路径 (默认: stdout)'
    )
    args = parser.parse_args()

    # ── 1. 加载新检索结果 ──
    input_path = args.input
    # 支持 glob 通配符：取最新匹配文件
    if '*' in input_path or '?' in input_path:
        import glob as glob_mod
        matches = sorted(glob_mod.glob(input_path))
        if not matches:
            print(f"错误: 没有文件匹配 '{input_path}'", file=sys.stderr)
            sys.exit(1)
        input_path = matches[-1]  # 取最新
        print(f"匹配到 {len(matches)} 个文件，使用最新: {input_path}", file=sys.stderr)

    with open(input_path, encoding='utf-8') as f:
        data = json.load(f)

    # 兼容多种 JSON 结构：纯数组、{"results": [...]}、{"data": [...]} 等
    if isinstance(data, list):
        papers = data
    elif isinstance(data, dict):
        papers = data.get('results') or data.get('data') or data.get('papers') or []
    else:
        papers = []

    if not papers:
        print("错误: JSON 文件中未找到论文数据（期望数组或含 results/data/papers 键的对象）", file=sys.stderr)
        sys.exit(1)

    # ── 2. 加载已有文献（索引优先 → fallback 实时解析）──
    index = load_index(args.index) if args.index else None

    if index:
        existing_dois, existing_titles = extract_from_index(index)
        print(f"已有文献: {index.get('count', '?')} 篇 (来自索引缓存)", file=sys.stderr)
    else:
        if args.index:
            print(f"索引文件不存在: {args.index}，回退到实时正则解析", file=sys.stderr)
        existing_dois = extract_existing_dois(args.wiki_dir)
        existing_titles = extract_existing_titles(args.wiki_dir)
        source = "实时正则解析"
        print(f"已有文献: {len(existing_dois)} DOI, {len(existing_titles)} 标题 (来自{source})", file=sys.stderr)

    print(f"待检查: {len(papers)} 篇", file=sys.stderr)

    # ── 3. 逐篇去重 ──
    unique_papers = []
    duplicates = []
    for p in papers:
        is_dup, reason = is_duplicate(p, existing_dois, existing_titles)
        if is_dup:
            duplicates.append((p, reason))
        else:
            unique_papers.append(p)

    # ── 4. 输出报告到 stderr ──
    if duplicates:
        print(f"\n去重排除 {len(duplicates)} 篇:", file=sys.stderr)
        for p, reason in duplicates:
            title = (p.get('title') or 'N/A')[:80]
            print(f"  ✗ {title} [{reason}]", file=sys.stderr)
    else:
        print(f"\n去重: 无重复文献", file=sys.stderr)

    print(f"有效文献: {len(unique_papers)} 篇", file=sys.stderr)

    # ── 5. 输出去重后的 JSON ──
    output = json.dumps(unique_papers, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"已写入: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
