# review

A Claude Code plugin with two critical-review commands:

- **`/scrutinise`** — deep, evidence-based critical review of recent work: bugs, design flaws, anti-patterns, missing tests, edge cases, security holes, inconsistencies. No skimming, no auto-fixing.
- **`/plan-review`** — multi-agent grounded review of a plan file, run entirely locally so it can verify every claim against the actual codebase.

Part of the [claude-plugins marketplace](../README.md).

## `/scrutinise`

Delegates to a `scrutiniser` subagent that reads project context (`CLAUDE.md`, architectural-decision docs), inspects the actual code in scope, traces changes against tests, and produces a structured report with findings tiered by severity (Critical / Important / Minor). The agent **never** edits files — it reports, you decide what to act on.

```
/scrutinise                              # default scope: today's commits + uncommitted changes
/scrutinise today's commits              # explicit scope
/scrutinise the auth module              # focus on a subsystem
/scrutinise the work in this session     # review what we just did together
/scrutinise the diff between main and HEAD
```

## `/plan-review`

Spawns three reviewers in parallel — `scrutiniser` (deep critical review), `Plan` (architecture and strategy), and `general-purpose` (claim-by-claim fact-checking against the code) — then synthesises their reports into one consolidated, severity-ranked verdict where every finding carries a concrete recommended action.

```
/plan-review docs/plans/my-plan.md
```

The dominant failure mode for plans is factual drift from code reality; a local session can verify claims a cloud sandbox cannot. The command reports — it never edits the plan file.

## The `scrutiniser` agent

Both commands rely on the bundled `scrutiniser` subagent. It can also be invoked directly via the Task tool with `subagent_type: scrutiniser` whenever critical review is appropriate. Running review in a subagent keeps the file-opening and grep noise out of the parent session's context — it returns a focused report and leaves the parent clean.

## Install

```
/plugin marketplace add sebastiansulinski/claude-plugins
/plugin install review@sebastiansulinski
```

## Layout

```
review/
├── .claude-plugin/plugin.json   # plugin manifest
├── commands/scrutinise.md       # the /scrutinise slash command
├── commands/plan-review.md      # the /plan-review slash command
├── agents/scrutiniser.md        # the deep-review subagent (shared by both commands)
└── README.md
```

## Philosophy

- **Read, don't skim.** Findings cite `file:line`. Vague concerns aren't findings.
- **Honest severity.** No padding the report with Minors to look thorough; no downgrading real bugs.
- **Project-aware.** Reads `CLAUDE.md` and architectural docs first so it can flag convention violations, not just generic issues.
- **No auto-fix.** Reviewer, not implementer.
