#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import List, Set


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_patch_path(path: str) -> str:
    path = path.strip()
    if path.startswith("a/") or path.startswith("b/"):
        path = path[2:]
    return path


def extract_changed_files_from_patch(patch_text: str) -> List[str]:
    changed: List[str] = []
    seen: Set[str] = set()
    plus_plus_pattern = re.compile(r"^\+\+\+\s+(.+)$", re.MULTILINE)

    for match in plus_plus_pattern.finditer(patch_text):
        raw = match.group(1).strip()
        if raw == "/dev/null":
            continue
        path = normalize_patch_path(raw)
        if path not in seen:
            seen.add(path)
            changed.append(path)

    if not changed:
        diff_git_pattern = re.compile(r"^diff --git a/(.+?) b/(.+)$", re.MULTILINE)
        for match in diff_git_pattern.finditer(patch_text):
            path = match.group(2).strip()
            path = normalize_patch_path(path)
            if path not in seen:
                seen.add(path)
                changed.append(path)

    return changed


def is_path_allowed(path: str, allowed_patterns: List[str]) -> bool:
    for pattern in allowed_patterns:
        pattern = pattern.strip()
        if pattern.endswith("/**"):
            prefix = pattern[:-3]
            if path == prefix or path.startswith(prefix + "/"):
                return True
        if fnmatch.fnmatch(path, pattern):
            return True
        if path == pattern:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether patch only touches allowed files")
    parser.add_argument("--patch", required=True, help="Path to unified diff patch")
    parser.add_argument("--current-task", required=True, help="Path to CURRENT_TASK.json")
    args = parser.parse_args()

    patch_path = Path(args.patch)
    current_task_path = Path(args.current_task)

    if not patch_path.exists():
        print(f"ERROR: patch file not found: {patch_path}", file=sys.stderr)
        return 1
    if not current_task_path.exists():
        print(f"ERROR: current task file not found: {current_task_path}", file=sys.stderr)
        return 1

    patch_text = patch_path.read_text(encoding="utf-8")
    current_task = read_json(current_task_path)

    allowed_files = current_task.get("allowed_files", [])
    if not isinstance(allowed_files, list) or not allowed_files:
        print("ERROR: CURRENT_TASK.json has no allowed_files", file=sys.stderr)
        return 1

    changed_files = extract_changed_files_from_patch(patch_text)

    if not changed_files:
        print("ERROR: No changed files detected in patch", file=sys.stderr)
        return 2

    violations = [p for p in changed_files if not is_path_allowed(p, allowed_files)]

    if len(changed_files) > len(allowed_files):
        print("PATCH_SCOPE_VIOLATION")
        print("Changed files:")
        for p in changed_files:
            print(f"  - {p}")
        print("Violations:")
        for p in violations or ["Patch touches more files than allowed task scope"]:
            print(f"  - {p}")
        return 4

    if violations:
        print("PATCH_SCOPE_VIOLATION")
        print("Changed files:")
        for p in changed_files:
            print(f"  - {p}")
        print("Violations:")
        for p in violations:
            print(f"  - {p}")
        return 3

    print("PATCH_SCOPE_OK")
    for p in changed_files:
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
