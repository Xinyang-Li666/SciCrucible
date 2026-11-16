"""brainstorming 机械统计 — 量化指标脚本（forge-health §11）

用法：在 SciCrucible 根目录运行
  python .claude/skills/forge-health/scripts/brainstorming-stats.py [base_dir]
"""
import sys
from pathlib import Path

base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
bdir = base / 'brainstorming'
wdir = base / 'wiki'

if not bdir.is_dir():
    print('brainstorming/ 目录为空，跳过')
    sys.exit(0)

EXCLUDE = {'todos.md', 'questions.md', 'INDEX.md'}
files = []

# 散落在根目录的 .md（排除保留文件）
for f in sorted(bdir.glob('*.md')):
    if f.name not in EXCLUDE:
        files.append(('散落', f))

# research/ 和 ideas/ 子目录
for sub in ('research', 'ideas'):
    sd = bdir / sub
    if sd.is_dir():
        for f in sorted(sd.glob('*.md')):
            files.append((sub, f))

# 建立全文索引（questions + todos + 全量 wiki）
corpus = ''
for n in ('questions.md', 'todos.md'):
    p = bdir / n
    if p.is_file():
        corpus += p.read_text(encoding='utf-8') + '\n'
if wdir.is_dir():
    for wf in sorted(wdir.rglob('*.md')):
        corpus += wf.read_text(encoding='utf-8') + '\n'

# 概念页 stem 集
cstems = set()
cdir = wdir / 'concepts'
if cdir.is_dir():
    cstems = {c.stem for c in cdir.glob('*.md')}

print('区 | 行数 | 短段 | 引用 | 概念页 | 文件 | 预览')
print('---|---|---|---|---|---|---')
for zone, fp in files:
    c = fp.read_text(encoding='utf-8')
    lines = c.count('\n')
    sp = sum(1 for p in c.split('\n\n') if 10 < len(p) < 80)
    ref = '是' if fp.stem in corpus else '否'
    con = '是' if fp.stem in cstems else '否'
    pv = ''
    for ln in c.splitlines():
        s = ln.strip()
        if s and not s.startswith('#'):
            pv = s[:40]
            break
    print(f'{zone} | {lines} | {sp} | {ref} | {con} | {fp.name} | {pv}')
