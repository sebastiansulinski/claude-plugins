#!/usr/bin/env bash
#
# Test harness for scripts/worktree.sh.
#
# Builds throwaway fixtures under mktemp -d (a plain repository and a
# superproject containing it as a submodule), stubs composer/npm with recording
# shims, and asserts every behaviour promised by the plan. No network access.
#
# Run: bash worktree/tests/run.sh
set -u

HARNESS_DIR=$(cd "$(dirname "$0")" && pwd -P)
SCRIPT="$HARNESS_DIR/../scripts/worktree.sh"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
WORK=$(cd "$WORK" && pwd -P)

PASS_COUNT=0
fail() {
    printf 'FAIL: %s\n  %s\n' "$1" "$2" >&2
    exit 1
}
pass() {
    PASS_COUNT=$((PASS_COUNT + 1))
    printf 'ok %d - %s\n' "$PASS_COUNT" "$1"
}

OUT="" ERR="" STATUS=0
run_in() {
    local dir=$1
    shift
    OUT=$( (cd "$dir" && "$@") 2>"$WORK/.stderr" )
    STATUS=$?
    ERR=$(cat "$WORK/.stderr")
}
run_in_stdin() {
    local dir=$1 payload=$2
    shift 2
    OUT=$( (cd "$dir" && printf '%s' "$payload" | "$@") 2>"$WORK/.stderr" )
    STATUS=$?
    ERR=$(cat "$WORK/.stderr")
}

expect_success() { [ "$STATUS" -eq 0 ] || fail "$1" "exit=$STATUS stdout=[$OUT] stderr=[$ERR]"; pass "$1"; }
expect_failure() { [ "$STATUS" -ne 0 ] || fail "$1" "expected non-zero exit; stdout=[$OUT]"; pass "$1"; }
assert_eq() { [ "$2" = "$3" ] || fail "$1" "expected [$3] got [$2]"; pass "$1"; }
assert_contains() { case "$2" in *"$3"*) pass "$1" ;; *) fail "$1" "expected to contain [$3]: [$2]" ;; esac; }
assert_not_contains() { case "$2" in *"$3"*) fail "$1" "expected NOT to contain [$3]: [$2]" ;; *) pass "$1" ;; esac; }
assert_file() { [ -f "$2" ] || fail "$1" "missing file: $2"; pass "$1"; }
assert_not_exists() { [ ! -e "$2" ] || fail "$1" "should not exist: $2"; pass "$1"; }

pyget() {
    printf '%s' "$1" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print($2)"
}

snap() { git -C "$1" status --porcelain; }
head_of() { git -C "$1" rev-parse HEAD; }
branch_of() { git -C "$1" branch --show-current; }

# ---------------------------------------------------------------- git isolation
export HOME="$WORK/home"
mkdir -p "$HOME"
export GIT_CONFIG_NOSYSTEM=1
git config --global user.email tester@example.test
git config --global user.name Tester
git config --global init.defaultBranch main

# The session identity must come only from what each case sets explicitly.
unset WORKTREE_SESSION CLAUDE_CODE_SESSION_ID CODEX_SESSION_ID CODEX_THREAD_ID

# ---------------------------------------------------------------------- shims
SHIM_DIR="$WORK/shims"
mkdir -p "$SHIM_DIR"
export SHIM_LOG="$WORK/shim.log"
: > "$SHIM_LOG"
cat > "$SHIM_DIR/composer" <<'EOS'
#!/bin/sh
echo "composer:$PWD:$*" >> "$SHIM_LOG"
mkdir -p vendor
exit 0
EOS
cat > "$SHIM_DIR/npm" <<'EOS'
#!/bin/sh
echo "npm:$PWD:$*" >> "$SHIM_LOG"
mkdir -p node_modules
exit 0
EOS
chmod +x "$SHIM_DIR/composer" "$SHIM_DIR/npm"
export PATH="$SHIM_DIR:$PATH"

# ------------------------------------------------------------------- fixtures
make_source_repo() {
    local dir=$1
    mkdir -p "$dir"
    (
        cd "$dir" || exit 1
        git init -q -b main
        printf '.env\nvendor/\nnode_modules/\nhook-output.txt\n' > .gitignore
        printf '{}\n' > composer.json
        printf '{}\n' > package.json
        printf '#!/bin/sh\necho committed > hook-output.txt\n' > .worktree-setup.sh
        printf '#!/bin/sh\necho custom > hook-output.txt\n' > custom-hook.sh
        chmod +x .worktree-setup.sh custom-hook.sh
        git add -A
        git commit -qm 'initial'
        git branch develop
    )
}

# ===========================================================================
# Fixture 1 — plain repository
# ===========================================================================
APP="$WORK/app"
make_source_repo "$APP"
printf 'APP_KEY=secret\n' > "$APP/.env"
printf 'work in progress\n' > "$APP/wip.txt"

SNAP_0=$(snap "$APP")
HEAD_0=$(head_of "$APP")
BRANCH_0=$(branch_of "$APP")
DEST_DEFAULT="$WORK/app-worktrees"

# --- P1: basic create with conventions --------------------------------------
run_in "$APP" "$SCRIPT" create alpha --json
expect_success "P1 create alpha succeeds"
ALPHA_PATH=$(pyget "$OUT" "d['path']")
assert_eq "P1 path is sibling-of-repo convention" "$ALPHA_PATH" "$DEST_DEFAULT/alpha"
assert_eq "P1 branch is wt/alpha" "$(pyget "$OUT" "d['branch']")" "wt/alpha"
assert_eq "P1 base is local develop" "$(pyget "$OUT" "d['base']")" "develop"
assert_file "P1 .env copied" "$ALPHA_PATH/.env"
assert_eq "P1 .env content matches" "$(cat "$ALPHA_PATH/.env")" "APP_KEY=secret"
assert_eq "P1 worktree is clean after bootstrap" "$(snap "$ALPHA_PATH")" ""
assert_contains "P1 composer ran inside the worktree" "$(cat "$SHIM_LOG")" "composer:$ALPHA_PATH:install --no-interaction"
assert_not_contains "P1 npm not run by default" "$(cat "$SHIM_LOG")" "npm:"
assert_eq "P1 worktreeBase marker recorded" "$(git -C "$APP" config --get branch.wt/alpha.worktreeBase)" "develop"
assert_eq "P1 worktree HEAD equals develop" "$(head_of "$ALPHA_PATH")" "$(git -C "$APP" rev-parse develop)"
assert_eq "P1 hook ran committed version" "$(cat "$ALPHA_PATH/hook-output.txt")" "committed"
assert_eq "P1 main checkout status untouched" "$(snap "$APP")" "$SNAP_0"
assert_eq "P1 main checkout HEAD untouched" "$(head_of "$APP")" "$HEAD_0"
assert_eq "P1 main checkout branch untouched" "$(branch_of "$APP")" "$BRANCH_0"

