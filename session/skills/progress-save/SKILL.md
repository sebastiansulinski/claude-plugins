---
name: progress-save
description: >-
  Save this main session and every sub-session it started to the main session's own progress file
  (docs/progress/<main-session>.md, named from its sidebar title), mirroring their exact sidebar titles, groups and
  settings, then commit and push it so they can be recreated under another account or reopened later. --all saves
  every main session's file. Use when the user says progress-save, "save progress", "I'm switching accounts" or "I'm
  logging out".
---

# Save a main session and its sub-sessions

**Arguments:** $ARGUMENTS

The **main session** is the one this skill runs in. Its sub-sessions are the sessions it started, and the sessions
those started in turn. Each main session has its own file. Never write another main session's file.

With `--all`, skip to "Save every main session" at the end.

## 0. Find or create this main session's file

Work from the repository root, which is the superproject when this checkout is a submodule
(`git rev-parse --show-superproject-working-tree`).

1. Read this session's details with `mcp__ccd_session_mgmt__get_session` (`"self"`): the identifier, exact title,
   sidebar group, pinned, model, effort, permission mode and working folder.
2. Look in every `docs/progress/*.md` for one whose session registry lists this session's identifier, in any column.
   If one does, it's this main session's file, even if the session has since been renamed.
3. Otherwise, name the file from the sidebar title. Lower-case it, turn every run of characters other than letters and
   digits into a single hyphen, and trim hyphens from both ends. "Core: Scrape" becomes `core-scrape`, so the file is
   `docs/progress/core-scrape.md`.
   - If that file exists but its registry names a different main session, don't touch it. Ask the user for a name.
4. Create any missing files from the bundled templates:
   - `docs/progress/README.md` from [the bundled README](../../references/progress-readme.md);
   - the main session's file from [the bundled workstream template](../../references/progress-workstream.md).

Read both files in full, along with the repository's `CLAUDE.md` and `AGENTS.md`.

## 1. Bring each sub-session to a clean point

List the sub-sessions with `mcp__ccd_session_mgmt__list_sessions` (`{"linked": true}`): every session whose
`startedBy` chain leads back to this session. Include archived ones (`include_archived`) and mark them closed.

Message each open sub-session by its `local_…` identifier with `SendMessage`. Ask it to:
- write or update its **hand-over note** at `docs/progress/notes/<main-session>/<session-name>.md`. The
  note covers what it knows that isn't in its plan or in git: the decisions it made and why, the gotchas it found,
  what it tried that failed, what it's waiting on, and its exact next step. Keep it current rather than
  appending a diary, and never write secrets in it;
- commit any finished chunk, with the project's checks green;
- leave unfinished work uncommitted and say what that work is;
- start no new chunk;
- reply with one line: its branch tip, and its next step.

Wait for each reply. Never commit on a session's behalf. Check that every note exists and was updated in this save.
If one is missing, say so in the report.

Then write this main session's own **hand-over note**, at `docs/progress/notes/<main-session>/<session-name>.md`
using its short name. It records the coordination knowledge: which session owns what, the merge order, what's
waiting on the user, and anything agreed between sessions that isn't written elsewhere.

If the session tools aren't available (the command line, for example), read the state from git only, and say so in
the report.

## 2. Verify from git, never from memory

For every repository involved, including submodules (`git submodule status`), run:
- `git worktree list`;
- for each branch and worktree in the file:
  - `git -C <worktree> log -1 --oneline`;
  - `git -C <worktree> status --short`;
  - the commit count against its base;
  - whether it's pushed (`git ls-remote --heads origin <branch>`).

Also check whether the main branches match their remotes.

## 3. Rewrite the file

**The session registry** has one row per session, the main session first. For each session, read
`mcp__ccd_session_mgmt__get_session` and record:
- its **exact title**, copied character for character from the sidebar;
- its short name;
- its sidebar group, and whether it's pinned;
- its model, effort and permission mode;
- its working folder, worktree and branch;
- its identifier, in this host and account's column. The column is labelled, for example, "Claude seb@example.com",
  using the account's email from the session context. Add the column if it's missing.

Keep the other accounts' columns as they are. Mark closed or archived sessions as closed.

**The other sections:**
- Rewrite the snapshot sections: "Where things stand", each sub-session's state, next step and resume brief, open
  questions, not yet assigned, and decisions.
- Record any uncommitted work as **uncommitted**, with what it is.
- Copy any shared notes a session depends on into `docs/progress/notes/<main-session>/`.
- List every session's hand-over note in the "Notes" section, and link it from that session's row or section.
- Update the snapshot date, and append one dated line to the log.

## 4. Commit and push

Stage only `docs/progress/`. Commit with a subject and body, adding no attribution trailer the project's
instructions forbid. Then push.

## 5. Report in two lines

- The file and the commit that holds the save.
- Anything that won't travel: uncommitted work in a worktree, a session that didn't reply, or unpushed branches. The
  branches matter only when moving to another machine.

## Save every main session (`--all`)

1. List every `docs/progress/*.md` except `README.md`. Read the main session row of each.
2. Save this session's own file first, if it has one, by following the steps above.
3. For every other file, look up the main session's identifier for this host and account.
   - **If it exists,** message it with `SendMessage`: "Run session:progress-save now and reply with the commit."
   - **If it's missing,** or the session no longer exists, leave that file untouched. Record that it wasn't saved, and
     why.
4. Report one line per file: saved at a given commit, or not saved and why.

Never write secrets. Name keys by their environment variable only.
