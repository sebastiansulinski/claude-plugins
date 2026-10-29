---
name: progress-resume
description: >-
  Resume an orchestrated workstream from its progress file (docs/progress/<workstream>.md). On an account whose session
  identifiers are in the file's registry it reopens those sessions and catches them up; on any other account it
  recreates the orchestrator and every sub-session from their resume briefs. Use when the user says progress-resume,
  "resume the workstream", "continue where we left off" or names a workstream to pick up.
---

# Resume an orchestrated workstream

**Workstream:** $ARGUMENTS

If no workstream is given and `docs/progress/` holds a single workstream file, use that one. Otherwise ask which.

This session becomes the orchestrator. Work from the repository root, which is the superproject when this checkout is
a submodule. Read these in full:
- `docs/progress/README.md`;
- `docs/progress/<workstream>.md`;
- the repository's `CLAUDE.md` and `AGENTS.md`;
- the notes in `docs/progress/notes/<workstream>/` that the file names.

## 1. Check the repositories against the file

- Run `git pull`, and `git fetch` in each submodule.
- Run `git worktree list` in each repository.
- For every worktree and branch in the session registry, run `log -1`, `status --short` and a commit count against
  its base.

Give the user one short list of every difference from the file. Git wins: correct the file before going on.

If the log's last line shows another account active, with no save after it, warn the user before restarting anything.
Two accounts' sessions writing the same worktree overwrite each other's work.

## 2. Reopen or recreate the sessions

For each `local_…` identifier in this host's columns, call `mcp__ccd_session_mgmt__get_session`.

- **The identifiers exist (the owning account):**
  - If the registry's orchestrator still exists and isn't this session, tell the user to open it and run
    progress-resume there instead, so it keeps its history. Stop, unless the user says to carry on here.
  - Unarchive any archived session with `mcp__ccd_session_mgmt__unarchive_session`.
  - Send each sub-session a catch-up with `SendMessage` (`to` is its identifier). The catch-up must:
    - say its memory is stale;
    - tell it to re-read the workstream file and its plan;
    - tell it to check `git log` and `git status` in its worktree before acting;
    - list what changed since its last activity, taken from the log and git: commits it didn't make, merges, and the
      owner's decisions;
    - tell it to carry on with the next step in its row.
- **The identifiers don't exist (another account):** start one session per open row with
  `mcp__ccd_session__start_session`:
  - `initiation`: "user_asked";
  - `context`: "fresh";
  - `use_worktree`: false (the row's worktree is used by its absolute path);
  - `name`: the row's name;
  - `prompt`: the row's resume brief, plus "Read docs/progress/<workstream>.md and README.md first; you have no memory
    of the earlier work";
  - `background`: the workstream's goal, decisions and standing rules.

  Record each new identifier, and this session as orchestrator, in this account's column. Add the column if it's
  missing, labelled with the host and the account's email.

  If starting a session is refused (Remote Control, for example), tell the user to run this from the desktop app.
- **No session tools at all (the command line):** print each open row's resume brief as a ready-to-paste prompt.
  Record identifiers only once the user confirms the sessions exist.

Skip rows marked done or closed.

## 3. Save and continue

- Commit and push the registry change (only `docs/progress/`, with a subject and body).
- Ask the user the file's first open question, and only that one.
- From then on, update the file at every milestone, as `docs/progress/README.md` describes.