# --- P2: remove with branch deletion (merged-equal) --------------------------
run_in "$APP" "$SCRIPT" remove alpha --delete-branch --json
expect_success "P2 remove alpha succeeds"
assert_not_exists "P2 worktree directory gone" "$ALPHA_PATH"
run_in "$APP" git show-ref --verify --quiet refs/heads/wt/alpha
expect_failure "P2 branch wt/alpha deleted"
run_in "$APP" git config --get branch.wt/alpha.worktreeBase
expect_failure "P2 worktreeBase marker cleaned up"
assert_eq "P2 main checkout status untouched" "$(snap "$APP")" "$SNAP_0"
assert_eq "P2 main checkout HEAD untouched" "$(head_of "$APP")" "$HEAD_0"
assert_eq "P2 main checkout branch untouched" "$(branch_of "$APP")" "$BRANCH_0"

# --- P3: invalid names --------------------------------------------------------
for bad_name in "" ".." "a/b" "-x" "a..b" "foo.lock"; do
    run_in "$APP" "$SCRIPT" create "$bad_name"
    expect_failure "P3 rejects name [$bad_name]"
done
run_in "$APP" "$SCRIPT" create "$(printf 'a\tb')"
expect_failure "P3 rejects control characters"

# --- P4: create aborts ---------------------------------------------------------
run_in "$APP" "$SCRIPT" create dupe --json
expect_success "P4 first create dupe succeeds"
run_in "$APP" "$SCRIPT" create dupe
expect_failure "P4 existing branch aborts"
assert_contains "P4 existing-branch message" "$ERR" "already exists"
run_in "$APP" "$SCRIPT" remove dupe --delete-branch
expect_success "P4 cleanup dupe"

mkdir -p "$DEST_DEFAULT/beta"
touch "$DEST_DEFAULT/beta/occupied.txt"
run_in "$APP" "$SCRIPT" create beta
expect_failure "P4 non-empty destination aborts"
rm -rf "$DEST_DEFAULT/beta"

run_in "$APP" "$SCRIPT" create gamma --dest "$APP/inner"
expect_failure "P4 destination inside repository aborts"
assert_not_exists "P4 no junk directory created inside repository" "$APP/inner"

mkdir -p "$WORK/norepo"
run_in "$WORK/norepo" "$SCRIPT" create delta
expect_failure "P4 not-a-repository aborts"

# --- P5: configuration honoured ------------------------------------------------
cat > "$APP/.worktree.json" <<EOF
{
    "baseBranch": "main",
    "branchPrefix": "plan/",
    "destination": "$WORK/custom dest",
    "bootstrap": { "composer": false }
}
EOF
: > "$SHIM_LOG"
run_in "$APP" "$SCRIPT" create cfga --json
expect_success "P5 create with config succeeds"
assert_eq "P5 branch uses configured prefix" "$(pyget "$OUT" "d['branch']")" "plan/cfga"
assert_eq "P5 base uses configured baseBranch" "$(pyget "$OUT" "d['base']")" "main"
assert_eq "P5 destination uses configured dir (with space)" "$(pyget "$OUT" "d['path']")" "$WORK/custom dest/cfga"
assert_not_contains "P5 composer disabled by config" "$(cat "$SHIM_LOG")" "composer:"

# --- P6: remove resolves from metadata, not mutable config ----------------------
cat > "$APP/.worktree.json" <<EOF
{
    "branchPrefix": "zz/",
    "destination": "$WORK/elsewhere"
}
EOF
run_in "$APP" "$SCRIPT" remove cfga --delete-branch --json
expect_success "P6 remove finds worktree despite config rewrite"
assert_not_exists "P6 original worktree removed" "$WORK/custom dest/cfga"
run_in "$APP" git show-ref --verify --quiet refs/heads/plan/cfga
expect_failure "P6 originally created branch deleted"
rm -f "$APP/.worktree.json"

# --- P7: flag precedence beats config in BOTH directions --------------------------
cat > "$APP/.worktree.json" <<'EOF'
{
    "bootstrap": { "composer": false, "npm": true }
}
EOF
: > "$SHIM_LOG"
run_in "$APP" "$SCRIPT" create prec --composer --no-npm --json
expect_success "P7 create with both-direction flag overrides succeeds"
PREC_PATH=$(pyget "$OUT" "d['path']")
assert_contains "P7 --composer overrides config false" "$(cat "$SHIM_LOG")" "composer:$PREC_PATH:"
assert_not_contains "P7 --no-npm overrides config true" "$(cat "$SHIM_LOG")" "npm:"
run_in "$APP" "$SCRIPT" remove prec --delete-branch
expect_success "P7 cleanup prec"
rm -f "$APP/.worktree.json"

: > "$SHIM_LOG"
run_in "$APP" "$SCRIPT" create npmon --npm --json
expect_success "P7 create with --npm succeeds"
NPMON_PATH=$(pyget "$OUT" "d['path']")
assert_contains "P7 --npm enables npm over default-off" "$(cat "$SHIM_LOG")" "npm:$NPMON_PATH:ci"
run_in "$APP" "$SCRIPT" remove npmon --delete-branch
expect_success "P7 cleanup npmon"

# --- P8: config parsing handles escaped strings and missing keys -------------------
cat > "$APP/.worktree.json" <<EOF
{
    "destination": "$WORK/esc \" dir"
}
EOF
run_in "$APP" "$SCRIPT" create escx --json
expect_success "P8 create with escaped-string destination succeeds"
assert_eq "P8 destination honours escaped quote" "$(pyget "$OUT" "d['path']")" "$WORK/esc \" dir/escx"
assert_eq "P8 missing branchPrefix falls back to wt/" "$(pyget "$OUT" "d['branch']")" "wt/escx"
run_in "$APP" "$SCRIPT" remove escx --delete-branch
expect_success "P8 cleanup escx"
rm -f "$APP/.worktree.json"

# --- P9: dirty worktree removal refusal ---------------------------------------------
run_in "$APP" "$SCRIPT" create rd --json
expect_success "P9 create rd succeeds"
RD_PATH=$(pyget "$OUT" "d['path']")
printf 'dirty\n' >> "$RD_PATH/composer.json"
run_in "$APP" "$SCRIPT" remove rd
expect_failure "P9 dirty worktree refused without --force"
run_in "$APP" "$SCRIPT" remove rd --force
expect_success "P9 dirty worktree removed with --force"
git -C "$APP" branch -qD wt/rd
git -C "$APP" config --unset branch.wt/rd.worktreeBase 2>/dev/null

# --- P10: unmerged branch deletion is NOT HEAD-relative -------------------------------
run_in "$APP" "$SCRIPT" create um --json
expect_success "P10 create um succeeds"
UM_PATH=$(pyget "$OUT" "d['path']")
printf 'change\n' >> "$UM_PATH/composer.json"
git -C "$UM_PATH" commit -aqm 'unmerged work'
git -C "$APP" checkout -qb unrelated
git -C "$APP" merge -q --no-ff wt/um -m 'merge into unrelated'
run_in "$APP" "$SCRIPT" remove um --delete-branch
expect_failure "P10 deletion refused: merged into HEAD but not into recorded base"
assert_contains "P10 refusal names the recorded base" "$ERR" "develop"
[ -d "$UM_PATH" ] || fail "P10 worktree left intact on refusal" "worktree was removed despite refusal"
pass "P10 worktree left intact on refusal"
run_in "$APP" git show-ref --verify --quiet refs/heads/wt/um
expect_success "P10 branch left intact on refusal"
run_in "$APP" "$SCRIPT" remove um --delete-branch --force
expect_success "P10 --force deletes unmerged branch"
assert_not_exists "P10 worktree gone after --force" "$UM_PATH"
git -C "$APP" checkout -q main
git -C "$APP" branch -qD unrelated

