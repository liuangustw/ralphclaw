#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import jsonschema
except ImportError:
    jsonschema = None

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / "state"
SCHEMA_DIR = ROOT / "schemas"

TASKS_PATH = STATE_DIR / "TASKS.json"
CURRENT_TASK_PATH = STATE_DIR / "CURRENT_TASK.json"
FAILURE_SUMMARY_PATH = STATE_DIR / "FAILURE_SUMMARY.json"
RUN_HISTORY_PATH = STATE_DIR / "RUN_HISTORY.jsonl"
REPLAN_PROPOSAL_PATH = STATE_DIR / "REPLAN_PROPOSAL.json"

TASKS_SCHEMA_PATH = SCHEMA_DIR / "TASKS.schema.json"
CURRENT_TASK_SCHEMA_PATH = SCHEMA_DIR / "CURRENT_TASK.schema.json"
FAILURE_SUMMARY_SCHEMA_PATH = SCHEMA_DIR / "FAILURE_SUMMARY.schema.json"
REPLAN_PROPOSAL_SCHEMA_PATH = SCHEMA_DIR / "REPLAN_PROPOSAL.schema.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Optional[Any] = None) -> Any:
    if not path.exists():
        if default is not None:
            return deepcopy(default)
        raise FileNotFoundError(f"Missing required file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_event(node: str, result: str, task_id: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> None:
    payload: Dict[str, Any] = {
        "timestamp": utc_now_iso(),
        "node": node,
        "task_id": task_id,
        "result": result,
    }
    if extra:
        payload.update(extra)
    append_jsonl(RUN_HISTORY_PATH, payload)


def load_schema(schema_path: Path) -> Optional[Dict[str, Any]]:
    if not schema_path.exists():
        return None
    return read_json(schema_path)


def validate_with_schema(data: Any, schema_path: Path, label: str) -> None:
    if jsonschema is None:
        return
    schema = load_schema(schema_path)
    if schema is None:
        return
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        raise ValueError(f"{label} failed schema validation: {e.message}") from e


def validate_tasks_state(data: Dict[str, Any]) -> None:
    validate_with_schema(data, TASKS_SCHEMA_PATH, "TASKS.json")


def validate_current_task(data: Dict[str, Any]) -> None:
    if data:
        validate_with_schema(data, CURRENT_TASK_SCHEMA_PATH, "CURRENT_TASK.json")


def validate_failure_summary(data: Dict[str, Any]) -> None:
    if data:
        validate_with_schema(data, FAILURE_SUMMARY_SCHEMA_PATH, "FAILURE_SUMMARY.json")


def validate_replan_proposal(data: Dict[str, Any]) -> None:
    if data:
        validate_with_schema(data, REPLAN_PROPOSAL_SCHEMA_PATH, "REPLAN_PROPOSAL.json")


def load_tasks_state() -> Dict[str, Any]:
    data = read_json(TASKS_PATH)
    if not isinstance(data, dict):
        raise ValueError("TASKS.json must be a JSON object")
    if "tasks" not in data or not isinstance(data["tasks"], list):
        raise ValueError("TASKS.json must contain a top-level 'tasks' array")
    validate_tasks_state(data)
    return data


def save_tasks_state(data: Dict[str, Any]) -> None:
    meta = data.setdefault("meta", {})
    meta["updated_at"] = utc_now_iso()
    validate_tasks_state(data)
    write_json(TASKS_PATH, data)


def load_current_task() -> Dict[str, Any]:
    data = read_json(CURRENT_TASK_PATH, default={})
    validate_current_task(data)
    return data


def save_current_task(data: Dict[str, Any]) -> None:
    validate_current_task(data)
    write_json(CURRENT_TASK_PATH, data)


def load_failure_summary() -> Dict[str, Any]:
    data = read_json(FAILURE_SUMMARY_PATH, default={})
    validate_failure_summary(data)
    return data


def save_failure_summary(data: Dict[str, Any]) -> None:
    validate_failure_summary(data)
    write_json(FAILURE_SUMMARY_PATH, data)


def load_replan_proposal() -> Dict[str, Any]:
    data = read_json(REPLAN_PROPOSAL_PATH, default={})
    validate_replan_proposal(data)
    return data


def save_replan_proposal(data: Dict[str, Any]) -> None:
    validate_replan_proposal(data)
    write_json(REPLAN_PROPOSAL_PATH, data)


def get_task_by_id(tasks_data: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    for task in tasks_data["tasks"]:
        if task.get("id") == task_id:
            return task
    raise ValueError(f"Task not found: {task_id}")


def find_task_index(tasks_data: Dict[str, Any], task_id: str) -> int:
    for i, task in enumerate(tasks_data["tasks"]):
        if task.get("id") == task_id:
            return i
    raise ValueError(f"Task not found: {task_id}")


def task_is_done(tasks_data: Dict[str, Any], task_id: str) -> bool:
    return get_task_by_id(tasks_data, task_id).get("status") == "done"


def dependencies_satisfied(tasks_data: Dict[str, Any], task: Dict[str, Any]) -> bool:
    return all(task_is_done(tasks_data, dep_id) for dep_id in task.get("depends_on", []))


def task_is_selectable(tasks_data: Dict[str, Any], task: Dict[str, Any]) -> bool:
    return task.get("status") in {"pending", "ready"} and dependencies_satisfied(tasks_data, task)


def build_current_task_payload(task: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task_id": task["id"],
        "title": task["title"],
        "description": task["description"],
        "allowed_files": task.get("allowed_files", []),
        "forbidden_files": task.get("forbidden_files", []),
        "acceptance": task.get("acceptance", []),
        "test_commands": task.get("test_commands", []),
        "retry_count": int(task.get("retry_count", 0)),
        "max_retries": int(task.get("max_retries", 3)),
        "stop_condition": "Pass all required acceptance checks without editing forbidden files."
    }


def normalize_root_cause(value: Optional[str]) -> str:
    if not value:
        return ""
    return " ".join(value.strip().lower().split())


def same_root_cause_repeated(task: Dict[str, Any], threshold: int = 3) -> Tuple[bool, str]:
    failure_summary = load_failure_summary()
    current_root = normalize_root_cause(
        failure_summary.get("root_cause_guess") or failure_summary.get("failure_type")
    )
    if not current_root:
        return False, ""
    recent = task.get("failure_history", [])
    count = 0
    for item in reversed(recent):
        past = normalize_root_cause(item.get("root_cause_guess") or item.get("summary"))
        if past == current_root:
            count += 1
        else:
            break
    return count >= (threshold - 1), current_root


def should_escalate(task: Dict[str, Any], failure_summary: Dict[str, Any]) -> Tuple[bool, str]:
    if failure_summary.get("status") == "ESCALATE":
        return True, "verifier_explicit_escalate"
    if failure_summary.get("out_of_scope_edits"):
        return True, "scope_violation"
    if failure_summary.get("failure_type") == "spec_conflict":
        return True, "spec_conflict"
    if int(task.get("retry_count", 0)) >= int(task.get("max_retries", 3)):
        return True, "retry_limit_reached"
    repeated, root = same_root_cause_repeated(task, threshold=3)
    if repeated:
        return True, f"same_root_cause_repeated:{root}"
    return False, ""


def next_task_id(tasks_data: Dict[str, Any]) -> str:
    max_num = 0
    for task in tasks_data["tasks"]:
        tid = task.get("id", "")
        if tid.startswith("task_"):
            try:
                max_num = max(max_num, int(tid.split("_")[1]))
            except ValueError:
                pass
    return f"task_{max_num + 1:03d}"


def proposal_task_to_task(
    proposal_task: Dict[str, Any],
    new_task_id: str,
    parent_task: Dict[str, Any],
    depends_on: Optional[List[str]] = None
) -> Dict[str, Any]:
    return {
        "id": new_task_id,
        "title": proposal_task["title"],
        "description": proposal_task["description"],
        "status": "pending",
        "priority": int(parent_task.get("priority", 100)),
        "depends_on": depends_on or list(parent_task.get("depends_on", [])),
        "allowed_files": list(proposal_task.get("allowed_files", [])),
        "forbidden_files": list(proposal_task.get("forbidden_files", [])),
        "acceptance": list(proposal_task.get("acceptance", [])),
        "test_commands": list(proposal_task.get("test_commands", [])),
        "rollback_hint": parent_task.get("rollback_hint", ""),
        "notes": proposal_task.get("notes", f"Generated from proposal for {parent_task.get('id')}"),
        "retry_count": 0,
        "max_retries": int(proposal_task.get("max_retries", parent_task.get("max_retries", 3))),
        "last_failure_reason": None,
        "failure_history": [],
        "output_artifacts": list(parent_task.get("output_artifacts", []))
    }


def select_next_ready_task() -> int:
    tasks_data = load_tasks_state()
    selectable = [task for task in tasks_data["tasks"] if task_is_selectable(tasks_data, task)]
    if not selectable:
        log_event(node="update_state", result="no_selectable_task")
        print("null")
        return 0
    selectable.sort(key=lambda t: (t.get("priority", 100), t.get("id", "")))
    selected = selectable[0]
    if selected.get("status") == "pending":
        selected["status"] = "ready"
    current_task = build_current_task_payload(selected)
    save_current_task(current_task)
    save_tasks_state(tasks_data)
    log_event(node="update_state", result="selected_task", task_id=selected["id"], extra={"title": selected.get("title")})
    print(json.dumps(current_task, indent=2, ensure_ascii=False))
    return 0


def increment_retry_count(task_id: Optional[str] = None) -> int:
    tasks_data = load_tasks_state()
    failure_summary = load_failure_summary()
    if task_id is None:
        task_id = failure_summary.get("task_id")
    if not task_id:
        raise ValueError("No task_id provided and none found in FAILURE_SUMMARY.json")
    task = get_task_by_id(tasks_data, task_id)
    escalate, reason = should_escalate(task, failure_summary)
    summary = failure_summary.get("root_cause_guess") or failure_summary.get("failure_type") or "unknown failure"
    failure_history = task.setdefault("failure_history", [])
    failure_history.append({
        "timestamp": utc_now_iso(),
        "failure_type": failure_summary.get("failure_type", "unknown"),
        "summary": summary,
        "root_cause_guess": failure_summary.get("root_cause_guess", "")
    })
    if escalate:
        task["status"] = "blocked"
        task["last_failure_reason"] = f"ESCALATE: {summary}"
        save_tasks_state(tasks_data)
        log_event(node="update_state", result="auto_escalated", task_id=task_id, extra={"reason": reason})
        print("ESCALATE")
        return 0
    task["retry_count"] = int(task.get("retry_count", 0)) + 1
    task["status"] = "in_progress"
    task["last_failure_reason"] = summary
    save_tasks_state(tasks_data)
    log_event(node="update_state", result="incremented_retry_count", task_id=task_id, extra={"retry_count": task["retry_count"]})
    print(task["retry_count"])
    return 0


def mark_task_done(task_id: Optional[str] = None) -> int:
    tasks_data = load_tasks_state()
    if task_id is None:
        current_task = load_current_task()
        task_id = current_task.get("task_id")
    if not task_id:
        raise ValueError("No task_id provided and none found in CURRENT_TASK.json")
    task = get_task_by_id(tasks_data, task_id)
    task["status"] = "done"
    task["last_failure_reason"] = None
    save_tasks_state(tasks_data)
    save_current_task({})
    save_failure_summary({})
    log_event(node="update_state", result="marked_task_done", task_id=task_id)
    print(task_id)
    return 0


def remaining_tasks_count() -> int:
    tasks_data = load_tasks_state()
    remaining = sum(1 for task in tasks_data["tasks"] if task.get("status") not in {"done", "cancelled"})
    log_event(node="update_state", result="remaining_tasks_count", extra={"count": remaining})
    print(remaining)
    return 0


def set_task_failed(task_id: Optional[str] = None) -> int:
    tasks_data = load_tasks_state()
    failure_summary = load_failure_summary()
    if task_id is None:
        task_id = failure_summary.get("task_id")
    if not task_id:
        raise ValueError("No task_id provided and none found in FAILURE_SUMMARY.json")
    task = get_task_by_id(tasks_data, task_id)
    task["status"] = "failed"
    summary = failure_summary.get("root_cause_guess") or failure_summary.get("failure_type") or "unknown failure"
    task["last_failure_reason"] = summary
    task.setdefault("failure_history", []).append({
        "timestamp": utc_now_iso(),
        "failure_type": failure_summary.get("failure_type", "unknown"),
        "summary": summary,
        "root_cause_guess": failure_summary.get("root_cause_guess", "")
    })
    save_tasks_state(tasks_data)
    log_event(node="update_state", result="set_task_failed", task_id=task_id)
    print(task_id)
    return 0


def show_current_task() -> int:
    print(json.dumps(load_current_task(), indent=2, ensure_ascii=False))
    return 0


def validate_all() -> int:
    validate_tasks_state(load_tasks_state())
    validate_current_task(load_current_task())
    validate_failure_summary(load_failure_summary())
    validate_replan_proposal(load_replan_proposal())
    print("OK")
    return 0


def apply_replan_proposal(proposal_path: Optional[Path] = None) -> int:
    tasks_data = load_tasks_state()
    proposal = read_json(proposal_path or REPLAN_PROPOSAL_PATH, default={})
    validate_replan_proposal(proposal)
    parent_task_id = proposal.get("parent_task_id")
    if not parent_task_id:
        raise ValueError("Replan proposal missing parent_task_id")
    parent_idx = find_task_index(tasks_data, parent_task_id)
    parent_task = tasks_data["tasks"][parent_idx]
    replacement_tasks = proposal.get("replacement_tasks", [])
    if not replacement_tasks:
        raise ValueError("Replan proposal must contain at least one replacement task")
    parent_task["status"] = "blocked"
    parent_task["last_failure_reason"] = f"replanned via proposal: {proposal.get('reason', '')}"

    created_ids: List[str] = []
    prev_task_id: Optional[str] = None
    for repl in replacement_tasks:
        new_id = next_task_id({"tasks": tasks_data["tasks"] + [{"id": x} for x in created_ids]})
        depends_on = [prev_task_id] if prev_task_id else list(parent_task.get("depends_on", []))
        new_task = proposal_task_to_task(repl, new_id, parent_task, depends_on)
        tasks_data["tasks"].append(new_task)
        created_ids.append(new_id)
        prev_task_id = new_id

    save_tasks_state(tasks_data)
    first_new_task = get_task_by_id(tasks_data, created_ids[0])
    save_current_task(build_current_task_payload(first_new_task))
    log_event(node="update_state", result="applied_replan_proposal", task_id=parent_task_id, extra={"strategy": proposal.get("strategy"), "created_tasks": created_ids})
    print(json.dumps({
        "parent_task_id": parent_task_id,
        "created_tasks": created_ids,
        "strategy": proposal.get("strategy"),
        "reason": proposal.get("reason")
    }, indent=2, ensure_ascii=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ralph-Claw state updater")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("select_next_ready_task")
    subparsers.add_parser("remaining_tasks_count")
    subparsers.add_parser("show_current_task")
    subparsers.add_parser("validate_all")
    subparsers.add_parser("apply_replan_proposal")

    for name in ("mark_task_done", "increment_retry_count", "set_task_failed"):
        p = subparsers.add_parser(name)
        p.add_argument("--task-id", dest="task_id")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "select_next_ready_task":
            return select_next_ready_task()
        if args.command == "remaining_tasks_count":
            return remaining_tasks_count()
        if args.command == "show_current_task":
            return show_current_task()
        if args.command == "validate_all":
            return validate_all()
        if args.command == "mark_task_done":
            return mark_task_done(task_id=args.task_id)
        if args.command == "increment_retry_count":
            return increment_retry_count(task_id=args.task_id)
        if args.command == "set_task_failed":
            return set_task_failed(task_id=args.task_id)
        if args.command == "apply_replan_proposal":
            return apply_replan_proposal()
        raise ValueError(f"Unknown command: {args.command}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
