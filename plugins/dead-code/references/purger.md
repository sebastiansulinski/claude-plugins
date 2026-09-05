# Purger procedure

Use from the purge skill for PHP/Laravel, JavaScript/TypeScript/Vue, Composer and JavaScript package cleanup.
A missing textual reference is a candidate for investigation, not proof that something is safe to remove.

## 1. State the analysis plan

Outline the requested categories: functions/methods, variables/properties, constants, Composer dependencies
and JavaScript dependencies. State any narrower module/package scope. Proceed with the read-only analysis;
no approval is needed merely to inspect. Keep findings separate from unrelated user edits.

## 2. Check all usage vectors

### Functions and methods

Find definitions and search the entire applicable codebase, including tests, for:

- Direct calls and class/method names used as strings.
- Container resolution, bindings, registrations, constructor and method injection.
- Controller route targets, model binding, view composers, Blade directives, observers and event discovery.
- Scheduled tasks, queued jobs, notifications, middleware and command dispatch.
- Config references, serialization, reflection, callbacks, call_user_func and dynamic method-name calls.
- Traits and their consuming classes; interface and abstract method contracts; magic methods.

Framework entry points such as boot/register/handle/rules/messages, lifecycle hooks, relationship methods,
accessors/mutators/scopes and property hooks are invoked by convention. Do not flag them merely because
there is no direct call. Interface implementations are not dead just because only the interface is referenced.
Test-only helpers are used. Public library APIs may have external consumers; without evidence about that
boundary, retain them and record a manual-review question rather than treating local absence as proof.

### Variables and properties

Check declared-but-unread and assigned-but-unread values. Account for variable variables, dynamic property
names, compact/extract, reflection, serialization, get_object_vars and hooks. A value whose assignment has
side effects cannot be removed merely because its result is unused. Preserve needed side effects.

### Constants

Check class/global constants and define() calls, direct and string constant() access, config, environment
integration and consumers outside the declaring file.

### Composer dependencies

Read require/require-dev and lock/package metadata. Map package namespaces to actual source. Check imports,
provider registration and auto-discovery, config, middleware, container resolution/bindings, commands,
Composer scripts/plugins and build tooling. Check package-level extra metadata, not only the root manifest.
Do not classify a package as unused because it has no import: it may register itself or support a build.
Distinguish root requirements from transitive dependencies; do not propose deleting a package needed by
another dependency. Missing vendor/source evidence limits certainty and must be recorded.

### JavaScript dependencies

Read dependencies/devDependencies and the repository's package-manager/lockfile choices. Check imports and
requires in JS/TS/Vue, Vue script/style blocks, Vite/Webpack/Tailwind/PostCSS plugins/config, package scripts,
TypeScript config/types, CSS imports and executable tooling. Build/test/dev-only use is real use. Check
transitive requirements and framework/plugin discovery before proposing removal.

## 3. Present the full findings list

Organize the report by category. Each candidate includes its verified definition/location or manifest entry,
why it appears unused, the usage vectors checked and any remaining uncertainty. Use the repository's report
format; absent another convention, present the complete findings together in one copyable text block:

```text
Dead Code Report

Unused Functions/Methods
1. ClassName::methodName() — path/to/file.php:42 — evidence and searches

Unused Variables/Properties
1. $propertyName — path/to/file.php:15 — evidence and searches

Unused Constants
1. CONSTANT_NAME — path/to/file.php:8 — evidence and searches

Unused Composer Packages
1. vendor/package-name — composer.json — evidence and searches

Unused JavaScript Packages
1. package-name — package.json — evidence and searches

Possibly unused — manual review
1. Item — remaining uncertainty; retained
```

Use “None verified” for empty categories; do not keep dummy entries. Ask which listed items to remove or
retain, then stop. Nothing is deleted before an explicit selection. If that exact selection is already
available from a prior report in the conversation, verify it still applies and proceed without reasking.

## 4. Remove only approved items

Work one category at a time. Follow applicable test-first requirements and preserve baseline results before
changes where necessary to distinguish new failures. Do not introduce a test that merely asserts absence.
For code, remove the approved item and newly orphaned imports/references without adjacent refactoring.
Follow the project's PHP version and style; use full variable names and imported class names.

For Composer packages use composer remove with the correct dependency section. For JavaScript packages use
the repository's established npm/yarn/pnpm removal operation. Keep manifests and lockfiles coherent; do not
hand-delete transitive lock entries. Package-manager scripts may execute project code, so use only the
repository's authorized environment. Do not add, upgrade or remove unrelated packages to make cleanup pass.

## 5. Verify and recover

After removals, run the repository's full PHP suite where present (for Laravel, php artisan test or Pest),
JavaScript/TypeScript tests where present, Composer install to verify dependency integrity, and the appropriate
JavaScript install plus production build. Honor repository-specific equivalents, lockfile/CI modes and any
required browser-build ordering. Report unavailable dependencies/services or blocked checks as unverified,
not passing. Do not install global tools or change production data for verification.

If a check fails, investigate whether a removal caused it. Restore only the implicated removal and its own
manifest/lockfile changes; never reset the whole checkout or erase another contributor's work. Re-run the
relevant check after recovery and report the failure, restoration and remaining results. Do not silently
remove additional code or dependencies to repair the build. End with removed/retained items and actual
verification evidence.
