---
name: create
description: Create an isolated Git worktree for parallel work in a plain repository or submodule.
---

# Create a worktree

Use the name and options supplied in the user's request. A name is required: if absent, ask for it rather than
inventing one. Recommend short kebab-case names. An optional base branch maps to `--from`; preserve requested
`--dest`, `--env`/`--no-env`, `--composer`/`--no-composer`, and `--npm`/`--no-npm` options.

Resolve the bundled [worktree runtime](../../scripts/worktree.sh) relative to this skill file, then use its
absolute path for every invocation. Run from the repository that owns the requested work: for a submodule,
run inside that submodule. Read applicable repository instructions before choosing a branch or destination.

1. Inspect `.worktree.json` when present and show resolved settings with `bash "$worktree_runtime" config`
   where resolvable, with `worktree_runtime` set to the absolute script path. A requested `--from` or `--dest`
   can override an invalid configured base or destination; a diagnostic `config` failure alone does not rule
   out that valid create invocation. The engine honours configuration and otherwise uses the shared `wt/`
   branch prefix. There is no prefix flag or environment override. If repository instructions require a
   different prefix and configuration does not provide it, explain the configuration prerequisite before
   creating anything. Configure the required prefix through the init workflow when authorized; do not
   silently rewrite repository settings or rename a branch after creation. Existing configuration wins.
2. Run the engine with separately quoted arguments:

   ```bash
   bash "$worktree_runtime" create "<name>" --from "<base-branch>" --json
   ```

   Omit `--from` when no base was requested; include only the supported options requested by the user.
   Pass arguments as shell-quoted values, never evaluate user-provided shell text.
3. Parse JSON output and report the path, branch, base, and each bootstrap result (`env`, `composer`, `npm`,
   `postSetup`). A nonzero exit can still include valid JSON when bootstrap failed after creation. Report
   the created worktree and failed step plainly; it remains available for manual recovery inside it.
4. Surface engine errors accurately. For invalid names, existing branches, unsafe destinations, or an
   unresolved base, correct the input. Do not improvise recovery operations against the shared Git directory.

After success, keep work and commits inside the new directory, on its own branch. Integrate it according to
the repository's branch and pull request policy. The original checkout's files, HEAD, and branch stay intact.
A copied `.env` uses the same services as the original checkout: use the test suite with its test configuration;
do not run destructive migrations, queue workers, or smoke runs against those shared services.
