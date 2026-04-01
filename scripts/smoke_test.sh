#!/usr/bin/env bash
set -euo pipefail

echo "== Smoke test start =="

python scripts/update_state.py validate_all

echo "== Select next task =="
python scripts/update_state.py select_next_ready_task > /tmp/current_task.json
cat /tmp/current_task.json

echo "== Simulate builder output =="
cat > app/utils/text.py <<'PY'
def normalize_spaces(text: str) -> str:
    return " ".join(text.split())


def slugify_title(text: str) -> str:
    return "-".join(text.strip().lower().split())
PY

echo "Changed app/utils/text.py" > artifacts/diff_summary.txt
cat > artifacts/last_patch.diff <<'PATCH'
diff --git a/app/utils/text.py b/app/utils/text.py
index e69de29..1111111 100644
--- a/app/utils/text.py
+++ b/app/utils/text.py
@@ -1,2 +1,6 @@
 def normalize_spaces(text: str) -> str:
     return " ".join(text.split())
+
+
+def slugify_title(text: str) -> str:
+    return "-".join(text.strip().lower().split())
PATCH

echo "== Run deterministic verifier =="
bash scripts/run_verifier.sh

STATUS=$(jq -r '.status' state/FAILURE_SUMMARY.json)

if [ "$STATUS" = "PASS" ]; then
  echo "== Mark task done =="
  python scripts/update_state.py mark_task_done --task-id task_001
else
  echo "== Increment retry =="
  python scripts/update_state.py increment_retry_count --task-id task_001
fi

echo "== Remaining tasks =="
python scripts/update_state.py remaining_tasks_count

echo "== Smoke test complete =="
