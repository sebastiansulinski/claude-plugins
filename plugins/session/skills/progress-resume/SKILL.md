---
name: progress-resume
description: Resume an orchestrated workstream from its progress file (docs/progress/<workstream>.md) — verify it against git, become the orchestrator, and recreate or brief every sub-task from the session registry. Use when the user asks to resume a workstream, continue where they left off, or pick work up under another account or host.
---

# Resume an orchestrated workstream

Identify the workstream from the user's request. If none is named and `docs/progress/` holds a single workstream
file, use it. Otherwise ask which.

This task becomes the orchestrator. Work from the repository root, which is the superproject when this checkout is a
submodule. Read these in full:
- `docs/progress/README.md`;
- `docs/progress/<workstream>.md`;
- the applicable `AGENTS.md` instructions;
- the notes in `docs/progress/notes/<workstream>/` that the file names.

Don't assume a private memory was injected.

## Verify against git

- Run `git pull`, and `git fetch` in each submodule.
- Run `git worktree list` in each repository.
- For every worktree and branch in the session registry, check the tip commit, `git status --short` and the commit
  count against its base.

Give the user one short list of every difference from the file. Git wins: correct the file before going on.

If the log's last line shows another account or host active, with no save after it, warn the user before starting any
work. Two agents writing the same worktree overwrite each other's work.

## Recreate the sub-tasks

This host can't reopen sessions from another account or host, so treat every open row as needing a new task. For each
row not marked done or closed:
- **When this host can delegate to a sub-agent or background task,** start one with the row's resume brief, working in
  the row's worktree by its absolute path. Add: "Read docs/progress/<workstream>.md and README.md first; you have no
  memory of the earlier work."
- **Otherwise,** print the brief as a ready-to-paste task, naming the worktree path.

Record task identifiers in this host's column of the **session registry** (for example "Codex seb@example.com") only
when the host reports them, and record this task as orchestrator. Add the column if it's missing.

When the user returns to an account whose sessions are still in the registry, those sessions can be reopened there.
Note in the log that this host took over, so the other account's resume can catch its sessions up.

## Save and continue

- Commit and push the registry change (only `docs/progress/`, with a subject and body).
- Ask the user the file's first open question, and only that one.
- From then on, update the file at every milestone, as `docs/progress/README.md` describes.