# --- P11: unmanaged worktrees refused without --unmanaged ------------------------------
git -C "$APP" worktree add -q "$WORK/manual/m1" -b manualbr develop
run_in "$APP" "$SCRIPT" remove m1
expect_failure "P11 manually created worktree refused"
assert_contains "P11 refusal mentions --unmanaged" "$ERR" "--unmanaged"
run_in "$APP" "$SCRIPT" remove m1 --unmanaged
expect_success "P11 --unmanaged removes it"
git -C "$APP" branch -qD manualbr

# --- P12: ambiguous basename aborts ------------------------------------------------------
run_in "$APP" "$SCRIPT" create dup --json
expect_success "P12 tool-created dup succeeds"
git -C "$APP" worktree add -q "$WORK/manual2/dup" -b dupbr develop
run_in "$APP" "$SCRIPT" remove dup
expect_failure "P12 ambiguous basename aborts"
assert_contains "P12 abort lists candidates" "$ERR" "$WORK/manual2/dup"
git -C "$APP" worktree remove "$WORK/manual2/dup"
git -C "$APP" branch -qD dupbr
run_in "$APP" "$SCRIPT" remove dup --delete-branch
expect_success "P12 cleanup dup"

# --- P13: post-setup hook is the worktree's own copy ---------------------------------------
printf '#!/bin/sh\necho dirty > hook-output.txt\n' > "$APP/.worktree-setup.sh"
run_in "$APP" "$SCRIPT" create hk --json
expect_success "P13 create hk succeeds"
HK_PATH=$(pyget "$OUT" "d['path']")
assert_eq "P13 dirty hook edit does not leak into worktree" "$(cat "$HK_PATH/hook-output.txt")" "committed"
git -C "$APP" checkout -q -- .worktree-setup.sh
run_in "$APP" "$SCRIPT" remove hk --delete-branch
expect_success "P13 cleanup hk"

cat > "$APP/.worktree.json" <<'EOF'
{
    "postSetup": "custom-hook.sh"
}
EOF
run_in "$APP" "$SCRIPT" create hk2 --json
expect_success "P13 create hk2 with relative postSetup succeeds"
HK2_PATH=$(pyget "$OUT" "d['path']")
assert_eq "P13 relative postSetup resolves inside worktree" "$(cat "$HK2_PATH/hook-output.txt")" "custom"
run_in "$APP" "$SCRIPT" remove hk2 --delete-branch
expect_success "P13 cleanup hk2"
rm -f "$APP/.worktree.json"

# --- P14: list ---------------------------------------------------------------------------------
run_in "$APP" "$SCRIPT" create l1 --json
expect_success "P14 create l1 succeeds"
L1_PATH=$(pyget "$OUT" "d['path']")
git -C "$APP" worktree add -q "$DEST_DEFAULT/lman" -b lmanbr develop

run_in "$APP" "$SCRIPT" list --json
expect_success "P14 list succeeds"
assert_eq "P14 l1 createdByTool true" "$(pyget "$OUT" "[e for e in d if e['path'].endswith('/l1')][0]['createdByTool']")" "True"
assert_eq "P14 l1 base recorded" "$(pyget "$OUT" "[e for e in d if e['path'].endswith('/l1')][0]['base']")" "develop"
assert_eq "P14 fresh branch mergedIntoBase true" "$(pyget "$OUT" "[e for e in d if e['path'].endswith('/l1')][0]['mergedIntoBase']")" "True"
assert_eq "P14 fresh clean branch canDeleteBranch true" "$(pyget "$OUT" "[e for e in d if e['path'].endswith('/l1')][0]['canDeleteBranch']")" "True"
assert_eq "P14 l1 underCurrentDestination true" "$(pyget "$OUT" "[e for e in d if e['path'].endswith('/l1')][0]['underCurrentDestination']")" "True"
assert_eq "P14 manual worktree createdByTool false despite location" "$(pyget "$OUT" "[e for e in d if e['path'].endswith('/lman')][0]['createdByTool']")" "False"
assert_eq "P14 manual worktree underCurrentDestination true" "$(pyget "$OUT" "[e for e in d if e['path'].endswith('/lman')][0]['underCurrentDestination']")" "True"
assert_eq "P14 main checkout createdByTool false" "$(pyget "$OUT" "[e for e in d if e['path'] == '$APP'][0]['createdByTool']")" "False"

printf 'commit me\n' >> "$L1_PATH/composer.json"
git -C "$L1_PATH" commit -aqm 'work on l1'
run_in "$APP" "$SCRIPT" list --json
expect_success "P14 list after commit succeeds"
assert_eq "P14 unmerged commit flips mergedIntoBase false" "$(pyget "$OUT" "[e for e in d if e['path'].endswith('/l1')][0]['mergedIntoBase']")" "False"
assert_eq "P14 unmerged commit flips canDeleteBranch false" "$(pyget "$OUT" "[e for e in d if e['path'].endswith('/l1')][0]['canDeleteBranch']")" "False"

printf 'uncommitted\n' >> "$L1_PATH/composer.json"
run_in "$APP" "$SCRIPT" list --json
expect_success "P14 list with dirty worktree succeeds"
assert_eq "P14 dirty flag true" "$(pyget "$OUT" "[e for e in d if e['path'].endswith('/l1')][0]['dirty']")" "True"
git -C "$L1_PATH" checkout -q -- composer.json

git -C "$APP" checkout -q develop
git -C "$APP" merge -q wt/l1
git -C "$APP" checkout -q main
run_in "$APP" "$SCRIPT" list --json
expect_success "P14 list after merge succeeds"
assert_eq "P14 merge flips mergedIntoBase true" "$(pyget "$OUT" "[e for e in d if e['path'].endswith('/l1')][0]['mergedIntoBase']")" "True"
assert_eq "P14 merge flips canDeleteBranch true" "$(pyget "$OUT" "[e for e in d if e['path'].endswith('/l1')][0]['canDeleteBranch']")" "True"

run_in "$APP" "$SCRIPT" create lsp --dest "$WORK/space dir" --json
expect_success "P14 create in destination with space succeeds"
run_in "$APP" "$SCRIPT" list --json
expect_success "P14 list parses path containing a space"
assert_eq "P14 space-path entry present" "$(pyget "$OUT" "[e for e in d if e['path'].endswith('/lsp')][0]['branch']")" "wt/lsp"
run_in "$APP" "$SCRIPT" remove lsp --delete-branch
expect_success "P14 cleanup lsp"

git -C "$APP" worktree remove "$DEST_DEFAULT/lman"
git -C "$APP" branch -qD lmanbr
run_in "$APP" "$SCRIPT" remove l1 --delete-branch
expect_success "P14 cleanup l1"

