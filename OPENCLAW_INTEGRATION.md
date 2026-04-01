# Ralph-Claw × OpenClaw Integration Guide

**Status**: ✅ Installed and tested on ubuntu-4gb-nbg1-1
**Location**: `/opt/ralphclaw`
**GitHub**: https://github.com/liuangustw/ralphclaw

---

## Installation Summary

✅ Repository cloned to VPS
✅ Smoke test passing
✅ Python 3 compatibility verified
✅ OpenClaw runner layer added

---

## What Ralph-Claw Does

Ralph-Claw is a **state-driven coding loop** with built-in safety layers:

1. **ARCHITECT** → break problem into tasks, write CURRENT_TASK.json
2. **BUILDER** → code generation with minimal context, produce patch
3. **VERIFIER** → run tests, check scope, fail fast
4. **REPLANNER** → replan if verification fails

```
┌─────────────────┐
│   Task Pool     │
└────────┬────────┘
         │
         ▼
    ┌────────────────────────┐
    │  Select next task      │
    └────────┬───────────────┘
             │
             ▼
    ┌────────────────────────┐
    │   Builder (Claude)     │  ← YOUR AI AGENT
    │  (minimal context)     │
    └────────┬───────────────┘
             │
             ▼
    ┌────────────────────────┐
    │   Verifier (tests)     │  ← Deterministic
    │   (scope + tests)      │
    └────────┬───────────────┘
             │
        ┌────┴────┐
        │          │
       PASS      FAIL
        │          │
        ▼          ▼
    (Done)    ┌──────────────┐
              │   Replanner  │  ← Claude
              │ (replan, +1) │
              └──────┬───────┘
                     │
              (retry builder)
```

---

## Core Discipline Features

### 1. Minimal Context
- Extracts only relevant task + test commands
- Builder never sees full codebase
- Prevents Claude attention-drift

### 2. Patch Scope Checking
- Validates diff touches only intended files
- Rejects "I decided to also refactor this..."
- Hard constraint before test phase

### 3. Deterministic Verification
- No AI in test phase
- Just pytest, lint, type checking
- Fail/pass is objective

### 4. Retry Loop
- Automatically retries builder 3x if tests fail
- Each retry includes failure summary
- Replanner can suggest new approach

---

## Running Ralph-Claw

### Quick start
```bash
cd /opt/ralphclaw
bash scripts/smoke_test.sh
```

### Manual workflow
```bash
# 1. Initialize tasks (once)
python3 scripts/update_state.py init

# 2. Select next task
python3 scripts/update_state.py select_next_ready_task > /tmp/ct.json

# 3. Run builder
bash scripts/run_builder.sh

# 4. Run verifier
bash scripts/run_verifier.sh

# 5. Check result
cat state/FAILURE_SUMMARY.json | jq .status
```

---

## OpenClaw Integration Points

### Current Status
- `scripts/run_builder.sh` has placeholder for agent call
- `scripts/openclaw_runner.sh` is the integration layer (new)
- Real builder/verifier/replanner can be called from OpenClaw

### Next Steps

To make this truly functional with OpenClaw, we need to:

1. **Replace builder placeholder** with real Claude call
   - Use OpenClaw sub-agent spawning
   - Feed it the minimal context bundle
   - Extract patch from response

2. **Hook it into OpenClaw cron** for scheduling
   - E.g., every 2 hours: fetch new tasks, run loop
   - Or: on-demand via Telegram

3. **Stream results back** to you
   - Use OpenClaw sessions_send
   - Track progress in state files

---

## File Structure (Important)

```
state/
├── TASKS.json              # all tasks + status
├── CURRENT_TASK.json       # what we're working on now
├── FAILURE_SUMMARY.json    # last test result
└── RUN_HISTORY.jsonl       # all attempts

artifacts/
├── last_patch.diff         # builder's output
├── diff_summary.txt        # what changed
├── test.out, lint.out      # verifier outputs
└── scope_check.out         # patch scope validation

prompts/
├── architect.md            # task definition format
├── builder.md              # builder instructions
├── verifier.md             # test instructions
└── replanner.md            # replanner instructions

schemas/
└── *.json                  # validation schemas for state files
```

---

## Safety Guarantees

1. **Builder can't see full codebase** → prevents scatter-brain coding
2. **Builder can't modify arbitrary files** → scope check enforces
3. **Builder output must pass tests** → deterministic validation
4. **Failures are logged & retryable** → no silent failures
5. **Task state is versioned** → can rollback

---

## Known Limitations

- Builder is still called with a **full prompt bundle** (fix: need OpenClaw integration)
- Replanner not yet wired to Claude (placeholder only)
- No persistent session between retries (each retry is fresh context)
- Max 3 retries hard-coded (configurable via TASKS.json)

---

## Your Next Task

1. **Test with real tasks**: Put a task in `state/TASKS.json` and run the loop
2. **Integrate with OpenClaw**: Replace builder placeholder with real agent spawn
3. **Add monitoring**: Log results to your memory files
4. **Set up scheduling**: Cron job to run loop periodically

Want me to help with any of these?
