#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p artifacts state

CURRENT_TASK="state/CURRENT_TASK.json"
PATCH_FILE="artifacts/last_patch.diff"
FAILURE_SUMMARY="state/FAILURE_SUMMARY.json"

TEST_OUT="artifacts/test.out"
LINT_OUT="artifacts/lint.out"
BUILD_OUT="artifacts/build.out"
RUNTIME_OUT="artifacts/runtime.out"
SCOPE_OUT="artifacts/scope_check.out"

: > "$TEST_OUT"
: > "$LINT_OUT"
: > "$BUILD_OUT"
: > "$RUNTIME_OUT"
: > "$SCOPE_OUT"

if [ ! -f "$CURRENT_TASK" ]; then
  echo "Missing $CURRENT_TASK" >&2
  exit 1
fi

TASK_ID=$(jq -r '.task_id // empty' "$CURRENT_TASK")
if [ -z "$TASK_ID" ]; then
  echo "CURRENT_TASK.json missing task_id" >&2
  exit 1
fi

echo "== Scope check =="
SCOPE_STATUS="passed"

if [ -f "$PATCH_FILE" ]; then
  if python scripts/check_patch_scope.py --patch "$PATCH_FILE" --current-task "$CURRENT_TASK" > "$SCOPE_OUT" 2>&1; then
    SCOPE_STATUS="passed"
  else
    SCOPE_STATUS="failed"
  fi
else
  echo "No patch file found for scope check." > "$SCOPE_OUT"
fi

echo "== Run test commands =="
TEST_STATUS="passed"

python3 - <<'PY' > /tmp/task_test_commands.txt
import json
from pathlib import Path
task = json.loads(Path("state/CURRENT_TASK.json").read_text(encoding="utf-8"))
for cmd in task.get("test_commands", []):
    print(cmd)
PY

if [ ! -s /tmp/task_test_commands.txt ]; then
  echo "No test_commands defined in CURRENT_TASK.json" > "$TEST_OUT"
  TEST_STATUS="failed"
else
  while IFS= read -r cmd; do
    echo "\$ $cmd" >> "$TEST_OUT"
    if bash -lc "$cmd" >> "$TEST_OUT" 2>&1; then
      :
    else
      TEST_STATUS="failed"
    fi
    echo "" >> "$TEST_OUT"
  done < /tmp/task_test_commands.txt
fi

echo "lint not configured" > "$LINT_OUT"
echo "build not configured" > "$BUILD_OUT"
echo "runtime checks not configured" > "$RUNTIME_OUT"

python3 - <<'PY'
import json
from pathlib import Path
from datetime import datetime, timezone

def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

task = json.loads(Path("state/CURRENT_TASK.json").read_text(encoding="utf-8"))
task_id = task["task_id"]

test_out = Path("artifacts/test.out").read_text(encoding="utf-8")
scope_out = Path("artifacts/scope_check.out").read_text(encoding="utf-8")

scope_status = "passed"
if "PATCH_SCOPE_VIOLATION" in scope_out:
    scope_status = "failed"

test_status = "passed"
if "FAILED" in test_out or "failed" in test_out.lower() or "error" in test_out.lower():
    test_status = "failed"
if "No test_commands defined" in test_out:
    test_status = "failed"

out_of_scope = []
capture = False
for line in scope_out.splitlines():
    if line.strip() == "Violations:":
        capture = True
        continue
    if capture and line.strip().startswith("- "):
        out_of_scope.append(line.strip()[2:])
    elif capture and not line.strip():
        break

failed_checks = []

if scope_status == "failed":
    failed_checks.append({
        "name": "patch scope check",
        "result": "failed",
        "summary": "Patch touched files outside allowed_files"
    })

failed_checks.append({
    "name": "task test commands",
    "result": "passed" if test_status == "passed" else "failed",
    "summary": "Executed commands listed in CURRENT_TASK.json.test_commands"
})

if scope_status == "failed":
    status = "ESCALATE"
    failure_type = "scope_violation"
    root_cause_guess = "Patch modified files outside allowed_files"
    retry_recommended = False
    escalate_recommended = True
elif test_status == "failed":
    status = "FAIL"
    failure_type = "test_failure"
    root_cause_guess = "One or more task test commands failed"
    retry_recommended = True
    escalate_recommended = False
else:
    status = "PASS"
    failure_type = "none"
    root_cause_guess = ""
    retry_recommended = False
    escalate_recommended = False

payload = {
    "task_id": task_id,
    "status": status,
    "failure_type": failure_type,
    "root_cause_guess": root_cause_guess,
    "failed_checks": failed_checks,
    "out_of_scope_edits": out_of_scope,
    "retry_recommended": retry_recommended,
    "escalate_recommended": escalate_recommended,
    "timestamp": now()
}

Path("state/FAILURE_SUMMARY.json").write_text(
    json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8"
)
PY

cat "$FAILURE_SUMMARY"
