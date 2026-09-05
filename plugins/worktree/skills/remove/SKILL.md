---
name: remove
description: Remove a named Git worktree with checks for uncommitted changes, unmerged branches, and unmanaged worktrees.
---

# Remove a worktree

Resolve the bundled [worktree runtime](../../scripts/worktree.sh) relative to this skill file, assigning its
absolute path to `worktree_runtime`. Run from the owning repository, or inside the targeted submodule.
Read applicable repository policies and retain any user authorization already given for this exact removal.

1. Always run `bash "$worktree_runtime" list --json` before removal. If the user supplied no name, show the
   list and ask which worktree to remove. Never target the main checkout.
2. Read the target's `dirty`, `base`, `mergedIntoBase`, `canDeleteBranch`, and `createdByTool` fields from that
   output. Names are directory basenames. If more than one entry has the requested basename, show candidate
   paths and stop for disambiguation; do not guess or reconstruct a path from current configuration.
3. Choose flags based on the user's request and the recorded state:
   - Dirty worktree: show `git -C "<target-path>" status --porcelain` and explain which uncommitted changes
     would be discarded. Add `--force` only with explicit authorization to discard those changes.
   - Offer `--delete-branch` only when `canDeleteBranch` is true. For an unmerged or unknown-base branch,
     leave the branch in place unless the user explicitly authorizes deleting that unmerged/unverified work;
     then the engine requires `--force`. Permission to remove the directory alone does not imply this.
   - An unmanaged worktree has no `worktreeBase` marker. Use `--unmanaged` only after explicit authorization
     to remove that particular unmanaged worktree. If the engine discovers it later, surface the refusal
     and obtain any missing authorization before retrying.
   - `--force` bypasses both dirty-work and branch-merge guards. When both risks exist, authorization must
     cover both; do not use one authorization to bypass the other.
4. Run the removal with separately quoted values, including only authorized flags:

   ```bash
   bash "$worktree_runtime" remove "<name>" --json
   ```

   Optional flags are `--delete-branch`, `--force`, and `--unmanaged`. Do not automatically retry a refusal
   with stronger flags. The engine checks merge status against the recorded base before removing anything.
5. Report the returned path and whether the branch was deleted. Preserve an engine refusal and its reason
   accurately; confirm that the target remains before saying it was removed.

This workflow removes a worktree and optionally its branch. It does not authorize deleting unrelated files,
editing shared Git metadata manually, or deleting similarly named worktrees to resolve an ambiguity.
