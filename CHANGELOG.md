# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
