#!/usr/bin/env bash
# worktree-resolve.sh — enumerate git worktrees and resolve a switch target.
#
# The actual "switch" (moving Cursor's workspace) happens through the
# cursor-app-control MCP tool and cannot be scripted. This script owns the
# deterministic, testable part: listing worktrees and resolving a user-provided
# query (directory name, branch name, or path) to a single canonical target,
# normalizing symlinked paths so "already at target" is detected reliably.
#
# Usage:
#   worktree-resolve.sh [--repo <path>] [--query <name|branch|path>] [--current <path>]
#
# Options:
#   --repo <path>      Repository directory to inspect (git -C). Default: cwd.
#   --query <value>    Target to resolve. Matched, in order, against:
#                        1. worktree directory basename (exact)
#                        2. branch name (exact)
#                        3. full path (exact, symlink-normalized)
#                        4. directory basename (prefix)
#                      If omitted, only the worktree listing is printed.
#   --current <path>   The active workspace path, used to compute
#                      ALREADY_AT_TARGET and mark [current] in the listing.
#   -h, --help         Print usage and exit 0.
#
# Output:
#   Always prints one WT line per worktree (tab-separated fields):
#     WT<TAB><path><TAB><head-sha><TAB><branch-or-"(detached)"><TAB><is_main><TAB><is_current>
#   When --query is given, additionally prints one of:
#     Resolved:
#       STATUS=resolved
#       TARGET_PATH=<canonical absolute path>
#       TARGET_BRANCH=<branch or "(detached)">
#       TARGET_NAME=<basename>
#       IS_MAIN=true|false
#       ALREADY_AT_TARGET=true|false
#     Not found:
#       STATUS=not_found
#       QUERY=<value>
#
# Exit codes:
#   0  worktrees listed (and target resolved if a query was given)
#   1  query given but no matching worktree
#   2  usage error / not a git repository

set -uo pipefail

REPO_DIR="."
QUERY=""
CURRENT=""
HAS_QUERY=false

usage() { sed -n '2,44p' "$0" | sed 's/^# \{0,1\}//'; }

ARG_ERR=""
while [ $# -gt 0 ]; do
    case "$1" in
        --repo)    REPO_DIR="${2:-}"; shift 2 || { ARG_ERR="--repo requires a value"; break; } ;;
        --query)   QUERY="${2:-}"; HAS_QUERY=true; shift 2 || { ARG_ERR="--query requires a value"; break; } ;;
        --current) CURRENT="${2:-}"; shift 2 || { ARG_ERR="--current requires a value"; break; } ;;
        -h|--help) usage; exit 0 ;;
        *)         ARG_ERR="unknown argument: $1"; break ;;
    esac
done

if [ -n "$ARG_ERR" ]; then
    echo "STATUS=error"; echo "ERROR_CODE=BAD_USAGE"; echo "ERROR=${ARG_ERR}"; exit 2
fi

if ! git -C "$REPO_DIR" rev-parse --git-dir > /dev/null 2>&1; then
    echo "STATUS=error"; echo "ERROR_CODE=NOT_A_REPO"; echo "ERROR='${REPO_DIR}' is not a git repository"; exit 2
fi

# realpath fallback for portability (macOS lacks GNU realpath by default in some setups).
canon() {
    local p="$1"
    if [ -e "$p" ]; then
        ( cd "$p" 2>/dev/null && pwd -P ) || echo "$p"
    else
        echo "$p"
    fi
}

CURRENT_CANON=""
[ -n "$CURRENT" ] && CURRENT_CANON="$(canon "$CURRENT")"

# Parse `git worktree list --porcelain` into parallel arrays.
paths=(); heads=(); branches=()
cur_path=""; cur_head=""; cur_branch=""
flush() {
    [ -z "$cur_path" ] && return
    paths+=("$cur_path"); heads+=("$cur_head"); branches+=("$cur_branch")
    cur_path=""; cur_head=""; cur_branch=""
}
while IFS= read -r line; do
    case "$line" in
        "worktree "*) flush; cur_path="${line#worktree }" ;;
        "HEAD "*)     cur_head="${line#HEAD }" ;;
        "branch "*)   cur_branch="${line#branch refs/heads/}" ;;
        "detached")   cur_branch="(detached)" ;;
        "")           flush ;;
    esac
done < <(git -C "$REPO_DIR" worktree list --porcelain)
flush

# The first entry from git worktree list is always the main working tree.
main_path="${paths[0]:-}"
main_canon="$(canon "$main_path")"

# Emit the listing.
for i in "${!paths[@]}"; do
    p="${paths[$i]}"; h="${heads[$i]:0:12}"; b="${branches[$i]:-(detached)}"
    pc="$(canon "$p")"
    is_main=false; [ "$pc" = "$main_canon" ] && is_main=true
    is_current=false; [ -n "$CURRENT_CANON" ] && [ "$pc" = "$CURRENT_CANON" ] && is_current=true
    printf 'WT\t%s\t%s\t%s\t%s\t%s\n' "$p" "$h" "$b" "$is_main" "$is_current"
done

[ "$HAS_QUERY" = false ] && exit 0

# Resolve the query. Track match index; -1 = none.
match=-1

# Pass 1: exact basename
for i in "${!paths[@]}"; do
    [ "$(basename "${paths[$i]}")" = "$QUERY" ] && { match=$i; break; }
done
# Pass 2: exact branch
if [ "$match" -eq -1 ]; then
    for i in "${!paths[@]}"; do
        [ "${branches[$i]}" = "$QUERY" ] && { match=$i; break; }
    done
fi
# Pass 3: exact path (symlink-normalized)
if [ "$match" -eq -1 ]; then
    q_canon="$(canon "$QUERY")"
    for i in "${!paths[@]}"; do
        [ "$(canon "${paths[$i]}")" = "$q_canon" ] && { match=$i; break; }
    done
fi
# Pass 4: basename prefix
if [ "$match" -eq -1 ]; then
    for i in "${!paths[@]}"; do
        case "$(basename "${paths[$i]}")" in "$QUERY"*) match=$i; break ;; esac
    done
fi

if [ "$match" -eq -1 ]; then
    echo "STATUS=not_found"
    echo "QUERY=${QUERY}"
    exit 1
fi

t_path="${paths[$match]}"
t_canon="$(canon "$t_path")"
t_branch="${branches[$match]:-(detached)}"
t_name="$(basename "$t_path")"
is_main=false; [ "$t_canon" = "$main_canon" ] && is_main=true
already=false; [ -n "$CURRENT_CANON" ] && [ "$t_canon" = "$CURRENT_CANON" ] && already=true

echo "STATUS=resolved"
echo "TARGET_PATH=${t_canon}"
echo "TARGET_BRANCH=${t_branch}"
echo "TARGET_NAME=${t_name}"
echo "IS_MAIN=${is_main}"
echo "ALREADY_AT_TARGET=${already}"
exit 0
