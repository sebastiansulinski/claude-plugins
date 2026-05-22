# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
