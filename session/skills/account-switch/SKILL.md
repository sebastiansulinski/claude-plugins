---
name: account-switch
description: >-
  Mirror every Claude desktop session (titles, sub-session nesting, sidebar groups, pins, archived state, scheduled
  tasks, full history) from the signed-in account onto another account on this Mac, so switching accounts leaves the
  sidebar exactly as it was. The target account's email address is mandatory. Use when the user says account-switch,
  "switch account", "I'm switching to <email>" or "move my sessions to the other account".
argument-hint: <target account email address>
---

# Switch accounts without losing the sidebar

**Arguments:** $ARGUMENTS

The Claude desktop app holds one account at a time, and each account has its own sidebar. Conversations, memory and
`~/.claude/CLAUDE.md` are shared by every account; the sidebar is not. This skill makes the other account's sidebar
an exact copy of this one. The other account's sessions that aren't on this one leave its sidebar; they stay in the
backup.

It works in two halves:
- **In the app (this skill):** check, preview and arm. Nothing in the app's data changes.
- **After quitting the app:** Seb runs one command in Terminal. It backs up, swaps the other account's sidebar in one
  recoverable step, checks the result and reopens the app.

The script is `${CLAUDE_PLUGIN_ROOT}/skills/account-switch/scripts/account_switch.py`. Always run it with
`python3 -I`. Call it `SCRIPT` below.

## 1. The target email address is mandatory

The first argument must be an email address. If it is missing or isn't an email address, stop and reply only:

> Usage: `/session:account-switch <email address of the account you're switching to>`

Never guess the target, even when there is only one other account.

## 2. Gather what the script needs

1. **This session's identifier:** `mcp__ccd_session_mgmt__get_session` with `"self"`.
2. **The signed-in account's email address:** the one the app gave you in this session's context (`userEmail`). If
   you don't have it, ask Seb. Never invent one.
3. **Running sessions:** `mcp__ccd_session_mgmt__list_sessions` with `include_archived: true` and `limit: 1000`.
   List any other session that is running or starting. Closing the app stops them, so ask whether to wait for them
   to finish first.

## 3. Preview

```bash
python3 -I "SCRIPT" preview --target-email "<target>" --source-email "<signed-in email>" --self-session "<id>"
```

The output is JSON. Act on the exit code:

- **0, a preview.** Summarise it for Seb in a few short lines:
  - both email addresses;
  - how many sessions are copied, and which of the target's sessions leave its sidebar (by title);
  - scheduled tasks and sidebar groups;
  - problems that already exist (missing conversations, sessions without history, sub-sessions whose main session
    is gone);
  - queued input or backlog items in the target that will be replaced;
  - `notCopied`, if any.

  Then ask once whether to go ahead.
- **3, `needsConfirmation: "source"`.** The app's cached account and the live evidence disagree. Show the evidence
  and the candidate accounts (session count, latest activity, recent titles), and ask Seb which account he's signed
  in to now. Re-run with `--confirm-source <scope>`.
- **3, `needsConfirmation: "target"`.** This email address hasn't been seen before. Show the candidates and ask
  which one belongs to it. Re-run with `--confirm-target <scope>`. The script remembers the answer, so it's asked
  only once per account.
- **5.** Refused: an interrupted switch needs finishing, or the target email is the signed-in account. Relay the
  message.
- **2.** Relay the error and stop.

## 4. Arm

Once Seb says go ahead, run the same command with `arm` instead of `preview`, with the same confirmation flags. Copy
the printed `applyCommand` to the clipboard with `pbcopy`, then tell Seb, in this order:

1. Quit the Claude app completely (Cmd+Q).
2. Open Terminal, paste the command (it's on the clipboard) and press Return. It backs up, switches, checks and
   reopens the app. If it is interrupted, running the same command again finishes or undoes it.
3. In the reopened app, sign out, then sign in as `<target>`.

Also say what doesn't carry over: Remote Control, per-session connector toggles (the app reconnects connectors for
the new account when a session starts) and per-account settings. Mention that the backups live in
`~/claude/account-switch/backups/`, and that the newest three are kept.

## Undo

To put the other account's previous sidebar back, Seb quits the app and runs:

```bash
python3 -I "SCRIPT" restore
```

It restores only that account's sessions and sidebar groups from the newest backup; a backup's identifier selects
another. It never overwrites conversations, `CLAUDE.md` or scheduled task instructions. It copies back only what is
missing, and missing conversations only with `--recover-missing-transcripts`.

`python3 -I "SCRIPT" status` lists operations, backups and the known account email addresses.
