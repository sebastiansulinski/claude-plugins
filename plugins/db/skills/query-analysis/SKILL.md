---
name: query-analysis
description: Audit Laravel Eloquent and query-builder usage in a user-selected repository without changing application code. Trace HTTP and background paths and write an evidence-backed query analysis report under docs/analysis/.
---

# Query analysis

Perform a read-only diagnostic pass. The sole filesystem deliverable is one analysis report; creating its
parent directory is allowed. Do not fix code or turn this audit into an implementation task.

## Target and boundaries

Use the repository path explicitly supplied with the invocation. Resolve relative paths from the invocation's
working directory. If no target was supplied, ask for it and wait; do not assume the current repository.
Confirm the directory exists and is Laravel, otherwise stop and explain. Read its applicable AGENTS.md,
architecture policies, relevant source and tests. Report unavailable source, dependencies or runtime evidence.

The default report location is docs/analysis/ under the invocation's working directory, matching the original
command's ./docs/analysis/ convention. Honor a user-specified report location. Do not create any other files,
run tests, install dependencies, run migrations or invoke application commands other than the optional
`php artisan route:list` to map entry points. Prefer reading routes when that is sufficient. No data writes.

## Trace the complete query path

Map HTTP entry points and background execution: routes, middleware, observers, listeners, notifications,
scheduled commands and queued jobs. Follow calls into actions, services, repositories, datasets, custom
Eloquent builders and models. Read complete methods rather than isolated search hits. Include:

- Eloquent terminal calls, scopes, aggregates, pagination, chunk/lazy/cursor iteration and existence checks.
- Relationship access, with/load/loadMissing, nested and polymorphic relations, withCount/withSum/withExists,
  has/whereHas and other relation predicates.
- DB facade calls, raw expressions, joins and subqueries.
- Blade, Inertia/JSON transformations and Livewire/component access that can trigger lazy loads.

Skip vendor/framework internals, seeders and general migration auditing unless requested. Read relevant
migration/index definitions only to ground the advisory index observations below. Do not claim full
coverage without tracing all relevant entry points; record what was scanned and what remains unverified.

## Findings that merit evidence

Confirm parent query, loop, model definition and any prior preload before claiming N+1 behavior. Consider:

- Lazy relation access per row; response transformers missing preload; incomplete nested preload;
  polymorphic access missing appropriate per-type preload; repeated queries inside loops.
- Unbounded get/all or hydrated models when pagination, chunking, streaming, pluck or aggregates are appropriate.
- Filtering/counting/mapping after fetching when equivalent work belongs in the database; get then pluck/first;
  loading wide rows or all relation columns when a verified consumer needs only a few.
- Re-fetching already loaded data in one request; repeated aggregates; count-based existence checks;
  redundant count plus get or additional counts around pagination.
- Unbounded whereIn lists populated by another query; correlated queries or relation predicates with a
  demonstrable costly shape; filter/order patterns with verified indexing relevance.

A collection count is appropriate when the collection is already needed; a builder count is appropriate
when rows need not be loaded. Do not flag either in isolation. Do not assume whereRelation, a join, a union
or a different subquery is cheaper than whereHas or another valid shape without supporting evidence.
Separate structural query-count or memory estimates from measured performance. Do not invent timings,
production row counts or query plans. When in doubt, leave the alleged defect out or record the uncertainty.

When the repository forbids query construction in controllers/middleware, flag each verified occurrence as
**High** under that actual rule. Otherwise do not import a policy from another project.

For columns used in actual filters/orders/joins, a missing index in the relevant migration is **Advisory**:
record the observation and source, including unavailable production-schema evidence, without recommending
an index change. Avoid index observations disconnected from any traced query.

## Severity and organization

Group by file and call site; report a shared root cause once with all affected sites. Use:

- **High:** a hot request path or O(n) query behavior scaling with rows/users, or the policy violation above.
- **Medium:** concrete extra queries or memory waste with bounded impact.
- **Low:** a small verified inefficiency or a problem requiring unusually large scale.
- **Advisory:** indexing observations or style notes that are not established defects.

Every finding cites a real file and verified line. Suggestions are directions grounded in the architecture,
not patches or speculative rewrites. Explain the actual access pattern and why it matters.

## Report

Write query-analysis-<repo-name>-<YYYY-MM-DD>.md with this structure:

```markdown
# Query Analysis — <repo name> (<YYYY-MM-DD>)

## Summary
- Files scanned: <actual count>
- Findings: High <n>, Medium <n>, Low <n>, Advisory <n>
- Top three recommendations: <up to three grounded directions; fewer if fewer findings>

## Findings

### [HIGH] <short title>
- **Location:** `path/to/file.php:42` (and sites sharing the root cause)
- **Symptom:** <what the code does>
- **Why it matters:** <query count, memory shape or scaling impact; label estimates>
- **Evidence:** <minimal code excerpt or call chain>
- **Suggested direction:** <high-level fix direction, not a patch>

### [MEDIUM] ...
### [LOW] ...
### [ADVISORY] ...

## Notes
- <ambiguity, unavailable evidence, skipped scope and manual investigations>
```

Omit empty finding placeholders. After saving, provide the report's absolute path, severity counts and the
three to five highest-impact finding titles with locations (or all if fewer). Offer to draft fixes for the
user's selected findings, and wait for a selection before any implementation.
