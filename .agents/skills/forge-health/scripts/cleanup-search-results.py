"""检索结果清理 — 删除超过阈值的旧检索文件（forge-health §10）

用法：在 SciCrucible 根目录运行
  python .claude/skills/forge-health/scripts/cleanup-search-results.py [--dry-run] [--cutoff-days 30]
"""
import sys
import os
import time
from pathlib import Path

DRY_RUN = '--dry-run' in sys.argv
# 可从命令行覆盖默认 30 天阈值
cutoff_days = 30
for i, arg in enumerate(sys.argv):
    if arg == '--cutoff-days' and i + 1 < len(sys.argv):
        cutoff_days = int(sys.argv[i + 1])
        break

BASE = Path('raw/search-results')
now = time.time()
cutoff = now - cutoff_days * 24 * 3600

for sub in ['json', 'bib']:
    d = BASE / sub
    if not d.exists():
        continue
    for f in sorted(d.glob('search-results-*')):
        if f.stat().st_mtime < cutoff:
            age_days = (now - f.stat().st_mtime) / 86400
            if DRY_RUN:
                print(f'  [DRY RUN] Would delete: {f.name} ({age_days:.0f}d old)')
            else:
                print(f'  🗑 {f.name} ({age_days:.0f}d old)')
                f.unlink()
    # 清理空目录
    remaining = list(d.glob('*'))
    if not remaining:
        if DRY_RUN:
            print(f'  [DRY RUN] Would remove empty dir: {sub}/')
        else:
            d.rmdir()
            print(f'  📁 Removed empty dir: {sub}/')

if DRY_RUN:
    print('\n⚠ DRY RUN — 未实际删除。去掉 --dry-run 执行实际清理。')
else:
    print('Done.')
