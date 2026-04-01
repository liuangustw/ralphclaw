#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p artifacts

PROMPT_FILE="prompts/builder.md"
CURRENT_TASK="state/CURRENT_TASK.json"
MIN_CONTEXT="artifacts/builder_min_context.txt"
RAW_OUTPUT="artifacts/builder_raw_output.txt"
PATCH_FILE="artifacts/last_patch.diff"
SUMMARY_FILE="artifacts/diff_summary.txt"
SPEC_FILE="specs/product_spec.md"
ACCEPT_FILE="specs/acceptance_tests.md"

if [ ! -f "$CURRENT_TASK" ]; then
  echo "Missing $CURRENT_TASK" >&2
  exit 1
fi

: > "$RAW_OUTPUT"
: > "$PATCH_FILE"
: > "$SUMMARY_FILE"

echo "== Preparing minimal builder context =="

python scripts/extract_allowed_context.py \
  --current-task "$CURRENT_TASK" \
  --output "$MIN_CONTEXT" \
  --repo-root "."

echo "== Running builder with minimal context =="

{
  cat "$PROMPT_FILE"
  echo
  echo "===== CURRENT_TASK.json ====="
  cat "$CURRENT_TASK"
  echo
  echo "===== MINIMAL_CONTEXT ====="
  cat "$MIN_CONTEXT"
  echo
  if [ -f "$SPEC_FILE" ]; then
    echo "===== product_spec.md ====="
    cat "$SPEC_FILE"
    echo
  fi
  if [ -f "$ACCEPT_FILE" ]; then
    echo "===== acceptance_tests.md ====="
    cat "$ACCEPT_FILE"
    echo
  fi
} > /tmp/builder_prompt_bundle.txt

# TODO: replace this placeholder with your real builder agent call
# Example idea:
# openclaw run agent builder --input /tmp/builder_prompt_bundle.txt > "$RAW_OUTPUT"
echo "ERROR: replace placeholder builder agent call in scripts/run_builder.sh" > "$RAW_OUTPUT"

echo "== Extracting patch from builder output =="

awk '
  BEGIN {capture=0}
  /^APPLY_PATCH:$/ {capture=1; next}
  capture {print}
' "$RAW_OUTPUT" > "$PATCH_FILE" || true

if [ ! -s "$PATCH_FILE" ]; then
  echo "No patch extracted from builder output." >&2
  echo "--- builder raw output ---" >&2
  cat "$RAW_OUTPUT" >&2
  exit 2
fi

echo "== Preflight: checking patch scope =="

python scripts/check_patch_scope.py \
  --patch "$PATCH_FILE" \
  --current-task "$CURRENT_TASK"

echo "== Preflight: checking patch apply =="

if git rev-parse --is-inside-work-tree >/dev/null 2>&1 && git apply --check "$PATCH_FILE" >/dev/null 2>&1; then
  git apply "$PATCH_FILE"
elif patch -p0 --dry-run < "$PATCH_FILE" >/dev/null 2>&1; then
  patch -p0 < "$PATCH_FILE"
else
  echo "Patch could not be applied cleanly." >&2
  exit 3
fi

echo "== Writing diff summary =="

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git diff -- app tests specs > "$SUMMARY_FILE" || true
else
  echo "git repository not detected; diff summary unavailable" > "$SUMMARY_FILE"
fi

echo "Builder patch applied successfully."
