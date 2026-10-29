---
name: progress-save
description: Save an orchestrated workstream's state to its progress file (docs/progress/<workstream>.md) and commit and push it, so the orchestrator and every sub-task can be resumed under another account or host. Use when the user asks to save progress, switch accounts, or log out.
---

# Save an orchestrated workstream's progress

Identify the workstream from the user's request. If none is named and `docs/progress/` holds a single workstream
file, use it; if there are several, ask which; if there are none, offer to start one.

## Prepare the files

Work from the repository root, which is the superproject when this checkout is a submodule
(`git rev-parse --show-superproject-working-tree`). If `docs/progress/README.md` is missing, create it from
[the bundled README](../../references/progress-readme.md). If the workstream file is missing, create it from
[the bundled workstream template](../../references/progress-workstream.md).

Read both in full, along with the applicable `AGENTS.md` instructions.

## Reach a clean point

This host can't message other tasks. Ask the user to bring each other running task in the session registry to a clean
point before saving:
- finished chunks committed, with the project's checks green;
- no new chunk started.

Don't wait on tasks you can't reach. Record what git shows instead.

## Verify from git

For every repository the workstream touches, including submodules (`git submodule status`), run:
- `git worktree list`;
- for each branch and worktree in the file:
  - the tip commit;
  - `git status --short`;
  - the commit count against its base branch;
  - whether it's pushed (`git ls-remote --heads origin <branch>`).

Also check whether the main branches match their remotes. Git wins over the file and over recollection.

## Rewrite the file

- Rewrite the snapshot sections: "Where things stand", each sub-task's state, next step and resume brief, open
  questions, not yet assigned, and decisions.
- In the **session registry**, add every task started since the last save and mark closed ones. Put identifiers in the
  column for this host and account, for example "Codex seb@example.com", and only when the host reports them. Add
  the column if it's missing.
- Record uncommitted work in any worktree as **uncommitted**, with what it is.
- Copy any notes the work depends on into `docs/progress/notes/<workstream>/`.
- Update the snapshot date and append one dated line to the log.

## Commit and push

Stage only `docs/progress/`. Commit with a subject and body, following the project's commit conventions, then push.

## Report

In two lines:
- the commit that holds the save;
- anything that won't travel: uncommitted work, unreachable tasks, or branches not pushed (these matter only when
  moving to another machine).

Never write secrets. Name keys by their environment variable only.
