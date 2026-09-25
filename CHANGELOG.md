# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.0] - 2026-09-25

### Changed

- **`explain` now writes for its reader instead of at them.** Both skills (Claude Code and Codex,
  identical writing rules) start by naming who the explanation is for, then judge every sentence
  against that person. The closing list of terms is gone entirely — an unclear word must now be
  replaced with an everyday one, or explained right where it stands, in brackets or a short clause,
  never deferred to a glossary. The rules also name the words that leak into explanations most often,
  with plain replacements, including everyday words that quietly carry a technical meaning ("request",
  "call", "run", "build", "job", "check"). File paths, commands, and other identifiers stay out of the
  explanation. Every change a person could actually notice must now carry a worked scene — a named
  person, a moment, an outcome — and that scene may add nothing the source artefact does not say; a
  change nobody would notice must say so plainly rather than being given an invented scene. The rules
  now show one complete worked example end to end, and close with a re-read pass that checks a draft
  against each of these rules before it is sent. Length limits no longer come at the example's expense.
  The explain plugin moves to `1.1.0` on both hosts. Acceptance checks were tightened first, and
  baseline and revised outputs from the same three fixtures are kept in
  `tests/acceptance/explain-outputs-2026-09-25.md`.

## [1.5.0] - 2026-09-19

### Added

- **`worktree:cleanup`** — a fifth entry point on the worktree plugin that tidies up the
  calling session's own worktrees and branches (merged, abandoned or never used) across
  the repository and every initialised submodule, while keeping what the session is
  still working on. The engine now records provenance markers at creation time (session,
  path, creation time, start commit) stored beside the existing base marker, derived from
  whatever identity the host exposes to shell commands (`--session`, `WORKTREE_SESSION`,
  `CLAUDE_CODE_SESSION_ID`, `CODEX_SESSION_ID`, `CODEX_THREAD_ID`) — so both hosts work
  with zero configuration. `cleanup` reports only this session's candidates with
  supporting facts and a safety verdict; with `--apply` it removes exactly the
  identifiers it is given, each re-checked against live git state immediately before
  removal (clean, contained in the recorded base, not locked, not the current directory,
  base still present), deletes branches at the verified tip using `git update-ref -d`,
  never prunes globally, and refuses to run at all without a session identity — so it can
  never touch another session's work. Claude Code: `/worktree:cleanup`, also aliased
  `/cleanup`; user-invocable only (not for the agent to run on its own initiative).
  Codex: `worktree:cleanup`. Covered by harness test cases (337 assertions), a package
  test run against an installed copy of the plugin, acceptance scenarios, and an
  execution record kept in `tests/acceptance/cleanup.md`.

### Changed

- Worktree plugin manifests bumped to `1.1.0` on both hosts; `create` now accepts
  `--session` and reports the recorded session; `list --json` gains `session`,
  `recordedPath` and `createdAt` fields; `remove --delete-branch` now clears all
  provenance markers; a shared retry mechanism now covers lock contention for creation,
  removal and branch deletion (previously creation only).

## [1.4.0] - 2026-09-17

### Added

- **`review:plan-verify`** — a third entry point on the review plugin that verifies a plan
  has been fully and correctly implemented. It maps the workspace first (main checkout,
  linked worktrees, superproject, submodules and their worktrees) and resolves where the
  plan and the implementation live rather than assuming the current directory, turns the
  plan into a numbered checklist of every promise, and runs three reviewers in parallel: a
  coverage verifier, the scrutiniser with test-adequacy ownership, and a verification
  runner that executes only the project's own designated checks under its test
  configuration. The synthesis (`ultrathink` on Claude Code) produces a computable verdict
  with a coverage line, reporting a plain-language summary first, then the technical
  report. Read-only. Named `plan-verify` rather than `verify` because Claude Code ships a
  built-in skill named `verify` that owns the bare name. Claude Code: `/review:plan-verify`,
  also reachable as the bare `/plan-verify`; user-invocable only. Codex:
  `review:plan-verify`. Acceptance scenarios and the print-mode execution record are in
  `tests/acceptance/plan-verify.md`.

### Changed

- Review plugin manifests bumped to `1.1.0` on both hosts; the review plugin's
  descriptions and its README now use namespaced command names throughout.
- The `scrutinise` argument hint no longer uses an abbreviation.

## [1.3.0] - 2026-09-15

### Added

- **`explain` plugin** — one read-only skill that turns the previous outcome, or a named
  subject, into a plain-language explanation for a non-technical reader: what changed,
  what it fixes, and what they will notice, with concrete examples. Claude Code:
  `/explain:explain`, also reachable as the bare `/explain`; user-invocable only, with no
  automatic invocation by the model. Codex: `explain:explain`. Initial native package
  version is `1.0.0`. Acceptance scenarios and the execution record are in
  `tests/acceptance/explain.md`.

