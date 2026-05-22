---
name: query-analysis
description: Read-only audit of Eloquent and query-builder usage in a chosen repository. Identifies queries with measurable potential for improvement in performance or memory footprint, and writes the findings to `./docs/analysis/`.
---

# Query Analysis

You are performing a **read-only diagnostic pass** on database query usage in a Laravel codebase. You must not edit, refactor, or create any application code. Your sole deliverable is a structured analysis report written to disk plus a concise summary in the prompt window.

## Step 1 — Target selection

Before doing anything else, ask the user:

> "Which repository directory should I analyse? (Provide the path relative to the current working directory, or an absolute path.)"

Wait for their answer. Do not assume the current directory. If the path does not exist or is not a Laravel repo, stop and report.

## Step 2 — Scope

Analyse every database call reachable from the application's HTTP layer **and** background workers:

- Eloquent model calls (`Model::query()`, `Model::where()`, `Model::find()`, `findOrFail`, `first`, `get`, `paginate`, `cursor`, `chunk`, `lazy`, `count`, `exists`, `pluck`, scopes).
- Relationship calls (`$model->relation`, `->load()`, `->loadMissing()`, `->with()`, `->withCount()`, `->withSum()`, `->has()`, `->whereHas()`, `->withExists()`).
- Query builder calls via `DB::table(...)`, `DB::select(...)`, `DB::statement(...)`, raw expressions, joins, subqueries.
- Custom Eloquent Builder classes (look for `extends Builder` in `*/Builders/*` or wherever the project keeps them).
- Repository / Service / Action / Dataset classes that compose queries.
- Middleware, observers, listeners, jobs, console commands, and notifications that hit the DB.
- Blade / Inertia / Livewire views that may trigger lazy loads (look for `$model->relation` access in templates and components).

Skip vendor code, framework internals, migration files, and seeders unless the user explicitly asks for them.

## Step 3 — What to flag

For each finding, the issue must be **concrete and verifiable from the code** — not speculative. Look for:

### Performance issues
- **N+1 lazy loads** — loop bodies that access `$item->relation` (or a method that does) without `with()` / `load()` on the parent collection. Confirm by reading the loop, the parent query, and the model definition.
- **Missing eager loading on Inertia/JSON responses** — datasets/transformers that touch relations on each row without preloading.
- **Nested relations only partially eager-loaded** — e.g. `with('posts')` then accessing `$post->author` inside a loop.
- **Repeated queries inside loops** — `Model::where(...)` called per iteration where a single `whereIn` would suffice.
- **`whereHas` where `whereRelation` or `whereIn(subquery)` would be cheaper**, or correlated subqueries that should be joins.
- **Polymorphic relations without `morphWith`** causing per-type lazy queries.
- **`get()` followed by in-memory filtering / mapping / counting** that the database could do (`->where(...)->count()`, `->pluck()`, aggregates).
- **`->count()` on a collection already loaded** instead of `->count()` on the builder — and the reverse where the result is already in memory.
- **Order-by on unindexed columns**, `LIKE '%foo%'` on large tables, `OR` conditions across columns where a union would use indexes.

### Resource / memory issues
- **`->get()` / `->all()` on potentially large tables** where `chunk`, `chunkById`, `lazy`, `cursor`, or `paginate` is appropriate.
- **`->pluck()` after `->get()`** (loads full models then discards them) — should be `->pluck()` on the builder.
- **Hydrating full Eloquent models when only a few columns are needed** — missing `select([...])`.
- **`->with('relation')` that loads every column of a wide table** when a constrained closure `with(['relation:id,name'])` would do.
- **Unbounded `whereIn` lists** built from another query — should be a subquery or join.
- **Re-fetching the same data inside one request** (datasets, middleware, and controllers all calling `auth()->user()->load(...)` against the same relations).

### Redundancy / shape issues
- **`->first()` immediately after `->where(...)->get()`**, or `->find()` after a fetched collection.
- **Duplicate aggregates** — separate `count()` + `get()` where `paginate()` already returns both, or repeated `count()` calls.
- **Counting via `->get()->count()`** instead of `->count()`.
- **`exists()` simulated with `count() > 0`**.
- **Query builders constructed in controllers/middleware** (where the analysed repo's `CLAUDE.md` forbids this — flag every occurrence).

### Indexing hints (advisory only)
If a query filters/orders/joins on a column with no index in the relevant migration, note it as **advisory** — don't recommend changes, just record the observation so the user can investigate.

## Step 4 — Methodology

1. Start by mapping the entry points: routes, scheduled commands, queued jobs, observers. From each, follow the call graph into actions/services/datasets and into Eloquent.
2. For each hot path, read the **full method** end-to-end before judging it. Do not flag based on a method name or single line — verify the actual access pattern, including any preceding `with()`/`load()`.
3. When in doubt, **leave it out**. False positives erode trust in the report.
4. Group findings by file, then by call site. Do not duplicate findings that share a root cause — flag the root and list the affected call sites underneath.
5. Estimate severity honestly:
   - **High** — runs on a hot request path (controller, dataset, middleware), scales with row count or user count, or causes O(n) queries.
   - **Medium** — wastes memory or runs extra queries but is bounded.
   - **Low** — cosmetic, micro-optimisation, or only matters at very large scale.
   - **Advisory** — indexing hints, style observations, non-issues worth recording.

## Step 5 — Output

Create the directory if it doesn't exist and write the report to:

```
./docs/analysis/query-analysis-<repo-name>-<YYYY-MM-DD>.md
```

Use this exact structure:

```markdown
# Query Analysis — <repo name> (<YYYY-MM-DD>)

## Summary
- Files scanned: <n>
- Findings: High <n>, Medium <n>, Low <n>, Advisory <n>
- Top three recommendations: <one line each>

## Findings

### [HIGH] <short title>
- **Location:** `path/to/file.php:42` (and other call sites if shared root cause)
- **Symptom:** <what the code does today, in one or two sentences>
- **Why it matters:** <concrete impact — queries per request, memory shape, scaling behaviour>
- **Evidence:** <code excerpt or call chain, kept to the minimum needed to verify>
- **Suggested direction:** <high-level fix idea — NOT a code patch>

### [MEDIUM] ...
### [LOW] ...
### [ADVISORY] ...

## Notes
- Anything ambiguous, anything skipped, anything the user should investigate manually.
```

After saving the file, print to the prompt window:
- The absolute path of the report.
- The per-severity counts.
- The top 3–5 highest-impact findings as bullet points (title + location only).
- An offer: "Want me to draft fixes for any of these? I'll wait for your selection."

## Constraints

- **Read only.** No edits, no new files outside the single analysis report. No running of migrations, tests, or artisan commands beyond `php artisan route:list` if needed to map entry points.
- Do not invent code that isn't there. Every finding must cite a real file and line.
- Do not recommend speculative rewrites ("you could use a CQRS pattern") — keep suggestions grounded in the existing architecture.
- Where the analysed repo's `CLAUDE.md` forbids query builders in controllers/middleware, treat every occurrence as a hard violation and flag it High.
