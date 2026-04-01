#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

bash scripts/snapshot_workspace.sh
bash scripts/run_builder.sh
bash scripts/run_verifier.sh

STATUS=$(jq -r '.status' state/FAILURE_SUMMARY.json)

if [ "$STATUS" = "PASS" ]; then
  echo "SAFE_RUN_PASS"
  exit 0
fi

echo "SAFE_RUN_FAIL_OR_ESCALATE -> rollback"
bash scripts/rollback_workspace.sh
exit 1
