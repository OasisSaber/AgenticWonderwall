#!/bin/bash
# AgenticWonderwall workflow update helper.
#
# 在已采用 AgenticWonderwall 工作流的仓库中运行：检查并将工作流模板内容
# 更新到上游最新 Release tag。本脚本与 scripts/aw-update-manifest.txt 一起
# 复制到采用项目（参见 docs/update-guide.md）。
#
# 用法:
#   bash scripts/aw-update.sh <command> [options]
#
# 子命令:
#   check   比较本地 .aw-update/VERSION 与目标 ref（默认上游最新 Release tag）
#   diff    列出本地与目标版本模板文件的差异；keep 文件只报告差异
#   stage   下载目标 ref 到 .aw-update/upstream/<ref>/（供后续 diff/apply）
#   apply   应用 sync 文件更新；默认 --dry-run，--yes 才实际写入
#
# 选项:
#   --repo <url>      上游仓库 URL（默认 https://github.com/OasisSaber/AgenticWonderwall.git）
#   --ref <ref>       Release tag（如 v1.1.0）；联网模式缺省取最新 tag，
#                     --source 模式必填
#   --source <dir>    使用本地目录作为上游（离线；测试与演练用）
#   --manifest <file> manifest 路径；缺省优先取上游 scripts/aw-update-manifest.txt，
#                     其次本地 scripts/aw-update-manifest.txt
#   --dry-run         只打印将要执行的操作，不写入（apply 默认行为）
#   --yes             实际写入（apply）
#   -h, --help        显示帮助
#
# 退出码:
#   check: 0 已是最新; 1 可更新或未记录版本; 2 无法确定; 3 用法错误
#   diff:  0 无差异; 1 有差异; 2 无法确定; 3 用法错误
#   apply: 0 完成（或 dry-run 完成）; 1 存在需要人工处理的项目; 2 无法确定; 3 用法错误
#   stage: 0 成功; 2 无法确定; 3 用法错误
#
# 安全边界:
#   - keep 文件（项目定制文件，见 manifest）永远不被本脚本覆盖；
#   - apply 不删除任何本地文件（上游移除的文件只提示，由人类处理）；
#   - 更新结果必须作为普通变更任务提交（jj change -> 验证 -> PR ->
#     人类 Squash Merge），本脚本不执行 merge、release 或远端修改。

set -o pipefail
set -u

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEFAULT_REPO="https://github.com/OasisSaber/AgenticWonderwall.git"
VERSION_FILE=".aw-update/VERSION"
UPSTREAM_CACHE_DIR=".aw-update/upstream"

usage() {
    sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'
}

# 版本比较：忽略 v 前缀与 pre-release 后缀，按 x.y.z 数值比较。
# 返回：0 = $1 == $2；1 = $1 > $2；2 = $1 < $2
ver_cmp() {
    local a="$1" b="$2"
    a="${a#v}"; b="${b#v}"
    a="${a%%-*}"; b="${b%%-*}"
    while [ -n "$a" ] || [ -n "$b" ]; do
        local pa pb
        pa="${a%%.*}"; pb="${b%%.*}"
        [ -z "$pa" ] && pa=0
        [ -z "$pb" ] && pb=0
        if [ "$pa" -gt "$pb" ]; then
            return 1
        elif [ "$pa" -lt "$pb" ]; then
            return 2
        fi
        if [ "${a#*.}" != "$a" ]; then a="${a#*.}"; else a=""; fi
        if [ "${b#*.}" != "$b" ]; then b="${b#*.}"; else b=""; fi
    done
    return 0
}

# 解析目标 ref：优先 --ref；--source 模式要求 --ref；否则联网查询最新 tag。
# 设置 TARGET_REF。返回 0 成功；2 无法确定；3 用法错误。
resolve_target_ref() {
    if [ -n "$OPT_REF" ]; then
        TARGET_REF="$OPT_REF"
        return 0
    fi
    if [ -n "$OPT_SOURCE" ]; then
        echo "ERROR: --source 模式必须同时指定 --ref。" >&2
        return 3
    fi
    local tags latest t rc
    tags="$(GIT_TERMINAL_PROMPT=0 git ls-remote --tags --refs -- "$OPT_REPO" 'refs/tags/v*' 2>/dev/null | sed 's#.*refs/tags/##')" || true
    if [ -z "$tags" ]; then
        echo "ERROR: 无法查询上游 tag（网络不可用？）。可指定 --ref 或使用 --source 离线目录。" >&2
        return 2
    fi
    latest=""
    while IFS= read -r t; do
        [ -z "$t" ] && continue
        if [ -z "$latest" ]; then
            latest="$t"
            continue
        fi
        ver_cmp "$t" "$latest"
        rc=$?
        [ "$rc" -eq 1 ] && latest="$t"
    done <<< "$tags"
    TARGET_REF="$latest"
    return 0
}

