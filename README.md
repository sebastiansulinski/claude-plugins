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
/plugin install good-morning@sebastiansulinski
/plugin install call-it-a-day@sebastiansulinski
/plugin install interrogate@sebastiansulinski
/plugin install deprecate-repo@sebastiansulinski
/plugin install query-analysis@sebastiansulinski
/plugin install release-manager@sebastiansulinski
/plugin install dead-code-purger@sebastiansulinski
```

## Plugins

| Plugin             | Command(s)                    | What it does |
|--------------------|-------------------------------|--------------|
| `review`           | `/scrutinise`, `/plan-review` | Deep critical review of recent work, and multi-agent grounded review of a plan file. |
| `good-morning`     | `/good-morning`               | Resume the previous session — reload memory, lessons, and context, then propose next steps. |
| `call-it-a-day`    | `/call-it-a-day`              | End-of-session capture so the next session resumes with no context loss. |
| `interrogate`      | `/interrogate`                | Ruthless requirements interrogation — exhaustive questions, never writes code. |
| `deprecate-repo`   | `/deprecate-repo`             | Fully deprecate and archive a repository. |
| `query-analysis`   | `/query-analysis`             | Read-only audit of Eloquent / query-builder usage; writes findings to `docs/analysis/`. |
| `release-manager`  | `/publish-release`            | Runs the full release workflow — changelog, semantic-version tag, GitHub release. |
| `dead-code-purger` | `/purge-dead-code`            | Finds and safely removes dead code and unused dependencies — only after your approval. |

Three plugins also ship a subagent: `review` includes `scrutiniser` (used by
both its commands), `release-manager` includes the agent `/publish-release`
spawns, and `dead-code-purger` the agent `/purge-dead-code` spawns. All three
agents can also be invoked directly via `subagent_type:`.

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
├── good-morning/
├── call-it-a-day/
├── interrogate/
├── deprecate-repo/
├── query-analysis/
├── release-manager/                  # /publish-release + agent
└── dead-code-purger/                 # /purge-dead-code + agent
```

Each plugin is a self-contained directory with a `.claude-plugin/plugin.json`
manifest plus `commands/` and/or `agents/`. To add a new plugin, create the
directory and register it in `.claude-plugin/marketplace.json`.
