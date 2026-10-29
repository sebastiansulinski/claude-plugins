# Progress: <workstream title>

**Snapshot:** <YYYY-MM-DD>, written by the orchestrator. Check every hash and branch below against git before relying
on it. The pattern is described in `docs/progress/README.md`.

## Resuming

- **Save before switching:** run `session:progress-save <workstream>` in the orchestrator session.
- **Continue:** run `session:progress-resume <workstream>` in a session opened at the repository root.

### Orchestrator prompt (fallback when the skills aren't installed)

```text
You are the orchestrator for <workstream title>. Read docs/progress/README.md and docs/progress/<workstream>.md in
full, verify every branch, commit and worktree they name against git, then recreate or reopen the sessions in the
session registry from their resume briefs and continue. Update docs/progress/<workstream>.md at every milestone and
commit and push it (docs/progress/ only).
```

## Session registry

| Role | Name | Worktree | Branch | <Host account> |
|---|---|---|---|---|
| Orchestrator | `<name>` | none (repository root) | `<branch>` | `<identifier>` |
| <Sub-session role> | `<name>` | `<absolute worktree path>` | `<branch>` | `<identifier>` |

## Where things stand

- <What is merged, deployed and pending, with commit hashes.>

## Sub-sessions

### <Sub-session role> (`<name>`)

- **Branch and worktree:** <branch> in <absolute worktree path>, based on <commit>. Pushed: <yes or no>.
- **Plan:** <plan path>.
- **State:** <commits ahead, what's built, what's uncommitted>.
- **Then:** <next step, and where it stops for the owner>.
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

- <Files in docs/progress/notes/<workstream>/ and what each holds.>

## Log

- <YYYY-MM-DD>: <What happened.>
