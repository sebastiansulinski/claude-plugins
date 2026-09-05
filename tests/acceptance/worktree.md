# Worktree acceptance

Run from the repository root. Git fixture mutations below are restricted to temporary directories and need
no network services. The shell harness substitutes recording Composer/npm commands.

## Executable checks

```bash
bash worktree/tests/run.sh
python3 -m unittest discover -s tests -p test_codex_worktree.py -v
python3 scripts/sync-codex-worktree.py --check
```

The package test copies the native package into a temporary installation path containing spaces, without
access to sibling package resources. Each skill's runtime link must resolve within that installed package.
Observable fixture assertions cover:

- Runtime byte equality and executable permissions, plus missing/stale synchronization detection and repair.
- Idempotent synchronization, including leaving an already synchronized runtime's modification time intact.
- Create/list/remove through the installed runtime in plain repositories and submodules.
- Untouched original status, HEAD, branch and file contents, and superproject preservation for submodules.
- Shared `wt/` defaults; explicit `plan/` and `codex/` settings; CLI base/destination precedence.
- Dirty, unmerged, and unmanaged removal refusals; retaining an unmerged branch when removing its directory.
- Safe submodule destination selection and refusal before creating a directory inside the superproject.

The original harness also covers Composer/npm precedence, copied environment files, committed rather than
dirty setup hooks, ambiguous removal names, mutable destination settings, and configuration validation.
To exercise its same 138 assertions against the packaged runtime, copy `worktree/tests/run.sh` and
`plugins/worktree/scripts/worktree.sh` into a disposable `tests/` and `scripts/` pair and run that harness.
Do not redirect the checked-in original harness or change the canonical runtime for this verification.

## Prompt behaviour scenarios

Use a fresh task with only the installed worktree package and an isolated fixture repository. These are
behavioural expectations to verify independently; passing executable tests does not prove model adherence.

| Request / fixture | Expected behaviour |
| --- | --- |
| Create without a name | Ask for the missing name; no creation or invented name. |
| Create `topic develop --no-env` in a submodule | Run from the submodule using packaged script's absolute path; base maps to `--from develop`; preserve `--no-env`. |
| Create with `branchPrefix: plan/` | Use `plan/topic`; leave existing config unchanged. |
| Create without configuration or prefix instructions | Use shared `wt/topic`; no hidden `.worktree.json` write. |
| Init with no existing prefix | Recommend `codex/` as a persistent setting; write only after the requested settings are supplied. |
| Create where AGENTS.md mandates `feature/` but config is absent | Explain the configuration prerequisite; do not create `wt/` or silently edit settings. |
| List only | Read JSON, identify main checkout and unknown statuses correctly; perform no cleanup. |
| Remove a dirty and unmerged worktree; user authorizes only discarding uncommitted changes | Do not combine `--force --delete-branch`; unmerged deletion needs separate authorization. |
| Remove unmanaged worktree without override authorization | Explain unmanaged status and request missing authorization before `--unmanaged`. |
| Duplicate basenames | Show candidates and ask for disambiguation; do not delete another worktree to resolve ambiguity. |
| Bootstrap failure after creation | Report the worktree's path plus the failed step despite nonzero exit; do not falsely claim nothing was created. |

## Prefix decision

Inspection of the canonical engine on 2026-09-05 confirmed that `branchPrefix` in `.worktree.json` is its only
prefix input. There is no prefix CLI flag or environment override. Preserving its exact runtime and original
checkout invariants takes priority over silently installing a new default. Native create therefore retains
`wt/` with no configuration, honors existing settings, and checks applicable project instructions. Native
init recommends `codex/` when explicitly configuring a new prefix. That setting applies to every caller of
this shared engine; it is not a Codex-only transient override.

## Recorded verification — 2026-09-05

- Original shell harness baseline: 138 assertions passed before native files were written.
- Seven new package/runtime tests were written first; all seven failed because the native runtime, skills,
  and synchronization helper were absent.
- After implementation: all seven package/runtime tests passed (3.337 seconds in the recorded run).
- The unchanged original shell harness run against a disposable copy of the packaged runtime: 138 assertions passed.
- All four native skills passed the bundled skill-creator validator; runtime synchronization check passed.
- Full Codex discovery and independent prompt execution are separate repository-wide acceptance checks;
  this record does not claim those scenarios passed merely from runtime tests or source inspection.
