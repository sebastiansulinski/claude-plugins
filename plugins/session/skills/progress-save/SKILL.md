---
name: progress-save
description: Save this main task and every sub-task it started to the main task's own progress file (docs/progress/<main-session>.md, named from its title), recording their exact titles, settings, branches and worktrees, then commit and push it so they can be recreated under another account or host. --all saves every main session's file. Use when the user asks to save progress, switch accounts, or log out.
---

# Save a main task and its sub-tasks

The **main task** is the one this skill runs in. Its sub-tasks are the tasks it started. Each main task or main
session has its own file. Never write another one's file.

If the user asks for `--all`, skip to "Save every main session" at the end.

## Find or create this main task's file

Work from the repository root, which is the superproject when this checkout is a submodule
(`git rev-parse --show-superproject-working-tree`).

1. Look in every `docs/progress/*.md` for one whose session registry lists this task's identifier, if the host
   reports one. If one does, it's this task's file.
2. Otherwise, name the file from this task's exact title. Lower-case it, turn every run of characters other than
   letters and digits into a single hyphen, and trim hyphens from both ends. "Core: Scrape" becomes `core-scrape`, so
   the file is `docs/progress/core-scrape.md`.
   - If the host doesn't expose the title, suggest a name from the branch or plan, and ask the user to confirm it.
   - If the file exists but belongs to a different main session, don't touch it. Ask for a name.
3. Create any missing files from the bundled templates:
   - `docs/progress/README.md` from [the bundled README](../../references/progress-readme.md);
   - the main task's file from [the bundled workstream template](../../references/progress-workstream.md).

Read both files in full, along with the applicable `AGENTS.md` instructions.

## Reach a clean point

This host can't message other tasks. Ask the user to bring each running sub-task in the session registry to a clean
point before saving:
- each sub-task write or update its **hand-over note** at `docs/progress/notes/<main-session>/<session-name>.md`. The
  note covers what it knows that isn't in its plan or in git: the decisions it made and why, the gotchas it found,
  what it tried that failed, what it's waiting on, and its exact next step. Keep it current rather than
  appending a diary, and never write secrets in it;
- finished chunks committed, with the project's checks green;
- no new chunk started.

Record what git shows for any task you can't reach, and note in the report whose hand-over note wasn't updated.

Write this main task's own **hand-over note** at `docs/progress/notes/<main-session>/<session-name>.md`, using its
short name. It records the coordination knowledge: which task owns what, the merge order, and what's waiting on the
user.

## Verify from git

For every repository involved, including submodules (`git submodule status`), run:
- `git worktree list`;
- for each branch and worktree in the file:
  - the tip commit;
  - `git status --short`;
  - the commit count against its base;
  - whether it's pushed (`git ls-remote --heads origin <branch>`).

Git wins over the file and over recollection.

## Rewrite the file

**The session registry** has one row per task, the main task first. For each one, record:
- its **exact title**, as the host shows it, where the host exposes it;
- its short name;
- its model and reasoning settings, where known;
- its working folder, worktree and branch;
- its identifier, only when the host reports one, in this host and account's column. Label the column, for example,
  "Codex seb@example.com", and add it if it's missing.

Keep the other columns as they are, including any Claude sidebar groups and pins. Mark closed tasks as closed.

**The other sections:**
- Rewrite the snapshot sections: "Where things stand", each sub-task's state, next step and resume brief, open
  questions, not yet assigned, and decisions.
- Record any uncommitted work as **uncommitted**, with what it is.
- Copy any notes the work depends on into `docs/progress/notes/<main-session>/`.
- List every task's hand-over note in the "Notes" section, and link it from that task's row or section.
- Update the snapshot date, and append one dated line to the log.

## Commit and push

Stage only `docs/progress/`. Commit with a subject and body, following the project's commit conventions, then push.

## Report

Two lines:
- the file, and the commit that holds the save;
- anything that won't travel: uncommitted work, tasks you couldn't reach, or branches that aren't pushed (these matter
  only when moving to another machine).

## Save every main session (`--all`)

This host can't ask other main sessions to save themselves.
- List every `docs/progress/*.md` except `README.md`, with its main session's title and its last snapshot date.
- Save this task's own file, following the steps above.
- Tell the user which other files need saving from their own main sessions.

Never write secrets. Name keys by their environment variable only.
