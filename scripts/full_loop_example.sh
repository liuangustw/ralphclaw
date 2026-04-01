#!/usr/bin/env bash
set -euo pipefail

python scripts/update_state.py select_next_ready_task >/dev/null

CURRENT_TASK_ID=$(jq -r '.task_id // empty' state/CURRENT_TASK.json)
if [ -z "$CURRENT_TASK_ID" ]; then
  echo "No selectable task."
  exit 0
fi

bash scripts/snapshot_workspace.sh
bash scripts/run_builder.sh
bash scripts/run_verifier.sh

STATUS=$(jq -r '.status' state/FAILURE_SUMMARY.json)

if [ "$STATUS" = "PASS" ]; then
  python scripts/update_state.py mark_task_done --task-id "$CURRENT_TASK_ID" >/dev/null
  echo "Task passed and kept."
elif [ "$STATUS" = "FAIL" ]; then
  echo "Task failed. Rolling back workspace."
  bash scripts/rollback_workspace.sh
  RESULT=$(python scripts/update_state.py increment_retry_count --task-id "$CURRENT_TASK_ID")
  if [ "$RESULT" = "ESCALATE" ]; then
    bash scripts/run_replanner.sh
    python scripts/update_state.py apply_replan_proposal >/dev/null
  fi
elif [ "$STATUS" = "ESCALATE" ]; then
  echo "Task escalated. Rolling back workspace."
  bash scripts/rollback_workspace.sh
  bash scripts/run_replanner.sh
  python scripts/update_state.py apply_replan_proposal >/dev/null
else
  echo "Unknown verifier status: $STATUS"
  bash scripts/rollback_workspace.sh
  exit 3
fi
