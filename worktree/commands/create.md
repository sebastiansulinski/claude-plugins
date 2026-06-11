---
description: Create an isolated git worktree for parallel work — works on plain repositories and submodules.
argument-hint: <name> [base-branch]
---

Create an isolated git worktree so work on a separate plan can proceed without touching this checkout.

**Arguments:** $ARGUMENTS

The first argument is the worktree name (required — short, kebab-case, typically the plan name). The optional second argument is the base branch; map it to the script's `--from` flag. Any further arguments the user supplies that look like script flags (`--dest`, `--env`/`--no-env`, `--composer`/`--no-composer`, `--npm`/`--no-npm`) pass through verbatim.

## Steps

1. If no name was given, ask for one — do not invent it.
2. From the repository the user wants the worktree for (the current working directory's repository — if the work targets a submodule, run from inside that submodule), execute:

   ```
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/worktree.sh" create <name> [--from <base-branch>] [passthrough flags] --json
   ```

3. Parse the JSON result and report to the user:
   - the worktree path and branch (and the base it was created from),
   - which bootstrap steps ran, were skipped, or failed (`env`, `composer`, `npm`, `postSetup`).
4. If the script fails, surface its error message verbatim — the messages are self-explanatory (invalid name, branch exists, destination inside the repository or superproject, unresolvable base branch). Do not improvise recovery git commands against the shared git directory; fix the input and re-run the script.
5. If a bootstrap step failed but the worktree was created, say so plainly: the worktree is usable, the failed step can be re-run manually inside it.

## Remind the user (briefly, after success)

- Work happens **only inside the new worktree directory**; the main checkout stays untouched.
- Commits are made from inside the worktree on its own branch — that is the intended workflow. Merge back via an ordinary branch merge in the main checkout, one plan branch at a time.
- A copied `.env` points the worktree at the **same services** (database, Redis, queues) as the main checkout: run the test suite only; no `artisan migrate:fresh`, no queue workers, no smoke runs from a worktree.

Do not embed any project-specific policy here — workspace rules live in the project's own CLAUDE.md.
