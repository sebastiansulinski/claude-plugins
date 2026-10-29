# Progress: <main session's exact title>

**Snapshot:** <YYYY-MM-DD>, written by the main session. Check every hash and branch below against git before relying
on it. The pattern is described in `docs/progress/README.md`.

## Resuming

- **Save before switching:** run `session:progress-save` in the main session.
- **Continue:** run `session:progress-resume <main-session>` in a session opened at the repository root.

### Main session prompt (fallback when the skills aren't installed)

```text
You are the main session "<main session's exact title>". Read docs/progress/README.md,
docs/progress/<main-session>.md and your hand-over note in docs/progress/notes/<main-session>/ in full, and verify every branch, commit and worktree they name against git. Then
reopen or recreate the sub-sessions in the session registry, with their exact titles, from their resume briefs, and
continue. Update docs/progress/<main-session>.md at every milestone and commit and push it (docs/progress/ only).
```

## Session registry

The main session comes first. Titles are copied exactly as the sidebar shows them.

| Role | Exact title | Short name | Sidebar group | Pinned | Model, effort, mode | Working folder | Worktree | Branch | <Host account> |
|---|---|---|---|---|---|---|---|---|---|
| Main session | <title> | `<name>` | <group or none> | <yes or no> | <model>, <effort>, <mode> | `<absolute path>` | none | `<branch>` | `<identifier>` |
| <Sub-session role> | <title> | `<name>` | <group or none> | <yes or no> | <model>, <effort>, <mode> | `<absolute path>` | `<absolute worktree path>` | `<branch>` | `<identifier>` |

## Where things stand

- <What is merged, deployed and pending, with commit hashes.>

## Sub-sessions

### <Sub-session's exact title> (`<name>`)

- **Branch and worktree:** <branch> in <absolute worktree path>, based on <commit>. Pushed: <yes or no>.
- **Plan:** <plan path>.
- **State:** <commits ahead, what's built, what's uncommitted>.
- **Then:** <next step, and where it stops for the owner>.
- **Hand-over note:** `docs/progress/notes/<main-session>/<session-name>.md`.
- **Resume brief:** "<A self-contained brief a new session can start from: the worktree, the plan, what to read
  first, what to build next, the checks to run, and what never to do.>"

## Open questions for the owner (ask one at a time)

1. <Question.>

## Not yet assigned

- <Known issues no session owns yet.>

## Decisions

- <Decision, with the date and the owner's words where they matter.>

## Standing rules

- <Rules every session follows: approvals, commits, environments, credentials.>

## Notes

- One hand-over note per session: <list each `docs/progress/notes/<main-session>/<session-name>.md`>.
- <Other files in docs/progress/notes/<main-session>/ and what each holds.>

## Log

- <YYYY-MM-DD>: <What happened.>
