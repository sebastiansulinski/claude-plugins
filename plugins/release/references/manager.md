# Release manager procedure

Run only the portion authorized by the user. A complete release follows this strict order:

1. Update and commit the changelog.
2. Create the annotated release tag from main and push it.
3. Publish the GitHub release using that tag and the changelog notes.

## Establish the release target and policy

Resolve the owning Git repository; inspect current branch/worktree, status, remotes and applicable AGENTS.md
instructions. Discover actual branch/PR rules, required checks, automated reviews, release/build scripts and
version-file conventions from repository configuration and available remote metadata. Do not transplant a
direct-push or merge recipe from another repository. Identify the human author/committer identity before
committing; do not add agent attribution to identity or messages.

Determine which completed changes are intended for release. Read commits and actual diffs since the relevant
latest tag, including the intended development branch if work has not yet reached main. Do not accidentally
release unrelated work from another branch or include a dirty checkout wholesale. Inspect existing releases
and tags rather than treating a failed tag lookup as proof that none exist. With no prior release, use the
repository's initial-version convention and state the basis; ask only if ambiguity materially changes scope.

If changes are on a development/feature branch, integrate them into main using the repository's prescribed
path. Do not assume develop exists, switch another occupied worktree, or push directly where PRs are required.
A full release authorization may cover necessary integration; ask only when the intended source or additional
scope is unresolved. Honor required check and review completion before merge, including unresolved automated
findings. If policy requires new branches/PRs for follow-up changes, follow it. Prepare and test allowed work
while checks run, but never create a release tag before policy permits integration.

## Determine and prepare the version

Honor an explicit valid version; otherwise derive the bump from actual changes: major for incompatible
changes, minor for compatible features, patch for compatible fixes. Follow repository conventions for
pre-1.0 versions and prereleases. State the chosen version and notable changes. Verify the intended tag and
release do not already exist locally/remotely before creating them. Never overwrite or move a conflicting tag;
report the conflict and ask for a different version if one is required.

Read the existing changelog (respect its filename/casing). Use its established format, normally:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- User-facing additions.

### Changed
- Behavior changes.

### Deprecated
- Upcoming removals.

### Removed
- Removed functionality.

### Fixed
- Corrections.

### Security
- Security changes.
```

Use only relevant sections. Write clear user-facing descriptions grounded in changes rather than copying
raw commit subjects. Update any required version files according to actual release conventions. Keep the
version section at the top of released entries, preserving an existing Unreleased section when appropriate.
Run the repository's applicable tests/build/release checks and inspect the resulting diff. Do not claim
untested artifacts passed; resolve required failed checks before publication. Commit the release changes
with a clear human-authored message through the policy-compliant integration path.

## Tag from main

Before tagging, independently verify:

- The release checkout is on main, and the release changes are committed and integrated.
- The exact main commit contains the intended tested artifacts and changelog/version changes.
- Required checks and reviews are complete for the release state; no unrelated dirty work is included.
- The intended published main revision and release commit agree, using remote evidence where available.
- The version/tag remains available and the human Git identity is correct.

Create an annotated tag using the repository's prefix convention (normally vX.Y.Z), with a release message.
Push only the intended tag after main integration has succeeded. Verify the remote tag points at the intended
release commit; an annotated tag's object ID differs from its peeled commit ID, so compare the commit.
Never force-push, retag or delete a public release to make this step appear successful.

## Publish and verify

Use the available GitHub API/CLI to publish a release for the verified pushed tag. Use the version's
changelog section as release notes and the tag as release target. Write multiline notes to a temporary file
and use gh release create --notes-file when structured tool arguments are unavailable. Avoid shell interpolation
of changelog content. Mark stable releases latest where appropriate; mark prereleases as prereleases instead.
Attach assets only when required by the requested scope and repository workflow.

Verify publication, release URL, tag and release flags from the remote response or a read-back. Report each
step's status, the final version, source commit, tag, notable changes and release URL. A local tag or successful
push alone is not a published GitHub release.

## Failure and retry boundaries

Stop dependent actions at the first failed prerequisite. Report whether changelog commit, main integration,
tag creation/push and GitHub publication completed. Do not continue to the next release step after an error.
For a transient or uncertain remote response, read remote state before retrying; do not create duplicates.
A retry of the same authorized operation may proceed once evidence establishes it is safe and the cause is
resolved. A conflicting tag, changed release scope, unresolved required review or unavailable authorization
requires resolution, not a bypass. If publication fails after the tag is pushed, preserve it and give the
concrete remaining step for that same tag. Never invent a successful release URL or silently bump again.
