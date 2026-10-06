#!/usr/bin/env bash
# test-worktree-create.sh — test harness for worktree-create.sh.
#
# Run from anywhere:
#   bash packages/worktrees/skills/create-worktree/scripts/test-worktree-create.sh
#
# Builds a throwaway git repo per scenario, runs worktree-create.sh, and asserts
# on its structured output, exit code, and the resulting git worktree state.
# Prints PASS/FAIL per scenario. Exits 0 if all pass, 1 if any fail.

set -uo pipefail

# Isolate from any ambient git context (e.g. when run inside a git commit hook,
# git exports GIT_DIR/GIT_INDEX_FILE/etc. that would leak into the throwaway
# repos this harness creates and break their git commands).
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_PREFIX GIT_COMMON_DIR \
      GIT_OBJECT_DIRECTORY GIT_NAMESPACE GIT_CEILING_DIRECTORIES 2>/dev/null || true

SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
SUT="${SCRIPTS_DIR}/worktree-create.sh"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT INT TERM

PASS_COUNT=0
FAIL_COUNT=0
pass() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "FAIL: $1 — $2"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

# Create a fresh repo with one commit on `main`. Echoes the repo path.
make_repo() {
    local name="$1"
    local repo="${TMP_DIR}/${name}"
    mkdir -p "$repo"
    git init -q "$repo"
    git -C "$repo" config user.email t@t.co
    git -C "$repo" config user.name t
    echo "seed" > "${repo}/README.md"
    git -C "$repo" add -A
    git -C "$repo" commit -q -m "initial"
    git -C "$repo" branch -M main
    echo "$repo"
}

# Run the SUT capturing stdout+stderr and exit code (set -e safe).
run_sut() {
    local _var_out="$1" _var_ec="$2"; shift 2
    local _out _ec
    _out="$(bash "$SUT" "$@" 2>&1)"; _ec=$?
    eval "${_var_out}=\$_out"
    eval "${_var_ec}=\$_ec"
}

# get_value KEY <<< "$output"
get_value() { grep "^$1=" | head -1 | cut -d= -f2-; }

# ---------------------------------------------------------------------------
# S01: create a NEW feature branch (two-phase detached-then-branch)
# ---------------------------------------------------------------------------
s01() {
    local repo; repo="$(make_repo s01)"
    local wt="${repo}/.worktrees/my-feature"
    local out ec
    run_sut out ec --repo "$repo" --path "$wt" --create-branch "feature/dev/my-feature"

    [ "$ec" -eq 0 ] || { fail "S01 new-branch" "exit ${ec}: ${out}"; return; }
    [ "$(echo "$out" | get_value STATUS)" = "created" ] || { fail "S01 new-branch" "STATUS not created: ${out}"; return; }
    [ "$(echo "$out" | get_value NEW_BRANCH)" = "true" ] || { fail "S01 new-branch" "NEW_BRANCH not true"; return; }
    [ "$(echo "$out" | get_value BRANCH)" = "feature/dev/my-feature" ] || { fail "S01 new-branch" "wrong BRANCH"; return; }
    [ -d "$wt" ] || { fail "S01 new-branch" "worktree dir missing"; return; }
    local head; head="$(git -C "$wt" rev-parse --abbrev-ref HEAD)"
    [ "$head" = "feature/dev/my-feature" ] || { fail "S01 new-branch" "worktree HEAD is ${head}"; return; }
    git -C "$repo" worktree list | grep -q "feature/dev/my-feature" || { fail "S01 new-branch" "branch not in worktree list"; return; }
    pass "S01 new-branch (detached-then-branch)"
}

# ---------------------------------------------------------------------------
# S02: checkout an EXISTING branch
# ---------------------------------------------------------------------------
s02() {
    local repo; repo="$(make_repo s02)"
    git -C "$repo" branch existing-thing
    local wt="${repo}/.worktrees/existing"
    local out ec
    run_sut out ec --repo "$repo" --path "$wt" --branch existing-thing

    [ "$ec" -eq 0 ] || { fail "S02 existing-branch" "exit ${ec}: ${out}"; return; }
    [ "$(echo "$out" | get_value MODE)" = "existing-branch" ] || { fail "S02 existing-branch" "wrong MODE"; return; }
    [ "$(echo "$out" | get_value NEW_BRANCH)" = "false" ] || { fail "S02 existing-branch" "NEW_BRANCH not false"; return; }
    [ "$(git -C "$wt" rev-parse --abbrev-ref HEAD)" = "existing-thing" ] || { fail "S02 existing-branch" "wrong HEAD"; return; }
    pass "S02 existing-branch"
}

