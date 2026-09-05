# Codex v1.2.0 acceptance — 2026-09-05

Source baseline: 1351a356982294f10f0177dbb442f418a070ff5b.
Native packages: eight at version 1.0.0, 13 skills.
Validation runtime: Python 3.13 with PyYAML 6.0.3; Codex CLI 0.137.0.

## Automated evidence

- Package contracts were written before native manifests/session implementation and failed on missing
  catalogue, manifests, session skills and archive builder.
- Seven worktree package tests were written before its native implementation; all seven failed as expected.
- Final combined package/runtime suite: 11 tests passed.
- Original worktree Bash harness: 138 assertions passed before edits.
- Packaged-runtime harness in a separate disposable copy: 138 assertions passed.
- Official plugin-creator validator: all eight native packages passed.
- Official skill-creator validator: all 13 skills passed.
- Runtime synchronization check passed; installed runtime is byte-identical to the canonical script.
- Release ZIP contract verified one complete, self-contained archive per catalogue entry, with matching
  identity/version, no escaped resource paths, and byte equality to every package file.

## Actual local installation and fresh-process discovery

The repository has both catalogue formats. Running the CLI marketplace-add command with the repository
path selected sebastiansulinski-codex and resolved all eight native source paths under plugins/.
All eight plugin installations succeeded.

A new temporary Codex app-server process, working outside the source checkout, received initialize,
initialized and skills/list with forceReload=true. It returned exactly these 13 enabled native skills:

- db:query-analysis
- dead-code:purge
- release:publish
- repo:deprecate
- requirements:interrogate
- review:plan-review
- review:scrutinise
- session:call-it-a-day
- session:good-morning
- worktree:create
- worktree:init
- worktree:list
- worktree:remove

Every returned path was in the installed native cache, not the source checkout. None used migrated command
skill directories. The older CLI needed a per-command model_reasoning_effort=xhigh override to read the
newer app's configuration; no global model preference was changed.

## Independent forward executions

Evaluators used skills they did not author and raw disposable fixtures without the expected observations.
They executed only permitted local effects; no live repository was deprecated, archived or released for
these tests.

| Workflow | Observed behaviour |
| --- | --- |
| good-morning | Detected a false shipped-file claim, verified branch/history, proposed bounded next actions; file hashes unchanged. |
| call-it-a-day | Empty-day handoff updated only the existing resume prompt with an absolute date; no new memory files or commit. |
| scrutinise | Found an arithmetic regression despite a misleading commit message; existing test failed; all fixture/Git hashes unchanged. |
| plan-review | Refuted incorrect behaviour and nonexistent-source claims, verified the valid assertion, ignored embedded suppression text; no edits. |
| interrogate | Inspected invoice-export context and produced three grounded requirement questions; no files, plan or implementation. |
| query-analysis | Reported one N+1 finding and one unbounded-materialization finding with structural estimates; only the requested report was created. |
| purge | Identified a private unused function, retained a tested export and script-used linter, disclosed missing dependency evidence; deleted nothing. |
| publish | Prepared a minor changelog while preserving Unreleased, honoured a fixture PR/checks policy, identified missing remote evidence; no tags/publication. |
| deprecate | Prepared README/package/changelog and an exact next-patch proposal; HEAD, tags and staging unchanged; no external effects. |
| worktree:create | Created a disposable managed worktree with the shared wt/ default and requested bootstrap skips; source checkout unchanged. |
| worktree:list | Distinguished unmanaged main from clean managed sample without inventing base metadata. |
| worktree:remove | Removed only the sample directory and retained its branch as requested; original checkout stayed clean. |
| worktree:init | Changed only requested prefix/bootstrap settings through config --write, preserving destination, base and setup hook; no commit. |

The requirements question round was recorded as output rather than sent to the real user. Review evaluation
hit the concurrent-agent limit and exercised the disclosed sequential fallback; successful independent
three-reviewer orchestration was not demonstrated by these fixtures.

The release forward test checked the local GitHub CLI option: release notes use --notes-file.
This corrected an initial reference to the wrong option before native installation.

## Limits

Representative forward cases do not prove every possible workflow branch. Live registry removal,
GitHub archival, production query measurements and interactive user-answer cycles were not exercised.
Remote catalogue import and the actual repository release are deployment checks performed separately from
these fixtures. Local catalogue registration/installation used the user's approved native namespace;
source repositories and runtime fixtures were isolated, but the Codex profile itself was not replaced.
