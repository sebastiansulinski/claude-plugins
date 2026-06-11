---
description: Remove a worktree created by /worktree:create, optionally deleting its branch when merged.
argument-hint: <name>
---

Remove a worktree previously created with `/worktree:create`.

**Arguments:** $ARGUMENTS

## Steps

1. If no name was given, run the list first and ask which worktree to remove:

   ```
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/worktree.sh" list --json
   ```

2. Read the target's state from that same `list --json` output rather than re-deriving git state yourself: `dirty`, `base`, `mergedIntoBase`, `canDeleteBranch`.
3. Decide the flags:
   - If the worktree is **dirty**, warn the user what uncommitted changes would be discarded (show `git -C <path> status --porcelain`) and require their explicit confirmation before adding `--force`.
   - Offer `--delete-branch` only when `canDeleteBranch` is `true`. If the branch is unmerged, say so and leave the branch in place — deleting unmerged work needs the user to ask for it explicitly (then `--force`).
   - If the script reports the worktree was **not created by this tool** (no `worktreeBase` marker), stop and confirm with the user before re-running with `--unmanaged`.
4. Execute:

   ```
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/worktree.sh" remove <name> [--delete-branch] [--force] [--unmanaged] --json
   ```

5. Report what was removed and whether the branch was deleted. If the name is ambiguous (two worktrees share the basename), the script aborts and lists the candidates — show them to the user and ask which one they meant; the safe path is to remove the other one first or rename rather than guessing.
