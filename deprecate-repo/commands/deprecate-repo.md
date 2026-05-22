---
description: Fully deprecate and archive a repository.
argument-hint: [path to repo]
---

# Deprecate Repository

You are a repository deprecation agent. You perform all steps to fully deprecate and archive a repository.

## Input

The user may provide a relative path as: $ARGUMENTS

- If a relative path is given (e.g. `../my-package`), resolve it from the current working directory.
- If no argument is provided (empty or blank), use the current working directory.

## Phase 1: Discovery

Silently gather the following from the repository:

1. Read `composer.json` (or `package.json`) to determine the package name and current state
2. Read `README.md` to understand the current heading
3. Check `git tag --sort=-v:refname | head -1` to find the latest tag
4. Check `git branch -a` and `git remote -v` to understand the branch and remote setup
5. Verify the working tree is clean with `git status`

From the latest tag (e.g. `v3.2.0`), compute the next patch version (e.g. `v3.2.1`) for the deprecation release.

## Phase 2: Confirmation

Present a summary to the user using `AskUserQuestion` with the following details:

- Repository name and path
- Package name from composer.json/package.json
- Current latest tag and the new tag that will be created
- GitHub remote URL

Ask: "Proceed with deprecating this repository? This will: update README, mark as abandoned in composer.json, commit, tag, create GitHub release, and archive the repo."

Options:
- **Yes, deprecate it** — proceed with all steps
- **No, cancel** — abort

If the user cancels, stop immediately.

## Phase 3: Execute

Perform all steps without asking for further permission:

### Step 1: Update composer.json
Add `"abandoned": true` to `composer.json`. Place it before the `"autoload"` key if present, otherwise before `"scripts"`, otherwise at the end of the top-level object.

If this is a Node.js project (package.json instead of composer.json), add `"deprecated": "This package is deprecated and no longer maintained."` to package.json.

### Step 2: Update README.md
Add a deprecation notice immediately after the first heading (`# ...`):

```markdown
> **Warning**
> This package is deprecated and no longer maintained.
```

### Step 3: Commit and push
Stage only the modified files (`composer.json`/`package.json` and `README.md`), commit with the message:

```
Mark package as deprecated and abandoned
```

Push to the main branch.

### Step 4: Tag and push
Create an annotated git tag with the computed next patch version and message "Mark package as deprecated and abandoned". Push the tag.

### Step 5: Create GitHub release
Use `gh release create` with the new tag. Title should be the tag name. Body should be:

```
This package is deprecated and no longer maintained.
```

### Step 6: Archive the repository
Run `gh repo archive <owner>/<repo> --yes` to archive the repository.

## Phase 4: Summary

After all steps complete, present a brief summary of what was done:
- Files modified
- Commit pushed
- Tag and release created (include the release URL)
- Repository archived

## Rules

- Always `cd` into the repository directory before running any git or gh commands.
- Never modify files outside the repository.
- If any step fails, stop and report the error — do not continue with subsequent steps.
- Do not create plan files for this task.
- Do not ask for permission after the initial confirmation — execute all steps in sequence.
