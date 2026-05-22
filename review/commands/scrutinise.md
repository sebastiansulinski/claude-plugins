---
description: Run a deep critical review of recent work — bugs, design, anti-patterns, missing tests, edge cases. No skimming.
argument-hint: [optional scope, e.g. "today's commits", "the auth module", "the work in this session"]
---

Spawn the `scrutiniser` agent (via the Task tool) to perform a forensic critical review.

**Scope to review:** $ARGUMENTS

If the scope above is empty, default the scope to: *"today's commits plus any uncommitted changes on the current branch"*.

When invoking the agent, pass it a self-contained brief that includes:

1. The resolved scope (state it explicitly so the agent doesn't have to guess).
2. A reminder that this is a **critical, no-skim review** — the agent should read the actual files, trace the changes, and verify behaviour against tests rather than trusting commit messages.
3. The current working directory and git branch so the agent has its bearings.
4. A note that the agent must **not** modify files or fix anything — its only job is to report findings.

After the agent returns, surface its report verbatim to me. Do not summarise it, do not collapse findings, do not editorialise. If the agent reports zero issues, say so plainly. If it reports issues, present the full report and stop — wait for me to decide what to act on.
