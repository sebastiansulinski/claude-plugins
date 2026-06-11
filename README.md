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
