#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p artifacts state

PROMPT_FILE="prompts/replanner.md"
RAW_OUTPUT="artifacts/replanner_raw_output.txt"
PROPOSAL_FILE="state/REPLAN_PROPOSAL.json"

: > "$RAW_OUTPUT"

if [ ! -f "state/TASKS.json" ]; then
  echo "Missing state/TASKS.json" >&2
  exit 1
fi

if [ ! -f "state/FAILURE_SUMMARY.json" ]; then
  echo "Missing state/FAILURE_SUMMARY.json" >&2
  exit 1
fi

echo "== Running replanner =="

cat "$PROMPT_FILE" > /tmp/replanner_prompt.txt
echo "" >> /tmp/replanner_prompt.txt
echo "===== TASKS.json =====" >> /tmp/replanner_prompt.txt
cat state/TASKS.json >> /tmp/replanner_prompt.txt
echo "" >> /tmp/replanner_prompt.txt
echo "===== CURRENT_TASK.json =====" >> /tmp/replanner_prompt.txt
cat state/CURRENT_TASK.json >> /tmp/replanner_prompt.txt 2>/dev/null || true
echo "" >> /tmp/replanner_prompt.txt
echo "===== FAILURE_SUMMARY.json =====" >> /tmp/replanner_prompt.txt
cat state/FAILURE_SUMMARY.json >> /tmp/replanner_prompt.txt
echo "" >> /tmp/replanner_prompt.txt

for f in artifacts/test.out artifacts/build.out artifacts/lint.out artifacts/runtime.out; do
  if [ -f "$f" ]; then
    echo "===== $f =====" >> /tmp/replanner_prompt.txt
    cat "$f" >> /tmp/replanner_prompt.txt
    echo "" >> /tmp/replanner_prompt.txt
  fi
done

# TODO: replace this placeholder with your real replanner agent call
# Example idea:
# openclaw run agent replanner --input /tmp/replanner_prompt.txt > "$RAW_OUTPUT"
echo "{}" > "$RAW_OUTPUT"
echo "ERROR: replace placeholder replanner agent call in scripts/run_replanner.sh" >&2

cp "$RAW_OUTPUT" "$PROPOSAL_FILE"

echo "Replanner output written to $PROPOSAL_FILE"
