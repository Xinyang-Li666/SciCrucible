"""概念页健康评分 — 量化统计脚本（forge-health §8）

用法：在 SciCrucible 根目录运行
  python .claude/skills/forge-health/scripts/concept-health.py
"""
import os
import re
import glob
from pathlib import Path
from datetime import datetime

# 递归覆盖各课题与通用层
concept_files = sorted(glob.glob('wiki/**/concepts/*.md', recursive=True))
for path in concept_files:
    f = Path(path)
    content = f.read_text(encoding='utf-8')
    lines = content.count('\n')
    refs = len(re.findall(r'\[\[[^]]+\]\]', content))
    mtime = datetime.fromtimestamp(f.stat().st_mtime)
    months_ago = (datetime.now() - mtime).days / 30.44
    short_paras = sum(1 for p in content.split('\n\n') if 10 < len(p) < 80)

    score = 100
    if lines > 300: score -= 15
    if lines > 500: score -= 15
    if refs > 15: score -= 10
    if months_ago > 6: score -= 20
    if months_ago > 12: score -= 15
    if short_paras < 3: score -= 15

    print(f'{score:3d} | {lines:3d}行 | {refs:2d}引用 | {months_ago:4.1f}月前 | {f.parent.parent.name}/{f.name}')
