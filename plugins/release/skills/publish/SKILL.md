---
name: publish
description: Prepare or publish a GitHub release using the repository's branch policies and changelog, tag, release sequence. Use for an explicit release request; a changelog-only request does not authorize tagging or publication.
---

# Release publication

Resolve the requested version from the invocation. If none is supplied, derive the semantic version bump
from the actual changes since the latest relevant release tag. Establish the target repository and branch;
release tags must be created from verified main. Read [the manager procedure](../../references/manager.md)
for the complete workflow, changelog format, checks and failure handling.

Respect the requested scope: preparing notes or a changelog does not authorize a tag, release or branch
merge. An explicit full release request authorizes the normal necessary release operations, subject to the
repository's actual branch, review and permission rules. Carry existing authorization across the workflow.

Use available Codex collaboration agents for useful independent history or policy checks, passing the
repository path, branch, requested version, scope and procedure. Keep publication serialized with one owner.
A reference file does not register a named agent; do not invent a tool or select a host-specific model.
If delegation is unavailable, perform the procedure locally and state any verification limits.

Report per-step progress and a final version, commit/tag and release URL. If a step fails, stop dependent
publication steps, report what succeeded and what remains, and follow the procedure's safe recovery guidance.
