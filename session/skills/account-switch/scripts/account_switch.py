#!/usr/bin/env python3
"""Mirror every Claude desktop session from the signed-in account onto another account on this Mac.

Always run with `python3 -I`. Subcommands:
  preview  read-only report of what a switch would do (run inside the app by /session:account-switch)
  arm      record an approved switch, to be applied once the app has quit
  apply    run the armed switch with the app closed (Terminal)
  restore  put a backup's target account back, with the app closed (Terminal)
  status   list operations and backups

Exit codes: 0 done, 2 error, 3 needs confirmation, 4 an interrupted operation was reconciled,
5 refused, 6 cloning unsupported.
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.util
from dataclasses import dataclass, field
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import time
from typing import Callable

SCRIPT = Path(__file__).resolve()
SCOPE_PART = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Removed from every copied record: Remote Control and connector state of the account that wrote it.
# The app rebuilds the connector configuration from the signed-in account whenever a session starts.
ACCOUNT_BOUND_FIELDS = (
    "bridgeSessionIds",
    "remoteControlUserEnabled",
    "enabledMcpTools",
    "remoteMcpServersConfig",
    "connectorWireNames",
)
# The app rewrites a session record when the session acts, not continuously, so allow a whole turn.
FRESH_SECONDS = 1800
KEEP_BACKUPS = 3
GROUP_SCOPES = "dframe-group-scopes"
COMMIT_STEPS = ("move-live-out", "move-staged-in", "write-config", "verify")
APPLY_CHECKPOINTS = (
    "backup-done",
    "staged",
    *(f"{edge}:{step}" for step in COMMIT_STEPS for edge in ("before", "after")),
)
PENDING_STATES = {"armed", "preparing", "applying", "recovering"}


class SwitchError(Exception):
    exit_code = 2


class NeedsConfirmation(SwitchError):
    exit_code = 3

    def __init__(self, what: str, payload: dict):
        super().__init__(f"confirm the {what} account")
        self.payload = {"needsConfirmation": what, **payload}


class Reconciled(SwitchError):
    exit_code = 4


class Refused(SwitchError):
    exit_code = 5


class CloneUnsupported(SwitchError):
    exit_code = 6


def claude_app_in(process_listing: str) -> bool:
    """Whether a `ps -axo comm=` listing holds the desktop app's main process.

    Matched by executable path: `pgrep -x Claude` misses it, and Claude Code's own processes run from a
    lower-case `claude.app` that must not count.
    """
    return any(line.strip().endswith("/Claude.app/Contents/MacOS/Claude") for line in process_listing.splitlines())


def app_is_running() -> bool:
    listing = subprocess.run(["ps", "-axo", "comm="], capture_output=True, text=True, check=True).stdout
    return claude_app_in(listing)


def clonefile(source: Path, destination: Path) -> None:
    """Copy-on-write clone of a file or folder tree. Never falls back to a full copy."""
    library = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
    function = getattr(library, "clonefile", None)
    if function is None:
        raise CloneUnsupported("this system has no clonefile")
    function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint32]
    if function(os.fsencode(source), os.fsencode(destination), 0x0001) != 0:
        error = ctypes.get_errno()
        if error in (errno.ENOTSUP, errno.EXDEV, getattr(errno, "EOPNOTSUPP", errno.ENOTSUP)):
            raise CloneUnsupported(f"cloning is not supported here: {os.strerror(error)}")
        raise SwitchError(f"clonefile failed for {source}: {os.strerror(error)}")


def reopen_claude() -> None:
    subprocess.run(["open", "-a", "Claude"], check=False)


@dataclass
class Env:
    home: Path
    app_running: Callable[[], bool] = app_is_running
    clone: Callable[[Path, Path], None] = clonefile
    checkpoint: Callable[[str], None] = field(default=lambda name: None)
    reopen_app: Callable[[], None] = reopen_claude
    now: Callable[[], float] = time.time

    @property
    def app_dir(self) -> Path:
        return self.home / "Library/Application Support/Claude"

    @property
    def sessions_root(self) -> Path:
        return self.app_dir / "claude-code-sessions"

    @property
    def desktop_config(self) -> Path:
        return self.app_dir / "claude_desktop_config.json"

    @property
    def app_config(self) -> Path:
        return self.app_dir / "config.json"

    @property
    def claude_home(self) -> Path:
        return self.home / ".claude"

    @property
    def state_root(self) -> Path:
        return self.home / "claude/account-switch"

    @property
    def operations(self) -> Path:
        return self.state_root / "operations"

    @property
    def backups(self) -> Path:
        return self.state_root / "backups"

    @property
    def accounts_file(self) -> Path:
        return self.state_root / "accounts.json"


# --- small helpers -------------------------------------------------------------------------------


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default
    except ValueError as error:
        raise SwitchError(f"{path} is not valid JSON: {error}") from error


def write_json_atomic(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    with open(temporary, "w") as handle:
        json.dump(data, handle, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec="seconds")


def file_hashes(root: Path) -> dict:
    hashes = {}
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "<dir>"
    return hashes


def fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        status = path.stat()
        digest.update(f"{path.relative_to(root)}|{status.st_size}|{status.st_mtime_ns}\n".encode())
    return digest.hexdigest()


def remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


# --- scopes and records --------------------------------------------------------------------------


def scope_path(env: Env, scope: str) -> Path:
    """The folder of an `<account>/<organisation>` scope, refusing anything outside the sessions folder."""
    parts = scope.split("/")
    if len(parts) != 2 or not all(SCOPE_PART.match(part) for part in parts):
        raise SwitchError(f"{scope!r} is not an <account id>/<organisation id> scope")
    path = env.sessions_root / parts[0] / parts[1]
    for candidate in (path.parent, path):
        if candidate.is_symlink():
            raise SwitchError(f"{candidate} is a symbolic link; refusing to follow it")
    if path.exists() and path.resolve().parent.parent != env.sessions_root.resolve():
        raise SwitchError(f"{path} resolves outside the sessions folder")
    return path


def discover_scopes(env: Env) -> list[str]:
    scopes = []
    if not env.sessions_root.is_dir():
        raise SwitchError(f"{env.sessions_root} does not exist; is the Claude desktop app installed?")
    for account in sorted(env.sessions_root.iterdir()):
        if not account.is_dir() or account.is_symlink() or not SCOPE_PART.match(account.name):
            continue
        for organisation in sorted(account.iterdir()):
            if organisation.is_dir() and not organisation.is_symlink() and SCOPE_PART.match(organisation.name):
                scopes.append(f"{account.name}/{organisation.name}")
    return scopes


def read_records(folder: Path) -> dict:
    records = {}
    for path in sorted(folder.glob("local_*.json")):
        record = read_json(path)
        if not isinstance(record, dict) or record.get("sessionId") != path.stem:
            raise SwitchError(f"{path} is not a session record for {path.stem}")
        if not isinstance(record.get("cliSessionId"), str) and record.get("transcriptUnavailable") is not True:
            raise SwitchError(f"{path} has neither a conversation nor transcriptUnavailable")
        records[path.stem] = record
    return records


def summarise(env: Env, scope: str) -> dict:
    records = read_records(scope_path(env, scope))
    recent = sorted(records.values(), key=lambda record: record.get("lastActivityAt") or 0, reverse=True)
    latest = recent[0].get("lastActivityAt") if recent else None
    return {
        "scope": scope,
        "sessions": len(records),
        "latestActivity": iso(latest / 1000) if latest else None,
        "recentTitles": [record.get("title") or record["sessionId"] for record in recent[:3]],
    }


def load_accounts(env: Env) -> dict:
    return read_json(env.accounts_file, {"accounts": {}}).setdefault("accounts", {})


def save_accounts(env: Env, accounts: dict) -> None:
    write_json_atomic(env.accounts_file, {"accounts": accounts})


def label(accounts: dict, scope: str, email: str, now: float) -> None:
    for other, info in list(accounts.items()):
        if other != scope and info.get("email", "").lower() == email.lower():
            del accounts[other]
    accounts[scope] = {"email": email, "lastSeen": iso(now)}


# --- identity ------------------------------------------------------------------------------------


def cached_scope(env: Env) -> tuple[str | None, str | None]:
    config = read_json(env.app_config, {}) or {}
    flag = config.get("sshTransportFlagLastAnswer") or {}
    flag_scope = None
    if flag.get("accountUuid") and flag.get("orgUuid"):
        flag_scope = f"{flag['accountUuid']}/{flag['orgUuid']}"
    return config.get("lastKnownAccountUuid"), flag_scope


def resolve_source(env: Env, scopes: list[str], self_session: str, confirm: str | None) -> str:
    last_known, flag_scope = cached_scope(env)
    fresh = []
    for scope in scopes:
        record = scope_path(env, scope) / f"{self_session}.json"
        if record.exists() and env.now() - record.stat().st_mtime <= FRESH_SECONDS:
            fresh.append(scope)
    if flag_scope and last_known == flag_scope.split("/")[0] and fresh == [flag_scope]:
        return flag_scope
    if confirm:
        scope_path(env, confirm)
        if confirm not in scopes:
            raise SwitchError(f"{confirm} is not an account folder on this Mac")
        return confirm
    raise NeedsConfirmation(
        "source",
        {
            "evidence": {
                "lastKnownAccountUuid": last_known,
                "cachedScope": flag_scope,
                "freshlyWrittenScopes": fresh,
            },
            "candidates": [summarise(env, scope) for scope in scopes],
        },
    )


def resolve_target(env: Env, scopes, source, target_email, confirm, accounts) -> tuple[str, bool]:
    known = [scope for scope, info in accounts.items() if info.get("email", "").lower() == target_email.lower()]
    if known:
        scope = known[0]
        if scope == source:
            raise Refused(f"{target_email} is the signed-in account")
        scope_path(env, scope)
        if scope not in scopes:
            raise SwitchError(f"{target_email} was recorded for {scope}, which no longer exists on this Mac")
        return scope, False
    labelled = set(accounts)
    candidates = [scope for scope in scopes if scope != source and scope not in labelled]
    if confirm:
        scope_path(env, confirm)
        if confirm == source:
            raise SwitchError("the target cannot be the signed-in account")
        if confirm not in candidates:
            raise SwitchError(f"{confirm} is not an unlabelled account folder on this Mac")
        return confirm, True
    if not candidates:
        raise SwitchError(
            f"no account on this Mac is unlabelled, so {target_email} can't be matched. "
            "Sign in to that account once in the app, sign back in here, then run this again."
        )
    raise NeedsConfirmation(
        "target", {"targetEmail": target_email, "candidates": [summarise(env, scope) for scope in candidates]}
    )


# --- preview -------------------------------------------------------------------------------------

KNOWN_ENTRIES = ("scheduled-tasks.json", "archived-sessions.idx", "waiting-input", "backlog")


def transcript_index(env: Env) -> set[str]:
    return {path.stem for path in (env.claude_home / "projects").glob("*/*.jsonl")}


def preview(env: Env, source: str, target: str) -> dict:
    if source == target:
        raise SwitchError("the source and target are the same account")
    source_dir, target_dir = scope_path(env, source), scope_path(env, target)
    source_records, target_records = read_records(source_dir), read_records(target_dir)
    transcripts = transcript_index(env)
    problems = {"missingTranscripts": [], "transcriptUnavailable": [], "brokenParents": []}
    for record in source_records.values():
        title = record.get("title") or record["sessionId"]
        if record.get("transcriptUnavailable") is True and not record.get("cliSessionId"):
            problems["transcriptUnavailable"].append(title)
        elif record.get("cliSessionId") not in transcripts:
            problems["missingTranscripts"].append(title)
        parent = (record.get("spawnedFrom") or {}).get("sessionId")
        if parent and parent not in source_records:
            problems["brokenParents"].append(title)
    groups = group_scopes(env)
    queued = target_dir / "waiting-input"
    backlog = read_json(target_dir / "backlog/tasks.json", {}) or {}
    not_copied = [
        path.name
        for path in sorted(source_dir.iterdir())
        if not (path.name.startswith(("local_", "deleted_")) or path.name in KNOWN_ENTRIES)
    ]
    return {
        "source": summarise(env, source),
        "target": {
            **summarise(env, target),
            "queuedInput": sorted(path.name for path in queued.iterdir()) if queued.is_dir() else [],
            "backlogItems": len(backlog.get("items") or []),
        },
        "copy": len(source_records),
        "remove": [
            {"sessionId": session_id, "title": record.get("title")}
            for session_id, record in target_records.items()
            if session_id not in source_records
        ],
        "scheduledTasks": {
            "source": len((read_json(source_dir / "scheduled-tasks.json", {}) or {}).get("scheduledTasks") or []),
            "target": len((read_json(target_dir / "scheduled-tasks.json", {}) or {}).get("scheduledTasks") or []),
        },
        "groups": {
            "source": len((groups.get(source) or {}).get("groups") or []),
            "target": len((groups.get(target) or {}).get("groups") or []),
        },
        "notCopied": not_copied,
        "problems": problems,
        "targetFingerprint": fingerprint(target_dir),
    }


# --- sidebar groups ------------------------------------------------------------------------------


def group_scopes(env: Env, config_path: Path | None = None) -> dict:
    config = read_json(config_path or env.desktop_config)
    if config is None:
        raise SwitchError(f"{config_path or env.desktop_config} is missing; the app's layout has changed")
    prefs = (config.get("preferences") or {}).get("epitaxyPrefs")
    if not isinstance(prefs, dict):
        raise SwitchError("the app's sidebar preferences (epitaxyPrefs) were not found; its layout has changed")
    return prefs.get(GROUP_SCOPES) or {}


def write_group_entry(env: Env, scope: str, value) -> None:
    config = read_json(env.desktop_config)
    scopes = config["preferences"]["epitaxyPrefs"].setdefault(GROUP_SCOPES, {})
    if value is None:
        scopes.pop(scope, None)
    else:
        scopes[scope] = value
    write_json_atomic(env.desktop_config, config)


# --- operations ----------------------------------------------------------------------------------


def operation_dir(env: Env, operation_id: str) -> Path:
    return env.operations / operation_id


def read_journal(env: Env, operation_id: str) -> dict:
    return read_json(operation_dir(env, operation_id) / "journal.json")


def write_journal(env: Env, operation_id: str, journal: dict) -> None:
    write_json_atomic(operation_dir(env, operation_id) / "journal.json", journal)


def list_operations(env: Env) -> list[tuple[str, dict]]:
    if not env.operations.is_dir():
        return []
    found = []
    for path in sorted(env.operations.iterdir()):
        journal = read_json(path / "journal.json")
        if journal:
            found.append((path.name, journal))
    return found


def new_operation(env: Env, journal: dict) -> str:
    env.operations.mkdir(parents=True, exist_ok=True)
    while True:
        # Microseconds keep identifiers in creation order; the random suffix keeps them unique.
        operation_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + secrets.token_hex(3)
        try:
            operation_dir(env, operation_id).mkdir()
            break
        except FileExistsError:
            continue
    write_journal(env, operation_id, {"id": operation_id, "created": iso(env.now()), **journal})
    return operation_id


def refuse_if_interrupted(env: Env) -> None:
    for operation_id, journal in list_operations(env):
        if journal["state"] in ("applying", "recovering"):
            raise Refused(
                f"operation {operation_id} was interrupted while changing data. Quit the app and run "
                f"`python3 -I '{SCRIPT}' apply` in Terminal to finish or roll it back first."
            )


class Lock:
    def __init__(self, env: Env):
        self.path = env.state_root / "lock"

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                try:
                    holder = int(self.path.read_text().strip() or 0)
                except (OSError, ValueError):
                    holder = 0
                if holder and process_alive(holder):
                    raise Refused(f"another account switch (process {holder}) is running")
                print(f"Replacing a stale lock left by process {holder or 'unknown'}.", file=sys.stderr)
                self.path.unlink(missing_ok=True)
                continue
            with os.fdopen(descriptor, "w") as handle:
                handle.write(str(os.getpid()))
            return self
        raise Refused("could not take the account-switch lock")

    def __exit__(self, *exception):
        self.path.unlink(missing_ok=True)


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


# --- backup --------------------------------------------------------------------------------------


def backup(env: Env, operation_id: str, kind: str, scopes: list[str], target: str, allow_full_copy: bool) -> Path:
    started = time.monotonic()
    folder = env.backups / operation_id
    remove(folder)
    folder.mkdir(parents=True)
    manifest = {"operation": operation_id, "kind": kind, "created": iso(env.now()), "target": target, "complete": False}
    write_json_atomic(folder / "manifest.json", manifest)
    hashes = {}
    for scope in scopes:
        shutil.copytree(scope_path(env, scope), folder / "sessions" / scope, symlinks=True)
        hashes[scope] = file_hashes(folder / "sessions" / scope)
    for config in (env.desktop_config, env.app_config):
        if config.exists():
            (folder / "app").mkdir(exist_ok=True)
            shutil.copy2(config, folder / "app" / config.name)
    (folder / "claude").mkdir()
    if (env.claude_home / "CLAUDE.md").exists():
        shutil.copy2(env.claude_home / "CLAUDE.md", folder / "claude/CLAUDE.md")
    if (env.claude_home / "scheduled-tasks").is_dir():
        shutil.copytree(env.claude_home / "scheduled-tasks", folder / "claude/scheduled-tasks", symlinks=True)
    projects = env.claude_home / "projects"
    method = "absent"
    if projects.is_dir():
        try:
            env.clone(projects, folder / "claude/projects")
            method = "clone"
        except CloneUnsupported:
            if not allow_full_copy:
                remove(folder)
                raise CloneUnsupported(
                    "this disk can't clone files, so backing up ~/.claude/projects means a full copy. "
                    "Re-run with --allow-full-copy to accept that."
                )
            shutil.copytree(projects, folder / "claude/projects", symlinks=True)
            method = "copy"
    manifest.update(
        complete=True,
        scopes=hashes,
        projects=method,
        includes=sorted(str(path.relative_to(folder)) for path in folder.iterdir()),
        measuredSeconds=round(time.monotonic() - started, 2),
    )
    write_json_atomic(folder / "manifest.json", manifest)
    return folder


def complete_backups(env: Env) -> list[Path]:
    if not env.backups.is_dir():
        return []
    return sorted(
        (path for path in env.backups.iterdir() if (read_json(path / "manifest.json", {}) or {}).get("complete")),
        key=lambda path: path.name,
    )


def prune(env: Env) -> list[str]:
    protected = {operation_id for operation_id, journal in list_operations(env) if journal["state"] in PENDING_STATES}
    removable = [path for path in complete_backups(env) if path.name not in protected]
    pruned = removable[:-KEEP_BACKUPS] if len(removable) > KEEP_BACKUPS else []
    for path in pruned:
        remove(path)
    return [path.name for path in pruned]


# --- staging -------------------------------------------------------------------------------------


def stage_apply(source_dir: Path, staging: Path) -> None:
    staging.mkdir(parents=True)
    archived = []
    for path in sorted(source_dir.iterdir()):
        name = path.name
        if name.startswith("local_") and name.endswith(".json"):
            record = json.loads(path.read_text())
            for key in ACCOUNT_BOUND_FIELDS:
                record.pop(key, None)
            (staging / name).write_text(json.dumps(record))
            # Keep the original time, but never one recent enough to pass for the app's own live write:
            # that freshness is how the signed-in account is recognised (resolve_source).
            modified = min(path.stat().st_mtime, time.time() - FRESH_SECONDS - 60)
            os.utime(staging / name, (modified, modified))
            if record.get("isArchived"):
                archived.append(record["sessionId"])
        elif name.startswith("deleted_") or name == "scheduled-tasks.json":
            if path.is_dir():
                shutil.copytree(path, staging / name, symlinks=True)
            else:
                shutil.copy2(path, staging / name)
        elif name == "backlog" and path.is_dir():
            shutil.copytree(path, staging / name, symlinks=True)
    (staging / "archived-sessions.idx").write_text(json.dumps({"v": 1, "archived": sorted(archived)}))
    (staging / "waiting-input").mkdir()


def quarantine_queue(backup_folder: Path, target: str) -> None:
    queued = backup_folder / "sessions" / target / "waiting-input"
    if queued.is_dir() and any(queued.iterdir()):
        shutil.copytree(queued, backup_folder / "quarantine/waiting-input")


# --- the transaction engine ----------------------------------------------------------------------


def verify(env: Env, operation_id: str) -> None:
    journal = read_journal(env, operation_id)
    live = scope_path(env, journal["target"])
    if file_hashes(live) != journal["expected"]:
        raise SwitchError("the target account folder does not match what was staged")
    if group_scopes(env).get(journal["target"]) != journal["expectedGroups"]:
        raise SwitchError("the target account's sidebar groups do not match the source")
    if journal.get("source"):
        manifest = read_json(env.backups / operation_id / "manifest.json")
        if file_hashes(scope_path(env, journal["source"])) != manifest["scopes"][journal["source"]]:
            raise SwitchError("the source account folder changed during the switch")


def run_engine(env: Env, operation_id: str, stage: Callable[[Path], None], expected_groups, allow_full_copy: bool):
    """Back up, stage, commit, verify. Rolls back on any error after the commit starts."""
    folder = operation_dir(env, operation_id)
    journal = read_journal(env, operation_id)
    target = journal["target"]
    scopes = [scope for scope in (journal.get("source"), target) if scope]
    remove(folder / "staging")
    backup_folder = backup(env, operation_id, journal["kind"], scopes, target, allow_full_copy)
    quarantine_queue(backup_folder, target)
    env.checkpoint("backup-done")
    stage(folder / "staging")
    env.checkpoint("staged")
    journal.update(expected=file_hashes(folder / "staging"), expectedGroups=expected_groups)
    live = scope_path(env, target)
    actions = {
        "move-live-out": lambda: os.rename(live, folder / "pre"),
        "move-staged-in": lambda: os.rename(folder / "staging", live),
        "write-config": lambda: write_group_entry(env, target, expected_groups),
        "verify": lambda: verify(env, operation_id),
    }
    try:
        for step in COMMIT_STEPS:
            journal.update(state="applying", step=step)
            write_journal(env, operation_id, journal)
            env.checkpoint(f"before:{step}")
            actions[step]()
            env.checkpoint(f"after:{step}")
    except Exception as error:
        rollback(env, operation_id)
        raise SwitchError(f"the switch failed and was rolled back: {error}") from error
    finish(env, operation_id)


def finish(env: Env, operation_id: str) -> None:
    journal = read_journal(env, operation_id)
    journal.update(state="complete", finished=iso(env.now()))
    write_journal(env, operation_id, journal)
    folder = operation_dir(env, operation_id)
    remove(folder / "pre")
    remove(folder / "staging")
    prune(env)


def rollback(env: Env, operation_id: str) -> None:
    journal = read_journal(env, operation_id)
    journal["state"] = "recovering"
    write_journal(env, operation_id, journal)
    folder = operation_dir(env, operation_id)
    live = scope_path(env, journal["target"])
    if (folder / "pre").exists():
        if live.exists():
            remove(folder / "discarded")
            os.rename(live, folder / "discarded")
        os.rename(folder / "pre", live)
    elif not live.exists():
        shutil.copytree(env.backups / operation_id / "sessions" / journal["target"], live, symlinks=True)
    if journal.get("step") in ("write-config", "verify"):
        saved = group_scopes(env, env.backups / operation_id / "app" / env.desktop_config.name)
        write_group_entry(env, journal["target"], saved.get(journal["target"]))
    remove(folder / "discarded")
    remove(folder / "staging")
    journal.update(state="rolled-back", finished=iso(env.now()))
    write_journal(env, operation_id, journal)


def reconcile(env: Env) -> list[str]:
    reports = []
    for operation_id, journal in list_operations(env):
        state = journal["state"]
        if state == "preparing":
            remove(operation_dir(env, operation_id) / "staging")
            journal["state"] = "cancelled"
            write_journal(env, operation_id, journal)
        elif state in ("applying", "recovering"):
            if state == "applying" and journal.get("step") == "verify":
                try:
                    verify(env, operation_id)
                except SwitchError:
                    rollback(env, operation_id)
                    reports.append(f"{operation_id}: interrupted during verification and rolled back")
                else:
                    finish(env, operation_id)
                    reports.append(f"{operation_id}: interrupted during verification; verified and completed")
            else:
                rollback(env, operation_id)
                reports.append(f"{operation_id}: interrupted at '{journal.get('step')}' and rolled back")
    return reports


def start_transaction(env: Env) -> None:
    if env.app_running():
        raise Refused("quit the Claude app first (Cmd+Q), then run this again")
    reports = reconcile(env)
    if reports:
        raise Reconciled(
            "An interrupted operation was reconciled:\n  "
            + "\n  ".join(reports)
            + "\nNothing else was done. Start the switch or restore again."
        )


# --- commands ------------------------------------------------------------------------------------


def identify(env: Env, args, accounts: dict) -> tuple[str, str, bool]:
    refuse_if_interrupted(env)
    scopes = discover_scopes(env)
    source = resolve_source(env, scopes, args.self_session, args.confirm_source)
    target, newly_labelled = resolve_target(env, scopes, source, args.target_email, args.confirm_target, accounts)
    return source, target, newly_labelled


def command_preview(env: Env, args) -> int:
    source, target, _ = identify(env, args, load_accounts(env))
    report = preview(env, source, target)
    report["source"]["email"] = args.source_email
    report["target"]["email"] = args.target_email
    print(json.dumps(report, indent=2))
    return 0


def command_arm(env: Env, args) -> int:
    accounts = load_accounts(env)
    source, target, _ = identify(env, args, accounts)
    report = preview(env, source, target)
    label(accounts, source, args.source_email, env.now())
    label(accounts, target, args.target_email, env.now())
    save_accounts(env, accounts)
    for operation_id, journal in list_operations(env):
        if journal["state"] == "armed":
            journal["state"] = "cancelled"
            write_journal(env, operation_id, journal)
    operation_id = new_operation(
        env,
        {
            "kind": "apply",
            "state": "armed",
            "source": source,
            "target": target,
            "sourceEmail": args.source_email,
            "targetEmail": args.target_email,
            "targetFingerprint": report["targetFingerprint"],
            "sourceSessions": report["copy"],
        },
    )
    command = f"python3 -I '{SCRIPT}' apply"
    print(json.dumps({"operation": operation_id, "applyCommand": command, "preview": report}, indent=2))
    return 0


def command_apply(env: Env, args) -> int:
    with Lock(env):
        start_transaction(env)
        armed = [(operation_id, journal) for operation_id, journal in list_operations(env)
                 if journal["state"] == "armed" and journal["kind"] == "apply"]
        if not armed:
            raise SwitchError("nothing is armed. Run /session:account-switch <email address> in the app first.")
        operation_id, journal = armed[-1]
        last_known, flag_scope = cached_scope(env)
        if last_known != journal["source"].split("/")[0] or flag_scope != journal["source"]:
            raise Refused("the signed-in account changed since the switch was armed. Run the skill again in the app.")
        report = preview(env, journal["source"], journal["target"])
        if report["targetFingerprint"] != journal["targetFingerprint"]:
            raise Refused("the target account's sessions changed since the preview. Run the skill again in the app.")
        if report["copy"] != journal["sourceSessions"]:
            print(f"The source now has {report['copy']} sessions (was {journal['sourceSessions']} at preview).")
        source_dir = scope_path(env, journal["source"])
        groups = group_scopes(env).get(journal["source"])
        run_engine(env, operation_id, lambda staging: stage_apply(source_dir, staging), groups, args.allow_full_copy)
    print(
        f"Done: {report['copy']} sessions mirrored onto {journal['targetEmail']}, "
        f"{len(report['remove'])} removed from its sidebar (kept in the backup).\n"
        f"Next: sign out in the app, then sign in as {journal['targetEmail']}.\n"
        "Not carried over: Remote Control, per-session connector toggles, per-account settings."
    )
    if not args.no_reopen:
        env.reopen_app()
    return 0


def recover_shared_files(env: Env, backup_folder: Path, target: str, transcripts: bool) -> list[str]:
    recovered = []
    restored_dir = scope_path(env, target)
    tasks = (read_json(restored_dir / "scheduled-tasks.json", {}) or {}).get("scheduledTasks") or []
    tasks_root = env.claude_home / "scheduled-tasks"
    for task in tasks:
        path = Path(task.get("filePath") or "")
        try:
            relative = path.relative_to(tasks_root)
        except ValueError:
            continue
        saved = backup_folder / "claude/scheduled-tasks" / relative
        if not path.exists() and saved.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(saved, path)
            recovered.append(str(path))
    if not (env.claude_home / "CLAUDE.md").exists() and (backup_folder / "claude/CLAUDE.md").exists():
        shutil.copy2(backup_folder / "claude/CLAUDE.md", env.claude_home / "CLAUDE.md")
        recovered.append(str(env.claude_home / "CLAUDE.md"))
    if transcripts:
        present = transcript_index(env)
        for record in read_records(restored_dir).values():
            cli = record.get("cliSessionId")
            if not cli or cli in present:
                continue
            for saved in (backup_folder / "claude/projects").glob(f"*/{cli}.jsonl"):
                destination = env.claude_home / "projects" / saved.parent.name / saved.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(saved, destination)
                companion = saved.with_suffix("")
                if companion.is_dir() and not destination.with_suffix("").exists():
                    shutil.copytree(companion, destination.with_suffix(""), symlinks=True)
                recovered.append(str(destination))
                break
    return recovered


def command_restore(env: Env, args) -> int:
    with Lock(env):
        start_transaction(env)
        backups = complete_backups(env)
        if args.operation:
            chosen = [path for path in backups if path.name == args.operation]
            if not chosen:
                raise SwitchError(f"no complete backup named {args.operation}")
            backup_folder = chosen[0]
        elif backups:
            backup_folder = backups[-1]
        else:
            raise SwitchError("there are no complete backups to restore")
        manifest = read_json(backup_folder / "manifest.json")
        target = manifest["target"]
        saved_dir = backup_folder / "sessions" / target
        saved_groups = group_scopes(env, backup_folder / "app" / env.desktop_config.name).get(target)
        live_count = len(read_records(scope_path(env, target)))
        print(
            f"Restore {target} from backup {backup_folder.name}: {len(read_records(saved_dir))} sessions "
            f"(now {live_count}). Only this account's sessions and sidebar groups change."
        )
        if not args.yes and input("Type yes to restore: ").strip().lower() != "yes":
            print("Nothing changed.")
            return 0
        operation_id = new_operation(
            env, {"kind": "restore", "state": "preparing", "source": None, "target": target,
                  "restoreFrom": backup_folder.name},
        )

        def stage(staging: Path) -> None:
            shutil.copytree(saved_dir, staging, symlinks=True)

        run_engine(env, operation_id, stage, saved_groups, args.allow_full_copy)
        recovered = recover_shared_files(env, backup_folder, target, args.recover_missing_transcripts)
    print(f"Restored {target} from {backup_folder.name}.")
    for path in recovered:
        print(f"  recovered {path}")
    if not args.no_reopen:
        env.reopen_app()
    return 0


def command_status(env: Env, args) -> int:
    print(
        json.dumps(
            {
                "operations": [
                    {"id": operation_id, "kind": journal.get("kind"), "state": journal["state"],
                     "target": journal.get("target"), "targetEmail": journal.get("targetEmail")}
                    for operation_id, journal in list_operations(env)
                ],
                "backups": [path.name for path in complete_backups(env)],
                "accounts": load_accounts(env),
            },
            indent=2,
        )
    )
    return 0


def email(value: str) -> str:
    if not EMAIL.match(value):
        raise argparse.ArgumentTypeError(f"{value!r} is not an email address")
    return value


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="account_switch.py", description=__doc__.splitlines()[0])
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("preview", "arm"):
        command = commands.add_parser(name)
        command.add_argument("--target-email", required=True)
        command.add_argument("--source-email", required=True)
        command.add_argument("--self-session", required=True)
        command.add_argument("--confirm-source")
        command.add_argument("--confirm-target")
    apply = commands.add_parser("apply")
    apply.add_argument("--allow-full-copy", action="store_true")
    apply.add_argument("--no-reopen", action="store_true")
    restore = commands.add_parser("restore")
    restore.add_argument("operation", nargs="?")
    restore.add_argument("--yes", action="store_true")
    restore.add_argument("--recover-missing-transcripts", action="store_true")
    restore.add_argument("--allow-full-copy", action="store_true")
    restore.add_argument("--no-reopen", action="store_true")
    commands.add_parser("status")
    return root


def main(argv: list[str] | None = None, env: Env | None = None) -> int:
    args = parser().parse_args(argv)
    env = env or Env(home=Path.home())
    handlers = {
        "preview": command_preview,
        "arm": command_arm,
        "apply": command_apply,
        "restore": command_restore,
        "status": command_status,
    }
    try:
        if args.command in ("preview", "arm"):
            for value in (args.target_email, args.source_email):
                if not EMAIL.match(value):
                    raise SwitchError(f"{value!r} is not an email address. Usage: /session:account-switch <email address>")
            if args.target_email.lower() == args.source_email.lower():
                raise Refused(f"{args.target_email} is the signed-in account; name the account to switch to")
        return handlers[args.command](env, args)
    except NeedsConfirmation as error:
        print(json.dumps(error.payload, indent=2))
        return error.exit_code
    except SwitchError as error:
        print(f"account-switch: {error}", file=sys.stderr)
        return error.exit_code


if __name__ == "__main__":
    sys.exit(main())
