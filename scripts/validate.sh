#!/bin/bash
# Technical validation for TheMasterplan.
#
# Verifies exactly four checks:
#   1. Internal Markdown links and anchors
#   2. Committed mode of Shell scripts
#   3. YAML syntax
#   4. Shell syntax

set -o pipefail

FAILED=0
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR" || exit 1

if ! command -v git >/dev/null 2>&1; then
    echo "ERROR: Git is required for technical validation." >&2
    exit 1
fi
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "ERROR: technical validation must run inside a Git worktree." >&2
    exit 1
fi

SHELL_FILES="$(mktemp)" || exit 1
trap 'rm -f "$SHELL_FILES"' EXIT
if ! git ls-files -z -- '*.sh' >"$SHELL_FILES"; then
    echo "ERROR: unable to enumerate tracked Shell scripts." >&2
    exit 1
fi

PYTHON=""
if python3 -c "import sys" >/dev/null 2>&1; then
    PYTHON="python3"
elif python -c "import sys" >/dev/null 2>&1; then
    PYTHON="python"
fi

echo "=== Validation ==="
echo ""

# ---- Check 1: Internal Markdown links and anchors ----
echo "--- Check 1: Internal Markdown links and anchors ---"
if [ -z "$PYTHON" ]; then
    echo "  UNAVAILABLE: Python is required for Markdown link validation."
    FAILED=$((FAILED + 1))
elif "$PYTHON" scripts/validate_markdown_links.py "$REPO_DIR"; then
    :
else
    FAILED=$((FAILED + 1))
fi
echo ""

# ---- Check 2: Committed Shell script modes ----
echo "--- Check 2: Committed Shell script modes ---"
MODE_ERRORS=0
CHECK_REV="HEAD"

if command -v jj >/dev/null 2>&1; then
    jj_revision=$(jj log -r @ --no-graph -T 'commit_id' 2>/dev/null || true)
    if [ -n "$jj_revision" ] && git cat-file -e "${jj_revision}^{commit}" 2>/dev/null; then
        CHECK_REV="$jj_revision"
    fi
fi

while IFS= read -r -d '' shell_file; do
    shell_file=${shell_file#./}
    # 发布模板（distribution/templates/）不是仓库执行脚本：mode 由生成侧
    # 消费项目决定，不要求本仓库以 100755 提交。
    case "$shell_file" in
        distribution/templates/*) continue ;;
    esac
    mode=$(git ls-tree "$CHECK_REV" -- "$shell_file" 2>/dev/null | awk '{print $1}')
    if [ -z "$mode" ]; then
        echo "  NOT TRACKED: $shell_file (revision $CHECK_REV)"
        MODE_ERRORS=$((MODE_ERRORS + 1))
    elif [ "$mode" != "100755" ]; then
        echo "  NOT EXECUTABLE: $shell_file (mode $mode, expected 100755)"
        MODE_ERRORS=$((MODE_ERRORS + 1))
    fi
done <"$SHELL_FILES"

if [ "$MODE_ERRORS" -eq 0 ]; then
    echo "  All Shell scripts are committed as 100755."
else
    echo "  $MODE_ERRORS Shell script mode error(s)."
    FAILED=$((FAILED + 1))
fi
echo ""

# ---- Check 3: YAML syntax ----
echo "--- Check 3: YAML syntax ---"
YAML_ERRORS=0

if [ -z "$PYTHON" ] || ! "$PYTHON" -c "import yaml" 2>/dev/null; then
    echo "  UNAVAILABLE: Python with PyYAML is required."
    YAML_ERRORS=$((YAML_ERRORS + 1))
else
    while IFS= read -r -d '' yaml_file; do
        if ! "$PYTHON" -c 'import pathlib, sys, yaml; yaml.safe_load(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))' "$yaml_file" 2>/dev/null; then
            echo "  YAML ERROR: $yaml_file"
            YAML_ERRORS=$((YAML_ERRORS + 1))
        fi
    done < <(find . -type d \( -name '.git' -o -name '.jj' -o -name 'node_modules' -o -name '.venv' -o -name 'venv' -o -name '.cache' -o -name '__pycache__' \) -prune -o -type f \( -name '*.yml' -o -name '*.yaml' \) -print0)
    while IFS= read -r -d '' skill_file; do
        if ! "$PYTHON" -c 'import pathlib, sys, yaml
lines = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
if not lines or lines[0] != "---":
    raise SystemExit(1)
end = next((i for i, line in enumerate(lines[1:], 1) if line == "---"), None)
if end is None:
    raise SystemExit(1)
yaml.safe_load("\n".join(lines[1:end]))' "$skill_file" 2>/dev/null; then
            echo "  YAML ERROR: $skill_file (frontmatter)"
            YAML_ERRORS=$((YAML_ERRORS + 1))
        fi
    done < <(find . -type d \( -name '.git' -o -name '.jj' -o -name 'node_modules' -o -name '.venv' -o -name 'venv' -o -name '.cache' -o -name '__pycache__' \) -prune -o -type f -name 'SKILL.md' -print0)
fi

if [ "$YAML_ERRORS" -eq 0 ]; then
    echo "  All YAML files parse correctly."
else
    echo "  $YAML_ERRORS YAML validation error(s)."
    FAILED=$((FAILED + 1))
fi
echo ""

# ---- Check 4: Shell syntax ----
echo "--- Check 4: Shell syntax ---"
SHELL_ERRORS=0

while IFS= read -r -d '' shell_file; do
    if ! bash -n "$shell_file"; then
        echo "  SHELL SYNTAX ERROR: $shell_file"
        SHELL_ERRORS=$((SHELL_ERRORS + 1))
    fi
done <"$SHELL_FILES"

if [ "$SHELL_ERRORS" -eq 0 ]; then
    echo "  All Shell scripts pass syntax validation."
else
    echo "  $SHELL_ERRORS Shell syntax error(s)."
    FAILED=$((FAILED + 1))
fi
echo ""

echo "=== Results ==="
if [ "$FAILED" -eq 0 ]; then
    echo "All four technical checks passed."
else
    echo "$FAILED technical check(s) failed."
fi
exit "$FAILED"
