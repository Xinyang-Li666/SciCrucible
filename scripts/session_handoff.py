"""Small, verifiable handoff for a fresh session."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

FIELDS = {'schema_version', 'objective', 'run_dir', 'batch_scope', 'completed_artifacts',
          'next_command', 'stop_condition', 'open_blockers', 'authorization_refs'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(value, check_hashes=False):
    if not isinstance(value, dict) or set(value) != FIELDS or value['schema_version'] != 'session-handoff/1.0':
        raise ValueError('Invalid handoff schema')
    for key in ('objective', 'run_dir', 'next_command', 'stop_condition'):
        if not isinstance(value[key], str) or not value[key].strip():
            raise ValueError('Invalid '+key)
    for key in ('batch_scope', 'completed_artifacts', 'open_blockers', 'authorization_refs'):
        if not isinstance(value[key], list):
            raise ValueError('Invalid '+key)
    if any(not isinstance(x, str) for key in ('batch_scope', 'open_blockers', 'authorization_refs') for x in value[key]):
        raise ValueError('Invalid list entry')
    for item in value['completed_artifacts']:
        if not isinstance(item, dict) or set(item) != {'path', 'sha256'} or not isinstance(item['path'], str):
            raise ValueError('Invalid artifact')
        if check_hashes and digest(item['path']) != item['sha256']:
            raise ValueError('Artifact hash mismatch')


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    write = sub.add_parser('write'); write.add_argument('--input', required=True); write.add_argument('--output', required=True)
    check = sub.add_parser('check'); check.add_argument('--handoff', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'write':
            value = json.loads(Path(args.input).read_text(encoding='utf-8'))
            validate(value)
            for item in value['completed_artifacts']:
                item['sha256'] = digest(item['path'])
            data = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
            if len(data) > 4000:
                raise ValueError('Handoff exceeds 4000 characters')
            with Path(args.output).open('x', encoding='utf-8') as fh:
                fh.write(data+'\n')
        else:
            value = json.loads(Path(args.handoff).read_text(encoding='utf-8'))
            validate(value, check_hashes=True)
        print(json.dumps({'status': 'ok'}, ensure_ascii=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'status': 'failed', 'code': type(exc).__name__}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