# --- P15: config --write and config read ------------------------------------------------------
GOOD_CONFIG='{"baseBranch":"develop","branchPrefix":"plan/","bootstrap":{"npm":false},"postSetup":null}'
run_in_stdin "$APP" "$GOOD_CONFIG" "$SCRIPT" config --write
expect_success "P15 config --write accepts valid configuration"
assert_file "P15 .worktree.json written" "$APP/.worktree.json"
assert_eq "P15 written file parses with branchPrefix" "$(python3 -c "import json;print(json.load(open('$APP/.worktree.json'))['branchPrefix'])")" "plan/"

for bad_payload in '{"foo":1}' '{"baseBranch":5}' '{"bootstrap":{"copyEnv":"yes"}}' '{"destination":"sub"}' '{"branchPrefix":"bad~/"}' 'not json'; do
    run_in_stdin "$APP" "$bad_payload" "$SCRIPT" config --write
    expect_failure "P15 config --write rejects [$bad_payload]"
done
assert_eq "P15 rejected writes do not clobber the file" "$(python3 -c "import json;print(json.load(open('$APP/.worktree.json'))['branchPrefix'])")" "plan/"

run_in "$APP" "$SCRIPT" config
expect_success "P15 config read succeeds"
assert_eq "P15 resolved baseBranch" "$(pyget "$OUT" "d['baseBranch']")" "develop"
assert_eq "P15 resolved branchPrefix" "$(pyget "$OUT" "d['branchPrefix']")" "plan/"
rm -f "$APP/.worktree.json"

# ===========================================================================
# C — session-scoped cleanup (plain repository)
# ===========================================================================
marker() { git -C "$1" config --get "branch.$2.$3" 2>/dev/null; }
wt_registered() { git -C "$1" worktree list --porcelain | grep -Fxq "worktree $2"; }
branch_exists() { git -C "$1" show-ref --verify --quiet "refs/heads/$2"; }

# --- C1: identity resolution and provenance markers -------------------------------------------
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" create c1 --json
expect_success "C1 create with WORKTREE_SESSION"
C1_PATH=$(pyget "$OUT" "d['path']")
assert_eq "C1 create reports the session" "$(pyget "$OUT" "d['session']")" "s1"
assert_eq "C1 session marker recorded" "$(marker "$APP" wt/c1 worktreeSession)" "s1"
assert_eq "C1 path marker equals the created path" "$(marker "$APP" wt/c1 worktreePath)" "$C1_PATH"
C1_CREATED=$(marker "$APP" wt/c1 worktreeCreated)
[[ $C1_CREATED =~ ^[0-9]+$ ]] || fail "C1 created marker is numeric" "got [$C1_CREATED]"
pass "C1 created marker is numeric"
assert_eq "C1 start marker equals the base tip" "$(marker "$APP" wt/c1 worktreeStart)" "$(git -C "$APP" rev-parse develop)"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" create c1b --session s2 --json
expect_success "C1 create with --session"
assert_eq "C1 --session overrides the variable" "$(marker "$APP" wt/c1b worktreeSession)" "s2"
run_in "$APP" env CLAUDE_CODE_SESSION_ID=cl1 "$SCRIPT" create c1c --json
expect_success "C1 create under CLAUDE_CODE_SESSION_ID"
assert_eq "C1 CLAUDE_CODE_SESSION_ID honoured" "$(marker "$APP" wt/c1c worktreeSession)" "cl1"
run_in "$APP" env CODEX_SESSION_ID=x1 CODEX_THREAD_ID=t1 "$SCRIPT" create c1d --json
expect_success "C1 create under both Codex variables"
assert_eq "C1 CODEX_SESSION_ID wins over CODEX_THREAD_ID" "$(marker "$APP" wt/c1d worktreeSession)" "x1"
run_in "$APP" env CODEX_THREAD_ID=t1 "$SCRIPT" create c1e --json
expect_success "C1 create under CODEX_THREAD_ID alone"
assert_eq "C1 CODEX_THREAD_ID honoured" "$(marker "$APP" wt/c1e worktreeSession)" "t1"
run_in "$APP" "$SCRIPT" create c1f --json
expect_success "C1 create with no identity"
assert_eq "C1 no session marker without identity" "$(marker "$APP" wt/c1f worktreeSession)" ""
assert_eq "C1 path marker still written without identity" "$(marker "$APP" wt/c1f worktreePath)" "$(pyget "$OUT" "d['path']")"
run_in "$APP" "$SCRIPT" list --json
expect_success "C1 list succeeds"
assert_eq "C1 list session for c1" "$(pyget "$OUT" "[e for e in d if e['path'] == '$C1_PATH'][0]['session']")" "s1"
assert_eq "C1 list session null without identity" "$(pyget "$OUT" "[e for e in d if e['path'].endswith('/c1f')][0]['session']")" "None"
assert_eq "C1 list recordedPath" "$(pyget "$OUT" "[e for e in d if e['path'] == '$C1_PATH'][0]['recordedPath']")" "$C1_PATH"
assert_eq "C1 list createdAt" "$(pyget "$OUT" "[e for e in d if e['path'] == '$C1_PATH'][0]['createdAt']")" "$C1_CREATED"
run_in "$APP" "$SCRIPT" remove c1 --delete-branch --json
expect_success "C1 remove --delete-branch"
for key in worktreeBase worktreePath worktreeCreated worktreeStart worktreeSession; do
    assert_eq "C1 remove unsets $key" "$(marker "$APP" wt/c1 "$key")" ""
done
for name in c1b c1c c1d c1e c1f; do
    run_in "$APP" "$SCRIPT" remove "$name" --delete-branch --json
    expect_success "C1 tidy $name"
done

# --- C2: refusal without an identity ------------------------------------------------------------
run_in "$APP" "$SCRIPT" cleanup --json
LAST_JSON=$OUT
expect_failure "C2 cleanup refuses without an identity"
assert_contains "C2 refusal names --session" "$ERR" "--session"
assert_contains "C2 refusal names WORKTREE_SESSION" "$ERR" "WORKTREE_SESSION"