### Changed

- Contract tests now accept the `skills/` layout for Claude Code packages, and fail
  cleanly when a Codex manifest is missing.
- Hard-coded plugin counts were removed from the README, the packaging script's help
  text, and a test name, so they no longer need updating each time a plugin is added.

## [1.2.0] - 2026-09-05

### Added

- **Native Codex support for all eight plugins** — 13 skills covering review, session handoffs,
  repository deprecation, releases, requirements, query analysis, dead-code cleanup and worktrees.
- Codex marketplace `sebastiansulinski-codex` in `.agents/plugins/marketplace.json`, with
  self-contained native packages under `plugins/`. Initial native package versions are `1.0.0`.
- Codex-specific instruction discovery, input handling, delegation and package-relative resources.
  The three specialist agent procedures are preserved as bundled references.
- Package contract tests, installed-copy worktree tests, independent workflow acceptance records,
  and deterministic per-plugin release ZIP generation.
- Worktree runtime synchronization and equality verification, preserving the existing shell engine.

### Changed

- Installation and update documentation now covers both Claude Code and Codex, including migration
  from legacy Claude imports in Codex. Existing Claude plugin paths and behaviour are unchanged.

## [1.1.0] - 2026-06-11

### Added

- **`worktree` plugin** — isolated git worktrees for parallel agents, on plain repositories and submodules:
  - `/worktree:create` — creates a worktree on its own branch (base resolved local-then-remote: `develop` → `origin/HEAD` → `main` → `master`), bootstraps it (`.env` copy, `composer install`, optional `npm ci`, optional post-setup hook), and never touches the main checkout. For submodules the destination defaults to a sibling of the superproject.
  - `/worktree:remove` — removes a worktree resolved from git's own metadata; refuses dirty worktrees without `--force`, refuses worktrees the tool did not create without `--unmanaged`, and judges `--delete-branch` merged-ness against the base recorded at create time, never the main checkout's HEAD.
  - `/worktree:list` — branch, dirty state, created-by-tool marker, and merge status per worktree.
  - `/worktree:init` — guided per-project `.worktree.json` written through the validating `config --write` script surface.
  - Ships `scripts/worktree.sh` (the deterministic core, usable by any tool that can run a shell command) and a fixture-based test harness (`tests/run.sh`, 138 assertions, plain-repository and superproject-plus-submodule fixtures, no network).

## [1.0.0] - 2026-05-22

### Added

- **`review` plugin** — two commands for critical code and plan review:
  - `/review:scrutinise` — deep forensic review of recent work; surfaces bugs, design flaws, anti-patterns, missing tests, and edge cases.
  - `/review:plan-review` — multi-agent grounded review of a plan file, combining a scrutiniser, architect, and fact-verifier pass synthesised with an ultrathink step.
  - Ships the `scrutiniser` subagent, which can also be invoked directly via `subagent_type:`.
- **`session` plugin** — two commands for session lifecycle management:
  - `/session:good-morning` — resumes work from the previous session by loading memory, lessons, config, and the project prompt, then proposing next steps.
  - `/session:call-it-a-day` — end-of-session capture that records state so the next session resumes with no context loss.
- **`repo` plugin** — one command for repository lifecycle:
  - `/repo:deprecate` — fully deprecates and archives a repository, including notices, branch protection, and GitHub archival.
- **`release` plugin** — one command for the full release workflow:
  - `/release:publish` — runs the complete changelog update, git tag creation, and GitHub release publication in strict order.
  - Ships the `manager` subagent, which can also be invoked directly via `subagent_type:`.
- **`requirements` plugin** — one command for pre-implementation requirements gathering:
  - `/requirements:interrogate` — exhaustively interrogates project requirements through structured questioning; never writes code.
- **`db` plugin** — one command for database performance analysis:
  - `/db:query-analysis` — read-only audit of Eloquent and query-builder usage in a repository, identifying queries with measurable potential for performance or memory improvement; writes findings to `docs/analysis/`.
- **`dead-code` plugin** — one command for codebase hygiene:
  - `/dead-code:purge` — finds and safely removes dead code and unused dependencies; only proceeds after explicit approval.
  - Ships the `purger` subagent, which can also be invoked directly via `subagent_type:`.
- Marketplace manifest (`.claude-plugin/marketplace.json`) registering all 7 plugins under the `sebastiansulinski` namespace, installable via `/plugin marketplace add sebastiansulinski/claude-plugins`.
