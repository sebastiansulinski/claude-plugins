# Session forward tests

Write these cases before the native session skills.

## Resume with a stale handoff

Fixture: a repository on codex/sample with one committed README, tasks/todo.md naming
docs/plans/sample.md as pending, and docs/prompt.md claiming the nonexistent src/finished.php shipped.
There is no memory directory. Ask: "Use good-morning to resume this project."

Accept: check actual branch/status/history and named files; flag stale shipped claim; identify the pending
plan; suggest next actions without editing or inventing memory. Missing optional documents are not errors.

## Wrap up a multi-plan day

Fixture: existing docs/prompt.md, two plans, tasks/todo.md containing the other plan, existing lessons and
status documents. One plan's work is committed, another has unfinished changes, and test output is supplied.
Ask: "Use call-it-a-day to capture today's work. No commit."

Accept: preserve the other plan's tracker/history, record shipped versus unfinished work accurately,
use absolute dates and a concrete next action, cite only verified paths/counts, do not create private memory
stores or commit. New handoff convention requires user direction.

## Empty day

Fixture: existing resume prompt, no changes or decisions.
Accept: record the absolute date and where to resume without inventing progress or rewriting unrelated files.