# 获取上游目录：优先 --source；其次已缓存的 .aw-update/upstream/<ref>/；
# 否则联网 clone 到缓存。设置 UPSTREAM_DIR_PATH。
ensure_upstream() {
    if [ -n "$OPT_SOURCE" ]; then
        if [ ! -d "$OPT_SOURCE" ]; then
            echo "ERROR: --source 目录不存在: $OPT_SOURCE" >&2
            return 2
        fi
        UPSTREAM_DIR_PATH="$OPT_SOURCE"
        return 0
    fi
    local cached tmp
    cached="$REPO_DIR/$UPSTREAM_CACHE_DIR/$TARGET_REF"
    if [ -d "$cached" ]; then
        UPSTREAM_DIR_PATH="$cached"
        return 0
    fi
    tmp="$(mktemp -d)" || return 2
    if GIT_TERMINAL_PROMPT=0 git clone --quiet --depth 1 --branch="$TARGET_REF" -- "$OPT_REPO" "$tmp/aw-upstream"; then
        mkdir -p "$(dirname "$cached")"
        rm -rf "$cached"
        mv "$tmp/aw-upstream" "$cached"
        UPSTREAM_DIR_PATH="$cached"
        rm -rf "$tmp"
        return 0
    fi
    rm -rf "$tmp"
    echo "ERROR: 无法从 $OPT_REPO 获取 ref $TARGET_REF（tag 不存在或网络不可用？）。" >&2
    return 2
}

# 解析 manifest 文件：每行 "<keep|sync> <path>"，# 开头为注释，空行忽略。
# 输出 "policy path" 行。
parse_manifest() {
    local file="$1" line policy path
    [ -f "$file" ] || return 1
    while IFS= read -r line || [ -n "$line" ]; do
        line="${line%$'\r'}"          # 容忍 Windows CRLF 行尾
        line="${line%%#*}"
        line="${line#"${line%%[![:space:]]*}"}"
        [ -z "$line" ] && continue
        read -r policy path <<< "$line"   # 分词但不做 glob 展开
        [ -z "$policy" ] && continue
        # 安全校验：拒绝绝对路径与含 .. 组件的条目，防止 apply 越界写入仓库外
        case "$path" in
            /*)
                echo "WARNING: 拒绝绝对路径条目 '$path'（$file）" >&2
                continue
                ;;
        esac
        case "/$path" in
            *"/../"*|*/..)
                echo "WARNING: 拒绝含 .. 组件的条目 '$path'（$file）" >&2
                continue
                ;;
        esac
        case "$policy" in
            keep|sync) echo "$policy $path" ;;
            *) echo "WARNING: manifest 未知策略 '$policy'（$file）" >&2 ;;
        esac
    done < "$file"
}

# 展开 manifest 条目为文件列表（相对 base）。支持目录条目（/ 结尾）与
# 路径最后一段的 * 通配。输出相对路径，每行一个。
expand_entry() {
    local entry="$1" base="$2" dir
    # 纵深防御：拒绝越界条目（正常由 parse_manifest 过滤）
    case "$entry" in
        /*|*".."*)
            echo "WARNING: 拒绝不安全条目 '$entry'" >&2
            return 0
            ;;
    esac
    case "$entry" in
        */)
            (cd "$base" && find "${entry%/}" -type f 2>/dev/null | sort) || true
            ;;
        *\**)
            dir="${entry%/*}"
            [ "$dir" = "$entry" ] && dir="."
            (cd "$base" && find "$dir" -maxdepth 1 -type f -name "${entry##*/}" 2>/dev/null | sed 's#^\./##' | sort) || true
            ;;
        *)
            [ -f "$base/$entry" ] && echo "$entry"
            ;;
    esac
}

# 收集差异：比较 local_root 与 upstream_root 中 manifest 列出的文件。
# 输出 "[状态] policy path" 行；状态为 新增/变更/删除/差异。
collect_diff() {
    local local_root="$1" upstream_root="$2" manifest="$3"
    local policy entry f all_files
    while read -r policy entry; do
        [ -z "$policy" ] && continue
        # 合并上游与本地展开的文件集合，才能检测“上游已删除”的文件
        all_files="$( { expand_entry "$entry" "$upstream_root"; expand_entry "$entry" "$local_root"; } | sort -u )"
        while read -r f; do
            [ -z "$f" ] && continue
            if [ -f "$upstream_root/$f" ]; then
                if [ -f "$local_root/$f" ]; then
                    if ! cmp -s "$local_root/$f" "$upstream_root/$f"; then
                        if [ "$policy" = "keep" ]; then
                            echo "[差异] $policy $f"
                        else
                            echo "[变更] $policy $f"
                        fi
                    fi
                else
                    echo "[新增] $policy $f"
                fi
            elif [ -f "$local_root/$f" ]; then
                echo "[删除] $policy $f"
            fi
        done <<< "$all_files"
    done < <(parse_manifest "$manifest")
}

