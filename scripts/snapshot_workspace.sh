#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p artifacts

SNAPSHOT_META="artifacts/workspace_snapshot.json"
PATCH_BACKUP="artifacts/pre_apply_working_tree.diff"

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  CURRENT_HEAD=$(git rev-parse HEAD)
  git diff > "$PATCH_BACKUP" || true

  cat > "$SNAPSHOT_META" <<EOF
{
  "mode": "git",
  "head": "$CURRENT_HEAD",
  "working_diff": "artifacts/pre_apply_working_tree.diff"
}
EOF

  echo "SNAPSHOT_OK git $CURRENT_HEAD"
else
  BACKUP_DIR="artifacts/workspace_backup"
  rm -rf "$BACKUP_DIR"
  mkdir -p "$BACKUP_DIR"

  [ -d app ] && cp -R app "$BACKUP_DIR/"
  [ -d tests ] && cp -R tests "$BACKUP_DIR/"
  [ -d specs ] && cp -R specs "$BACKUP_DIR/"

  cat > "$SNAPSHOT_META" <<EOF
{
  "mode": "copy",
  "backup_dir": "artifacts/workspace_backup"
}
EOF

  echo "SNAPSHOT_OK copy"
fi
