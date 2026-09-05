---
name: purge
description: Investigate dead code and unused Composer or JavaScript dependencies, present verified findings, and remove only items the user explicitly approves. Use for a requested cleanup or unused-code audit.
---

# Dead-code investigation and cleanup

Resolve the requested scope from the invocation. If none is given, inspect the whole codebase across
functions/methods, variables/properties, constants, Composer dependencies and JavaScript dependencies.
Read [the purger procedure](../../references/purger.md) before starting; it contains the usage checks,
report format, approval boundary and verification sequence.

Read applicable repository instructions and preserve their testing/style policies. Present the analysis
scope, then investigate one category at a time. When available and useful, delegate bounded independent
categories to actual Codex collaboration agents. Give each agent the absolute repository path, explicit
scope, relevant policy and procedure, and a read-only mandate. Inherit the selected model; do not assume
a Markdown procedure registers a named agent. If delegation is unavailable, perform the same checks locally
and disclose the lack of an independent pass. Combine and verify delegated findings before presenting them.

Present the full categorized findings report and obtain explicit approval of the actual items before
removal. A request to find or clean dead code authorizes the investigation, not deletion of an unseen list.
Carry forward an existing explicit selection from the conversation instead of asking for it again.
Remove only selected items; follow the procedure's verification and failure recovery. Report the exact
changes, checks and anything retained or still uncertain.
