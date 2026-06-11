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

printf '\nAll %d assertions passed.\n' "$PASS_COUNT"
