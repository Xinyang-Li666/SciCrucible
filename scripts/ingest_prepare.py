"""Read-only PDF preparation. Never writes wiki pages or moves source files."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tempfile

from extract_pdf import extract_pages, render_pages

CACHE_VERSION = 1
# Conservative candidate extraction: PDF bracket glyphs may decode as CJK.
# Unusual DOI suffixes still require the human metadata check.
DOI = re.compile(r'10\.\d{4,9}/[-._;()/:a-z0-9+%]+', re.I | re.ASCII)


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(text)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path, data):
    atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2))


def normalize_doi(value):
    value = value.lower().rstrip('.,;:')
    while value.endswith(')') and value.count(')') > value.count('('):
        value = value[:-1]
    return value


def prepare(root, source=None, topic=None):
    root = Path(root).resolve()
    source = Path(source).resolve() if source else root / 'raw/new-papers'
    if not source.exists():
        raise FileNotFoundError(source)
    files = ([source] if source.is_file() else
             sorted((p for p in source.rglob('*') if p.is_file() and p.suffix.lower() == '.pdf'),
                    key=lambda p: str(p).lower()))
    cache = root / '.kiro/.ingest_cache'
    result = {'schema_version': CACHE_VERSION, 'prepared_at': datetime.now(timezone.utc).isoformat(),
              'topic': topic, 'source': str(source), 'warnings': [], 'papers': []}
    index = {}
    index_path = root / 'wiki/literature_index.json'
    if index_path.exists():
        try:
            raw_index = json.loads(index_path.read_text(encoding='utf-8-sig'))
            if not isinstance(raw_index, dict):
                raise ValueError('Expected DOI-keyed object')
            index = {normalize_doi(k): v for k, v in raw_index.items() if k.startswith('10.')}
        except (ValueError, OSError) as exc:
            result['warnings'].append(f'Index unreadable; requires deduplication review: {exc}')
    seen_hash = {}
    for pdf in files:
        row = {'source_pdf': str(pdf), 'status': 'error', 'warnings': []}
        try:
            with pdf.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            row['sha256'] = digest
            if digest in seen_hash:
                row.update(status='duplicate_sha256', duplicate_of=seen_hash[digest])
            else:
                stored = cache / 'pages' / f'{digest}.json'
                pages = None
                if stored.exists():
                    try:
                        payload = json.loads(stored.read_text(encoding='utf-8'))
                        if (payload.get('version') == CACHE_VERSION and payload.get('sha256') == digest
                                and isinstance(payload.get('pages'), list)
                                and all(isinstance(p, str) for p in payload['pages'])):
                            pages = payload['pages']
                    except (ValueError, OSError, AttributeError):
                        pass  # Bad cache is regenerated from the original PDF.
                row['cache_hit'] = pages is not None
                if pages is None:
                    pages = extract_pages(pdf)
                    write_json(stored, {'version': CACHE_VERSION, 'sha256': digest, 'pages': pages})
                row['page_count'] = len(pages)
                row['characters_per_page'] = [len(p.strip()) for p in pages]
                candidates = sorted({normalize_doi(m) for m in DOI.findall('\n'.join(pages[:3]))})
                row['doi_candidates'] = candidates
                row['index_matches'] = {d: index[d] for d in candidates if d in index}
                if len(pages) <= 1:
                    row['warnings'].append('single_page_requires_review')
                if sum(row['characters_per_page']) < 400:
                    row['warnings'].append('little_text_requires_ocr_or_review')
                if any(n < 40 for n in row['characters_per_page']):
                    row['warnings'].append('sparse_pages_require_visual_review')
                if len(candidates) != 1:
                    row['warnings'].append('doi_missing_or_ambiguous')
                if row['index_matches']:
                    row['warnings'].append('possible_already_ingested_verify_title_and_doi')
                if result['warnings']:
                    row['warnings'].append('index_unavailable')
                text_path = cache / 'texts' / f'{digest}.txt'
                atomic_write(text_path, render_pages(pages))
                row.update(text_file=str(text_path), pages_file=str(stored),
                           status='needs_review' if row['warnings'] else 'ready')
                seen_hash[digest] = str(pdf)
        except Exception as exc:
            row.update(status='error', error=f'{type(exc).__name__}: {exc}')
        result['papers'].append(row)
        write_json(cache / 'manifest.json', result)
    groups = {}
    for row in result['papers']:
        for doi in row.get('doi_candidates', []):
            groups.setdefault(doi, []).append(row)
    for doi, group in groups.items():
        if len(group) > 1:
            for row in group:
                row['status'] = 'needs_review'
                row['warnings'].append(f'possible_duplicate_doi:{doi}')
    result['counts'] = dict(Counter(row['status'] for row in result['papers']))
    write_json(cache / 'manifest.json', result)
    report = ['# PDF预检（不是摄入完成）', '', f'课题：{topic or "待按内容判定"}',
              '', 'ready仅表示通过自动预检；所有文件仍需核对正文完整性、本文DOI和科学内容。',
              '', '| 文件 | 页数 | 状态 | 说明 |', '|---|---:|---|---|']
    for row in result['papers']:
        name = Path(row['source_pdf']).name.replace('|', '\\|')
        detail = row.get('error') or '; '.join(row['warnings']) or row.get('duplicate_of', '')
        report.append(f'| {name} | {row.get("page_count", "—")} | {row["status"]} | {detail.replace(chr(10), " ").replace("|", "/")} |')
    atomic_write(cache / 'report.md', '\n'.join(report) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', nargs='?', help='PDF file or directory')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--topic', help='Suggested topic; final classification requires content review')
    args = parser.parse_args()
    manifest = prepare(args.root, args.source, args.topic)
    print(json.dumps(manifest['counts'], ensure_ascii=False))
    print(args.root / '.kiro/.ingest_cache/report.md')
    raise SystemExit(1 if manifest['counts'].get('error') else 0)
