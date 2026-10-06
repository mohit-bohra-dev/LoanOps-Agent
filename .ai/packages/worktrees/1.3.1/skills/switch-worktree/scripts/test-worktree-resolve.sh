#!/usr/bin/env bash
# test-worktree-resolve.sh — test harness for worktree-resolve.sh.
#
# Run:
#   bash packages/worktrees/skills/switch-worktree/scripts/test-worktree-resolve.sh
#
# Builds a throwaway repo with several worktrees (including a symlinked global
# path mirroring the .worktrees layout) and asserts on resolution behavior.

set -uo pipefail

# Isolate from any ambient git context (e.g. when run inside a git commit hook,
# git exports GIT_DIR/GIT_INDEX_FILE/etc. that would leak into the throwaway
# repos this harness creates and break their git commands).
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_PREFIX GIT_COMMON_DIR \
      GIT_OBJECT_DIRECTORY GIT_NAMESPACE GIT_CEILING_DIRECTORIES 2>/dev/null || true

SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
SUT="${SCRIPTS_DIR}/worktree-resolve.sh"
CREATE="${SCRIPTS_DIR}/../../create-worktree/scripts/worktree-create.sh"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT INT TERM

PASS_COUNT=0
FAIL_COUNT=0
pass() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "FAIL: $1 — $2"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

get_value() { grep "^$1=" | head -1 | cut -d= -f2-; }

run_sut() {
    local _var_out="$1" _var_ec="$2"; shift 2
    local _out _ec
    _out="$(bash "$SUT" "$@" 2>&1)"; _ec=$?
    eval "${_var_out}=\$_out"
    eval "${_var_ec}=\$_ec"
}

# Build a repo with two extra worktrees:
#   .worktrees/my-feature  -> branch feature/dev/my-feature
#   .worktrees/experiment  -> branch experiment
# Also create a global symlink dir pointing at .worktrees to test symlink norm.
build_repo() {
    local repo="${TMP_DIR}/repo"
    git init -q "$repo"
    git -C "$repo" config user.email t@t.co
    git -C "$repo" config user.name t
    echo seed > "${repo}/README.md"
    git -C "$repo" add -A
    git -C "$repo" commit -q -m initial
    git -C "$repo" branch -M main
    bash "$CREATE" --repo "$repo" --path "${repo}/.worktrees/my-feature" --create-branch feature/dev/my-feature > /dev/null 2>&1
    bash "$CREATE" --repo "$repo" --path "${repo}/.worktrees/experiment" --create-branch experiment > /dev/null 2>&1
    # Global symlink mirroring ~/.cursor/worktrees/<project>
    mkdir -p "${TMP_DIR}/global"
    ln -s "${repo}/.worktrees" "${TMP_DIR}/global/repo"
    echo "$repo"
}

REPO="$(build_repo)"

# ---------------------------------------------------------------------------
# S01: listing includes main + 2 worktrees
# ---------------------------------------------------------------------------
s01() {
    local out ec
    run_sut out ec --repo "$REPO"
    [ "$ec" -eq 0 ] || { fail "S01 list" "exit ${ec}"; return; }
    local n; n="$(echo "$out" | grep -c '^WT')"
    [ "$n" -eq 3 ] || { fail "S01 list" "expected 3 WT lines, got ${n}: ${out}"; return; }
    echo "$out" | grep -q 'feature/dev/my-feature' || { fail "S01 list" "missing feature branch"; return; }
    pass "S01 list"
}

# ---------------------------------------------------------------------------
# S02: resolve by directory basename
# ---------------------------------------------------------------------------
s02() {
    local out ec
    run_sut out ec --repo "$REPO" --query my-feature
    [ "$ec" -eq 0 ] || { fail "S02 by-name" "exit ${ec}: ${out}"; return; }
    [ "$(echo "$out" | get_value STATUS)" = "resolved" ] || { fail "S02 by-name" "not resolved"; return; }
    [ "$(echo "$out" | get_value TARGET_NAME)" = "my-feature" ] || { fail "S02 by-name" "wrong name"; return; }
    [ "$(echo "$out" | get_value TARGET_BRANCH)" = "feature/dev/my-feature" ] || { fail "S02 by-name" "wrong branch"; return; }
    pass "S02 resolve-by-name"
}

