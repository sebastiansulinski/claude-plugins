# claude-plugins

Sebastian Sulinski's personal Claude Code plugin marketplace — commands and
agents bundled for native install across machines.

## Install

Add the marketplace once:

```
/plugin marketplace add sebastiansulinski/claude-plugins
```

This registers under the marketplace name **`sebastiansulinski`** (set in
`.claude-plugin/marketplace.json`). Then install whichever plugins you want:

```
/plugin install review@sebastiansulinski
/plugin install session@sebastiansulinski
/plugin install repo@sebastiansulinski
/plugin install release@sebastiansulinski
/plugin install requirements@sebastiansulinski
/plugin install db@sebastiansulinski
/plugin install dead-code@sebastiansulinski
/plugin install worktree@sebastiansulinski
```

## Plugins

Plugin commands are namespaced `plugin:command` — each reads as a `category:action` phrase.

| Plugin | Commands | What it does |
|--------|----------|--------------|
| `review` | `/review:scrutinise`, `/review:plan-review` | Deep critical review of recent work, and multi-agent grounded review of a plan file. |
| `session` | `/session:good-morning`, `/session:call-it-a-day` | Resume the previous session, and capture end-of-session state so the next resumes cleanly. |
| `repo` | `/repo:deprecate` | Fully deprecate and archive a repository. |
| `release` | `/release:publish` | Run the full changelog → git tag → GitHub release workflow. |
| `requirements` | `/requirements:interrogate` | Exhaustive requirements interrogation — never writes code. |
| `db` | `/db:query-analysis` | Read-only audit of Eloquent / query-builder usage; writes findings to `docs/analysis/`. |
| `dead-code` | `/dead-code:purge` | Find and safely remove dead code and unused dependencies — only after your approval. |
| `worktree` | `/worktree:create`, `/worktree:remove`, `/worktree:list`, `/worktree:init` | Isolated git worktrees for parallel agents — works on plain repositories and submodules. |

Three plugins also ship a subagent — `review` (`scrutiniser`), `release`
(`manager`), and `dead-code` (`purger`). Each is spawned by its plugin's
command, and can also be invoked directly via `subagent_type:`.

## Updating

```
/plugin marketplace update sebastiansulinski   # refresh the catalogue
/plugin update review@sebastiansulinski        # update a single plugin
```

## Layout

```
claude-plugins/
├── .claude-plugin/marketplace.json   # the marketplace manifest
├── review/                           # one directory per plugin…
│   ├── .claude-plugin/plugin.json    #   …each with its own manifest
│   ├── commands/
│   └── agents/
├── session/
├── repo/
├── release/
├── requirements/
├── db/
├── dead-code/
└── worktree/                         # also ships scripts/ and tests/
```

Each plugin is a self-contained directory with a `.claude-plugin/plugin.json`
manifest plus `commands/` and/or `agents/`. To add a new plugin, create the
directory and register it in `.claude-plugin/marketplace.json`.

## The `worktree` plugin

Creates isolated git worktrees so several agents (or Claude Code sessions) can
work on different plans in the same repository at the same time without
overwriting each other's files. Each worktree is a separate directory on its
own branch; the main checkout is never touched. Works identically on plain
repositories and on submodules — for a submodule, worktrees default to a
sibling of the **superproject**, since a sibling of the submodule would still
sit inside the superproject's working tree.

The commands wrap one deterministic script, `worktree/scripts/worktree.sh`
(any tool that can run a shell command can use it directly):

```
worktree.sh create <name> [--from <branch>] [--dest <dir>]
            [--env|--no-env] [--composer|--no-composer] [--npm|--no-npm] [--json]
worktree.sh remove <name> [--delete-branch] [--force] [--unmanaged] [--json]
worktree.sh list   [--json]
worktree.sh config [--write]
```

**Conventions (zero configuration):** base branch resolves local-then-remote
through `develop` → `origin/HEAD` → `main` → `master`; destination is a sibling
directory `<repo>-worktrees/`; bootstrap copies `.env` (if present) and runs
`composer install` (if `composer.json` exists); `npm ci` only on request. A
committed, executable `.worktree-setup.sh` in the repository runs inside each
new worktree as a project-specific hook.

**Per-project configuration (optional):** `/worktree:init` writes a
`.worktree.json` to the repository root (always through `config --write`,
which validates it). Precedence: command-line flags → `.worktree.json` →
conventions. Supported keys: `baseBranch`, `destination`, `branchPrefix`
(default `wt/`), `bootstrap.copyEnv` / `bootstrap.composer` / `bootstrap.npm`,
`postSetup`. Parsing the file requires `python3`; the zero-configuration path
does not.

**Safety properties** (all covered by the test harness):

