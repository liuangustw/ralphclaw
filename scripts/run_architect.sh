#!/usr/bin/env bash
# Ralph-Claw Architect: Task decomposition and planning
# Uses Gemini Free Tier 1 API

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p artifacts state

PROMPT_FILE="prompts/architect.md"
RAW_OUTPUT="artifacts/architect_raw_output.txt"
CURRENT_TASK_FILE="state/CURRENT_TASK.json"

: > "$RAW_OUTPUT"

if [ ! -f "state/TASKS.json" ]; then
  echo "Missing state/TASKS.json" >&2
  exit 1
fi

echo "== Running architect =="

# Prepare architect prompt
cat "$PROMPT_FILE" > /tmp/architect_prompt.txt
echo "" >> /tmp/architect_prompt.txt
echo "===== TASKS.json =====" >> /tmp/architect_prompt.txt
cat state/TASKS.json >> /tmp/architect_prompt.txt
echo "" >> /tmp/architect_prompt.txt

if [ -f "state/FAILURE_SUMMARY.json" ]; then
  echo "===== FAILURE_SUMMARY.json (last failure context) =====" >> /tmp/architect_prompt.txt
  cat state/FAILURE_SUMMARY.json >> /tmp/architect_prompt.txt
  echo "" >> /tmp/architect_prompt.txt
fi

if [ -f "specs/product_spec.md" ]; then
  echo "===== product_spec.md =====" >> /tmp/architect_prompt.txt
  cat specs/product_spec.md >> /tmp/architect_prompt.txt
  echo "" >> /tmp/architect_prompt.txt
fi

echo "== Calling Gemini Architect API =="

GEMINI_KEY="${GEMINI_API_KEYS_FREE_TIER_1:-$GEMINI_API_KEY}"

if [ -z "$GEMINI_KEY" ]; then
  echo "Error: GEMINI_API_KEYS_FREE_TIER_1 or GEMINI_API_KEY not set" >&2
  exit 1
fi

# Call Gemini with architect role
python3 scripts/call_gemini.py \
  --role architect \
  --key "$GEMINI_KEY" \
  --input /tmp/architect_prompt.txt \
  --output "$RAW_OUTPUT" 2>&1 | head -5

echo "== Parsing architect output =="

# Extract JSON from response
if grep -q "{" "$RAW_OUTPUT" 2>/dev/null; then
  # Try to extract valid JSON from the response
  python3 << 'PY'
import json
import re
from pathlib import Path

raw = Path("artifacts/architect_raw_output.txt").read_text()

# Try to find JSON in the response
json_match = re.search(r'\{.*\}', raw, re.DOTALL)
if json_match:
    try:
        task_obj = json.loads(json_match.group())
        # Validate required fields
        if "task_id" in task_obj and "title" in task_obj:
            Path("state/CURRENT_TASK.json").write_text(
                json.dumps(task_obj, indent=2),
                encoding="utf-8"
            )
            print(f"Architect selected task: {task_obj.get('task_id')} - {task_obj.get('title')}")
            exit(0)
    except json.JSONDecodeError:
        pass

print("Error: Could not parse architect response as JSON" >&2, file=sys.stderr)
exit(1)
PY
else
  echo "Error: Architect response did not contain valid JSON" >&2
  cat "$RAW_OUTPUT" >&2
  exit 1
fi

echo "== Architect task selection complete =="