# --- C3: the report is read-only and session-scoped ---------------------------------------------
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" create cs --json
expect_success "C3 create owned safe"
CS_PATH=$(pyget "$OUT" "d['path']")
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" create cd --json
expect_success "C3 create owned dirty"
CD_PATH=$(pyget "$OUT" "d['path']")
printf 'uncommitted\n' > "$CD_PATH/dirty.txt"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" create cu --json
expect_success "C3 create owned unmerged"
CU_PATH=$(pyget "$OUT" "d['path']")
printf 'change\n' >> "$CU_PATH/composer.json"
git -C "$CU_PATH" commit -aqm 'unmerged work'
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" create cm --json
expect_success "C3 create owned merged"
CM_PATH=$(pyget "$OUT" "d['path']")
printf 'merged change\n' >> "$CM_PATH/package.json"
git -C "$CM_PATH" commit -aqm 'merged work'
git -C "$APP" checkout -q develop
git -C "$APP" merge -q --no-ff wt/cm -m 'merge cm into develop'
git -C "$APP" checkout -q main
run_in "$APP" env WORKTREE_SESSION=s2 "$SCRIPT" create co --json
expect_success "C3 create other-session"
CO_PATH=$(pyget "$OUT" "d['path']")
run_in "$APP" "$SCRIPT" create cn --json
expect_success "C3 create untagged managed"
CN_PATH=$(pyget "$OUT" "d['path']")
git -C "$APP" worktree add -q "$WORK/manual/c3hand" -b c3handbr develop
SNAP_C3=$(snap "$APP"); HEAD_C3=$(head_of "$APP"); BRANCH_C3=$(branch_of "$APP")
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --json
LAST_JSON=$OUT
expect_success "C3 report succeeds"
assert_eq "C3 report names the session" "$(pyget "$OUT" "d['session']")" "s1"
assert_eq "C3 report is not applied" "$(pyget "$OUT" "d['applied']")" "False"
assert_eq "C3 one repository in scope" "$(pyget "$OUT" "len(d['repositories'])")" "1"
assert_eq "C3 repository path is the main checkout" "$(pyget "$OUT" "d['repositories'][0]['path']")" "$APP"
assert_eq "C3 exactly the four owned worktrees are candidates" "$(pyget "$OUT" "sorted(w['path'] for w in d['repositories'][0]['worktrees'])")" "$(python3 -c "print(sorted(['$CS_PATH','$CD_PATH','$CU_PATH','$CM_PATH']))")"
assert_eq "C3 other, untagged, manual counted as not considered" "$(pyget "$OUT" "d['repositories'][0]['notConsidered']")" "3"
cs_entry() { pyget "$LAST_JSON" "[w for w in d['repositories'][0]['worktrees'] if w['path'] == '$1'][0]$2"; }
assert_eq "C3 safe worktree id" "$(cs_entry "$CS_PATH" "['id']")" "wt:$CS_PATH"
assert_eq "C3 safe worktree verdict" "$(cs_entry "$CS_PATH" "['safe']")" "True"
assert_eq "C3 safe worktree reason unused" "$(cs_entry "$CS_PATH" "['reason']")" "unused"
assert_eq "C3 safe worktree action candidate" "$(cs_entry "$CS_PATH" "['action']")" "candidate"
assert_eq "C3 merged worktree reason merged" "$(cs_entry "$CM_PATH" "['reason']")" "merged"
assert_eq "C3 merged worktree safe" "$(cs_entry "$CM_PATH" "['safe']")" "True"
assert_eq "C3 dirty worktree unsafe" "$(cs_entry "$CD_PATH" "['safe']")" "False"
assert_eq "C3 dirty worktree reason" "$(cs_entry "$CD_PATH" "['reason']")" "dirty"
assert_eq "C3 dirty flag" "$(cs_entry "$CD_PATH" "['dirty']")" "True"
assert_eq "C3 unmerged worktree reason" "$(cs_entry "$CU_PATH" "['reason']")" "unmerged"
assert_eq "C3 unmerged commits ahead of base" "$(cs_entry "$CU_PATH" "['commitsAheadOfBase']")" "1"
assert_eq "C3 unmerged mergedIntoBase false" "$(cs_entry "$CU_PATH" "['mergedIntoBase']")" "False"
assert_eq "C3 tip is the branch head" "$(cs_entry "$CS_PATH" "['tip']")" "$(git -C "$APP" rev-parse wt/cs)"
assert_eq "C3 no orphan branches yet" "$(pyget "$OUT" "len(d['repositories'][0]['branches'])")" "0"
for path in "$CS_PATH" "$CD_PATH" "$CU_PATH" "$CM_PATH" "$CO_PATH" "$CN_PATH" "$WORK/manual/c3hand"; do
    [ -d "$path" ] || fail "C3 report is read-only" "$path vanished"
done
pass "C3 report leaves every worktree in place"
assert_eq "C3 main checkout status unchanged" "$(snap "$APP")" "$SNAP_C3"
assert_eq "C3 main checkout HEAD unchanged" "$(head_of "$APP")" "$HEAD_C3"
assert_eq "C3 main checkout branch unchanged" "$(branch_of "$APP")" "$BRANCH_C3"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup
LAST_JSON=$OUT
expect_success "C3 human report succeeds"
assert_contains "C3 human report states the session-only scope" "$OUT" "created by this session"
assert_contains "C3 human report names the session" "$OUT" "s1"

# --- C4: apply removes exactly the named targets ------------------------------------------------
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --remove "wt:$CS_PATH" --json
LAST_JSON=$OUT
expect_failure "C4 --remove without --apply is refused"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$CS_PATH" --json
LAST_JSON=$OUT
expect_success "C4 apply removes the requested safe worktree"
assert_eq "C4 applied flag" "$(pyget "$OUT" "d['applied']")" "True"
assert_eq "C4 target action removed" "$(cs_entry "$CS_PATH" "['action']")" "removed"
assert_eq "C4 target branch deleted" "$(cs_entry "$CS_PATH" "['branchDeleted']")" "True"
assert_not_exists "C4 target directory gone" "$CS_PATH"
run_in "$APP" git show-ref --verify --quiet refs/heads/wt/cs
expect_failure "C4 target branch gone"
assert_eq "C4 target markers unset" "$(marker "$APP" wt/cs worktreeSession)" ""
assert_eq "C4 merged candidate not requested is left" "$(cs_entry "$CM_PATH" "['action']")" "left"
assert_eq "C4 not-requested reason" "$(cs_entry "$CM_PATH" "['reason']")" "not-requested"
[ -d "$CM_PATH" ] || fail "C4 unrequested candidate untouched" "$CM_PATH vanished"
pass "C4 unrequested candidate untouched"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$CD_PATH" --json
LAST_JSON=$OUT
expect_failure "C4 requesting a dirty worktree exits non-zero"
assert_eq "C4 dirty target left" "$(cs_entry "$CD_PATH" "['action']")" "left"
assert_eq "C4 dirty target reason" "$(cs_entry "$CD_PATH" "['reason']")" "dirty"
[ -d "$CD_PATH" ] || fail "C4 dirty worktree still present" "$CD_PATH vanished"
pass "C4 dirty worktree still present"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$CU_PATH" --json
LAST_JSON=$OUT
expect_failure "C4 requesting an unmerged worktree exits non-zero"
assert_eq "C4 unmerged target reason" "$(cs_entry "$CU_PATH" "['reason']")" "unmerged"
run_in "$APP" git show-ref --verify --quiet refs/heads/wt/cu
expect_success "C4 unmerged branch still present"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$CO_PATH" --json
LAST_JSON=$OUT
expect_failure "C4 another session's worktree is an unknown identifier"
assert_contains "C4 unknown identifier named" "$ERR" "wt:$CO_PATH"
[ -d "$CO_PATH" ] || fail "C4 other-session worktree untouched" "$CO_PATH vanished"
pass "C4 other-session worktree untouched"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$WORK/nowhere" --json
LAST_JSON=$OUT
expect_failure "C4 unknown path is an error"
for path in "$CD_PATH" "$CU_PATH" "$CM_PATH" "$CO_PATH" "$CN_PATH" "$WORK/manual/c3hand"; do
    [ -d "$path" ] || fail "C4 foreign and unrequested worktrees intact" "$path vanished"
