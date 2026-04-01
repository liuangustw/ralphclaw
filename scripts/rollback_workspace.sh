#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SNAPSHOT_META="artifacts/workspace_snapshot.json"

if [ ! -f "$SNAPSHOT_META" ]; then
  echo "No workspace snapshot metadata found." >&2
  exit 1
fi

MODE=$(python - <<'PY'
import json
from pathlib import Path
data = json.loads(Path("artifacts/workspace_snapshot.json").read_text(encoding="utf-8"))
print(data.get("mode", ""))
PY
)

if [ "$MODE" = "git" ]; then
  echo "== Rolling back git workspace =="
  git reset --hard HEAD >/dev/null 2>&1
  git clean -fd >/dev/null 2>&1 || true
  echo "ROLLBACK_OK git"
  exit 0
fi

if [ "$MODE" = "copy" ]; then
  echo "== Rolling back copied workspace =="
  BACKUP_DIR=$(python - <<'PY'
import json
from pathlib import Path
data = json.loads(Path("artifacts/workspace_snapshot.json").read_text(encoding="utf-8"))
print(data.get("backup_dir", ""))
PY
)
  if [ -z "$BACKUP_DIR" ] || [ ! -d "$BACKUP_DIR" ]; then
    echo "Backup directory missing." >&2
    exit 2
  fi

  rm -rf app tests specs
  [ -d "$BACKUP_DIR/app" ] && cp -R "$BACKUP_DIR/app" ./app
  [ -d "$BACKUP_DIR/tests" ] && cp -R "$BACKUP_DIR/tests" ./tests
  [ -d "$BACKUP_DIR/specs" ] && cp -R "$BACKUP_DIR/specs" ./specs

  echo "ROLLBACK_OK copy"
  exit 0
fi

echo "Unknown snapshot mode: $MODE" >&2
exit 3