- the source checkout's status, HEAD, and current branch are untouched by
  `create` and `remove`;
- destinations are validated to sit outside the repository AND any
  superproject working tree;
- `remove` resolves its target from git's worktree metadata (never from the
  mutable configuration), refuses worktrees it did not create unless
  `--unmanaged`, refuses dirty worktrees unless `--force`, and judges branch
  merged-ness against the base recorded at create time — never against the
  main checkout's current HEAD;
- concurrent `index.lock` contention on the shared git directory is retried
  once — it is contention, not corruption.

Run the tests with:

```
bash worktree/tests/run.sh
```

### Worked example — two agents on two plans, in parallel

The point of the plugin: you have an agent working in your main checkout and
two more plans waiting. Give each plan its own worktree and the agents
physically cannot overwrite each other.

The example uses a workspace `~/code/platform` (a superproject) containing a
submodule `app` — the same flow applies to a plain repository, minus the
submodule notes.

```
# 1. Always start from inside the repository the work targets.
#    (For a submodule, that means inside the submodule itself.)
cd ~/code/platform/app

# 2. One worktree per plan — in Claude Code, just type:
/worktree:create checkout-flow
/worktree:create search-filters
```

Each command creates a directory like `~/code/app-worktrees/checkout-flow` on
its own branch (`wt/checkout-flow`, branched from `develop`), copies `.env`,
and runs `composer install`. Note the destination is a sibling of
**platform** (the superproject), not of the submodule — that is the
submodule-aware default.

```
# 3. Open a separate Claude Code session per worktree:
cd ~/code/app-worktrees/checkout-flow && claude
cd ~/code/app-worktrees/search-filters && claude
```

Each agent implements, runs tests, and commits **inside its own directory on
its own branch**. The main checkout (and any agent already working there)
never sees a thing.

```
# 4. When a plan is finished and committed, merge it from the MAIN checkout —
#    one branch at a time, running the test suite between merges:
cd ~/code/platform/app
git merge wt/checkout-flow
# …run the suite, verify…

# 5. Then clean up — removes the directory AND the branch (only allowed
#    because the branch is now merged):
/worktree:remove checkout-flow --delete-branch
```

### Command-by-command examples

Everything below works two ways: as a slash command in Claude Code
(`/worktree:create …` — Claude runs the script for you and reports back), or
by calling the script directly from any tool that can run a shell command.
When installed as a plugin the script lives at
`${CLAUDE_PLUGIN_ROOT}/scripts/worktree.sh`; from a clone of this repository
it is `worktree/scripts/worktree.sh`. The examples below alias it as `wt` for
brevity:

```
alias wt='bash ~/code/claude-plugins/worktree/scripts/worktree.sh'
```

**create** — run from inside the target repository:

```
wt create checkout-flow                  # branch wt/checkout-flow from develop,
                                         # .env copied, composer install run
wt create hotfix --from main             # branch from main instead
wt create dashboard --npm                # also run npm ci (off by default)
wt create quick-probe --no-composer --no-env   # bare worktree, no bootstrap
wt create reports --dest ~/scratch/wt    # explicit destination
wt create checkout-flow --json           # machine-readable result:
# {"path":"~/code/my-app-worktrees/checkout-flow",
#  "branch":"wt/checkout-flow","base":"develop",
#  "bootstrap":{"env":"copied","composer":"ran","npm":"skipped","postSetup":"skipped"}}
```

**list** — what exists, what is dirty, what is safe to clean up:

```
wt list
#   manual   develop                  ~/code/my-app          <- the main checkout
# * managed  wt/checkout-flow         ~/code/my-app-worktrees/checkout-flow
#   managed  wt/reports               ~/code/my-app-worktrees/reports
# (* = uncommitted changes)

wt list --json    # adds per-entry: base, mergedIntoBase, canDeleteBranch,
                  # createdByTool, underCurrentDestination
```

**remove** — safe by default, every override is explicit:

```
wt remove reports                          # worktree gone, branch kept
wt remove reports --delete-branch          # branch too — but ONLY if merged
                                           # into the base recorded at create time
wt remove checkout-flow                    # refused: uncommitted changes
wt remove checkout-flow --force            # discard them and remove
wt remove experiments --delete-branch --force   # delete an unmerged branch too
wt remove old-manual-thing --unmanaged     # required for worktrees this tool
                                           # did not create
```

**init** — optional per-repository configuration. In Claude Code,
`/worktree:init` asks four questions (base branch, destination, bootstrap
steps, post-setup hook) and writes `.worktree.json` for you. Directly:

```
wt config            # show the resolved effective configuration
printf '%s' '{
    "baseBranch": "develop",
    "branchPrefix": "plan/",
    "bootstrap": { "npm": false }
}' | wt config --write     # validated, then written to .worktree.json
```

