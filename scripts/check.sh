#!/bin/bash
# Authoritative repository validation entrypoint for AgenticWonderwall.

set -o pipefail

FAILED=0
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR" || exit 1

PYTHON=""
if python3 -c "import sys" >/dev/null 2>&1; then
    PYTHON="python3"
elif python -c "import sys" >/dev/null 2>&1; then
    PYTHON="python"
fi

echo "=== Repository check ==="
echo ""

echo "--- Check 1: Python syntax ---"
PYTHON_ERRORS=0
if [ -z "$PYTHON" ]; then
    echo "  UNAVAILABLE: Python is required."
    PYTHON_ERRORS=$((PYTHON_ERRORS + 1))
else
    while IFS= read -r -d '' python_file; do
        if ! "$PYTHON" - "$python_file" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
except SyntaxError as error:
    print(
        f"  PYTHON SYNTAX ERROR: {path}:{error.lineno}: {error.msg}",
        file=sys.stderr,
    )
    raise SystemExit(1)
PY
        then
            PYTHON_ERRORS=$((PYTHON_ERRORS + 1))
        fi
    done < <(git ls-files -z -- 'scripts/*.py')
fi

if [ "$PYTHON_ERRORS" -eq 0 ]; then
    echo "  All tracked Python validation scripts compile."
else
    echo "  $PYTHON_ERRORS Python syntax error(s)."
    FAILED=$((FAILED + 1))
fi
echo ""

echo "--- Check 2: Validation unit tests ---"
if [ -z "$PYTHON" ]; then
    echo "  UNAVAILABLE: Python is required."
    FAILED=$((FAILED + 1))
elif "$PYTHON" -m unittest discover -s scripts -p 'test_*.py'; then
    echo "  Validation unit tests passed."
else
    echo "  Validation unit tests failed."
    FAILED=$((FAILED + 1))
fi
echo ""

echo "--- Check 3: Technical validation ---"
if bash scripts/validate.sh; then
    echo "  Technical validation passed."
else
    echo "  Technical validation failed."
    FAILED=$((FAILED + 1))
fi
echo ""

echo "=== Repository check results ==="
if [ "$FAILED" -eq 0 ]; then
    echo "All repository checks passed."
else
    echo "$FAILED repository check category or categories failed."
fi
exit "$FAILED"
