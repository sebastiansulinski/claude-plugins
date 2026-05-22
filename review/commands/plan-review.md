---
description: Multi-agent grounded review of a plan file — scrutiniser + architect + fact-verifier, synthesised with an ultrathink pass.
argument-hint: <path to plan file>
---

# Plan review — multi-agent grounded review

Run a **multi-agent grounded review** of a planning document, entirely locally.
A local session has full filesystem visibility into the codebase (and any git
submodules) that a cloud planning sandbox cannot match. The dominant failure
mode for plans is **factual drift from code reality**: a plan asserting things
about the code that are not actually true. This review exists to catch that.

## Target plan

`$ARGUMENTS`

If that is empty, ask the user which plan file to review and stop until they
answer. Then **Read the plan file in full** before doing anything else. If it
cannot be read, tell the user and stop.

## Step 1 — Launch three independent reviewers IN PARALLEL

Spawn all three agents below **in a single message** (three `Agent` tool calls
together) so they run concurrently. Give each agent:

- the absolute path to the plan file;
- the instruction that this is a **read-only review — report findings, do NOT
  edit any file**;
- the note that it has full filesystem access to the whole codebase. If the
  repository uses git submodules, it must run `git submodule status` to
  enumerate them and review across all of them. Each agent must **verify
  against the actual code, never take the plan's word**;
- the instruction that **every finding must carry an explicit Recommended
  action** — the concrete fix, not just the problem. When more than one fix is
  possible, recommend the one that makes the plan most correct and robust:
  **accuracy over simplicity**. A simpler alternative may be named only as a
  clearly-labelled secondary option with its trade-off stated.

**Agent 1 — `scrutiniser`** (subagent_type: `scrutiniser`)
Deep critical review of the plan as an engineering artifact: design bugs, false
or unverifiable claims, design flaws, anti-patterns, missing edge cases,
internal contradictions, missing test coverage, security/safety gaps. Read the
real code (and submodules) to confirm or refute claims. Report each finding with
a severity (Critical / Important / Minor) and `file:line` evidence.

**Agent 2 — `Plan`** (subagent_type: `Plan`)
Review the plan's structure and strategy: phase sequencing and any stated
hard-order, dependency correctness, scope realism, whether phases are sized
right, whether parallelisation claims hold, risk coverage, and anything material
missing entirely. Architectural soundness, not line-level bugs. Report concrete
recommendations.

**Agent 3 — `general-purpose`** (subagent_type: `general-purpose`)
The anti-drift agent. Go through the plan **claim by claim**. Every factual
assertion about the codebase — "file X exists", "Y is not installed", "Z is a
stub", "the current type declares only …", class names, file paths, migration
filenames, dependency lists, enum casings — must be checked against the ACTUAL
code across the codebase and any submodules. Report each checked claim as
**VERIFIED / WRONG / UNVERIFIABLE** with `file:line` evidence, and list every
WRONG or UNVERIFIABLE claim prominently at the top of its report.

## Step 2 — Synthesise (ultrathink)

When all three reports are back, **ultrathink** and synthesise them into ONE
consolidated report. Do not concatenate — de-duplicate overlapping findings,
resolve any disagreement between agents (state which side you take and why), and
rank by severity. Tie-break rule: where Agent 3's `file:line` evidence
contradicts a claim in the plan or another agent, **Agent 3's evidence wins**.

**Every issue — at every severity — must carry an explicit Recommended action.**
Choose the action that makes the plan most **correct and robust**: prioritise
accuracy over simplicity or expedience. A wrong-but-simple plan is worse than a
correct-but-involved one. Where a genuinely simpler alternative exists, name it
as a clearly-labelled secondary option with its trade-off — but the primary
recommendation is always the most accurate one.

The synthesised report must contain:

1. **Verdict** — sound as-is / sound with fixes / needs rework.
2. **Factual corrections** — every WRONG or UNVERIFIABLE claim (Agent 3).
   Highest priority: these are the cloud-sandbox blind spot this review exists
   to catch. For each: the claim, the `file:line` evidence, and the
   **Recommended action** (what the plan should say instead, or what to verify).
3. **Critical + Important findings** — design and structural issues,
   deduplicated. For each: the problem, why it matters, and the **Recommended
   action**.
4. **Minor findings** — each with a one-line **Recommended action**.
5. **Recommended plan edits** — a single concrete, ordered list consolidating
   every Recommended action above into exactly what to change in the plan file.

## Step 3 — Stop

Output the synthesised report in the conversation. Do **NOT** edit the plan
file. Wait for the user to decide which findings to fold in.
