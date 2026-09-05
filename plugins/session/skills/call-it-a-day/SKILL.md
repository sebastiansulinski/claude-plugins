---
name: call-it-a-day
description: Capture an end-of-session project handoff in existing resume, task, plan, and lesson documents so work can resume accurately. Use when the user asks to wrap up or record the session state.
---

# Capture the session handoff

Discover actual project conventions through applicable AGENTS.md instructions and existing documents.
Do not invent private memory locations or assume a host memory service exists.

The next session should be able to read at most three existing entry-point documents and know what shipped,
where unfinished work stopped, the first action to take, and decisions affecting that work. Multi-plan
entry points can link to each plan's detailed status record.

## 1. Classify and reconcile

State whether this was an active-plan, multi-plan, ad-hoc, or empty day.

Check Git status/history, the in-session record, and verification results. Separate committed work,
uncommitted changes, decisions, proposals, and pending checks. Flag unexpected changes without claiming
them as this session's work.

Reuse relevant test/lint/typecheck results obtained against the final state. Run missing or stale checks
appropriate to the changes. Record actual commands/results; label unavailable checks instead of inventing
counts. Use absolute dates in durable records.

## 2. Rewrite the existing resume prompt

Locate the existing resume file, for example docs/prompt.md, RESUME.md, or NEXT.md. If no convention exists,
ask where the handoff belongs before creating one; prepare its content while waiting.

Rewrite it with:

- State summary: active plan/chunk, completed outcome, and next work.
- Ordered documents to read first, including precise plan sections where useful.
- Shipped work with verified paths/counts; identify uncommitted work separately.
- Mid-stream task, completed part, remaining part, and next concrete action.
- Decisions made in this session that constrain upcoming work.
- The first two or three commands or actions to resume.

For ad-hoc work, omit inapplicable plan-status tasks. For an empty day, record an absolute-date no-progress
note pointing to the prior handoff rather than inventing progress.

## 3. Update existing status and memory records

For each active plan touched, update its existing status document. Move completed chunks out of pending
work, cite paths, record load-bearing decisions, and leave the next step explicit. Preserve its schema
and metadata. Do not backfill phases from recollection.

Use memory tools/files only when the host or project actually provides them and their scope is suitable.
Project-local status documents are valid alternatives. Create a status record for a new plan only when an
established convention authorizes it; otherwise ask where it belongs.

Update an existing index only when status meaningfully changes, a useful memory is added, or a pointer is
stale. Keep index entries short and put detail in referenced records. Preserve link/frontmatter conventions.
Check a neighboring record before creating one. Do not create a private memory tree.

## 4. Capture useful lessons

Record user corrections and non-obvious successful approaches when they affect future decisions.
Use the project's existing lessons file; broader patterns may go in an available, appropriate memory store.
Include why the pattern matters and its limits. Avoid duplicating facts recoverable from code/history, and
do not put credentials or unrelated personal information in repository documents.

## 5. Update tasks and plan markers

Tick off verified complete tasks and keep remaining checks/reviews visible. Update each relevant multi-plan
tracker without overwriting another plan's history. If a separate tracker is needed, follow an existing
archive convention or ask before restructuring records.

Change phase-complete markers only when criteria are met. Update status without restructuring the plan.
Skip inapplicable steps with a brief reason.

## 6. Verify the handoff

Check cited current paths and topic links; explicitly label future paths as planned. Verify counts against
actual output, distinguish unrun checks, and use absolute ISO dates. Ensure the next action is concrete and
each status record makes sense without this conversation. Fix broken links or contradictions.

Return updated files, the stopping point, and next action. Do not commit or push unless explicitly authorized
as part of this task.
