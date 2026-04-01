#!/usr/bin/env bash
# OpenClaw integration layer for ralphclaw
# This script manages persistent builder/verifier/replanner sessions

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

AGENT_MODE="${1:-builder}"  # builder, verifier, replanner
PROMPT_BUNDLE="${2:-/tmp/prompt_bundle.txt}"
OUTPUT_FILE="${3:-/tmp/agent_output.txt}"

SESSION_KEY="ralphclaw:${AGENT_MODE}"
TIMEOUT_SECONDS=300

# Helper: send message to session
send_to_session() {
  local msg="$1"
  local session="$2"
  
  # Try using openclaw cron to send to session
  # This is a placeholder - real implementation would use sessions_send
  echo "Sending to session: $session"
  echo "$msg" >> "$OUTPUT_FILE"
}

# Helper: ensure session exists
ensure_session() {
  local role="$1"
  
  case "$role" in
    builder)
      echo "Initializing builder role..."
      cat prompts/builder.md
      ;;
    verifier)
      echo "Initializing verifier role..."
      cat prompts/verifier.md
      ;;
    replanner)
      echo "Initializing replanner role..."
      cat prompts/replanner.md
      ;;
    *)
      echo "Unknown role: $role" >&2
      return 1
      ;;
  esac
}

# Main logic
case "$AGENT_MODE" in
  builder)
    echo "== Ralph-Claw Builder (OpenClaw) =="
    echo "Session: $SESSION_KEY"
    echo "Prompt bundle: $PROMPT_BUNDLE"
    echo "Output: $OUTPUT_FILE"
    
    # In production: spawn isolated agent with Sonnet-level reasoning
    # For now: run in-process with full context
    {
      echo "=== BUILDER PROMPT ==="
      cat "$PROMPT_BUNDLE"
      echo ""
      echo "=== YOUR TASK ==="
      echo "Read the above task specification and generate a unified diff patch."
      echo "Format the patch between APPLY_PATCH: and END_PATCH markers."
    } > "$OUTPUT_FILE"
    
    echo "Builder output written to: $OUTPUT_FILE"
    ;;
    
  verifier)
    echo "== Ralph-Claw Verifier (OpenClaw) =="
    echo "Session: $SESSION_KEY"
    
    # Run deterministic tests
    bash scripts/run_verifier.sh
    ;;
    
  replanner)
    echo "== Ralph-Claw Replanner (OpenClaw) =="
    echo "Session: $SESSION_KEY"
    
    # Run replanner logic
    bash scripts/run_replanner.sh
    ;;
    
  *)
    echo "Usage: $0 <builder|verifier|replanner> <prompt_bundle> <output_file>"
    exit 1
    ;;
esac

exit 0
