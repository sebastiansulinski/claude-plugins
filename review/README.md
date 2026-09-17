# review

A plugin with three critical-review entry points, shipped for Claude Code and Codex:

- **`/review:scrutinise`** — deep, evidence-based critical review of recent work: bugs, design flaws, anti-patterns, missing tests, edge cases, security holes, inconsistencies. No skimming, no auto-fixing.
- **`/review:plan-review`** — multi-agent grounded review of a plan file, run entirely locally so it can verify every claim against the actual codebase.
- **`/review:plan-verify`** (also `/plan-verify`) — verification that a plan has been fully and correctly implemented: three independent reviewers, one deep synthesis, a plain-language summary first.

Part of the [claude-plugins marketplace](../README.md). Codex users get the same three workflows as `review:scrutinise`, `review:plan-review` and `review:plan-verify`; see the root README for installation.

## `/review:scrutinise`

Delegates to a `scrutiniser` subagent that reads project context (`CLAUDE.md`, architectural-decision docs), inspects the actual code in scope, traces changes against tests, and produces a structured report with findings tiered by severity (Critical / Important / Minor). The agent **never** edits files — it reports, you decide what to act on.

```
/review:scrutinise                              # default scope: today's commits + uncommitted changes
/review:scrutinise today's commits              # explicit scope
/review:scrutinise the auth module              # focus on a subsystem
/review:scrutinise the work in this session     # review what we just did together
/review:scrutinise the diff between main and HEAD
```

## `/review:plan-review`

Spawns three reviewers in parallel — `scrutiniser` (deep critical review), `Plan` (architecture and strategy), and `general-purpose` (claim-by-claim fact-checking against the code) — then synthesises their reports into one consolidated, severity-ranked verdict where every finding carries a concrete recommended action.

```
/review:plan-review docs/plans/my-plan.md
```

The dominant failure mode for plans is factual drift from code reality; a local session can verify claims a cloud sandbox cannot. The command reports — it never edits the plan file.

## `/review:plan-verify`

Answers the question "was this plan actually done?" Before anything else it maps the workspace — main checkout, linked worktrees, superproject, submodules and their worktrees — and resolves where the plan is and where the implementation lives, since the two are often not the current directory. It then turns the plan into a numbered checklist of every promise and launches three reviewers in parallel: a coverage verifier (implemented, partial, missing, deviated, unverifiable, plus unplanned changes), the `scrutiniser` (forensic review, including whether each test really guards the behaviour it is named for), and a verification runner that executes only the project's own designated test, validation and build commands under the project's test configuration. An `ultrathink` synthesis produces a verdict with a coverage line, then a summary a non-technical reader can follow, then the technical report. Read-only: it never edits, fixes, reverts or updates the plan's status.

```
/plan-verify docs/plans/my-plan.md                         # verify against the plan
/plan-verify docs/plans/my-plan.md the uncommitted work    # scope hint
/plan-verify docs/plans/my-plan.md in worktree checkout-flow
/plan-verify                                          # infer the plan from the conversation, task list or branch
```

The skill is user-invocable only; the model does not trigger it from prose.

## The `scrutiniser` agent

All three entry points rely on the bundled `scrutiniser` subagent. It can also be invoked directly via the Agent tool with the name the tool lists (`review:scrutiniser` when installed from the marketplace) whenever critical review is appropriate. Running review in a subagent keeps the file-opening and grep noise out of the parent session's context — it returns a focused report and leaves the parent clean.

## Install

```
/plugin marketplace add sebastiansulinski/claude-plugins
/plugin install review@sebastiansulinski
```

## Layout

```
review/
├── .claude-plugin/plugin.json   # plugin manifest
├── commands/scrutinise.md       # /review:scrutinise
├── commands/plan-review.md      # /review:plan-review
├── skills/plan-verify/SKILL.md       # /review:plan-verify, also /plan-verify
├── agents/scrutiniser.md        # the deep-review subagent (shared by all three)
└── README.md
```

## Philosophy

- **Read, don't skim.** Findings cite `file:line`. Vague concerns aren't findings.
- **Honest severity.** No padding the report with Minors to look thorough; no downgrading real bugs.
- **Project-aware.** Reads `CLAUDE.md` and architectural docs first so it can flag convention violations, not just generic issues.
- **No auto-fix.** Reviewer, not implementer.
