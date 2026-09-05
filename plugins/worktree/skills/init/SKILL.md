---
name: init
description: Configure optional per-project Git worktree settings through guided questions and validated .worktree.json writes.
---

# Configure worktrees

Use this workflow when the user asks to create or change worktree settings. Configuration is optional.
Resolve the bundled [worktree runtime](../../scripts/worktree.sh) relative to this skill file and assign its
absolute path to `worktree_runtime`. Run from the owning repository, including inside a targeted submodule.

1. Read applicable repository instructions. Run `bash "$worktree_runtime" config` and inspect the existing
   `.worktree.json` if present. The command shows resolved settings, while the file identifies explicit
   overrides. Retain existing keys and values unless the user requests changes.
2. Inspect available branches and `origin/HEAD`, plus the presence of `composer.json`, `package.json`, `.env`,
   and a committed `.worktree-setup.sh`. Ground recommendations in these observations.
3. Gather only the settings still needed, using an available input tool within its question limit or ordinary
   conversation. Treat existing values and explicit instructions as the defaults:
   - Base branch for new worktrees.
   - Destination, outside both the repository and any superproject. The normal destination is a sibling of
     the repository, or a sibling of its superproject for submodules.
   - Branch prefix. Preserve an existing prefix; for a new Codex configuration recommend `codex/` unless
     project instructions say otherwise. The unchanged shared engine uses `wt/` without configuration.
   - Bootstrap: copy `.env`, run `composer install`, and run `npm ci`. npm defaults to off; Composer is used
     when its manifest is present.
   - Optional post-setup script. A relative path resolves inside the new worktree; the conventional
     `.worktree-setup.sh` is picked up automatically when no override is set.
4. Build the requested JSON using only `baseBranch`, `destination`, `branchPrefix`, `bootstrap` (keys `copyEnv`,
   `composer`, `npm`), and `postSetup`. Omit new convention defaults; preserve existing explicit overrides.
   For example, a new configuration requesting only Codex's prefix is `{"branchPrefix":"codex/"}`.
5. Send the JSON through stdin to the validated writer:

   ```bash
   bash "$worktree_runtime" config --write < "$worktree_config_payload"
   ```

   Here `worktree_config_payload` is a temporary file containing the exact requested JSON. Use structured
   file writing or safe shell quoting, then delete that temporary file. Never write `.worktree.json` directly:
   the runtime validates keys, types, prefix syntax, and destination containment before replacing it.
6. If validation fails, relay the reason and correct the invalid value within the user's choices. Re-run
   `config` after a successful write and show the resolved settings. Suggest committing `.worktree.json`
   according to the repository's workflow; do not commit it unless that is authorized.

Configuring `codex/` is an explicit persistent repository setting, shared with other callers of this engine.
It is not a hidden per-session override. Copying `.env` also shares the original checkout's service endpoints.
