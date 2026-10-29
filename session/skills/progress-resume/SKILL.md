---
name: progress-resume
description: >-
  Resume a main session and its sub-sessions from the main session's progress file (docs/progress/<main-session>.md).
  On an account whose identifiers are in the file it reopens those sessions and catches them up; on any other account
  it recreates every sub-session with its exact sidebar title, group, pin and settings from its resume brief. Use when
  the user says progress-resume, "resume", "continue where we left off" or names a session to pick up.
---

# Resume a main session and its sub-sessions

**Main session:** $ARGUMENTS

Accept the file's name, for example `core-scrape`, or the main session's exact title. If neither is given, list the
files in `docs/progress/`, with each one's main session title, and ask which one.

This session takes over as the main session. Work from the repository root, which is the superproject when this
checkout is a submodule. Read these in full, including the main session's own **hand-over note** at
`docs/progress/notes/<main-session>/<session-name>.md`:
- `docs/progress/README.md`;
- the main session's file;
- the repository's `CLAUDE.md` and `AGENTS.md`;
- the notes in `docs/progress/notes/<main-session>/` that the file names.

## 1. Check the repositories against the file

- Run `git pull`, and `git fetch` in each submodule.
- Run `git worktree list` in each repository.
- For every worktree and branch in the session registry, check `log -1`, `status --short`, and a commit count against
  its base.

Give the user one short list of every difference from the file. Git wins: correct the file before going on.

If the log's last line shows another account active, with no save after it, warn the user before restarting
anything. Two accounts' sessions writing the same worktree would overwrite each other's work.

## 2. Reopen or recreate the sessions

Check the identifiers in this host and account's column with `mcp__ccd_session_mgmt__get_session`.

### The identifiers exist (the owning account)

- **The recorded main session still exists and isn't this session:** tell the user to open it and run
  progress-resume there, so it keeps its own history. Stop, unless the user says to carry on here.
- **An archived session:** unarchive it with `mcp__ccd_session_mgmt__unarchive_session`.
- **Sidebar placement:** if a session's title, group or pin no longer matches the file, restore them with the
  sidebar tools (`mcp__ccd_session_mgmt__set_session_title`, `mcp__ccd_sidebar__move_sessions`,
  `mcp__ccd_sidebar__set_pinned`).
- **Catch-up:** send each open sub-session a catch-up with `SendMessage` (`to` is its identifier). It says:
  - its memory is stale;
  - re-read the main session's file, its own plan, and its own hand-over note at
    `docs/progress/notes/<main-session>/<session-name>.md`;
  - check `git log` and `git status` in its worktree before acting;
  - what changed since its last activity, taken from the log and git: commits it didn't make, merges, and the owner's
    decisions;
  - carry on with the next step in its row.

### The identifiers don't exist (another account)

1. **This session becomes the main session.** Rename it to the main session's **exact title** with
   `mcp__ccd_session_mgmt__set_session_title`. Move it to the recorded sidebar group and pin with the sidebar tools,
   creating the group with `mcp__ccd_sidebar__create_group` if it's missing.
2. **Recreate each open sub-session**, in registry order, with `mcp__ccd_session__start_session`:
   - `initiation`: "user_asked";
   - `context`: "fresh";
   - `title`: the row's **exact title**;
   - `name`: the row's short name;
   - `model`, `effort` and `permission_mode`: the row's values (the app may refuse a value above this session's own;
     note any it lowers);
   - `use_worktree`: false (the row's worktree is used by its absolute path);
   - `prompt`: the row's resume brief, plus "Read docs/progress/<main-session>.md, README.md and your hand-over note
     at docs/progress/notes/<main-session>/<session-name>.md first; you have no memory of the earlier work. Keep that
     hand-over note current from now on";
   - `background`: the main session's goal, decisions and standing rules.
3. **Restore each new session's sidebar group and pin** with the sidebar tools.
4. **Record the identifiers.** Write each new identifier, this session's included, in this account's column. Add the
   column if it's missing, labelled with the host and the account's email.

If starting a session is refused (over Remote Control, for example), tell the user to run this from the desktop app.

### No session tools at all (the command line)

Print each open row's exact title and resume brief as a ready-to-paste prompt. Record identifiers only once the user
confirms the sessions exist.

Skip rows marked done or closed.

## 3. Save and continue

- Commit and push the registry change: only `docs/progress/`, with a subject and body.
- Ask the user the file's first open question, and only that one.
- From then on, update the file at every milestone, as `docs/progress/README.md` describes.
