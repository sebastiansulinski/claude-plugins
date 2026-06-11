#!/usr/bin/env bash
#
# worktree.sh — create, remove, list, and configure isolated git worktrees so
# multiple agents can work on different plans in the same repository without
# file collisions. Works on plain repositories and on submodules (a submodule
# is a complete git repository; git worktree handles its relocated git
# directory transparently).
#
# Subcommands:
#   create <name> [--from <branch>] [--dest <dir>]
#                 [--env|--no-env] [--composer|--no-composer] [--npm|--no-npm] [--json]
#   remove <name> [--delete-branch] [--force] [--unmanaged] [--json]
#   list   [--json]
#   config [--write]
#
# Configuration precedence: command-line flags -> .worktree.json (repository
# root) -> conventions. The zero-config convention path has no python3
# dependency; parsing .worktree.json requires python3.
#
# Concurrency note: concurrent processes hitting the shared git directory can
# transiently fail with index.lock contention — contention, not corruption.
# The create path retries once after a 2-second pause before giving up.
set -euo pipefail

JSON_MODE=0

die() {
    printf 'worktree.sh: %s\n' "$*" >&2
    exit 1
}

info() {
    if [ "$JSON_MODE" -eq 0 ]; then
        printf '%s\n' "$*"
    fi
}

