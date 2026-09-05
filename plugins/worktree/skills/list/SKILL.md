---
name: list
description: List Git worktrees with their branch, dirty state, recorded base, and merge status for a repository or submodule.
---

# List worktrees

Resolve the bundled [worktree runtime](../../scripts/worktree.sh) relative to this skill file, assigning its
absolute path to `worktree_runtime`. Run from the repository the user means; run inside a submodule to list
that submodule's worktrees.

```bash
bash "$worktree_runtime" list --json
```

Present a readable table with name (path basename), branch, clean/dirty status, tool-created/manual status,
recorded base, and `mergedIntoBase`. Preserve unknown/null values as unknown rather than treating them as false.
The first entry is Git's main checkout: label it and exclude it from removal candidates.

Call out actionable results without changing anything:

- `canDeleteBranch: true` identifies clean work merged into its recorded base; it can be offered for the
  worktree remove workflow with `--delete-branch`.
- Dirty worktrees contain unfinished changes.
- Tool-created entries with `underCurrentDestination: false` remain valid but now live outside the configured
  destination, usually following a configuration change. Include their actual paths.

Use the runtime's metadata to distinguish tool-created worktrees from manually created ones. Location alone
cannot establish ownership. Listing is read-only; do not prune, remove worktrees, or delete branches.
