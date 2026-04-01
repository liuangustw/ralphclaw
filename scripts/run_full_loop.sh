#!/usr/bin/env bash
# Ralph-Claw Full Loop with Gemini APIs
# Architect (Free Tier 1) → Builder (Free Tier 2) → Verifier → Replanner (Free Tier 3)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Load API keys from environment
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

MAX_ITERATIONS=3
ITERATION=0

echo "=========================================="
echo "Ralph-Claw Full Loop (Gemini APIs)"
echo "=========================================="
echo ""

# Initialize state if needed
if [ ! -f "state/TASKS.json" ]; then
  echo "Error: state/TASKS.json not found. Run: python3 scripts/update_state.py init"
  exit 1
fi

while [ $ITERATION -lt $MAX_ITERATIONS ]; do
  ITERATION=$((ITERATION + 1))
  
  echo ""
  echo "=== Iteration $ITERATION/$MAX_ITERATIONS ==="
  echo ""
  
  # Step 1: Architect selects next task
  echo "📋 Step 1: Architect (Gemini Free Tier 1)"
  bash scripts/run_architect.sh || {
    echo "Architect failed" >&2
    exit 1
  }
  
  TASK_ID=$(jq -r '.task_id // empty' state/CURRENT_TASK.json 2>/dev/null || echo "")
  if [ -z "$TASK_ID" ]; then
    echo "No more tasks to process"
    break
  fi
  
  echo "✓ Selected task: $TASK_ID"
  echo ""
  
  # Step 2: Builder generates code
  echo "🔨 Step 2: Builder (Gemini Free Tier 2)"
  if ! bash scripts/run_builder.sh; then
    echo "Builder failed" >&2
    exit 1
  fi
  
  if [ -f "artifacts/last_patch.diff" ] && [ -s "artifacts/last_patch.diff" ]; then
    echo "✓ Patch generated"
  else
    echo "⚠ No patch generated"
  fi
  echo ""
  
  # Step 3: Verifier checks
  echo "✅ Step 3: Verifier (Automated)"
  bash scripts/run_verifier.sh || true
  
  VERIFY_STATUS=$(jq -r '.status // "UNKNOWN"' state/FAILURE_SUMMARY.json 2>/dev/null)
  echo "✓ Verification: $VERIFY_STATUS"
  echo ""
  
  if [ "$VERIFY_STATUS" = "PASS" ]; then
    echo "🎉 Task completed!"
    python3 scripts/update_state.py mark_task_done --task-id "$TASK_ID" 2>/dev/null || true
    echo ""
    echo "Continuing to next task..."
    sleep 1
    
  elif [ "$VERIFY_STATUS" = "FAIL" ]; then
    FAILURE_TYPE=$(jq -r '.failure_type // "unknown"' state/FAILURE_SUMMARY.json)
    ROOT_CAUSE=$(jq -r '.root_cause_guess // "unknown"' state/FAILURE_SUMMARY.json)
    
    echo "❌ Task failed: $FAILURE_TYPE"
    echo "   Root cause: $ROOT_CAUSE"
    echo ""
    echo "🔄 Step 4: Replanner (Gemini Free Tier 3)"
    
    if bash scripts/run_replanner.sh; then
      REPLANNED=$(jq -r '.replacement_tasks | length // 0' state/REPLAN_PROPOSAL.json 2>/dev/null)
      echo "✓ Replanned into $REPLANNED subtasks"
      
      # Apply replan
      python3 scripts/update_state.py apply_replan_proposal 2>/dev/null || true
      echo ""
      echo "Retrying with refined tasks..."
      sleep 1
    else
      echo "⚠ Replanner failed, skipping this task"
      python3 scripts/update_state.py increment_retry_count --task-id "$TASK_ID" 2>/dev/null || true
      break
    fi
    
  else
    echo "⚠ Verification status unclear: $VERIFY_STATUS"
    break
  fi
done

echo ""
echo "=========================================="
echo "Loop complete (iteration $ITERATION)"
echo "=========================================="

REMAINING=$(python3 scripts/update_state.py remaining_tasks_count 2>/dev/null || echo "?")
echo "Remaining tasks: $REMAINING"