# 查询本地 manifest 中某路径的策略（keep/sync；目录/通配条目返回空）。
# 用于 apply 时检测上游把 keep 条目降级为 sync 的情况，防止覆盖定制文件。
local_policy() {
    local manifest="$REPO_DIR/scripts/aw-update-manifest.txt" policy entry
    [ -f "$manifest" ] || return 0
    while read -r policy entry; do
        [ -z "$policy" ] && continue
        if [ "$entry" = "$1" ]; then
            echo "$policy"
            return 0
        fi
    done < <(parse_manifest "$manifest")
    return 0
}

cmd_check() {
    local local_ver rc
    resolve_target_ref || return $?
    if [ -f "$REPO_DIR/$VERSION_FILE" ]; then
        local_ver="$(cat "$REPO_DIR/$VERSION_FILE")"
        local_ver="${local_ver%$'\r'}"
    fi
    if [ -z "${local_ver:-}" ]; then
        echo "未记录本地版本（缺少 $VERSION_FILE）。"
        echo "上游目标版本: $TARGET_REF"
        echo "状态: 需要初始化版本记录（运行 apply 或手工写入 $VERSION_FILE）"
        return 1
    fi
    echo "本地版本: $local_ver"
    echo "上游目标: $TARGET_REF"
    ver_cmp "$local_ver" "$TARGET_REF"
    rc=$?
    case "$rc" in
        0)
            echo "状态: 已是最新"
            return 0
            ;;
        2)
            echo "状态: 可更新"
            return 1
            ;;
        *)
            echo "状态: 本地版本高于上游目标（$local_ver > $TARGET_REF），无需更新"
            return 0
            ;;
    esac
}

cmd_diff() {
    local diff_out
    resolve_target_ref || return $?
    ensure_upstream || return $?
    resolve_manifest || return $?
    diff_out="$(collect_diff "$REPO_DIR" "$UPSTREAM_DIR_PATH" "$MANIFEST")"
    if [ -z "$diff_out" ]; then
        echo "目标版本 $TARGET_REF 与本地无差异。"
        return 0
    fi
    echo "目标版本: $TARGET_REF"
    echo "---"
    echo "$diff_out"
    return 1
}

cmd_stage() {
    resolve_target_ref || return $?
    if [ -n "$OPT_SOURCE" ]; then
        echo "提示: --source 模式直接使用本地目录，无需 stage。"
        return 0
    fi
    ensure_upstream || return $?
    echo "已就绪: $UPSTREAM_DIR_PATH"
    return 0
}

