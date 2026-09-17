# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