With that configuration committed, `wt create checkout-flow` produces
branch `plan/checkout-flow` instead of `wt/checkout-flow`. Most
repositories need no configuration at all — conventions cover the common case.

### Post-setup hook recipes (`.worktree-setup.sh`)

The hook is the plugin's extension point: a committed, executable
`.worktree-setup.sh` at the repository root runs **inside each new worktree**
after bootstrap (override the filename with the `postSetup` key in
`.worktree.json`). Two contract details shape every recipe:

- **A failing hook fails the create** — the worktree is left in place for
  inspection, but the command exits non-zero. So a recipe that only applies
  to some layouts must detect "not applicable" and `exit 0`, never error.
- **It runs in the worktree's directory on the worktree's branch** — a hook
  edit committed on a plan branch does not change what runs for the next
  worktree created from the base branch.

The recipes below are real setups, generalised. Each is a complete hook; to
combine them, paste the bodies into one script.

#### Recipe 1 — shared docs across a submodule's worktrees

The setup this recipe comes from: a superproject (`platform/`) holds an app
submodule (`app/`) plus planning documents in `platform/docs/plans/` and
architectural-decision logs in `platform/docs/context/`. Those documents are
the **coordination record between parallel sessions**, so they must exist as
a single copy — but a worktree of the submodule lives outside the
superproject tree and cannot see them by any relative path.

The fix: derive the superproject root from the git common directory (a
submodule's is always `<superproject>/.git/modules/<name>`) and symlink the
shared directories into the checkout. One repo-relative path form —
`plans/…`, `context/…` — then resolves identically in the main checkout and
every worktree:

```sh
#!/bin/sh
# .worktree-setup.sh — link the superproject's shared docs into this
# checkout. Run it once manually in the MAIN checkout too, so the same
# paths work everywhere. A non-submodule clone is a silent no-op.

set -eu

common=$(git rev-parse --git-common-dir)

case $common in
    */.git/modules/*)
        super=${common%/.git/modules/*}
        ;;
    *)
        exit 0
        ;;
esac

for name in plans context; do
    if [ -d "$super/docs/$name" ]; then
        ln -sfn "$super/docs/$name" "$name"
        echo "linked $name -> $super/docs/$name"
    fi
done
```

Add the link names to `.gitignore` (`/plans`, `/context`). **Never commit the
symlinks themselves**: a committed symlink stores a fixed relative target,
which resolves from the main checkout's location and breaks from every
worktree — the hook recreates the links with absolute targets per checkout
instead.

Two conventions make this pay off in plan documents: write paths to the
repository's own files **repo-relative** (`src/…` means "in your checkout" —
the only safe meaning when several working copies exist), and write paths to
the shared docs through the link names (`plans/…`, `context/…`).

#### Recipe 2 — build the frontend bundle so browser tests work immediately

Bootstrap installs dependencies but deliberately never builds. If your test
suite serves a built bundle (Vite manifest, compiled assets), a fresh
worktree fails browser tests until someone remembers to build — make the
hook remember instead:

```sh
#!/bin/sh
# .worktree-setup.sh — produce the built bundle the browser-test server
# serves. Skips silently when the project has no build script.

set -eu

if [ -f package.json ] && grep -q '"build"' package.json; then
    npm run build
fi
```

Pair it with `"bootstrap": { "npm": true }` in `.worktree.json` (the build
needs `node_modules`). The trade-off is creation time — for a quick probe
worktree, `wt create probe --no-npm` skips both the install and, because the
build script then fails the `node_modules` check, effectively the build.

#### Recipe 3 — per-worktree environment isolation (Laravel example)

Bootstrap copies the main checkout's `.env` verbatim — which means every
worktree points at the SAME development database and storage as the main
checkout. Fine for suites that override the connection (an in-memory SQLite
test database), dangerous for anything touching the dev services. Give each
worktree its own writable state:

```sh
#!/bin/sh
# .worktree-setup.sh — point this worktree at its own SQLite database and
# storage so parallel sessions cannot trample the main checkout's data.

set -eu

[ -f .env ] || exit 0

db="$PWD/database/worktree.sqlite"

mkdir -p database
touch "$db"

sed -i '' \
    -e "s|^DB_CONNECTION=.*|DB_CONNECTION=sqlite|" \
    -e "s|^DB_DATABASE=.*|DB_DATABASE=$db|" \
    .env

php artisan key:generate --force --no-interaction
php artisan storage:link --force --no-interaction
php artisan migrate --force --no-interaction
```

(The `sed -i ''` form is macOS; on Linux drop the empty string.) The same
shape works for any stack: rewrite the copied environment so every stateful
path or port is unique to the worktree, then initialise it.