done
pass "C4 foreign and unrequested worktrees intact"
for b in wt/co wt/cn c3handbr wt/cd wt/cu wt/cm; do
    branch_exists "$APP" "$b" || fail "C4 branches intact" "$b vanished"
done
pass "C4 branches intact"
assert_eq "C4 main checkout status unchanged" "$(snap "$APP")" "$SNAP_C3"
assert_eq "C4 main checkout HEAD unchanged" "$(head_of "$APP")" "$HEAD_C3"
assert_eq "C4 main checkout branch unchanged" "$(branch_of "$APP")" "$BRANCH_C3"

# --- C5: apply re-validates from live state ----------------------------------------------------
printf 'late edit\n' > "$CM_PATH/late.txt"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$CM_PATH" --json
LAST_JSON=$OUT
expect_failure "C5 target that became dirty is left"
assert_eq "C5 reason dirty" "$(cs_entry "$CM_PATH" "['reason']")" "dirty"
[ -d "$CM_PATH" ] || fail "C5 dirty target present" "$CM_PATH vanished"
pass "C5 dirty target present"
git -C "$CM_PATH" add late.txt && git -C "$CM_PATH" commit -qm 'late commit'
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$CM_PATH" --json
LAST_JSON=$OUT
expect_failure "C5 target that gained a commit is left"
assert_eq "C5 reason unmerged" "$(cs_entry "$CM_PATH" "['reason']")" "unmerged"
run_in "$APP" git show-ref --verify --quiet refs/heads/wt/cm
expect_success "C5 branch with the late commit survives"

# --- C6: expected-tip deletion and checked-out-elsewhere ----------------------------------------
git -C "$APP" branch c6 develop
run_in "$APP" bash -c "source '$SCRIPT' && delete_branch_at_tip c6 0000000000000000000000000000000000000001"
expect_failure "C6 deletion with a stale tip is refused"
run_in "$APP" git show-ref --verify --quiet refs/heads/c6
expect_success "C6 branch intact after refusal"
run_in "$APP" bash -c "source '$SCRIPT' && delete_branch_at_tip c6 \$(git rev-parse c6)"
expect_success "C6 deletion with the current tip succeeds"
run_in "$APP" git show-ref --verify --quiet refs/heads/c6
expect_failure "C6 branch gone"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" create c6w --json
expect_success "C6 create owned"
C6_PATH=$(pyget "$OUT" "d['path']")
git -C "$APP" worktree add -q -f "$WORK/manual/c6twin" wt/c6w
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$C6_PATH" --json
LAST_JSON=$OUT
expect_failure "C6 branch checked out elsewhere: worktree removed, branch left, non-zero"
assert_not_exists "C6 owned worktree directory gone" "$C6_PATH"
assert_eq "C6 removed flag" "$(cs_entry "$C6_PATH" "['removed']")" "True"
assert_eq "C6 branch not deleted" "$(cs_entry "$C6_PATH" "['branchDeleted']")" "False"
assert_eq "C6 reason checked-out-elsewhere" "$(cs_entry "$C6_PATH" "['reason']")" "checked-out-elsewhere"
run_in "$APP" git show-ref --verify --quiet refs/heads/wt/c6w
expect_success "C6 branch survives"
git -C "$APP" worktree remove --force "$WORK/manual/c6twin"

# --- C7: orphan branches and prunable registrations ---------------------------------------------
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --json
LAST_JSON=$OUT
expect_success "C7 report after C6"
assert_eq "C7 c6w is now an orphan candidate" "$(pyget "$OUT" "[b['id'] for b in d['repositories'][0]['branches']]")" "['br:$APP:wt/c6w']"
assert_eq "C7 orphan unused and safe" "$(pyget "$OUT" "d['repositories'][0]['branches'][0]['reason']")" "unused"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "br:$APP:wt/c6w" --json
LAST_JSON=$OUT
expect_success "C7 orphan deleted on request"
assert_eq "C7 orphan action" "$(pyget "$OUT" "d['repositories'][0]['branches'][0]['action']")" "removed"
run_in "$APP" git show-ref --verify --quiet refs/heads/wt/c6w
expect_failure "C7 orphan branch gone"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" create c7u --json
expect_success "C7 create unmerged orphan source"
C7U_PATH=$(pyget "$OUT" "d['path']")
printf 'x\n' >> "$C7U_PATH/composer.json" && git -C "$C7U_PATH" commit -aqm 'orphan work'
git -C "$APP" worktree remove --force "$C7U_PATH"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "br:$APP:wt/c7u" --json
LAST_JSON=$OUT
expect_failure "C7 unmerged orphan is left"
assert_eq "C7 unmerged orphan reason" "$(pyget "$OUT" "[b for b in d['repositories'][0]['branches'] if b['branch'] == 'wt/c7u'][0]['reason']")" "unmerged"
run_in "$APP" git show-ref --verify --quiet refs/heads/wt/c7u
expect_success "C7 unmerged orphan branch survives"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" create c7p --json
expect_success "C7 create prunable source"
C7P_PATH=$(pyget "$OUT" "d['path']")
run_in "$APP" env WORKTREE_SESSION=s2 "$SCRIPT" create c7f --json
expect_success "C7 create foreign prunable source"
C7F_PATH=$(pyget "$OUT" "d['path']")
rm -rf "$C7P_PATH" "$C7F_PATH"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --json
LAST_JSON=$OUT
expect_success "C7 report with prunable registrations"
assert_eq "C7 prunable owned worktree reported" "$(cs_entry "$C7P_PATH" "['prunable']")" "True"
assert_eq "C7 prunable owned worktree safe" "$(cs_entry "$C7P_PATH" "['safe']")" "True"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$C7P_PATH" --json
LAST_JSON=$OUT
expect_success "C7 prunable owned registration removed"
assert_eq "C7 prunable branch deleted" "$(cs_entry "$C7P_PATH" "['branchDeleted']")" "True"
wt_registered "$APP" "$C7P_PATH" && fail "C7 owned registration gone" "still registered"
pass "C7 owned registration gone"
wt_registered "$APP" "$C7F_PATH" || fail "C7 foreign prunable registration untouched" "was pruned"
pass "C7 foreign prunable registration untouched"

