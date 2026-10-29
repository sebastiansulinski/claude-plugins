# Progress files: resuming orchestrated work across accounts and hosts

A progress file records where a piece of multi-session work stands: the orchestrating session, every sub-session it
started, their branches, worktrees and plans, and what each one does next. With it, work can be continued under a
different account, or a different host (Claude Code or Codex) on the same machine, and later resumed on the original
account with its own sessions caught up.

## Files

- `docs/progress/<workstream>.md`: one per workstream, in the layout of the bundled workstream template.
- `docs/progress/notes/<workstream>/`: hand-over notes and reviews the sessions share. A host's private notes or memory
  aren't visible to another account, so anything a session needs lives here.

Every workstream file has a **session registry**: one row per session, one column per host and account (for example
"Claude seb@example.com" or "Codex seb@example.com"). Session and task identifiers belong to one host and account, so
each column holds only the identifiers that host and account can reopen.

## Commands

- `session:progress-save <workstream>` before logging out or switching:
  - brings each sub-session to a clean point where the host allows it;
  - checks git;
  - rewrites the file;
  - commits and pushes it.
- `session:progress-resume <workstream>` after logging in:
  - On a host and account whose identifiers are in the registry, it reopens those sessions and catches them up on
    what changed.
  - Otherwise it recreates the orchestrator and every sub-session from their resume briefs, then records the new
    identifiers in a new column.

## Rules

- **One account drives a workstream at a time.** Save before switching. Two accounts' sessions writing the same
  worktree overwrite each other's work.
- **Branches and worktrees are local to the machine.** On the same machine every account and host shares them. A
  different machine needs every branch in the registry pushed first.
- **Uncommitted work in a worktree stays where it is.** The file records it as uncommitted, and the session resuming
  that worktree decides what to do with it.
- **Update the file at every milestone:**
  - a session started or closed;
  - a plan approved or changed;
  - a chunk committed;
  - a merge or push;
  - a deploy or check;
  - a decision by the owner.

  Each update rewrites the snapshot sections and appends one dated line to the log. Commit only `docs/progress/`, then
  push.
- **Check every claim against git.** Facts are hashes, branch names and paths, with the snapshot date. Anything
  unverified is marked as unverified.
- **Never write secrets.** Keys are named by their environment variable only.
