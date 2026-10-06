#!/usr/bin/env bash
# worktree-create.sh — create a git worktree, optionally creating a new branch.
#
# This script owns the git-level worktree creation so the sequence is
# deterministic, testable, and consistent. The new-branch flow deliberately
# uses a two-phase "detached HEAD first, then create the branch inside the
# worktree" technique and ROLLS BACK the worktree if the branch step fails,
# so a failed branch creation never leaves an orphaned detached worktree.
#
# Usage:
#   worktree-create.sh --path <abs-worktree-path> [mode] [options]
#
# Mode (choose at most one; default = create a new branch named after the dir):
#   --create-branch <branch>   Create a NEW branch in the worktree.
#                              Phase 1: git worktree add --detach <path> <start>
#                              Phase 2: git -C <path> switch -c <branch>
#                              On phase-2 failure the worktree is removed.
#   --branch <branch>          Check out an EXISTING branch
#                              (git worktree add <path> <branch>).
#   --detach                   Detached-HEAD worktree at <start-point>, no branch.
#   (no mode)                  Create a new branch named after the worktree dir
#                              basename (same two-phase flow as --create-branch).
#
# Options:
#   --start-point <ref>        Base commit/branch/tag for the worktree.
#                              Default: HEAD.
#   --repo <path>              Repository directory to operate in (git -C).
#                              Default: current working directory.
#   --json                     Emit a JSON object instead of KEY=VALUE lines.
#   -h, --help                 Print usage and exit 0.
#
# Output (KEY=VALUE lines on stdout, one per line):
#   Success:
#     STATUS=created
#     WORKTREE_PATH=<absolute path>
#     BRANCH=<branch name or empty for detached>
#     MODE=create-branch|existing-branch|detached|default-branch
#     NEW_BRANCH=true|false
#     START_POINT=<ref given, or HEAD>
#   Failure:
#     STATUS=error
#     ERROR_CODE=<code>
#     ERROR=<human readable message>
#
# Exit codes:
#   0  success
#   1  operation error (git failed, branch/worktree conflict, invalid ref)
#   2  usage error (bad or missing arguments, not a git repository)
#
# Error codes (ERROR_CODE):
#   BAD_USAGE, NOT_A_REPO, WORKTREE_EXISTS, INVALID_REF,
#   BRANCH_EXISTS, BRANCH_IN_USE, GIT_ERROR

set -uo pipefail

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
WT_PATH=""
CREATE_BRANCH=""
EXISTING_BRANCH=""
DETACH=false
START_POINT="HEAD"
REPO_DIR="."
JSON=false
MODE_COUNT=0

usage() {
    sed -n '2,50p' "$0" | sed 's/^# \{0,1\}//'
}

# ARG_ERR is set when parsing fails so we can emit a structured error afterwards.
ARG_ERR=""

while [ $# -gt 0 ]; do
    case "$1" in
        --path)
            WT_PATH="${2:-}"; shift 2 || { ARG_ERR="--path requires a value"; break; } ;;
        --create-branch)
            CREATE_BRANCH="${2:-}"; MODE_COUNT=$((MODE_COUNT + 1)); shift 2 || { ARG_ERR="--create-branch requires a value"; break; } ;;
        --branch)
            EXISTING_BRANCH="${2:-}"; MODE_COUNT=$((MODE_COUNT + 1)); shift 2 || { ARG_ERR="--branch requires a value"; break; } ;;
        --detach)
            DETACH=true; MODE_COUNT=$((MODE_COUNT + 1)); shift ;;
        --start-point)
            START_POINT="${2:-}"; shift 2 || { ARG_ERR="--start-point requires a value"; break; } ;;
        --repo)
            REPO_DIR="${2:-}"; shift 2 || { ARG_ERR="--repo requires a value"; break; } ;;
        --json)
            JSON=true; shift ;;
        -h|--help)
            usage; exit 0 ;;
        *)
            ARG_ERR="unknown argument: $1"; break ;;
    esac
done

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
emit_error() {
    # emit_error <exit_code> <error_code> <message>
    local code="$1" ecode="$2" msg="$3"
    if [ "$JSON" = true ]; then
        printf '{"status":"error","errorCode":"%s","error":"%s"}\n' \
            "$ecode" "$(printf '%s' "$msg" | sed 's/\\/\\\\/g; s/"/\\"/g')"
    else
        echo "STATUS=error"
        echo "ERROR_CODE=${ecode}"
        echo "ERROR=${msg}"
    fi
    exit "$code"
}