# ---------------------------------------------------------------------------
# S03: detached-only worktree
# ---------------------------------------------------------------------------
s03() {
    local repo; repo="$(make_repo s03)"
    local wt="${repo}/.worktrees/detached"
    local out ec
    run_sut out ec --repo "$repo" --path "$wt" --detach

    [ "$ec" -eq 0 ] || { fail "S03 detached" "exit ${ec}: ${out}"; return; }
    [ "$(echo "$out" | get_value MODE)" = "detached" ] || { fail "S03 detached" "wrong MODE"; return; }
    [ "$(echo "$out" | get_value BRANCH)" = "" ] || { fail "S03 detached" "BRANCH should be empty"; return; }
    git -C "$wt" symbolic-ref -q HEAD > /dev/null 2>&1 && { fail "S03 detached" "HEAD is not detached"; return; }
    pass "S03 detached"
}

# ---------------------------------------------------------------------------
# S04: default mode — branch named after the worktree dir basename
# ---------------------------------------------------------------------------
s04() {
    local repo; repo="$(make_repo s04)"
    local wt="${repo}/.worktrees/quick-fix"
    local out ec
    run_sut out ec --repo "$repo" --path "$wt"

    [ "$ec" -eq 0 ] || { fail "S04 default-branch" "exit ${ec}: ${out}"; return; }
    [ "$(echo "$out" | get_value MODE)" = "default-branch" ] || { fail "S04 default-branch" "wrong MODE"; return; }
    [ "$(git -C "$wt" rev-parse --abbrev-ref HEAD)" = "quick-fix" ] || { fail "S04 default-branch" "wrong HEAD"; return; }
    pass "S04 default-branch"
}

# ---------------------------------------------------------------------------
# S05: ROLLBACK — new-branch fails because branch already exists; no orphan
# ---------------------------------------------------------------------------
s05() {
    local repo; repo="$(make_repo s05)"
    git -C "$repo" branch taken
    local wt="${repo}/.worktrees/taken-wt"
    local out ec
    run_sut out ec --repo "$repo" --path "$wt" --create-branch taken

    [ "$ec" -eq 1 ] || { fail "S05 rollback-branch-exists" "exit ${ec}, expected 1: ${out}"; return; }
    [ "$(echo "$out" | get_value ERROR_CODE)" = "BRANCH_EXISTS" ] || { fail "S05 rollback-branch-exists" "wrong ERROR_CODE: ${out}"; return; }
    # The key assertion: no orphaned worktree left behind.
    [ ! -e "$wt" ] || { fail "S05 rollback-branch-exists" "orphan worktree dir left at ${wt}"; return; }
    git -C "$repo" worktree list | grep -q "taken-wt" && { fail "S05 rollback-branch-exists" "orphan in worktree list"; return; }
    pass "S05 rollback-branch-exists (no orphan)"
}

# ---------------------------------------------------------------------------
# S06: branch already checked out in another worktree -> BRANCH_IN_USE
# ---------------------------------------------------------------------------
s06() {
    local repo; repo="$(make_repo s06)"
    # Put feature/dev/foo into worktree A first.
    bash "$SUT" --repo "$repo" --path "${repo}/.worktrees/a" --create-branch feature/dev/foo > /dev/null 2>&1
    # Now try to check that same existing branch out into worktree B.
    local out ec
    run_sut out ec --repo "$repo" --path "${repo}/.worktrees/b" --branch feature/dev/foo

    [ "$ec" -eq 1 ] || { fail "S06 branch-in-use" "exit ${ec}, expected 1: ${out}"; return; }
    [ "$(echo "$out" | get_value ERROR_CODE)" = "BRANCH_IN_USE" ] || { fail "S06 branch-in-use" "wrong ERROR_CODE: ${out}"; return; }
    [ ! -e "${repo}/.worktrees/b" ] || { fail "S06 branch-in-use" "orphan worktree b left behind"; return; }
    pass "S06 branch-in-use"
}

# ---------------------------------------------------------------------------
# S07: worktree path already exists -> WORKTREE_EXISTS
# ---------------------------------------------------------------------------
s07() {
    local repo; repo="$(make_repo s07)"
    local wt="${repo}/.worktrees/occupied"
    mkdir -p "$wt"
    local out ec
    run_sut out ec --repo "$repo" --path "$wt" --create-branch feature/dev/x

    [ "$ec" -eq 1 ] || { fail "S07 worktree-exists" "exit ${ec}, expected 1"; return; }
    [ "$(echo "$out" | get_value ERROR_CODE)" = "WORKTREE_EXISTS" ] || { fail "S07 worktree-exists" "wrong ERROR_CODE: ${out}"; return; }
    pass "S07 worktree-exists"
}

