---
description: List git worktrees for the current repository with branch, dirty state, and merge status.
---

List all git worktrees of the current repository (run from inside a submodule to list that submodule's worktrees).

## Steps

1. Execute:

   ```
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/worktree.sh" list --json
   ```

2. Present the result as a readable table: name (path basename), branch, clean/dirty, created-by-tool or manual, base branch, and whether the branch is merged into its base (`mergedIntoBase`).
3. Point out anything actionable:
   - worktrees whose `canDeleteBranch` is `true` — finished work that can be cleaned up with `/worktree:remove <name> --delete-branch`,
   - dirty worktrees — work in progress,
   - entries with `underCurrentDestination` `false` that ARE tool-created — orphaned by a destination config change; they still work, but note where they live.
4. The main checkout appears in the list too (it is a worktree from git's perspective) — label it as the main checkout, not as a candidate for removal.
