---
name: interrogate
description: Interrogate new-feature or existing-project requirements through grounded questions and a confirmed summary. Use when the user requests requirements discovery before planning; do not implement or prescribe solutions.
---

# Requirements interrogation

Discover missing requirements through questions grounded in the actual project. During discovery,
interrogation and summary, write no code, documentation files or plans, and do not suggest solutions.
Use context supplied in the invocation; do not ask the user to repeat answers already given.

## Establish scope

Determine whether this is a **new feature** or a **general/existing-project concern**. If the request does
not resolve this, ask which applies. For a new feature, obtain its purpose, intended behavior and known
context before discovery; the resulting feature brief bounds every later question. For general work,
use the concern or additional context supplied by the user to bound discovery.

Ask questions through a user-input tool when available and permitted in the current mode. Honor its actual
question/option limits; use short rounds of one to three questions rather than demanding an unsupported
batch. When a suitable tool is unavailable, ask directly in conversation and wait for the answers.
Missing required answers are not permission to guess. Never invent a host-specific question or mode tool.

## Discover before interrogating

Read the applicable AGENTS.md instructions, README, relevant project documents and existing plans/tasks.
Inspect actual structure, manifests, dependencies, config, routes, APIs, key interfaces, data models,
integrations and entry points. Understand:

- Project purpose, stack, core domains and architectural patterns.
- How data enters, is transformed and leaves the system.
- Jobs, deployment/environment boundaries and operational dependencies.
- Staged or planned work, scaffolding, TODOs and module dependencies.

For a feature, focus on code it touches, extends or depends upon. Verify behavioral claims against source;
documentation records intent, not proof. Keep discovery details internal until the summary. Brief progress
updates may state what is being examined without dumping an unsolicited architecture report.

## Interrogate

Group questions by domain or concern. Ask, wait for answers, and probe follow-up gaps. Explore requirements,
boundaries, edge cases, decisions, constraints and dependencies until material assumptions are resolved.
Do not substitute defaults for user decisions or interpret vague answers as settled requirements.

For a new feature, cover its interactions with existing code, data, APIs and infrastructure: access control,
error handling, backward compatibility, migration, rollout, testing, limits, operational failure and privacy
where relevant. For general work, focus on gaps between observed code and a complete specification.
Distinguish an unanswered product decision from a fact that can be checked in source; investigate the latter.
When an answer is vague, request the concrete behavior or constraint. Ask what may still have been missed.
Do not force irrelevant topics into the scope or claim every possible assumption has been eliminated.

## Confirm the summary

Present a structured conversational summary by domain/concern, separating verified code behavior, user
answers and open decisions. For a new feature include purpose, scope, behavior, edge cases, constraints,
dependencies and remaining decisions. State evidence or verification limits for code claims.
Ask the user to confirm that the summary is complete; resolve corrections before proceeding.

## Transition to planning

Only after the user confirms the summary is complete, ask whether to turn the findings into an
implementation plan. Summary confirmation alone does not authorize planning. If that specific planning
approval is already supplied, carry it forward without asking again.

On approval, write a descriptive kebab-case plan under docs/plans/ or the project's explicit plan location,
using the discovery, answers and confirmed summary. Use a planning tool only if it actually exists and is
permitted; a conversational request cannot change the host's operating mode. Include the repository-relative
plan path in the response. Stop after saving the plan and wait for implementation approval. This skill
itself never implements the feature.
