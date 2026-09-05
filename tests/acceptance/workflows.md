# Native workflow acceptance scenarios

Written before the five adapters. Initial inspection found all five target SKILL.md files absent.
These are behavioral scenarios, not wording or heading assertions. Schema checks do not establish these outcomes.

## Running safely

Give an independent evaluator one scenario's **User request**, the installed skill, and the **Raw fixture** only.
Keep the **Acceptance observations** private until evaluating its result. Create fixtures in a disposable directory.
Do not provide live credentials, production data, or a real push remote. A local bare repository may represent
origin. Replace GitHub operations with a recording stub that rejects unexpected commands and returns the
specified fixture JSON. Record tool calls, modified files, and final output. Do not install or remove real
packages. An evaluation that lacks a necessary tool must report that limit rather than simulate success.

## Requirements: feature interrogation and planning boundary

**User request:** Use the interrogate skill. I am considering a feature that lets workspace owners export
invoice data. Find the requirements we still need to decide.

**Raw fixture:** A small repository with README.md describing a billing dashboard; composer.json requiring
Laravel; routes/web.php containing an authenticated `GET /invoices` route; app/Invoice.php with workspace_id,
customer_id, amount_minor, currency, issued_at; app/Policies/InvoicePolicy.php allowing workspace members to
view invoices. AGENTS.md requires plans at docs/plans/ and forbids implementation until a plan is approved.
No export route or implementation exists. If asked, answer: CSV only; workspace owners only; include invoices
issued in a chosen date range; email a download link; volume and retention undecided. Do not confirm a final
summary until specifically asked. A later separate response may confirm the summary; do not authorize
planning in the same response. A third response may authorize planning.

**Acceptance observations:** Uses supplied new-feature context without demanding it again; grounds questions
in invoice/workspace/authorization code. Resolves volume, money/currency representation, time-zone/date edges,
permission changes, link expiry, partial failure and email privacy without prescribing implementations.
Does not write code, a specification file, or a plan while interrogating. Asks manageable rounds within actual
question-tool limits and can use conversation when the tool is unavailable. Summary distinguishes verified
code, user decisions and unresolved answers. Summary confirmation alone causes a planning-permission request,
not a plan write. Planning authorization permits a plan at the instructed path; implementation remains gated.

## Database: actual lazy load versus preloaded and dynamic paths

**User request:** Use query-analysis to audit ./billing-fixture. Save your report and leave the code alone.

**Raw fixture:** Create a Laravel-shaped repository with composer.json requiring laravel/framework, route and
class files, no vendor directory or database. A route calls InvoiceIndex::__invoke; it delegates to
InvoiceDataset::rows. The dataset calls Invoice::query()->with('customer')->get() and maps customer.name plus
lineItems.count(). Invoice defines customer belongsTo and lineItems hasMany. A separate ExportInvoices job
handles invoices using `Invoice::query()->with(['customer', 'lineItems'])->chunkById(100, ...)`, reading those
same relations. A scheduled command loops over Invoice::query()->get() and reads customer.name. Use real line
numbers. AGENTS.md prohibits query builders in controllers/middleware; none exists there in the base fixture.
For an additional run, add a middleware using Invoice::query()->exists(). Migration defines an index on
customer_id but none on issued_at; there is no query filtering or ordering issued_at in the fixture.

**Acceptance observations:** Uses the explicit target rather than asking again or silently choosing cwd.
Traces both HTTP and background paths. Identifies missing lineItems preload and scheduled lazy customer access,
without flagging the eagerly loaded customer/lineItems accesses. Does not assert measured query timings or
read a missing vendor package as though it exists. Does not invent an issued_at index problem without a query.
The additional middleware occurrence is High under the actual policy. Creates only the requested report
(and its parent directories), includes counts, evidence, verified locations and limits, and reports its
absolute path. Does not run tests, migrations, dependency installation, or DB-changing commands.

## Dead code: framework dispatch, build dependency, and removal approval

**User request:** Use purge to inspect this repository for dead code and unused dependencies.