# 校验写入目标不越出 REPO_DIR：沿 path 的目录链找最近已存在祖先，解析其
# 物理路径（pwd -P 处理 symlink）并验证仍在 REPO_DIR 内。返回 0 通过。
check_target_within_repo() {
    local path="$1" rel target_dir repo_physical
    rel="$(dirname "$path")"
    while [ -n "$rel" ] && [ "$rel" != "." ] && [ ! -e "$REPO_DIR/$rel" ]; do
        rel="$(dirname "$rel")"
    done
    if [ -z "$rel" ] || [ "$rel" = "." ]; then
        return 0   # 整条路径均为新建，不可能越过 REPO_DIR
    fi
    if [ -d "$REPO_DIR/$rel" ]; then
        target_dir="$(cd "$REPO_DIR" && cd "$rel" 2>/dev/null && pwd -P)" || target_dir=""
        repo_physical="$(cd "$REPO_DIR" && pwd -P 2>/dev/null)" || repo_physical="$REPO_DIR"
        case "$target_dir" in
            "$repo_physical"|"$repo_physical"/*) return 0 ;;
            *)
                echo "ERROR: 拒绝越界目标路径 '$path'" >&2
                return 1
                ;;
        esac
    fi
    # 最近祖先是一个普通文件：路径冲突，交由 mkdir/cp 失败
    return 0
}

cmd_apply() {
    local diff_out status policy path need_action local_pol apply_failed
    resolve_target_ref || return $?
    ensure_upstream || return $?
    resolve_manifest || return $?
    diff_out="$(collect_diff "$REPO_DIR" "$UPSTREAM_DIR_PATH" "$MANIFEST")"
    need_action=0
    apply_failed=0
    if [ "$OPT_YES" -eq 1 ] && [ ! -f "$REPO_DIR/scripts/aw-update-manifest.txt" ]; then
        echo "提示: 本地缺少 scripts/aw-update-manifest.txt，keep 降级保护可能不完整；"
        echo "      建议从上游同步 manifest 后再执行 apply。"
    fi
    if [ -n "$diff_out" ]; then
        while read -r status policy path; do
            case "$policy:$status" in
                sync:*新增*|sync:*变更*)
                    local_pol="$(local_policy "$path")"
                    if [ "$local_pol" = "keep" ]; then
                        echo "提示: 本地 manifest 将 $path 视为 keep 定制文件；上游已改为 sync，"
                        echo "      本脚本不自动覆盖，请人工合并差异。"
                        need_action=1
                    elif [ "$OPT_YES" -eq 1 ]; then
                        # 写入前边界校验（含 symlink 中间组件）
                        if ! check_target_within_repo "$path"; then
                            need_action=1
                            apply_failed=1
                            continue
                        fi
                        mkdir -p "$(dirname "$REPO_DIR/$path")"
                        if cp "$UPSTREAM_DIR_PATH/$path" "$REPO_DIR/$path"; then
                            echo "已更新: $path"
                        else
                            echo "ERROR: 无法更新 $path" >&2
                            need_action=1
                            apply_failed=1
                        fi
                    else
                        echo "[dry-run] 将更新: $path"
                    fi
                    ;;
                sync:*删除*)
                    echo "提示: 上游已移除 $path；本脚本不删除本地文件，请人工确认是否删除。"
                    need_action=1
                    ;;
                keep:*)
                    echo "提示: $path 是定制文件（keep），不会自动覆盖，请人工合并差异。"
                    need_action=1
                    ;;
            esac
        done <<< "$diff_out"
    fi
    if [ "$OPT_YES" -eq 1 ] && [ "$apply_failed" -eq 0 ]; then
        mkdir -p "$REPO_DIR/.aw-update"
        if echo "$TARGET_REF" > "$REPO_DIR/$VERSION_FILE"; then
            echo "版本记录已更新: $VERSION_FILE = $TARGET_REF"
        else
            echo "ERROR: 无法写入 $VERSION_FILE" >&2
            need_action=1
        fi
    elif [ "$OPT_YES" -eq 1 ]; then
        echo "警告: 存在未完成的更新，版本记录未推进（$VERSION_FILE 保持原值）。"
        need_action=1
    else
        echo "[dry-run] 将更新版本记录: $VERSION_FILE = $TARGET_REF（--yes 时写入）"
    fi
    echo ""
    echo "更新后请运行验证入口（如 bash scripts/check.sh），并将本次更新作为变更任务提交"
    echo "（jj change -> 验证 -> Pull Request -> 人类 Squash Merge）。"
    return "$need_action"
}

# resolve_manifest：设置 MANIFEST。
resolve_manifest() {
    if [ -n "$OPT_MANIFEST" ]; then
        MANIFEST="$OPT_MANIFEST"
    elif [ -n "${UPSTREAM_DIR_PATH:-}" ] && [ -f "$UPSTREAM_DIR_PATH/scripts/aw-update-manifest.txt" ]; then
        MANIFEST="$UPSTREAM_DIR_PATH/scripts/aw-update-manifest.txt"
    else
        MANIFEST="$REPO_DIR/scripts/aw-update-manifest.txt"
    fi
    if [ ! -f "$MANIFEST" ]; then
        echo "ERROR: manifest 不存在: $MANIFEST" >&2
        return 2
    fi
    return 0
}

# ---- 入口 ----
OPT_REPO="$DEFAULT_REPO"
OPT_REF=""
OPT_SOURCE=""
OPT_MANIFEST=""
OPT_YES=0

CMD="${1:-}"
shift 2>/dev/null || true

case "$CMD" in
    check|diff|stage|apply) ;;
    -h|--help|"")
        usage
        exit 0
        ;;
    *)
        echo "ERROR: 未知子命令 '$CMD'。" >&2
        usage
        exit 3
        ;;
esac

while [ "$#" -gt 0 ]; do
    case "$1" in
        --repo) OPT_REPO="${2:-}"; shift 2 ;;
        --ref) OPT_REF="${2:-}"; shift 2 ;;
        --source) OPT_SOURCE="${2:-}"; shift 2 ;;
        --manifest) OPT_MANIFEST="${2:-}"; shift 2 ;;
        --dry-run) OPT_YES=0; shift ;;
        --yes) OPT_YES=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *)
            echo "ERROR: 未知选项 '$1'。" >&2
            usage
            exit 3
            ;;
    esac
done

if [ -z "${OPT_REPO:-}" ] || [ -z "$OPT_REPO" ]; then
    echo "ERROR: --repo 不能为空。" >&2
    exit 3
fi

cmd_$CMD
exit $?
