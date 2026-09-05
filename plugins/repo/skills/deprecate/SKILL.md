---
name: deprecate
description: Prepare and carry out an explicitly requested repository deprecation and GitHub archival, including notices and a final release. Require approval of the concrete target and archive effects before external mutations.
---

# Deprecate and archive a repository

Use the supplied path, resolving relative paths from the invocation's working directory; if no path is
provided, use that directory. Operate only inside the resolved repository. This workflow does not create a
plan file unless the user's applicable project instructions require one.

## Discover the concrete target

Read applicable AGENTS.md instructions, composer.json or package.json, README and changelog. Inspect Git
status, branch/worktree, remotes and release tags, and verify the intended GitHub owner/repository. Confirm
the working tree is clean before preparing changes; do not fold unrelated edits into deprecation. Inspect
branch/PR policies, required checks/reviews, release conventions and the configured human Git identity.
Never commit or push as an agent.

Determine the latest relevant semantic version tag and its next patch version, preserving its prefix.
Resolve missing/ambiguous tags or multiple plausible remotes before publication; do not invent a target.
A configured Git remote alone is not proof of which repository the user intends to archive if identities
conflict. Do not deprecate a package registry account or delete local files as an implied extra step.

## Prepare a reviewable result, then confirm

Prepare these local edits, preserving existing formatting:

- **Composer:** add or update the top-level `"abandoned": true` before `"autoload"`, otherwise before `"scripts"`,
  otherwise at the end. Preserve unrelated metadata.
- **Node-only repository:** add `"deprecated": "This package is deprecated and no longer maintained."` to
  package.json. This is repository metadata; it does not prove registry-level deprecation.
- **README:** immediately after its first heading, add the following notice once:

```markdown
> **Warning**
> This package is deprecated and no longer maintained.
```

- **Changelog:** record the deprecation in the next patch release using the existing changelog's format and
  filename. If none exists, prepare CHANGELOG.md with the release entry. Changelog preparation must precede
  tagging and GitHub publication.

Inspect the diff and validate the edited manifests. Present the exact repository name/path, package name,
GitHub remote, current tag, proposed next patch tag and files/diff. State that completion will commit and
integrate the notices, push the release tag, publish the deprecation release and finally archive that exact
GitHub repository. Ask for explicit confirmation of those effects unless the conversation already contains
specific informed approval for this target and scope. Carry that approval forward; do not repeatedly ask.

Use a confirmation/input tool only when available and allowed for this type of decision; otherwise ask in
conversation. Never treat silence as consent. Until confirmed, do not commit, push, tag, publish or archive.
If the user cancels, stop all publication and remove only this workflow's own uncommitted preparation edits
when they can be safely separated; preserve unrelated/concurrent changes and report any retained preview.

## Execute after approval

Proceed without adding permission checkpoints for actions already covered by the confirmation:

1. Stage only the manifest, README, changelog and any explicitly required release files. Commit using
   `Mark package as deprecated and abandoned`. Integrate into main through the repository's branch/PR policy,
   honoring checks and automated reviews. Never directly push a protected branch or bypass policy.
2. From verified main containing the committed deprecation changes, create the annotated next-patch tag with
   message `Mark package as deprecated and abandoned`. Push that tag and verify its remote commit target.
3. Publish the GitHub release for that tag. Use the tag as title and this exact release body:
   `This package is deprecated and no longer maintained.` Verify the published release and retain its URL.
4. Only after successful release verification, archive the confirmed GitHub owner/repository through the
   available API or `gh repo archive <owner>/<repo> --yes`. Read back its archived status.

Keep these actions serialized. Before publication, verify the release checkout is main, all expected changes
are committed, the tag is available, and the target identity still matches the confirmation. Respect actual
verification requirements. Do not silently widen permissions or disable branch protection to finish.

At any failed step, stop dependent actions and report the error plus completed steps. For uncertain remote
responses, read the state before retrying the same authorized operation. Never rewrite an existing tag or
archive after release failure. Do not retry against another repository or choose a new version implicitly.

## Final report

List files modified, whether the commit reached main, the tag and release URL, and the verified archive
status. Distinguish preparation, partial completion and actual publication. Mention any required verification
that could not run and any remaining follow-up.
