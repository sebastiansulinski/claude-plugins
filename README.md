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
└── dead-code/
```

Each plugin is a self-contained directory with a `.claude-plugin/plugin.json`
manifest plus `commands/` and/or `agents/`. To add a new plugin, create the
directory and register it in `.claude-plugin/marketplace.json`.
