---
description: Publish a release — update the changelog, create the git tag, and publish the GitHub release.
argument-hint: [optional version, e.g. "1.2.0"]
---

Spawn the `manager` agent (via the Task tool) to run the full release workflow.

**Requested version:** $ARGUMENTS

If no version is given above, the agent determines the bump (major / minor /
patch) from the commits since the last tag.

When invoking the agent, pass it a self-contained brief that includes:

1. The requested version if specified, otherwise the instruction to derive it
   from commit history.
2. The current working directory and git branch — the release must be cut
   from `main`.
3. A reminder of the strict order: update the changelog, create and push the
   tag, then publish the GitHub release.

Surface the agent's per-step progress and its final release summary to me. If
any step fails, stop and report it — do not continue.