# ---------------------------------------------------------------------------
# S03: resolve by branch name
# ---------------------------------------------------------------------------
s03() {
    local out ec
    run_sut out ec --repo "$REPO" --query feature/dev/my-feature
    [ "$ec" -eq 0 ] || { fail "S03 by-branch" "exit ${ec}"; return; }
    [ "$(echo "$out" | get_value TARGET_NAME)" = "my-feature" ] || { fail "S03 by-branch" "wrong name: $out"; return; }
    pass "S03 resolve-by-branch"
}

# ---------------------------------------------------------------------------
# S04: resolve by symlinked global path -> canonical .worktrees path
# ---------------------------------------------------------------------------
s04() {
    local out ec
    local symlinked="${TMP_DIR}/global/repo/experiment"
    run_sut out ec --repo "$REPO" --query "$symlinked"
    [ "$ec" -eq 0 ] || { fail "S04 symlink-path" "exit ${ec}: ${out}"; return; }
    local tp; tp="$(echo "$out" | get_value TARGET_PATH)"
    # Canonical target should live under the real .worktrees, not the symlink dir.
    case "$tp" in
        *"/global/"*) fail "S04 symlink-path" "target not canonicalized: ${tp}"; return ;;
    esac
    [ "$(echo "$out" | get_value TARGET_NAME)" = "experiment" ] || { fail "S04 symlink-path" "wrong name"; return; }
    pass "S04 resolve-symlinked-path"
}

# ---------------------------------------------------------------------------
# S05: already-at-target detection (current == target, via symlink)
# ---------------------------------------------------------------------------
s05() {
    local out ec
    local symlinked_current="${TMP_DIR}/global/repo/my-feature"
    run_sut out ec --repo "$REPO" --query my-feature --current "$symlinked_current"
    [ "$ec" -eq 0 ] || { fail "S05 already-at" "exit ${ec}"; return; }
    [ "$(echo "$out" | get_value ALREADY_AT_TARGET)" = "true" ] || { fail "S05 already-at" "not detected: ${out}"; return; }
    pass "S05 already-at-target"
}

# ---------------------------------------------------------------------------
# S06: not-found query -> exit 1, still lists worktrees
# ---------------------------------------------------------------------------
s06() {
    local out ec
    run_sut out ec --repo "$REPO" --query nonexistent-xyz
    [ "$ec" -eq 1 ] || { fail "S06 not-found" "exit ${ec}, expected 1"; return; }
    [ "$(echo "$out" | get_value STATUS)" = "not_found" ] || { fail "S06 not-found" "wrong STATUS"; return; }
    echo "$out" | grep -q '^WT' || { fail "S06 not-found" "listing missing"; return; }
    pass "S06 not-found"
}

# ---------------------------------------------------------------------------
# S07: main worktree flagged IS_MAIN=true
# ---------------------------------------------------------------------------
s07() {
    local out ec
    run_sut out ec --repo "$REPO" --query "$(basename "$REPO")"
    [ "$ec" -eq 0 ] || { fail "S07 main" "exit ${ec}: ${out}"; return; }
    [ "$(echo "$out" | get_value IS_MAIN)" = "true" ] || { fail "S07 main" "IS_MAIN not true: ${out}"; return; }
    pass "S07 resolve-main"
}

# ---------------------------------------------------------------------------
# S08: not a git repo -> exit 2
# ---------------------------------------------------------------------------
s08() {
    local plain="${TMP_DIR}/plain"; mkdir -p "$plain"
    local out ec
    run_sut out ec --repo "$plain" --query x
    [ "$ec" -eq 2 ] || { fail "S08 not-a-repo" "exit ${ec}, expected 2"; return; }
    pass "S08 not-a-repo"
}

echo "Running worktree-resolve.sh scenarios..."
echo ""
s01; s02; s03; s04; s05; s06; s07; s08
echo ""
echo "Results: ${PASS_COUNT} passed, ${FAIL_COUNT} failed"
[ "$FAIL_COUNT" -gt 0 ] && exit 1
exit 0