emit_success() {
    # emit_success <mode> <branch> <new_branch>
    local mode="$1" branch="$2" new_branch="$3"
    if [ "$JSON" = true ]; then
        printf '{"status":"created","worktreePath":"%s","branch":"%s","mode":"%s","newBranch":%s,"startPoint":"%s"}\n' \
            "$WT_PATH" "$branch" "$mode" "$new_branch" "$START_POINT"
    else
        echo "STATUS=created"
        echo "WORKTREE_PATH=${WT_PATH}"
        echo "BRANCH=${branch}"
        echo "MODE=${mode}"
        echo "NEW_BRANCH=${new_branch}"
        echo "START_POINT=${START_POINT}"
    fi
    exit 0
}

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
[ -n "$ARG_ERR" ] && emit_error 2 BAD_USAGE "$ARG_ERR"
[ -z "$WT_PATH" ] && emit_error 2 BAD_USAGE "--path is required"
[ "$MODE_COUNT" -gt 1 ] && emit_error 2 BAD_USAGE "choose at most one of --create-branch, --branch, --detach"
[ -z "$START_POINT" ] && emit_error 2 BAD_USAGE "--start-point requires a value"

# git -C prefix as an array so REPO_DIR spaces are safe.
GIT=(git -C "$REPO_DIR")

if ! "${GIT[@]}" rev-parse --git-dir > /dev/null 2>&1; then
    emit_error 2 NOT_A_REPO "'${REPO_DIR}' is not a git repository"
fi

if [ -e "$WT_PATH" ]; then
    emit_error 1 WORKTREE_EXISTS "a file or directory already exists at ${WT_PATH}"
fi

# Validate the start-point resolves to something git understands.
if ! "${GIT[@]}" rev-parse --verify --quiet "${START_POINT}^{commit}" > /dev/null 2>&1; then
    emit_error 1 INVALID_REF "start-point '${START_POINT}' is not a valid commit/branch/tag"
fi

# ---------------------------------------------------------------------------
# Mode: existing branch — atomic single-shot add
# ---------------------------------------------------------------------------
if [ -n "$EXISTING_BRANCH" ]; then
    if ! "${GIT[@]}" rev-parse --verify --quiet "refs/heads/${EXISTING_BRANCH}" > /dev/null 2>&1; then
        emit_error 1 INVALID_REF "branch '${EXISTING_BRANCH}' does not exist; use --create-branch to make a new branch"
    fi
    add_err="$("${GIT[@]}" worktree add "$WT_PATH" "$EXISTING_BRANCH" 2>&1)"
    if [ $? -ne 0 ]; then
        if printf '%s' "$add_err" | grep -qE "already used by worktree|already checked out"; then
            emit_error 1 BRANCH_IN_USE "branch '${EXISTING_BRANCH}' is already checked out in another worktree"
        fi
        emit_error 1 GIT_ERROR "$add_err"
    fi
    emit_success "existing-branch" "$EXISTING_BRANCH" "false"
fi

# ---------------------------------------------------------------------------
# Mode: detached only
# ---------------------------------------------------------------------------
if [ "$DETACH" = true ]; then
    add_err="$("${GIT[@]}" worktree add --detach "$WT_PATH" "$START_POINT" 2>&1)"
    if [ $? -ne 0 ]; then
        emit_error 1 GIT_ERROR "$add_err"
    fi
    emit_success "detached" "" "false"
fi

# ---------------------------------------------------------------------------
# Mode: new branch (explicit --create-branch, or default from dir basename)
# Two-phase: detached HEAD first, then create the branch inside the worktree.
# ---------------------------------------------------------------------------
NEW_BRANCH="$CREATE_BRANCH"
MODE="create-branch"
if [ -z "$NEW_BRANCH" ]; then
    NEW_BRANCH="$(basename "$WT_PATH")"
    MODE="default-branch"
fi

# Fail early if the branch already exists — avoids a pointless detached worktree.
if "${GIT[@]}" rev-parse --verify --quiet "refs/heads/${NEW_BRANCH}" > /dev/null 2>&1; then
    emit_error 1 BRANCH_EXISTS "a branch named '${NEW_BRANCH}' already exists"
fi

# Phase 1: create the detached-HEAD worktree at the start point.
add_err="$("${GIT[@]}" worktree add --detach "$WT_PATH" "$START_POINT" 2>&1)"
if [ $? -ne 0 ]; then
    emit_error 1 GIT_ERROR "$add_err"
fi

# Phase 2: create the branch inside the freshly-created worktree.
sw_err="$(git -C "$WT_PATH" switch -c "$NEW_BRANCH" 2>&1)"
if [ $? -ne 0 ]; then
    # Roll back the detached worktree so we never leave an orphan behind.
    "${GIT[@]}" worktree remove --force "$WT_PATH" > /dev/null 2>&1
    "${GIT[@]}" worktree prune > /dev/null 2>&1
    if printf '%s' "$sw_err" | grep -q "already exists"; then
        emit_error 1 BRANCH_EXISTS "a branch named '${NEW_BRANCH}' already exists"
    fi
    if printf '%s' "$sw_err" | grep -qE "already used by worktree|already checked out"; then
        emit_error 1 BRANCH_IN_USE "branch '${NEW_BRANCH}' is already checked out in another worktree"
    fi
    emit_error 1 GIT_ERROR "$sw_err"
fi

emit_success "$MODE" "$NEW_BRANCH" "true"
