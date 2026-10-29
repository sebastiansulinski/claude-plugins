# Progress files: resuming orchestrated work across accounts and hosts

Each **main session** gets a progress file: the session you work in directly, together with every sub-session it
started. The file records the main session and its sub-sessions as they appear in the sidebar, with their branches,
worktrees and plans and what each one does next.

With it, the work can be continued under a different account, or a different host (Claude Code or Codex), on the same
machine. It can then be resumed later on the original account, with that account's own sessions caught up.

## Files

- `docs/progress/<main-session>.md`: one file per main session. The name is the main session's sidebar title in lower
  case, with every run of other characters turned into a hyphen. For example, "Core: Scrape" becomes
  `core-scrape.md`.
- `docs/progress/notes/<main-session>/`: hand-over notes and reviews the sessions share. A host's private notes and
  memory aren't visible to another account, so anything a session needs lives here.

Each file has a **session registry**: one row per session, the main session first. A row records:
- the session's exact title as the sidebar shows it;
- its sidebar group, and whether it's pinned;
- its model, effort and permission mode;
- its working folder, worktree and branch;
- one identifier column per host and account, for example "Claude seb@example.com" or "Codex seb@example.com".

Identifiers belong to one host and account, so each column holds only the identifiers that host and account can
reopen.

## Commands

- `session:progress-save`, run in the main session before logging out or switching. It:
  - finds this main session's file, or creates it;
  - brings each sub-session to a clean point where the host allows it;
  - checks git;
  - rewrites the file;
  - commits and pushes it.

  With `--all`, it saves every main session that has a file, by asking each one to save itself.
- `session:progress-resume <main-session>`, after logging in.
  - On a host and account whose identifiers are in the registry, it reopens those sessions and catches each one up.
  - Otherwise it recreates the main session's role in the current session, then recreates every sub-session with its
    exact title, group, pin, model, effort and permission mode. It records the new identifiers in a new column.

## Rules

- **One account drives a main session's work at a time.** Save before switching. Two accounts' sessions writing the
  same worktree would overwrite each other's work.
- **Branches and worktrees are local to the machine.** On the same machine, every account and host shares them. A
  different machine needs every branch in the registry pushed first.
- **Uncommitted work in a worktree stays where it is.** The file records it as uncommitted, and the session resuming
  that worktree decides what to do with it.
- **Update the file at every milestone:**
  - a session started, renamed or closed;
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
