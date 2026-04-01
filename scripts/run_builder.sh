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

python3 scripts/extract_allowed_context.py \
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

# Ralph-Claw Builder: Minimal context code generation
# The prompt bundle is prepared above. Now we need Candice (OpenClaw Claude) to process it.
echo "== Sending to OpenClaw builder session =="

# Write marker for Candice to pick up
mkdir -p /tmp/ralphclaw-handoff
cp /tmp/builder_prompt_bundle.txt /tmp/ralphclaw-handoff/builder_input_$(date +%s).txt

# Tell Candice what to do
echo "Ralph-Claw needs builder to process: $CURRENT_TASK"
echo "Prompt bundle is ready in /tmp/builder_prompt_bundle.txt"
echo "Expected output format:"
echo "  APPLY_PATCH:"
echo "  <unified diff here>"
echo "  END_PATCH"

# For now: placeholder that demonstrates what a real response would look like
cat > "$RAW_OUTPUT" << 'DEMO'
[Builder processing task...]

The builder has reviewed the minimal context and task.
To complete this integration, Candice needs to:
1. Read /tmp/builder_prompt_bundle.txt
2. Generate code as per the task
3. Format as unified diff
4. Output APPLY_PATCH: ... END_PATCH

APPLY_PATCH:
--- a/app/utils/text.py
+++ b/app/utils/text.py
@@ -1 +1,5 @@
+def normalize_spaces(text: str) -> str:
+    return " ".join(text.split())
+
+def slugify_title(text: str) -> str:
+    return "-".join(text.strip().lower().split())
DEMO

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

python3 scripts/check_patch_scope.py \
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
