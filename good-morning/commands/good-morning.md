---
description: Resume work from the previous session — load memory, lessons, config, and the project's prompt, then propose next steps.
---

It is a new day and we are picking up where we left off. Before doing anything else, rebuild context from the durable sources so your suggestions are grounded in what was actually decided and shipped, not guesses.

## 1. Load context (in this order)

Read whichever of these exist. Skip silently if absent — do not announce missing files.

1. **Auto memory** — `MEMORY.md` is already in your context. Scan it now for active plans, the user's profile, recent feedback, and any pointers to topic files (`project_*.md`, `feedback_*.md`, etc.). Open the topic files that look relevant to the current project state.
2. **Global instructions** — `~/.claude/CLAUDE.md`.
3. **Project instructions** — `./CLAUDE.md` at the repository root, plus any nested `CLAUDE.md` files inside directories you're likely to touch.
4. **Context docs** — `./docs/context/*.md` if the directory exists (architectural-decisions logs).
5. **Lessons** — `./tasks/lessons.md` if it exists.
6. **Task list** — `./tasks/todo.md` if it exists — this is the most direct signal of what was in progress.
7. **Today's prompt** — `./docs/prompt.md` if it exists. Treat this as the user's standing brief for the session.
8. **Active plans** — any plan referenced as in-progress by memory or `todo.md`, typically under `./docs/plans/`.

## 2. Check the ground truth

Memory and plans go stale. Confirm what's actually on disk:

- `git status` — uncommitted work, untracked files.
- `git log --oneline -10` — what shipped recently.
- `git branch --show-current` — are we on `main` or a feature branch?

If a memory entry names a file, function, or flag that no longer exists, flag it and treat the memory as stale rather than acting on it.

## 3. Report back

Give a tight summary, no more than ~10 lines:

- **Where we are**: branch, last commit, anything uncommitted.
- **What's in flight**: the active plan or task and its current phase/step.
- **Open threads**: anything flagged as partial, pending review, or blocked.

## 4. Propose next steps

Suggest 2–4 concrete next steps ranked by what fits the current state best. For each, name the file or task it touches and the rough size (small fix, medium task, multi-step). End with a single recommendation and the main tradeoff so the user can redirect.

Do not start implementing until the user picks a direction.
