---
description: Find and safely remove dead code and unused dependencies — verified, and only after your approval.
argument-hint: [optional scope, e.g. "the auth module", "composer dependencies"]
---

Spawn the `purger` agent (via the Task tool) to find and remove dead code.

**Scope to purge:** $ARGUMENTS

If no scope is given above, the agent analyses the whole codebase — unused
functions, variables, constants, and Composer / NPM dependencies.

When invoking the agent, pass it a self-contained brief that includes:

1. The resolved scope (state it explicitly).
2. The current working directory so the agent has its bearings.
3. A reminder that it must present a full categorised findings list and get
   explicit approval before removing anything — nothing is deleted unprompted.

Surface the agent's findings report to me and stop for my approval before any
removal proceeds.