json_escape() {
    local value=$1
    value=${value//\\/\\\\}
    value=${value//\"/\\\"}
    printf '%s' "$value"
}

physical_dir() {
    (cd "$1" 2>/dev/null && pwd -P)
}

# is_under <child> <parent> — true when child is strictly under parent.
is_under() {
    case $1 in
        "$2"/*) return 0 ;;
    esac
    return 1
}

REPO_ROOT="" SUPER_ROOT=""
resolve_repo() {
    local toplevel super
    if ! toplevel=$(git rev-parse --show-toplevel 2>/dev/null); then
        die "not inside a git repository"
    fi
    REPO_ROOT=$(physical_dir "$toplevel") || die "cannot resolve repository root '$toplevel'"
    SUPER_ROOT=""
    super=$(git rev-parse --show-superproject-working-tree 2>/dev/null || true)
    if [ -n "$super" ]; then
        SUPER_ROOT=$(physical_dir "$super") || die "cannot resolve superproject root '$super'"
    fi
}

CFG_BASE="" CFG_DEST="" CFG_PREFIX="" CFG_COPYENV="" CFG_COMPOSER="" CFG_NPM="" CFG_POSTSETUP=""
load_config() {
    local config_file="$REPO_ROOT/.worktree.json" parsed
    if [ ! -f "$config_file" ]; then
        return 0
    fi
    if ! command -v python3 >/dev/null 2>&1; then
        die ".worktree.json exists but python3 is required to parse it"
    fi
    if ! parsed=$(python3 - "$config_file" <<'PYEOF'
import json
import shlex
import sys

try:
    with open(sys.argv[1]) as handle:
        data = json.load(handle)
except Exception as error:
    sys.stderr.write(f"invalid JSON: {error}\n")
    raise SystemExit(1)
if not isinstance(data, dict):
    sys.stderr.write("configuration root must be a JSON object\n")
    raise SystemExit(1)
strings = {
    "baseBranch": "CFG_BASE",
    "destination": "CFG_DEST",
    "branchPrefix": "CFG_PREFIX",
    "postSetup": "CFG_POSTSETUP",
}
for key, variable in strings.items():
    value = data.get(key)
    if value is not None:
        print(f"{variable}={shlex.quote(str(value))}")
bootstrap = data.get("bootstrap") or {}
flags = {"copyEnv": "CFG_COPYENV", "composer": "CFG_COMPOSER", "npm": "CFG_NPM"}
for key, variable in flags.items():
    if isinstance(bootstrap, dict) and key in bootstrap and bootstrap[key] is not None:
        print(f"{variable}={'true' if bootstrap[key] else 'false'}")
PYEOF
    ); then
        die "invalid .worktree.json in $REPO_ROOT"
    fi
    eval "$parsed"
}

# verify_ref <candidate> — sets VERIFIED to the usable ref name, checking the
# local branch first, then the origin remote-tracking branch (a stock clone —
# including git submodule add — often has the base only as a remote ref), then
# any directly resolvable commit-ish.
VERIFIED=""
verify_ref() {
    local candidate=$1
    if git show-ref --verify --quiet "refs/heads/$candidate"; then
        VERIFIED=$candidate
        return 0
    fi
    if git show-ref --verify --quiet "refs/remotes/origin/$candidate"; then
        VERIFIED="origin/$candidate"
        return 0
    fi
    if git rev-parse --verify --quiet "${candidate}^{commit}" >/dev/null 2>&1; then
        VERIFIED=$candidate
        return 0
    fi
    return 1
}

BASE=""
resolve_base() {
    local requested=$1 origin_head
    if [ -n "$requested" ]; then
        if ! verify_ref "$requested"; then
            die "base branch '$requested' not found (local or origin)"
        fi
        BASE=$VERIFIED
        return 0
    fi
    if [ -n "$CFG_BASE" ]; then
        if ! verify_ref "$CFG_BASE"; then
            die "configured baseBranch '$CFG_BASE' not found (local or origin)"
        fi
        BASE=$VERIFIED
        return 0
    fi
    if verify_ref develop; then
        BASE=$VERIFIED
        return 0
    fi
    origin_head=$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null || true)
    if [ -n "$origin_head" ]; then
        BASE=$origin_head
        return 0
    fi
    if verify_ref main; then
        BASE=$VERIFIED
        return 0
    fi
    if verify_ref master; then
        BASE=$VERIFIED
        return 0
    fi
    die "could not resolve a base branch (tried develop, origin/HEAD, main, master)"
}

# resolve_dest <requested> <create|nocreate> — sets DEST to the destination
# directory holding all worktrees. Convention: sibling of the repository, or
# sibling of the SUPERPROJECT when the repository is a submodule (a sibling of
# the submodule would still sit inside the superproject's working tree).
DEST=""
resolve_dest() {
    local requested=$1 mode=$2 candidate anchor
    if [ -n "$requested" ]; then
        candidate=$requested
    elif [ -n "$CFG_DEST" ]; then
        candidate=$CFG_DEST
    else
        if [ -n "$SUPER_ROOT" ]; then
            anchor=$(dirname "$SUPER_ROOT")
        else
            anchor=$(dirname "$REPO_ROOT")
        fi
        candidate="$anchor/$(basename "$REPO_ROOT")-worktrees"
    fi
    case $candidate in
        /*) ;;
        *) candidate="$REPO_ROOT/$candidate" ;;
    esac
    validate_dest_outside "$candidate"
    if [ "$mode" = create ]; then
        mkdir -p "$candidate" || die "cannot create destination '$candidate'"
    fi
    if [ -d "$candidate" ]; then
        DEST=$(physical_dir "$candidate") || die "cannot resolve destination '$candidate'"
        validate_dest_outside "$DEST"
    else
        DEST=$candidate
    fi
}

validate_dest_outside() {
    local dest=$1
    if [ "$dest" = "$REPO_ROOT" ] || is_under "$dest" "$REPO_ROOT"; then
        die "destination '$dest' is inside the repository working tree — worktrees must live outside it"
    fi
    if [ -n "$SUPER_ROOT" ]; then
        if [ "$dest" = "$SUPER_ROOT" ] || is_under "$dest" "$SUPER_ROOT"; then
            die "destination '$dest' is inside the superproject working tree — worktrees must live outside it"
        fi
    fi
}

validate_name() {
    local name=$1
    if [ -z "$name" ]; then
        die "worktree name is required"
    fi
    case $name in
        -*) die "worktree name must not start with '-'" ;;
    esac
    case $name in
        */* | *'\'*) die "worktree name must not contain path separators" ;;
    esac
    case $name in
        *..*) die "worktree name must not contain '..'" ;;
    esac
    if ! [[ $name =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
        die "worktree name '$name' contains unsupported characters (allowed: letters, digits, '.', '_', '-')"
    fi
}

worktree_add() {
    local path=$1 branch=$2 base=$3 output
    if output=$(git worktree add "$path" -b "$branch" "$base" 2>&1); then
        return 0
    fi
    case $output in
        *index.lock* | *'could not lock'* | *'Unable to create'*)
            sleep 2
            if output=$(git worktree add "$path" -b "$branch" "$base" 2>&1); then
                return 0
            fi
            ;;
    esac
    die "git worktree add failed: $output"
}

# enumerate_worktrees — fills WT_PATHS / WT_BRANCHES (branch empty when
# detached) and MAIN_WT from NUL-delimited porcelain output, so paths
# containing spaces cannot break parsing.
WT_PATHS=() WT_BRANCHES=() MAIN_WT=""
enumerate_worktrees() {
    WT_PATHS=()
    WT_BRANCHES=()
    MAIN_WT=""
    local token current_path="" current_branch=""
    while IFS= read -r -d '' token || [ -n "$token" ]; do
        if [ -z "$token" ]; then
            if [ -n "$current_path" ]; then
                if [ -z "$MAIN_WT" ]; then
                    MAIN_WT=$current_path
                fi
                WT_PATHS+=("$current_path")
                WT_BRANCHES+=("$current_branch")
            fi
            current_path=""
            current_branch=""
        else
            case $token in
                'worktree '*) current_path=${token#worktree } ;;
                'branch refs/heads/'*) current_branch=${token#branch refs/heads/} ;;
            esac
        fi
    done < <(git worktree list --porcelain -z)
    if [ -n "$current_path" ]; then
        if [ -z "$MAIN_WT" ]; then
            MAIN_WT=$current_path
        fi
        WT_PATHS+=("$current_path")
        WT_BRANCHES+=("$current_branch")
    fi
}

cmd_create() {
    local name="" from="" dest_flag=""
    local flag_env="" flag_composer="" flag_npm=""
    while [ $# -gt 0 ]; do
        case $1 in
            --from)
                shift
                from=${1:-}
                if [ -z "$from" ]; then die "--from requires a value"; fi
                ;;
            --dest)
                shift
                dest_flag=${1:-}
                if [ -z "$dest_flag" ]; then die "--dest requires a value"; fi
                ;;
            --env) flag_env=on ;;
            --no-env) flag_env=off ;;
            --composer) flag_composer=on ;;
            --no-composer) flag_composer=off ;;
            --npm) flag_npm=on ;;
            --no-npm) flag_npm=off ;;
            --json) JSON_MODE=1 ;;
            --) ;;
            -*) die "unknown option '$1' for create" ;;
            *)
                if [ -n "$name" ]; then die "unexpected argument '$1'"; fi
                name=$1
                ;;
        esac
        shift
    done
    validate_name "$name"
    resolve_repo
    load_config

    local prefix=${CFG_PREFIX:-wt/}
    local branch="$prefix$name"
    if ! git check-ref-format --branch "$branch" >/dev/null 2>&1; then
        die "invalid branch name '$branch'"
    fi
    resolve_base "$from"
    resolve_dest "$dest_flag" create

    local worktree_path="$DEST/$name"
    if ! is_under "$worktree_path" "$DEST"; then
        die "resolved worktree path '$worktree_path' escapes the destination '$DEST'"
    fi
    if git show-ref --verify --quiet "refs/heads/$branch"; then
        die "branch '$branch' already exists — pick another name or remove the old worktree first"
    fi
    if [ -e "$worktree_path" ] && [ -n "$(ls -A "$worktree_path" 2>/dev/null)" ]; then
        die "directory '$worktree_path' exists and is not empty"
    fi
    if [ -n "$SUPER_ROOT" ]; then
        info "note: this repository is a submodule of '$SUPER_ROOT'; its shared git directory lives under the superproject"
    fi

    worktree_add "$worktree_path" "$branch" "$BASE"
    git config "branch.$branch.worktreeBase" "$BASE"

    local env_status=skipped composer_status=skipped npm_status=skipped hook_status=skipped failed=""

    # .env copy — default on; both flag directions override config.
    local env_enabled=true
    if [ "$flag_env" = off ]; then
        env_enabled=false
    elif [ -z "$flag_env" ] && [ "$CFG_COPYENV" = false ]; then
        env_enabled=false
    fi
    if [ "$env_enabled" = true ]; then
        if [ -f "$REPO_ROOT/.env" ]; then
            if cp "$REPO_ROOT/.env" "$worktree_path/.env"; then
                env_status=copied
            else
                env_status=failed
                failed=env
            fi
        elif [ "$flag_env" = on ]; then
            env_status=failed
            failed=env
        fi
    fi

    # composer install — default on when composer.json exists.
    if [ -z "$failed" ]; then
        local composer_enabled=true
        if [ "$flag_composer" = off ]; then
            composer_enabled=false
        elif [ -z "$flag_composer" ] && [ "$CFG_COMPOSER" = false ]; then
            composer_enabled=false
        fi
        if [ "$composer_enabled" = true ] && [ -f "$worktree_path/composer.json" ]; then
            if (cd "$worktree_path" && composer install --no-interaction >&2); then
                composer_status=ran
            else
                composer_status=failed
                failed=composer
            fi
        fi
    fi

    # npm ci — default OFF (slow; many backend plans never need it).
    if [ -z "$failed" ]; then
        local npm_enabled=false
        if [ "$flag_npm" = on ]; then
            npm_enabled=true
        elif [ -z "$flag_npm" ] && [ "$CFG_NPM" = true ]; then
            npm_enabled=true
        fi
        if [ "$npm_enabled" = true ] && [ -f "$worktree_path/package.json" ]; then
            if (cd "$worktree_path" && npm ci >&2); then
                npm_status=ran
            else
                npm_status=failed
                failed=npm
            fi
        fi
    fi

    # post-setup hook — the worktree's OWN copy (it came from the base branch),
    # never the source checkout's, so a dirty hook edit cannot leak across.
    if [ -z "$failed" ]; then
        local hook=${CFG_POSTSETUP:-.worktree-setup.sh}
        case $hook in
            /*) ;;
            *) hook="$worktree_path/$hook" ;;
        esac
        if [ -f "$hook" ] && [ -x "$hook" ]; then
            if (cd "$worktree_path" && "$hook" >&2); then
                hook_status=ran
            else
                hook_status=failed
                failed=postSetup
            fi
        fi
    fi

    if [ "$JSON_MODE" -eq 1 ]; then
        printf '{"path":"%s","branch":"%s","base":"%s","bootstrap":{"env":"%s","composer":"%s","npm":"%s","postSetup":"%s"}}\n' \
            "$(json_escape "$worktree_path")" \
            "$(json_escape "$branch")" \
            "$(json_escape "$BASE")" \
            "$env_status" "$composer_status" "$npm_status" "$hook_status"
    else
        info "worktree created: $worktree_path"
        info "branch: $branch (from $BASE)"
        info "bootstrap: env=$env_status composer=$composer_status npm=$npm_status postSetup=$hook_status"
    fi
    if [ -n "$failed" ]; then
        printf 'worktree.sh: bootstrap step %s failed — worktree left in place at %s\n' "$failed" "$worktree_path" >&2
        exit 1
    fi
}

cmd_remove() {
    local name="" delete_branch=0 force=0 unmanaged=0
    while [ $# -gt 0 ]; do
        case $1 in
            --delete-branch) delete_branch=1 ;;
            --force) force=1 ;;
            --unmanaged) unmanaged=1 ;;
            --json) JSON_MODE=1 ;;
            -*) die "unknown option '$1' for remove" ;;
            *)
                if [ -n "$name" ]; then die "unexpected argument '$1'"; fi
                name=$1
                ;;
        esac
        shift
    done
    validate_name "$name"
    resolve_repo
    load_config
    enumerate_worktrees

    # Targets come from git's own worktree metadata, never reconstructed from
    # the (mutable) configuration.
    local index=0 match_count=0 target_path="" target_branch="" candidates=""
    while [ "$index" -lt "${#WT_PATHS[@]}" ]; do
        local candidate_path=${WT_PATHS[$index]} candidate_branch=${WT_BRANCHES[$index]}
        if [ "$candidate_path" != "$MAIN_WT" ] && [ "$(basename "$candidate_path")" = "$name" ]; then
            match_count=$((match_count + 1))
            target_path=$candidate_path
            target_branch=$candidate_branch
            candidates="$candidates  $candidate_path"$'\n'
        fi
        index=$((index + 1))
    done
    if [ "$match_count" -eq 0 ]; then
        die "no worktree named '$name' found"
    fi
    if [ "$match_count" -gt 1 ]; then
        die "ambiguous name '$name' — candidates:"$'\n'"$candidates"
    fi

    # The worktreeBase marker written by create is the created-by-this-tool
    # signal; --unmanaged is the explicit escape hatch for everything else.
    local recorded_base=""
    if [ -n "$target_branch" ]; then
        recorded_base=$(git config --get "branch.$target_branch.worktreeBase" 2>/dev/null || true)
    fi
    if [ -z "$recorded_base" ] && [ "$unmanaged" -eq 0 ]; then
        die "worktree '$target_path' was not created by this tool (branch '${target_branch:-detached}' has no worktreeBase marker) — pass --unmanaged to remove it anyway"
    fi

    local dirty
    dirty=$(git -C "$target_path" status --porcelain 2>/dev/null | head -n 1 || true)
    if [ -n "$dirty" ] && [ "$force" -eq 0 ]; then
        die "worktree '$target_path' has uncommitted changes — pass --force to discard them"
    fi

    # Merged status is judged against the recorded base, never against the main
    # checkout's current HEAD — and BEFORE removal, so a refusal leaves the
    # worktree intact.
    if [ "$delete_branch" -eq 1 ] && [ -n "$target_branch" ]; then
        local base_for_check=$recorded_base
        if [ -z "$base_for_check" ]; then
            resolve_base ""
            base_for_check=$BASE
        fi
        if ! git rev-parse --verify --quiet "${base_for_check}^{commit}" >/dev/null 2>&1; then
            if [ "$force" -eq 0 ]; then
                die "recorded base '$base_for_check' no longer exists — pass --force to delete branch '$target_branch' anyway"
            fi
        elif ! git merge-base --is-ancestor "$target_branch" "$base_for_check" 2>/dev/null; then
            if [ "$force" -eq 0 ]; then
                die "branch '$target_branch' is not merged into '$base_for_check' — pass --force to delete it anyway"
            fi
        fi
    fi

    if [ "$force" -eq 1 ]; then
        git worktree remove --force "$target_path"
    else
        git worktree remove "$target_path"
    fi

    local branch_deleted=false
    if [ "$delete_branch" -eq 1 ] && [ -n "$target_branch" ]; then
        git branch -D "$target_branch" >/dev/null
        git config --unset "branch.$target_branch.worktreeBase" 2>/dev/null || true
        branch_deleted=true
    fi

    if [ "$JSON_MODE" -eq 1 ]; then
        local branch_json=null
        if [ -n "$target_branch" ]; then
            branch_json="\"$(json_escape "$target_branch")\""
        fi
        printf '{"removed":"%s","branch":%s,"branchDeleted":%s}\n' \
            "$(json_escape "$target_path")" "$branch_json" "$branch_deleted"
    else
        info "removed: $target_path"
        if [ "$branch_deleted" = true ]; then
            info "deleted branch: $target_branch"
        fi
    fi
}

cmd_list() {
    while [ $# -gt 0 ]; do
        case $1 in
            --json) JSON_MODE=1 ;;
            -*) die "unknown option '$1' for list" ;;
            *) die "unexpected argument '$1'" ;;
        esac
        shift
    done
    resolve_repo
    load_config
    resolve_dest "" nocreate
    enumerate_worktrees

    local index=0 entries=""
    while [ "$index" -lt "${#WT_PATHS[@]}" ]; do
        local entry_path=${WT_PATHS[$index]} entry_branch=${WT_BRANCHES[$index]}
        index=$((index + 1))

        local dirty=false
        if [ -n "$(git -C "$entry_path" status --porcelain 2>/dev/null | head -n 1)" ]; then
            dirty=true
        fi

        # createdByTool comes from the branch marker, NOT from whether the path
        # sits under the (mutable) resolved destination.
        local recorded_base="" created_by_tool=false
        if [ -n "$entry_branch" ]; then
            recorded_base=$(git config --get "branch.$entry_branch.worktreeBase" 2>/dev/null || true)
            if [ -n "$recorded_base" ]; then
                created_by_tool=true
            fi
        fi

        local base_json=null merged_json=null can_delete_json=null
        if [ "$created_by_tool" = true ]; then
            base_json="\"$(json_escape "$recorded_base")\""
            if git rev-parse --verify --quiet "${recorded_base}^{commit}" >/dev/null 2>&1; then
                if git merge-base --is-ancestor "$entry_branch" "$recorded_base" 2>/dev/null; then
                    merged_json=true
                else
                    merged_json=false
                fi
            fi
            if [ "$merged_json" = true ] && [ "$dirty" = false ]; then
                can_delete_json=true
            elif [ "$merged_json" != null ]; then
                can_delete_json=false
            fi
        fi

        local under_dest=false
        if [ -n "$DEST" ] && is_under "$entry_path" "$DEST"; then
            under_dest=true
        fi

        local branch_json=null
        if [ -n "$entry_branch" ]; then
            branch_json="\"$(json_escape "$entry_branch")\""
        fi

        local entry
        entry=$(printf '{"path":"%s","branch":%s,"dirty":%s,"createdByTool":%s,"base":%s,"mergedIntoBase":%s,"canDeleteBranch":%s,"underCurrentDestination":%s}' \
            "$(json_escape "$entry_path")" "$branch_json" "$dirty" "$created_by_tool" \
            "$base_json" "$merged_json" "$can_delete_json" "$under_dest")
        if [ -n "$entries" ]; then
            entries="$entries,$entry"
        else
            entries=$entry
        fi

        if [ "$JSON_MODE" -eq 0 ]; then
            local marker=" "
            if [ "$dirty" = true ]; then marker="*"; fi
            local managed="manual"
            if [ "$created_by_tool" = true ]; then managed="managed"; fi
            printf '%s %-8s %-30s %s\n' "$marker" "$managed" "${entry_branch:-detached}" "$entry_path"
        fi
    done

    if [ "$JSON_MODE" -eq 1 ]; then
        printf '[%s]\n' "$entries"
    fi
}

cmd_config() {
    local write=0
    while [ $# -gt 0 ]; do
        case $1 in
            --write) write=1 ;;
            --json) JSON_MODE=1 ;;
            -*) die "unknown option '$1' for config" ;;
            *) die "unexpected argument '$1'" ;;
        esac
        shift
    done
    resolve_repo

    if [ "$write" -eq 1 ]; then
        if ! command -v python3 >/dev/null 2>&1; then
            die "python3 is required for config --write"
        fi
        local temp_file prefix
        temp_file=$(mktemp)
        # The heredoc occupies python's stdin, so the payload piped into this
        # command travels on duplicated file descriptor 3 instead.
        if ! prefix=$(python3 - "$temp_file" "$REPO_ROOT" "${SUPER_ROOT:-}" 3<&0 <<'PYEOF'
import json
import os
import sys

target, repo_root, super_root = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with os.fdopen(3) as payload:
        data = json.load(payload)
except Exception as error:
    sys.stderr.write(f"invalid JSON on stdin: {error}\n")
    raise SystemExit(1)
if not isinstance(data, dict):
    sys.stderr.write("configuration must be a JSON object\n")
    raise SystemExit(1)
allowed = {
    "baseBranch": str,
    "destination": str,
    "branchPrefix": str,
    "postSetup": (str, type(None)),
    "bootstrap": dict,
}
unknown = sorted(set(data) - set(allowed))
if unknown:
    sys.stderr.write(f"unknown keys: {', '.join(unknown)}\n")
    raise SystemExit(1)
for key, expected in allowed.items():
    if key in data and data[key] is not None and not isinstance(data[key], expected):
        sys.stderr.write(f"key '{key}' has the wrong type\n")
        raise SystemExit(1)
bootstrap = data.get("bootstrap") or {}
allowed_bootstrap = {"copyEnv", "composer", "npm"}
unknown = sorted(set(bootstrap) - allowed_bootstrap)
if unknown:
    sys.stderr.write(f"unknown bootstrap keys: {', '.join(unknown)}\n")
    raise SystemExit(1)
for key, value in bootstrap.items():
    if not isinstance(value, bool):
        sys.stderr.write(f"bootstrap.{key} must be a boolean\n")
        raise SystemExit(1)
destination = data.get("destination")
if destination is not None:
    absolute = destination if os.path.isabs(destination) else os.path.join(repo_root, destination)
    resolved = os.path.realpath(absolute)
    roots = [repo_root] + ([super_root] if super_root else [])
    for root in roots:
        real_root = os.path.realpath(root)
        if resolved == real_root or resolved.startswith(real_root + os.sep):
            sys.stderr.write(
                f"destination '{destination}' resolves inside '{real_root}' — worktrees must live outside the working tree\n"
            )
            raise SystemExit(1)
with open(target, "w") as handle:
    json.dump(data, handle, indent=4)
    handle.write("\n")
print(data.get("branchPrefix", ""))
PYEOF
        ); then
            rm -f "$temp_file"
            die "configuration rejected"
        fi
        # A bare prefix (e.g. plan/) is not itself a valid branch name, so the
        # prefix is validated with a sentinel name appended.
        if [ -n "$prefix" ]; then
            if ! git check-ref-format --branch "${prefix}probe" >/dev/null 2>&1; then
                rm -f "$temp_file"
                die "invalid branchPrefix '$prefix'"
            fi
        fi
        mv "$temp_file" "$REPO_ROOT/.worktree.json"
        if [ "$JSON_MODE" -eq 1 ]; then
            printf '{"written":"%s"}\n' "$(json_escape "$REPO_ROOT/.worktree.json")"
        else
            info "wrote $REPO_ROOT/.worktree.json"
        fi
        return 0
    fi

    load_config
    resolve_base ""
    resolve_dest "" nocreate
    local prefix=${CFG_PREFIX:-wt/}
    local copy_env=${CFG_COPYENV:-true} composer=${CFG_COMPOSER:-true} npm=${CFG_NPM:-false}
    local super_json=null post_setup_json=null
    if [ -n "$SUPER_ROOT" ]; then
        super_json="\"$(json_escape "$SUPER_ROOT")\""
    fi
    if [ -n "$CFG_POSTSETUP" ]; then
        post_setup_json="\"$(json_escape "$CFG_POSTSETUP")\""
    fi
    printf '{"repository":"%s","superproject":%s,"baseBranch":"%s","destination":"%s","branchPrefix":"%s","bootstrap":{"copyEnv":%s,"composer":%s,"npm":%s},"postSetup":%s}\n' \
        "$(json_escape "$REPO_ROOT")" "$super_json" "$(json_escape "$BASE")" \
        "$(json_escape "$DEST")" "$(json_escape "$prefix")" \
        "$copy_env" "$composer" "$npm" "$post_setup_json"
}

usage() {
    cat <<'EOF'
Usage:
  worktree.sh create <name> [--from <branch>] [--dest <dir>]
                     [--env|--no-env] [--composer|--no-composer] [--npm|--no-npm] [--json]
  worktree.sh remove <name> [--delete-branch] [--force] [--unmanaged] [--json]
  worktree.sh list   [--json]
  worktree.sh config [--write]
EOF
}

case ${1:-} in
    create | remove | list | config)
        subcommand=$1
        shift
        "cmd_$subcommand" "$@"
        ;;
    -h | --help | help | "")
        usage
        ;;
    *)
        die "unknown subcommand '$1' (expected create, remove, list, or config)"
        ;;
esac
