#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract minimal builder context from CURRENT_TASK.json")
    parser.add_argument("--current-task", required=True, help="Path to CURRENT_TASK.json")
    parser.add_argument("--output", required=True, help="Path to output context file")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    args = parser.parse_args()

    current_task_path = Path(args.current_task)
    output_path = Path(args.output)
    repo_root = Path(args.repo_root)

    task = json.loads(current_task_path.read_text(encoding="utf-8"))
    allowed_files = task.get("allowed_files", [])
    forbidden_files = task.get("forbidden_files", [])
    acceptance = task.get("acceptance", [])
    test_commands = task.get("test_commands", [])

    lines = []
    lines.append("===== CURRENT TASK SUMMARY =====")
    lines.append(json.dumps({
        "task_id": task.get("task_id"),
        "title": task.get("title"),
        "description": task.get("description"),
        "allowed_files": allowed_files,
        "forbidden_files": forbidden_files,
        "acceptance": acceptance,
        "test_commands": test_commands,
        "stop_condition": task.get("stop_condition"),
    }, indent=2, ensure_ascii=False))
    lines.append("")

    lines.append("===== REPOSITORY FILE TREE (SHALLOW) =====")
    for p in sorted(repo_root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(repo_root).as_posix()
            if rel.startswith(".git/"):
                continue
            if rel.startswith(("app/", "tests/", "specs/")):
                lines.append(rel)
    lines.append("")

    for file_path in allowed_files:
        path = repo_root / file_path
        lines.append(f"===== FILE: {file_path} =====")
        if path.exists() and path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = "<BINARY_OR_NON_UTF8_FILE>"
        else:
            content = "<FILE_NOT_FOUND>"
        lines.append(content)
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
