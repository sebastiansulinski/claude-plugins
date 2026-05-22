---
description: End-of-session capture — record state so the next session resumes with no context loss.
---

It's the end of today's session. Capture the state so tomorrow-you can resume cleanly with no context loss.

This command is project-agnostic. **Discover the project's actual conventions before writing anything** — what counts as a "plan file", "resume prompt", "todo", or "lessons file" is defined by the current project's `CLAUDE.md` and the files already on disk. Do not assume any specific filename or directory layout. Honour what's there; don't invent.

## What "done" looks like

Tomorrow's session must be able to read **at most three artefacts** the project already uses — typically the resume prompt, the relevant project-status memory, and the todo / execution log — and know exactly:

1. What shipped today (with concrete file paths + verifiable counts where applicable: test counts, perf numbers, etc.).
2. Where work stopped mid-stream (which task, which step within it, what's left).
3. The first command or action to run on resume.
4. Any decision that was made today that's load-bearing for upcoming work.

## Steps

Work through these in order. **If a step has nothing worth recording, write one sentence stating that and skip it.** Do not pad. Do not invent.

### 0. Detect the situation

Before anything else, classify today:

- **Active-plan day** — work was scoped to one named plan / phase / chunk (the common case for chunked TDD).
- **Multi-plan day** — work spanned two or more active plans. Update each one's status memory; name them all in the resume prompt.
- **Ad-hoc day** — bug fixes, research, ops, exploration with no plan attached. Skip the plan-status / plan-header / todo steps; the resume prompt still gets rewritten.
- **Empty day** — genuinely nothing shipped, nothing decided. Update the resume prompt anyway with a one-line "no progress YYYY-MM-DD — resume from prior date's notes"; skip everything else.

State the classification out loud at the start of the wrap-up so it's auditable.

### 1. Reconcile what actually happened

Ground yourself in disk truth before writing anything:

- `git status` and a short `git log` to see what was committed today and what's still uncommitted. If `git status` shows unexpected files (things you didn't intend to touch), flag them to the user before continuing — do not roll them into the handoff.
- Run whatever test / lint / typecheck the project actually uses (check `CLAUDE.md` or `package.json` / `composer.json` / `Makefile` etc.). Capture the real counts you'll cite later.
- Inspect the in-session task list (if the harness has one loaded) to see what was completed today, what's in-progress, what's pending next.

### 2. Update the resume prompt

Find the project's resume-prompt file. Conventional names: `docs/prompt.md`, `RESUME.md`, `NEXT.md`, or whatever `CLAUDE.md` names. If it exists, rewrite it (don't append — start fresh). If the project has no resume-prompt convention, ask before creating one.

The rewrite must cover:

- **TL;DR** — one paragraph: active plan + chunk (if any), today's headline outcome, what's next.
- **Where to read first** — ordered list of files (relative paths), including the relevant status memory and active plan section.
- **Today's shipped work** — bullets with concrete relative paths (`<module>/<file>:<line-range>` where a specific spot matters tomorrow) and verifiable counts.
- **Mid-stream state, if any** — task name, what's done, what's left, the next concrete step (a test to write, a file to edit, a command to run).
- **Locked decisions worth carrying forward** — only architectural decisions made today that affect upcoming work. Not a project recap.
- **How to start the morning** — the literal first 2–3 commands or actions.

### 3. Update the relevant project-status memory

In the auto-memory directory for this project (the `MEMORY.md` index + topic files). Edit the existing `project_*_status.md` for each plan you touched today — don't create a new one unless the plan is genuinely new.

- Move today's completed chunks from "Next" to a "What [phase] shipped" section with concrete file paths.
- Update the frontmatter `description:` to reflect the new "last shipped" state (keep it under ~250 chars — it's surfaced in memory-chooser UIs).
- Record any architectural decision confirmed today in a "Decisions confirmed during [phase]" section.
- Add `[[link]]` pointers to any new lesson / feedback memories you create in step 5.

If no status memory exists yet for a brand-new plan, create one mirroring the structure of an existing well-formed `project_*_status.md` in the same directory. Initial entry only — do not backfill prior phases.

### 4. Update the auto-memory index — `MEMORY.md`

Only touch it if:

- A plan's status header moved meaningfully (phase complete, plan archived, new active plan).
- You wrote a new lesson / feedback memory in step 5 — add the one-line pointer.
- An existing pointer became stale.

Keep entries to one line, under ~200 chars. Move detail into topic files.

### 5. Capture corrections + non-obvious successes

If the user corrected your approach today — or confirmed a non-obvious approach worked without pushback — capture the pattern.

- **Project-specific learnings** go to the project's lessons file (`tasks/lessons.md` is common; check `CLAUDE.md`).
- **Broadly-applicable patterns** also go to a `feedback_*.md` topic memory in the auto-memory directory, with a one-line pointer in `MEMORY.md`.

A memory is only worth writing if it is **non-obvious, surprising, and applicable to future conversations**. Include the *why* so future-you can judge edge cases instead of mechanically following the rule. Frontmatter must match the project's convention — check an existing well-formed file in the same directory before writing a new one, and copy its shape exactly (field names, nesting, type tag).

Do NOT save: code patterns, conventions, file paths, project structure, or git history. Those are derivable.

### 6. Update the execution log / todo

Find the project's chunked task log (often `tasks/todo.md` or similar). Tick off today's completed chunks. Leave the next pending chunk visible at the top of the unchecked list. If you opened new sub-chunks today that weren't in the original plan, list them.

If the file is currently scoped to a *different* plan than today's active one, do not overwrite it. Archive it (`tasks/todo-archive/<old-plan>.md` or whatever the project's archive convention is — ask if there isn't one) and start a fresh log for the active plan. Destroying historical context is worse than asking.

### 7. Flip the plan header if a phase closed

If today's work closed a phase in the active plan, update its status header (e.g. "Phase N status: ✅ DONE YYYY-MM-DD"). Don't restructure or expand — just flip the marker.

### 8. Verify the handoff is real

This is a falsifiable checklist, not a vibe check:

- **Resume prompt**: contains all six fields named in step 2 (TL;DR, where to read first, today's shipped work, mid-stream state, locked decisions, how to start). No empty headings.
- **Every cited file path exists** — run `ls` / equivalent on each relative path the resume prompt names.
- **Every cited count matches** the test / lint output captured in step 1. Re-run the smallest version of the check if you're unsure.
- **Status memory** is self-contained: a reader who's never seen this conversation can understand what the next chunk is from the memory alone.
- **`[[link]]` pointers** in the status memory resolve to topic files that actually exist (or are explicitly noted as planned).
- **No relative date words** anywhere ("today", "yesterday", "last week") — substitute the absolute ISO date (`YYYY-MM-DD`, e.g. `2026-05-19`).

If any check fails, fix it before declaring done.

## Rules

- **Never auto-commit.** The user will say "commit it" if they want the handoff artefacts in a commit.
- **Be specific over thorough.** "P2.3 done" is useless; "P2.3 — added <action> at <path>; N HTTP tests in <path>" is useful.
- **Discover, don't assume.** Read `CLAUDE.md` (project + global) and inspect the directory layout before writing — this command makes no claim about filenames, only about the shape of the workflow.
- **Skip with reason, never silently.** If you skip a step, say which one and why in one line.