# --- C8: ownership needs the recorded path as well as the branch marker --------------------------
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" create c8 --json
expect_success "C8 create owned"
C8_PATH=$(pyget "$OUT" "d['path']")
git -C "$APP" worktree remove "$C8_PATH"
git -C "$APP" worktree add -q "$WORK/manual/c8hand" wt/c8
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --json
LAST_JSON=$OUT
expect_success "C8 report"
assert_eq "C8 hand-made worktree on an owned branch is not a candidate" "$(pyget "$OUT" "[w for w in d['repositories'][0]['worktrees'] if w['branch'] == 'wt/c8']")" "[]"
assert_eq "C8 checked-out owned branch is not an orphan" "$(pyget "$OUT" "[b for b in d['repositories'][0]['branches'] if b['branch'] == 'wt/c8']")" "[]"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$WORK/manual/c8hand" --json
LAST_JSON=$OUT
expect_failure "C8 hand-made worktree cannot be requested"
[ -d "$WORK/manual/c8hand" ] || fail "C8 hand-made worktree intact" "vanished"
pass "C8 hand-made worktree intact"
git -C "$APP" worktree remove "$WORK/manual/c8hand"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --json
LAST_JSON=$OUT
expect_success "C8 report after hand-made removal"
assert_eq "C8 branch becomes an orphan candidate" "$(pyget "$OUT" "[b['id'] for b in d['repositories'][0]['branches'] if b['branch'] == 'wt/c8']")" "['br:$APP:wt/c8']"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "br:$APP:wt/c8" --json
LAST_JSON=$OUT
expect_success "C8 tidy orphan"

# --- C9: current directory, locks, missing base -------------------------------------------------
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" create c9 --json
expect_success "C9 create owned"
C9_PATH=$(pyget "$OUT" "d['path']")
run_in "$C9_PATH" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$C9_PATH" --json
LAST_JSON=$OUT
expect_failure "C9 current directory is never removed"
assert_eq "C9 reason current-directory" "$(cs_entry "$C9_PATH" "['reason']")" "current-directory"
[ -d "$C9_PATH" ] || fail "C9 current worktree present" "vanished"
pass "C9 current worktree present"
git -C "$APP" worktree lock "$C9_PATH"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$C9_PATH" --json
LAST_JSON=$OUT
expect_failure "C9 locked worktree is left"
assert_eq "C9 reason locked" "$(cs_entry "$C9_PATH" "['reason']")" "locked"
git -C "$APP" worktree unlock "$C9_PATH"
git -C "$APP" branch tmpbase develop
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" create c9b --from tmpbase --json
expect_success "C9 create from a temporary base"
C9B_PATH=$(pyget "$OUT" "d['path']")
git -C "$APP" branch -qD tmpbase
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$C9B_PATH" --json
LAST_JSON=$OUT
expect_failure "C9 missing base is left"
assert_eq "C9 reason base-missing" "$(cs_entry "$C9B_PATH" "['reason']")" "base-missing"
assert_eq "C9 baseExists false" "$(cs_entry "$C9B_PATH" "['baseExists']")" "False"
run_in "$APP" git show-ref --verify --quiet refs/heads/wt/c9b
expect_success "C9 branch with missing base survives"
run_in "$APP" "$SCRIPT" remove c9b --force
expect_success "C9 tidy c9b"
git -C "$APP" branch -qD wt/c9b
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$C9_PATH" --json
LAST_JSON=$OUT
expect_success "C9 tidy c9"

# --- C10: lock contention on branch deletion -----------------------------------------------------
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" create c10 --json
expect_success "C10 create owned"
C10_PATH=$(pyget "$OUT" "d['path']")
mkdir -p "$APP/.git/refs/heads/wt"
: > "$APP/.git/refs/heads/wt/c10.lock"
( sleep 1; rm -f "$APP/.git/refs/heads/wt/c10.lock" ) &
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$C10_PATH" --json
LAST_JSON=$OUT
wait
expect_success "C10 deletion succeeds once the lock is released"
assert_eq "C10 branch deleted on retry" "$(cs_entry "$C10_PATH" "['branchDeleted']")" "True"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" create c10b --json
expect_success "C10 create owned (held lock)"
C10B_PATH=$(pyget "$OUT" "d['path']")
: > "$APP/.git/refs/heads/wt/c10b.lock"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$C10B_PATH" --json
LAST_JSON=$OUT
expect_failure "C10 held lock: non-zero exit"
assert_eq "C10 held lock: worktree removed" "$(cs_entry "$C10B_PATH" "['removed']")" "True"
assert_eq "C10 held lock: branch left" "$(cs_entry "$C10B_PATH" "['branchDeleted']")" "False"
assert_eq "C10 held lock: reason" "$(cs_entry "$C10B_PATH" "['reason']")" "lock-contention"
rm -f "$APP/.git/refs/heads/wt/c10b.lock"
run_in "$APP" git show-ref --verify --quiet refs/heads/wt/c10b
expect_success "C10 held lock: branch survives"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "br:$APP:wt/c10b" --json
LAST_JSON=$OUT
expect_success "C10 tidy orphan"

# --- C11: identifiers do not cross repositories -------------------------------------------------
APP2="$WORK/app2"
make_source_repo "$APP2"
run_in "$APP2" env WORKTREE_SESSION=s1 "$SCRIPT" create same --json
expect_success "C11 create in the second repository"
APP2_SAME=$(pyget "$OUT" "d['path']")
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" create same --json
expect_success "C11 create in the first repository"
APP_SAME=$(pyget "$OUT" "d['path']")
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$APP2_SAME" --json
LAST_JSON=$OUT
expect_failure "C11 the other repository's identifier is unknown here"
[ -d "$APP2_SAME" ] || fail "C11 other repository's worktree intact" "vanished"
pass "C11 other repository's worktree intact"
run_in "$APP" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$APP_SAME" --json
LAST_JSON=$OUT
expect_success "C11 own identifier removed"
run_in "$APP2" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$APP2_SAME" --json
LAST_JSON=$OUT
expect_success "C11 tidy second repository"

# --- C tidy: leave the fixture as the P cases left it --------------------------------------------
run_in "$APP" "$SCRIPT" remove cd --force
expect_success "C tidy cd"
run_in "$APP" "$SCRIPT" remove cu --delete-branch --force
expect_success "C tidy cu"
run_in "$APP" "$SCRIPT" remove cm --delete-branch --force
expect_success "C tidy cm"
run_in "$APP" "$SCRIPT" remove co --delete-branch
expect_success "C tidy co"
run_in "$APP" "$SCRIPT" remove cn --delete-branch
expect_success "C tidy cn"
git -C "$APP" worktree remove "$WORK/manual/c3hand"
git -C "$APP" worktree prune
git -C "$APP" branch -qD c3handbr wt/cd wt/c7u wt/c7f 2>/dev/null || true

# --- P16: final main-checkout invariants ---------------------------------------------------------
assert_eq "P16 main checkout status unchanged after all tests" "$(snap "$APP")" "$SNAP_0"
assert_eq "P16 main checkout HEAD unchanged after all tests" "$(head_of "$APP")" "$HEAD_0"
assert_eq "P16 main checkout branch unchanged after all tests" "$(branch_of "$APP")" "$BRANCH_0"

# ===========================================================================
# Fixture 2 — superproject + submodule (stock clone: develop is remote-only)
# ===========================================================================
UPSTREAM="$WORK/upstream"
make_source_repo "$UPSTREAM"
SUPER="$WORK/super"
mkdir -p "$SUPER"
(
    cd "$SUPER" || exit 1
    git init -q -b main
    git commit -q --allow-empty -m 'initial'
    git -c protocol.file.allow=always submodule add -q "$UPSTREAM" sub
    git commit -qm 'add submodule'
)
SUB="$SUPER/sub"
printf 'APP_KEY=subsecret\n' > "$SUB/.env"
printf 'in-flight work\n' > "$SUB/wip.txt"

