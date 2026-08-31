#!/usr/bin/env bash
# Company Scanner - kiem tra moi thu roi chay app.
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else
  echo "[LOI] Khong tim thay Python. Cai tai https://www.python.org/downloads/"
  exit 1
fi

exec "$PY" start.py "$@"
