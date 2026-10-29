---
name: progress-resume
description: Resume a main session and its sub-sessions from the main session's progress file (docs/progress/<main-session>.md) — verify it against git, take over as the main task, and recreate or brief every sub-task with its exact title from the session registry. Use when the user asks to resume, continue where they left off, or pick work up under another account or host.
---

# Resume a main session and its sub-sessions

Accept either the file's name (for example `core-scrape`) or the main session's exact title. If neither is given, list
the files in `docs/progress/`, each with its main session's title, and ask which one.

This task takes over as the main task. Work from the repository root, which is the superproject when this checkout is
a submodule. Read these in full:
- `docs/progress/README.md`;
- the main session's file;
- the applicable `AGENTS.md` instructions;
- the notes in `docs/progress/notes/<main-session>/` that the file names.

Don't assume a private memory was injected.

## Verify against git

- Run `git pull`, and `git fetch` in each submodule.
- Run `git worktree list` in each repository.
- For every worktree and branch in the session registry, check the tip commit, `git status --short` and the commit
  count against its base.

Give the user one short list of every difference from the file. Git wins: correct the file before going on.

If the log's last line shows another account or host active, with no save after it, warn the user before starting any
work. Two agents writing the same worktree would overwrite each other's work.

## Recreate the sub-tasks

This host can't reopen sessions from another account or host, so every open row needs a new task. Where the host
lets you set a title, give this task the main session's **exact title**.

For each row not marked done or closed:
- **When this host can delegate to a sub-agent or background task,** start one with the row's resume brief and its
  exact title, working in the row's worktree by its absolute path. Add: "Read docs/progress/<main-session>.md and
  README.md first; you have no memory of the earlier work." Use the row's model and reasoning settings where the host
  allows.
- **Otherwise,** print the exact title and the brief as a ready-to-paste task, naming the worktree path.

Record identifiers in this host's column of the **session registry**, for example "Codex seb@example.com", only when
the host reports them. Record this task as the main task. Add the column if it's missing.

The Claude sidebar groups and pins in the file stay as they are, for when the work returns to a Claude account. Note
in the log that this host took over, so the other account's resume can catch its sessions up.

## Save and continue

- Commit and push the registry change: only `docs/progress/`, with a subject and body.
- Ask the user the file's first open question, and only that one.
- From then on, update the file at every milestone, as `docs/progress/README.md` describes.