run_in "$SUB" git show-ref --verify --quiet refs/heads/develop
expect_failure "S0 precondition: no local develop in submodule clone"

SUB_SNAP_0=$(snap "$SUB")
SUB_HEAD_0=$(head_of "$SUB")
SUB_BRANCH_0=$(branch_of "$SUB")
SUPER_SNAP_0=$(snap "$SUPER")

# --- S1: create from inside the submodule -------------------------------------------------------
: > "$SHIM_LOG"
run_in "$SUB" "$SCRIPT" create sm1 --json
expect_success "S1 create inside submodule succeeds"
SM1_PATH=$(pyget "$OUT" "d['path']")
assert_eq "S1 destination is sibling of the SUPERPROJECT" "$SM1_PATH" "$WORK/sub-worktrees/sm1"
assert_eq "S1 base resolved from origin/develop" "$(pyget "$OUT" "d['base']")" "origin/develop"
assert_eq "S1 branch is wt/sm1" "$(pyget "$OUT" "d['branch']")" "wt/sm1"
assert_eq "S1 worktreeBase marker records remote base" "$(git -C "$SUB" config --get branch.wt/sm1.worktreeBase)" "origin/develop"
assert_file "S1 .env copied" "$SM1_PATH/.env"
assert_eq "S1 worktree clean" "$(snap "$SM1_PATH")" ""
assert_contains "S1 composer ran inside worktree" "$(cat "$SHIM_LOG")" "composer:$SM1_PATH:install --no-interaction"
assert_eq "S1 worktree HEAD equals upstream develop" "$(head_of "$SM1_PATH")" "$(git -C "$UPSTREAM" rev-parse develop)"
run_in "$SUB" git show-ref --verify --quiet refs/heads/develop
expect_failure "S1 no local develop branch created by resolution"

# --- S2: destination inside the superproject aborts -----------------------------------------------
run_in "$SUB" "$SCRIPT" create sm2 --dest "$SUPER/wt"
expect_failure "S2 destination inside superproject aborts"
assert_contains "S2 message names the superproject rule" "$ERR" "superproject"

# --- S3: remove from inside the submodule ----------------------------------------------------------
run_in "$SUB" "$SCRIPT" remove sm1 --delete-branch --json
expect_success "S3 remove inside submodule succeeds"
assert_not_exists "S3 worktree gone" "$SM1_PATH"
run_in "$SUB" git show-ref --verify --quiet refs/heads/wt/sm1
expect_failure "S3 branch deleted"

# --- S4: submodule and superproject invariants ------------------------------------------------------
assert_eq "S4 submodule status unchanged" "$(snap "$SUB")" "$SUB_SNAP_0"
assert_eq "S4 submodule HEAD unchanged" "$(head_of "$SUB")" "$SUB_HEAD_0"
assert_eq "S4 submodule branch unchanged" "$(branch_of "$SUB")" "$SUB_BRANCH_0"
assert_eq "S4 superproject status unchanged" "$(snap "$SUPER")" "$SUPER_SNAP_0"

# --- S5: cleanup recurses into submodules from the superproject ----------------------------------
run_in "$SUB" env WORKTREE_SESSION=s1 "$SCRIPT" create sc1 --json
expect_success "S5 create owned in the submodule"
SC1_PATH=$(pyget "$OUT" "d['path']")
run_in "$SUPER" env WORKTREE_SESSION=s1 "$SCRIPT" create sp1 --json
expect_success "S5 create owned in the superproject"
SP1_PATH=$(pyget "$OUT" "d['path']")
SUB_SNAP_5=$(snap "$SUB"); SUB_HEAD_5=$(head_of "$SUB"); SUB_BRANCH_5=$(branch_of "$SUB"); SUPER_SNAP_5=$(snap "$SUPER")
run_in "$SUPER" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --json
LAST_JSON=$OUT
expect_success "S5 recursive report from the superproject"
assert_eq "S5 two repositories in scope" "$(pyget "$OUT" "[r['path'] for r in d['repositories']]")" "['$SUPER', '$SUB']"
assert_eq "S5 submodule worktree listed under the submodule" "$(pyget "$OUT" "[w['id'] for w in d['repositories'][1]['worktrees']]")" "['wt:$SC1_PATH']"
assert_eq "S5 superproject worktree listed under the superproject" "$(pyget "$OUT" "[w['id'] for w in d['repositories'][0]['worktrees']]")" "['wt:$SP1_PATH']"
run_in "$SUPER" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --no-recurse --json
LAST_JSON=$OUT
expect_success "S5 --no-recurse report"
assert_eq "S5 --no-recurse covers the superproject only" "$(pyget "$OUT" "[r['path'] for r in d['repositories']]")" "['$SUPER']"
run_in "$SUB" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --json
LAST_JSON=$OUT
expect_success "S5 report from inside the submodule"
assert_eq "S5 from the submodule, the superproject is out of scope" "$(pyget "$OUT" "[r['path'] for r in d['repositories']]")" "['$SUB']"
run_in "$SUPER" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$SC1_PATH" --json
LAST_JSON=$OUT
expect_success "S5 apply from the superproject removes the submodule worktree"
assert_not_exists "S5 submodule worktree gone" "$SC1_PATH"
run_in "$SUB" git show-ref --verify --quiet refs/heads/wt/sc1
expect_failure "S5 submodule branch deleted"
[ -d "$SP1_PATH" ] || fail "S5 unrequested superproject worktree intact" "vanished"
pass "S5 unrequested superproject worktree intact"
run_in "$SUPER" env WORKTREE_SESSION=s1 "$SCRIPT" cleanup --apply --remove "wt:$SP1_PATH" --json
LAST_JSON=$OUT
expect_success "S5 tidy superproject worktree"
assert_eq "S5 submodule status unchanged" "$(snap "$SUB")" "$SUB_SNAP_5"
assert_eq "S5 submodule HEAD unchanged" "$(head_of "$SUB")" "$SUB_HEAD_5"
assert_eq "S5 submodule branch unchanged" "$(branch_of "$SUB")" "$SUB_BRANCH_5"
assert_eq "S5 superproject status unchanged" "$(snap "$SUPER")" "$SUPER_SNAP_5"

# --- S6: final invariants after cleanup cases ----------------------------------------------------
assert_eq "S6 submodule status unchanged after all tests" "$(snap "$SUB")" "$SUB_SNAP_0"
assert_eq "S6 submodule HEAD unchanged after all tests" "$(head_of "$SUB")" "$SUB_HEAD_0"
assert_eq "S6 submodule branch unchanged after all tests" "$(branch_of "$SUB")" "$SUB_BRANCH_0"
assert_eq "S6 superproject status unchanged after all tests" "$(snap "$SUPER")" "$SUPER_SNAP_0"

printf '\nAll %d assertions passed.\n' "$PASS_COUNT"
