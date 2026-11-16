#!/usr/bin/env bash
# Preparation only; same backend as Windows. No source moves or wiki writes.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -n "${INGEST_PYTHON:-}" ]]; then
    exec "$INGEST_PYTHON" "$SCRIPT_DIR/ingest_prepare.py" "$@"
elif command -v python3 >/dev/null 2>&1; then
    exec python3 "$SCRIPT_DIR/ingest_prepare.py" "$@"
else
    exec python "$SCRIPT_DIR/ingest_prepare.py" "$@"
fi
