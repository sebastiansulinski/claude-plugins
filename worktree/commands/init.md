---
description: Write per-project worktree configuration (.worktree.json) through guided questions.
---

Configure worktree behaviour for the current repository by writing a `.worktree.json` to its root. Configuration is OPTIONAL — the conventions (base branch auto-detected, sibling destination, bootstrap inferred from `composer.json` / `package.json` / `.env` presence) are right for most repositories. Run this only when the user wants explicit settings.

## Steps

1. Show the current effective configuration first:

   ```
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/worktree.sh" config
   ```

   This prints the fully-resolved values (after precedence: existing `.worktree.json` → conventions), including whether the repository is a submodule. Re-running this command later edits the existing configuration in place — present current values as the defaults.

2. Inspect the repository briefly so your suggested answers are grounded: which branches exist (`develop`? what is `origin/HEAD`?), whether `composer.json`, `package.json`, and `.env` exist.

3. Ask the user the four questions, presenting the detected/current values as recommended defaults:
   - **Base branch** — which branch new worktrees branch from.
   - **Destination** — where worktree directories live. The convention default (sibling of the repository, or sibling of the superproject for submodules) is usually right; only set this to override it. It must resolve OUTSIDE the repository and any superproject working tree.
   - **Bootstrap steps** — copy `.env`? run `composer install`? run `npm ci`? (npm defaults to off — it is slow and backend plans rarely need it).
   - **Post-setup hook** — an optional script path, resolved inside each new worktree, for project-specific setup. Default: none (the conventional `.worktree-setup.sh` is picked up automatically if the repository commits one).

4. Assemble the answers into a JSON object using only these keys (omit any the user left at convention defaults — absent keys fall back to conventions):

   ```json
   {
       "baseBranch": "develop",
       "destination": "../../my-repo-worktrees",
       "branchPrefix": "plan/",
       "bootstrap": { "copyEnv": true, "composer": true, "npm": false },
       "postSetup": null
   }
   ```

5. Write it through the script — NEVER write `.worktree.json` directly; the script owns validation (unknown keys, types, branch-prefix syntax, destination containment) and serialization:

   ```
   printf '%s' '<the JSON>' | bash "${CLAUDE_PLUGIN_ROOT}/scripts/worktree.sh" config --write
   ```

6. If validation rejects the input, relay the script's reason, fix the value with the user, and retry. On success, run `config` once more and show the user the final resolved configuration. Suggest committing `.worktree.json` so the settings travel with the repository.
