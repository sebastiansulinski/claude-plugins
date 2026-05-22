# claude-plugins

The **`seb`** plugin marketplace — Sebastian Sulinski's personal Claude Code
commands, bundled for native install across machines.

## Install

Add the marketplace once:

```
/plugin marketplace add sebastiansulinski/claude-plugins
```

This registers under the marketplace name **`seb`** (set in
`.claude-plugin/marketplace.json`). Then install whichever plugins you want:

```
/plugin install review@seb
/plugin install good-morning@seb
/plugin install call-it-a-day@seb
/plugin install interrogate@seb
/plugin install deprecate-repo@seb
/plugin install query-analysis@seb
```

## Plugins

| Plugin           | Command(s)                    | What it does |
|------------------|-------------------------------|--------------|
| `review`         | `/scrutinise`, `/plan-review` | Deep critical review of recent work, and multi-agent grounded review of a plan file. |
| `good-morning`   | `/good-morning`               | Resume the previous session — reload memory, lessons, and context, then propose next steps. |
| `call-it-a-day`  | `/call-it-a-day`              | End-of-session capture so the next session resumes with no context loss. |
| `interrogate`    | `/interrogate`                | Ruthless requirements interrogation — exhaustive questions, never writes code. |
| `deprecate-repo` | `/deprecate-repo`             | Fully deprecate and archive a repository. |
| `query-analysis` | `/query-analysis`             | Read-only audit of Eloquent / query-builder usage; writes findings to `docs/analysis/`. |

The `review` plugin also ships the `scrutiniser` subagent, which both its
commands use and which can be invoked directly via `subagent_type: scrutiniser`.

## Updating

```
/plugin marketplace update seb     # refresh the catalogue
/plugin update review@seb          # update a single plugin
```

## Layout

```
claude-plugins/
├── .claude-plugin/marketplace.json   # the marketplace manifest
├── review/                           # one directory per plugin…
│   ├── .claude-plugin/plugin.json    #   …each with its own manifest
│   ├── commands/
│   └── agents/
├── good-morning/
├── call-it-a-day/
├── interrogate/
├── deprecate-repo/
└── query-analysis/
```

Each plugin is a self-contained directory with a `.claude-plugin/plugin.json`
manifest plus `commands/` (and `agents/` where needed). To add a new plugin,
create the directory and register it in `.claude-plugin/marketplace.json`.
