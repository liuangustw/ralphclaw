#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts

: > artifacts/test.out
: > artifacts/lint.out
: > artifacts/build.out
: > artifacts/runtime.out

if command -v pytest >/dev/null 2>&1; then
  pytest tests/test_text_utils.py -q > artifacts/test.out 2>&1 || true
else
  echo "pytest not found" > artifacts/test.out
fi

echo "lint not configured" > artifacts/lint.out
echo "build not configured" > artifacts/build.out
echo "runtime checks not configured" > artifacts/runtime.out