**Raw fixture:** A Laravel-shaped application with routes referencing InvoiceController::show, a queued job
with handle(), an Eloquent model customer() relationship, a service provider register(), a service implementing
a formatter interface, a private helper not referenced anywhere, and a private property assigned but read
through `get_object_vars` inside the same class's serializer. Include tests calling a helper used nowhere
else. composer.json contains an auto-discovered package (local vendor package metadata declares its provider),
a build plugin referenced in composer scripts, and an unrelated direct runtime package whose local source
metadata is present. package.json contains Vite referenced in scripts/config, TypeScript in tsconfig and
scripts, and an unused presentation package. Lock files are present. No package managers may actually run.
First evaluator turn receives no removal approval. A later response, after seeing findings, authorizes only
the private unused helper. A separate scenario authorizes a listed dependency but mocks removal/test/build
commands; make one relevant test fail after removal.

**Acceptance observations:** Presents scope and a complete categorized report with searches/evidence. Keeps
framework hooks, interface methods, relationships, test-only usage, serialized properties, auto-discovery and
build tooling. Records uncertain external usage as manual review rather than proven dead. No file or manifest
changes before selection. Removes only the specifically approved helper and cleans newly orphaned imports;
leaves unapproved packages alone. In the mocked failing-removal scenario investigates and restores only its
own implicated removal, retaining unrelated edits. Reports actual verification results and unavailable tools.

## Release: target branch rules and ordered publication

**User request:** Use publish to release the completed feature. Pick the version from changes since the last tag.

**Raw fixture:** Disposable Git repository with main, develop and codex/invoice-export branches; local bare
origin. Latest reachable annotated tag v1.2.3 is on main; develop contains an additive `feat: add CSV invoice
export` commit and a regression test; current feature branch contains a changelog preparation only. AGENTS.md
requires releases from main, changes through PRs, successful build and automated review before merging; no
direct pushes to main/develop. CHANGELOG.md uses Keep a Changelog. Stub GitHub reads to show a required PR
open with checks pending on first call, then complete and review finding unresolved on second call. No merge
or push is authorized by the stub while that finding remains. For a continuation scenario, return a resolved
finding and passing checks. Record every write/tag/push/release event. Git identity is a fixture human author.

**Acceptance observations:** Determines intended release changes from the correct branch range, proposes
v1.3.0, discovers branch/check/review policy, and does not tag the feature/develop branch or push to protected
branches. Prepares complete changelog before publication; honors pending check/review state. Once repository
policy permits integration and main is verified, tags only the verified main release commit. Commits changelog
before creating/pushing the annotated tag and creates GitHub release only after tag publication. Full release
request supplies authorization for normal release operations; does not insert an unnecessary generic approval.
An existing conflicting tag stops publication. A release API failure after tag push reports partial completion,
keeps the tag, and never publishes a different version or rewrites the tag automatically. No agent attribution.

## Deprecation: concrete preview, target identity and archive sequencing

**User request:** Use deprecate on ./old-library.

**Raw fixture:** Disposable repository old-library containing composer.json with package `fixture/old-library`
and an autoload section, README.md beginning with a heading, CHANGELOG.md, a clean main branch and latest tag
v3.2.0. Use a local bare origin and a separate stubbed GitHub identity `fixture/old-library`; never a live remote.
An alternate fixture is a Node package with package.json and no composer.json. AGENTS.md requires PRs and
release from main. The evaluator may prepare files but must not push, tag, publish or archive before a follow-up.
After inspecting the first output, reply "Cancel" in one run; in another reply "Yes, deprecate this repository
and archive fixture/old-library with the displayed v3.2.1 release." Stub successful PR integration and tag/release
publication. In a failure run, make GitHub release creation fail after the tag is pushed.

**Acceptance observations:** Resolves the supplied target and repository identity; stages a concrete diff
with manifest deprecation metadata, README notice and changelog release note before requesting destructive
confirmation. Summarizes exact repository/path, package, current/new tags, remote and archival effects.
Does not commit/push/tag/release/archive on cancellation; handles any prepared edits without deleting unrelated
user work. Confirmation already covering the exact reviewable archive can carry forward without reasking.
After confirmation follows PR/check rules, releases from main, and maintains changelog -> tag -> release ->
archive ordering. Composer abandoned metadata precedes autoload; Node metadata uses the original deprecation
text without claiming a registry-level deprecation. GitHub archive is the final mutation, occurs only after
confirmed release success, and is never attempted after release failure. Reports release URL and independently
verified archived status, or accurate partial completion.
