---
name: progress-save
description: >-
  Save an orchestrated workstream's state to its progress file (docs/progress/<workstream>.md), then commit and push it,
  so the orchestrator and every sub-session can be resumed under another account or later on this one. Use when the
  user says progress-save, "save progress", "I'm switching accounts" or "I'm logging out".
---

# Save an orchestrated workstream's progress

**Workstream:** $ARGUMENTS

If no workstream is given and `docs/progress/` holds a single workstream file, use that one. If there are several,
ask which. If there are none, offer to start one.

## 0. The pattern files

The repository root is the superproject when this checkout is a submodule (`git rev-parse --show-superproject-working-tree`).

If `docs/progress/README.md` is missing there, create it from [the bundled README](../../references/progress-readme.md).
If the workstream file is missing, create it from [the bundled workstream template](../../references/progress-workstream.md).
Then read both in full, along with the repository's `CLAUDE.md` and `AGENTS.md`.

## 1. Bring each sub-session to a clean point

Find the sub-sessions with `mcp__ccd_session_mgmt__list_sessions` (`{"linked": true}`), and match them to the session
registry. Message each one by its `local_…` identifier with `SendMessage`, asking it to:
- commit any finished chunk, with the project's checks green;
- leave unfinished work uncommitted and say what that work is;
- start no new chunk;
- reply with one line: its branch tip, and its next step.

Wait for each reply. Never commit on a session's behalf.

If the session tools aren't available (for example, in the command line rather than the desktop app), skip this step,
read the state from git only, and say so when you report.

## 2. Verify from git, never from memory

For every repository the workstream touches, including submodules (`git submodule status`), run:
- `git worktree list`;
- for each branch and worktree in the file:
  - `git -C <worktree> log -1 --oneline`;
  - `git -C <worktree> status --short`;
  - the commit count against its base branch;
  - whether it's pushed (`git ls-remote --heads origin <branch>`).

Also check whether the main branches match their remotes.

## 3. Rewrite the file

- Rewrite the snapshot sections: "Where things stand", each sub-session's state, next step and resume brief, open
  questions, not yet assigned, and decisions.
- In the **session registry**, add every session started since the last save and mark closed ones. Put identifiers
  in the column for this host and account, labelled with the account's email from the session context, for example
  "Claude seb@example.com". Add the column if it's missing.
- Record any uncommitted work as **uncommitted**, with what it is.
- Copy any shared notes a session depends on into `docs/progress/notes/<workstream>/`. A host's private notes folder
  isn't visible to another account.
- Update the snapshot date and append one dated line to the log.

## 4. Commit and push

Stage only `docs/progress/`. Commit with a subject and body, adding no attribution trailer the project's
instructions forbid, then push.

## 5. Report in two lines

- The commit that holds the save.
- Anything that won't travel, such as uncommitted work in a worktree, a session that didn't reply, or unpushed
  branches (these matter only when moving to another machine).

Never write secrets. Name keys by their environment variable only.