# ---------------------------------------------------------------------------
# S08: invalid start-point -> INVALID_REF
# ---------------------------------------------------------------------------
s08() {
    local repo; repo="$(make_repo s08)"
    local out ec
    run_sut out ec --repo "$repo" --path "${repo}/.worktrees/w" --create-branch feature/dev/y --start-point nope-not-a-ref

    [ "$ec" -eq 1 ] || { fail "S08 invalid-ref" "exit ${ec}, expected 1"; return; }
    [ "$(echo "$out" | get_value ERROR_CODE)" = "INVALID_REF" ] || { fail "S08 invalid-ref" "wrong ERROR_CODE: ${out}"; return; }
    pass "S08 invalid-ref"
}

# ---------------------------------------------------------------------------
# S09: not a git repo -> NOT_A_REPO (usage exit 2)
# ---------------------------------------------------------------------------
s09() {
    local notrepo="${TMP_DIR}/s09-plain"
    mkdir -p "$notrepo"
    local out ec
    run_sut out ec --repo "$notrepo" --path "${notrepo}/.worktrees/w" --create-branch feature/dev/z

    [ "$ec" -eq 2 ] || { fail "S09 not-a-repo" "exit ${ec}, expected 2"; return; }
    [ "$(echo "$out" | get_value ERROR_CODE)" = "NOT_A_REPO" ] || { fail "S09 not-a-repo" "wrong ERROR_CODE: ${out}"; return; }
    pass "S09 not-a-repo"
}

# ---------------------------------------------------------------------------
# S10: bad usage — two modes at once -> BAD_USAGE
# ---------------------------------------------------------------------------
s10() {
    local repo; repo="$(make_repo s10)"
    local out ec
    run_sut out ec --repo "$repo" --path "${repo}/.worktrees/w" --detach --create-branch feature/dev/w

    [ "$ec" -eq 2 ] || { fail "S10 bad-usage" "exit ${ec}, expected 2"; return; }
    [ "$(echo "$out" | get_value ERROR_CODE)" = "BAD_USAGE" ] || { fail "S10 bad-usage" "wrong ERROR_CODE: ${out}"; return; }
    pass "S10 bad-usage"
}

# ---------------------------------------------------------------------------
# S11: --start-point from an existing branch tip carries the right commit
# ---------------------------------------------------------------------------
s11() {
    local repo; repo="$(make_repo s11)"
    # Add a second commit on a base branch.
    git -C "$repo" checkout -q -b base
    echo "more" >> "${repo}/README.md"
    git -C "$repo" commit -q -am "second"
    local base_sha; base_sha="$(git -C "$repo" rev-parse HEAD)"
    git -C "$repo" checkout -q main
    local wt="${repo}/.worktrees/from-base"
    local out ec
    run_sut out ec --repo "$repo" --path "$wt" --create-branch feature/dev/from-base --start-point base

    [ "$ec" -eq 0 ] || { fail "S11 start-point" "exit ${ec}: ${out}"; return; }
    [ "$(git -C "$wt" rev-parse HEAD)" = "$base_sha" ] || { fail "S11 start-point" "worktree not at base tip"; return; }
    pass "S11 start-point"
}

# ---------------------------------------------------------------------------
# S12: --json output shape
# ---------------------------------------------------------------------------
s12() {
    local repo; repo="$(make_repo s12)"
    local out ec
    run_sut out ec --repo "$repo" --path "${repo}/.worktrees/j" --create-branch feature/dev/j --json

    [ "$ec" -eq 0 ] || { fail "S12 json" "exit ${ec}: ${out}"; return; }
    echo "$out" | grep -q '"status":"created"' || { fail "S12 json" "no status field: ${out}"; return; }
    echo "$out" | grep -q '"newBranch":true' || { fail "S12 json" "no newBranch field: ${out}"; return; }
    pass "S12 json"
}

echo "Running worktree-create.sh scenarios..."
echo ""
s01; s02; s03; s04; s05; s06; s07; s08; s09; s10; s11; s12
echo ""
echo "Results: ${PASS_COUNT} passed, ${FAIL_COUNT} failed"
[ "$FAIL_COUNT" -gt 0 ] && exit 1
exit 0
