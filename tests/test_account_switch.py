"""The account switch mirrors every Claude desktop session from the signed-in account onto another account."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "session/skills/account-switch/scripts/account_switch.py"

SOURCE_ACCOUNT = "11111111-1111-4111-8111-111111111111"
SOURCE_ORG = "22222222-2222-4222-8222-222222222222"
TARGET_ACCOUNT = "33333333-3333-4333-8333-333333333333"
TARGET_ORG = "44444444-4444-4444-8444-444444444444"
THIRD_ACCOUNT = "55555555-5555-4555-8555-555555555555"
THIRD_ORG = "66666666-6666-4666-8666-666666666666"
SOURCE = f"{SOURCE_ACCOUNT}/{SOURCE_ORG}"
TARGET = f"{TARGET_ACCOUNT}/{TARGET_ORG}"
THIRD = f"{THIRD_ACCOUNT}/{THIRD_ORG}"
SELF = "local_aaaaaaaa-0000-4000-8000-000000000001"
SOURCE_EMAIL = "me@source.example"
TARGET_EMAIL = "me@target.example"


def load_module():
    spec = importlib.util.spec_from_file_location("account_switch", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Crash(BaseException):
    """Stands in for the process being killed: nothing catches it."""


class Home:
    """A fake home folder holding two (or three) Claude desktop accounts."""

    def __init__(self, root: Path, third_account: bool = False):
        self.root = root
        self.app = root / "Library/Application Support/Claude"
        self.sessions = self.app / "claude-code-sessions"
        self.claude = root / ".claude"
        self.build_source()
        self.build_target()
        if third_account:
            self.write_record(THIRD, "local_third-1", "Third account session", cli="cli-third-1")
        self.write_json(
            self.app / "config.json",
            {
                "lastKnownAccountUuid": SOURCE_ACCOUNT,
                "sshTransportFlagLastAnswer": {"accountUuid": SOURCE_ACCOUNT, "orgUuid": SOURCE_ORG},
            },
        )
        self.write_json(
            self.app / "claude_desktop_config.json",
            {
                "preferences": {
                    "keepAwakeEnabled": True,
                    "epitaxyPrefs": {
                        "starred-local-code-sessions": [SELF],
                        "dframe-group-scopes": {
                            SOURCE: {"groups": [{"id": "cg-1", "name": "Flow"}], "assignments": {SELF: "cg-1"}},
                            TARGET: {"groups": [{"id": "cg-old", "name": "Old"}], "assignments": {}},
                        },
                    },
                }
            },
        )
        (self.claude / "projects/-Users-seb-code-flow").mkdir(parents=True)
        for cli in ("cli-self", "cli-child"):
            (self.claude / "projects/-Users-seb-code-flow" / f"{cli}.jsonl").write_text('{"type":"user"}\n')
        (self.claude / "CLAUDE.md").write_text("# Global\n")
        task = self.claude / "scheduled-tasks/renewal-check/SKILL.md"
        task.parent.mkdir(parents=True)
        task.write_text("check renewal\n")
        self.freshen(SOURCE)

    def scope(self, scope: str) -> Path:
        return self.sessions / scope

    def write_json(self, path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    def write_record(self, scope, session_id, title, cli=None, **fields):
        record = {"sessionId": session_id, "title": title, "lastActivityAt": 1_700_000_000_000, **fields}
        if cli:
            record["cliSessionId"] = cli
        self.write_json(self.scope(scope) / f"{session_id}.json", record)
        return record

    def build_source(self):
        self.write_record(
            SOURCE,
            SELF,
            "Flow main",
            cli="cli-self",
            bridgeSessionIds=["session_x"],
            remoteControlUserEnabled=True,
            enabledMcpTools={"tool": True},
            remoteMcpServersConfig=[{"uuid": "connector"}],
            connectorWireNames={"a": "b"},
            isStarred=True,
            model="claude-opus-5-5",
        )
        self.write_record(
            SOURCE,
            "local_child",
            "Flow child",
            cli="cli-child",
            isArchived=True,
            spawnedFrom={"sessionId": SELF},
        )
        self.write_record(SOURCE, "local_gone", "No history", transcriptUnavailable=True)
        self.write_record(SOURCE, "local_lost", "Missing transcript", cli="cli-missing")
        self.write_record(SOURCE, "local_orphan", "Orphan", cli="cli-self", spawnedFrom={"sessionId": "local_nowhere"})
        (self.scope(SOURCE) / "deleted_abc").write_text("1700000000000")
        self.write_json(
            self.scope(SOURCE) / "scheduled-tasks.json",
            {
                "scheduledTasks": [
                    {
                        "id": "renewal-check",
                        "filePath": str(self.claude / "scheduled-tasks/renewal-check/SKILL.md"),
                        "notifySessionId": SELF,
                        "enabled": True,
                    }
                ]
            },
        )
        (self.scope(SOURCE) / "waiting-input").mkdir()

    def build_target(self):
        self.write_record(TARGET, SELF, "Flow main (stale)", cli="cli-self")
        self.write_record(TARGET, "local_target_only", "Only on the target", cli="cli-self")
        (self.scope(TARGET) / "waiting-input").mkdir(parents=True)
        (self.scope(TARGET) / "waiting-input" / SELF).write_text("stale queued input")
        self.write_json(self.scope(TARGET) / "backlog/tasks.json", {"version": 1, "items": [{"id": "todo_1"}]})
        self.write_json(self.scope(TARGET) / "scheduled-tasks.json", {"scheduledTasks": []})
        self.write_json(self.scope(TARGET) / "archived-sessions.idx", {"v": 1, "archived": ["local_target_only"]})
        old = time.time() - 86_400
        for path in self.scope(TARGET).rglob("*"):
            os.utime(path, (old, old))

    def freshen(self, scope: str) -> None:
        now = time.time()
        os.utime(self.scope(scope) / f"{SELF}.json", (now, now))

    def records(self, scope: str) -> dict:
        return {
            path.stem: json.loads(path.read_text()) for path in sorted(self.scope(scope).glob("local_*.json"))
        }

    def groups(self) -> dict:
        data = json.loads((self.app / "claude_desktop_config.json").read_text())
        return data["preferences"]["epitaxyPrefs"]["dframe-group-scopes"]

    def snapshot(self, scope: str) -> dict:
        return {
            str(path.relative_to(self.scope(scope))): (path.read_bytes() if path.is_file() else b"<dir>")
            for path in sorted(self.scope(scope).rglob("*"))
        }


class SwitchTestCase(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.home = Home(Path(directory.name), third_account=getattr(self, "THIRD_ACCOUNT", False))
        self.running = False
        self.crash_at = None
        self.clone_supported = True
        self.reopened = 0

    def env(self):
        def clone(source, destination):
            if not self.clone_supported:
                raise self.module.CloneUnsupported("cloning is not supported on this disk")
            import shutil

            shutil.copytree(source, destination, symlinks=True)

        def checkpoint(name):
            if name == self.crash_at:
                raise Crash(name)

        def reopen():
            self.reopened += 1

        return self.module.Env(
            home=self.home.root,
            app_running=lambda: self.running,
            clone=clone,
            checkpoint=checkpoint,
            reopen_app=reopen,
        )

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = self.module.main(list(argv), env=self.env())
        self.out, self.err = out.getvalue(), err.getvalue()
        return code

    def json_out(self):
        return json.loads(self.out)

    def identity_args(self, target_email=TARGET_EMAIL, *extra):
        return [
            "--target-email",
            target_email,
            "--source-email",
            SOURCE_EMAIL,
            "--self-session",
            SELF,
            *extra,
        ]

    def arm(self, *extra):
        code = self.run_cli("arm", *self.identity_args(TARGET_EMAIL, "--confirm-target", TARGET, *extra))
        self.assertEqual(code, 0, self.err)
        return self.json_out()

    def apply(self, *extra):
        self.running = False
        return self.run_cli("apply", *extra)

    def operations(self):
        root = self.home.root / "claude/account-switch/operations"
        return {
            path.name: json.loads((path / "journal.json").read_text())
            for path in sorted(root.iterdir())
            if (path / "journal.json").exists()
        }


class DiscoveryTest(SwitchTestCase):
    def test_a_missing_target_email_stops_before_anything_is_read(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.module.main(["preview", "--source-email", SOURCE_EMAIL, "--self-session", SELF], env=self.env())

    def test_a_malformed_target_email_stops_even_with_one_other_account(self):
        code = self.run_cli("preview", *self.identity_args("not-an-email"))
        self.assertEqual(code, 2)
        self.assertIn("email address", self.err)

    def test_the_signed_in_accounts_own_email_is_refused(self):
        code = self.run_cli("preview", *self.identity_args(SOURCE_EMAIL))
        self.assertEqual(code, 5)

    def test_agreeing_evidence_establishes_the_source_scope(self):
        code = self.run_cli("preview", *self.identity_args(TARGET_EMAIL, "--confirm-target", TARGET))
        self.assertEqual(code, 0, self.err)
        self.assertEqual(self.json_out()["source"]["scope"], SOURCE)

    def test_shared_session_ids_do_not_decide_the_source(self):
        # The same identifier exists in both accounts; only the freshly written copy counts.
        self.home.freshen(TARGET)
        code = self.run_cli("preview", *self.identity_args())
        self.assertEqual(code, 3)
        self.assertEqual(self.json_out()["needsConfirmation"], "source")

    def test_stale_or_mismatched_hints_ask_for_confirmation(self):
        cases = {
            "stale last known account": {"lastKnownAccountUuid": TARGET_ACCOUNT},
            "stale feature flag": {"sshTransportFlagLastAnswer": {"accountUuid": TARGET_ACCOUNT, "orgUuid": TARGET_ORG}},
            "same account, other organisation": {
                "sshTransportFlagLastAnswer": {"accountUuid": SOURCE_ACCOUNT, "orgUuid": TARGET_ORG}
            },
        }
        for name, change in cases.items():
            with self.subTest(case=name):
                config_path = self.home.app / "config.json"
                original = config_path.read_text()
                config = json.loads(original)
                config.update(change)
                config_path.write_text(json.dumps(config))
                code = self.run_cli("arm", *self.identity_args(TARGET_EMAIL, "--confirm-target", TARGET))
                self.assertEqual(code, 3)
                self.assertFalse((self.home.root / "claude/account-switch/accounts.json").exists())
                config_path.write_text(original)

    def test_no_fresh_record_asks_for_confirmation_and_confirming_works(self):
        old = time.time() - 3600
        os.utime(self.home.scope(SOURCE) / f"{SELF}.json", (old, old))
        self.assertEqual(self.run_cli("preview", *self.identity_args()), 3)
        code = self.run_cli(
            "preview", *self.identity_args(TARGET_EMAIL, "--confirm-source", SOURCE, "--confirm-target", TARGET)
        )
        self.assertEqual(code, 0, self.err)

    def test_an_unknown_email_lists_unlabelled_accounts_and_confirming_records_it(self):
        code = self.run_cli("preview", *self.identity_args())
        self.assertEqual(code, 3)
        payload = self.json_out()
        self.assertEqual(payload["needsConfirmation"], "target")
        candidate = payload["candidates"][0]
        self.assertEqual(candidate["scope"], TARGET)
        self.assertEqual(candidate["sessions"], 2)
        self.assertIn("Only on the target", candidate["recentTitles"])
        self.arm()
        accounts = json.loads((self.home.root / "claude/account-switch/accounts.json").read_text())["accounts"]
        self.assertEqual(accounts[TARGET]["email"], TARGET_EMAIL)
        self.assertEqual(accounts[SOURCE]["email"], SOURCE_EMAIL)

    def test_a_known_email_resolves_without_asking(self):
        self.arm()
        code = self.run_cli("preview", *self.identity_args())
        self.assertEqual(code, 0, self.err)
        self.assertEqual(self.json_out()["target"]["scope"], TARGET)

    def test_paths_outside_the_sessions_folder_are_rejected(self):
        code = self.run_cli("preview", *self.identity_args(TARGET_EMAIL, "--confirm-target", "../../x/y"))
        self.assertEqual(code, 2)

    def test_the_source_cannot_be_the_target(self):
        code = self.run_cli("preview", *self.identity_args(TARGET_EMAIL, "--confirm-target", SOURCE))
        self.assertEqual(code, 2)


class ThreeAccountsTest(SwitchTestCase):
    THIRD_ACCOUNT = True

    def test_a_known_email_resolves_among_three_accounts(self):
        self.run_cli("arm", *self.identity_args("third@example.com", "--confirm-target", THIRD))
        code = self.run_cli("preview", *self.identity_args("third@example.com"))
        self.assertEqual(code, 0, self.err)
        self.assertEqual(self.json_out()["target"]["scope"], THIRD)

    def test_an_unknown_email_with_no_unlabelled_accounts_stops(self):
        self.run_cli("arm", *self.identity_args("third@example.com", "--confirm-target", THIRD))
        self.arm()
        code = self.run_cli("preview", *self.identity_args("new@example.com"))
        self.assertEqual(code, 2)
        self.assertIn("sign in", self.err.lower())


class PreviewTest(SwitchTestCase):
    def test_preview_writes_nothing_and_reports_problems(self):
        before = {path: path.stat().st_mtime_ns for path in self.home.root.rglob("*")}
        code = self.run_cli("preview", *self.identity_args(TARGET_EMAIL, "--confirm-target", TARGET))
        self.assertEqual(code, 0, self.err)
        self.assertEqual(before, {path: path.stat().st_mtime_ns for path in self.home.root.rglob("*")})
        report = self.json_out()
        self.assertEqual(report["copy"], 5)
        self.assertEqual([item["title"] for item in report["remove"]], ["Only on the target"])
        self.assertEqual(report["problems"]["missingTranscripts"], ["Missing transcript"])
        self.assertEqual(report["problems"]["transcriptUnavailable"], ["No history"])
        self.assertEqual(report["problems"]["brokenParents"], ["Orphan"])
        self.assertEqual(report["target"]["queuedInput"], [SELF])
        self.assertEqual(report["target"]["backlogItems"], 1)

    def test_an_invalid_record_stops_the_preview(self):
        (self.home.scope(SOURCE) / "local_bad.json").write_text("{not json")
        code = self.run_cli("preview", *self.identity_args(TARGET_EMAIL, "--confirm-target", TARGET))
        self.assertEqual(code, 2)


class ApplyTest(SwitchTestCase):
    def test_apply_mirrors_the_source_onto_the_target(self):
        source_before = self.home.snapshot(SOURCE)
        self.arm()
        self.assertEqual(self.apply(), 0, self.err)
        source, target = self.home.records(SOURCE), self.home.records(TARGET)
        self.assertEqual(set(source), set(target))
        for session_id, record in source.items():
            expected = {key: value for key, value in record.items() if key not in self.module.ACCOUNT_BOUND_FIELDS}
            self.assertEqual(target[session_id], expected)
        self.assertEqual(target["local_child"]["spawnedFrom"], {"sessionId": SELF})
        self.assertTrue(target[SELF]["isStarred"])
        scope = self.home.scope(TARGET)
        self.assertEqual(
            json.loads((scope / "scheduled-tasks.json").read_text()),
            json.loads((self.home.scope(SOURCE) / "scheduled-tasks.json").read_text()),
        )
        self.assertEqual(json.loads((scope / "archived-sessions.idx").read_text()), {"v": 1, "archived": ["local_child"]})
        self.assertTrue((scope / "deleted_abc").exists())
        self.assertEqual(list((scope / "waiting-input").iterdir()), [])
        self.assertFalse((scope / "backlog").exists())
        groups = self.home.groups()
        self.assertEqual(groups[TARGET], groups[SOURCE])
        config = json.loads((self.home.app / "claude_desktop_config.json").read_text())
        self.assertTrue(config["preferences"]["keepAwakeEnabled"])
        self.assertEqual(self.home.snapshot(SOURCE), source_before)
        self.assertEqual(self.reopened, 1)
        self.assertEqual(list(self.operations().values())[0]["state"], "complete")

    def test_the_backup_holds_the_full_inventory(self):
        self.arm()
        self.assertEqual(self.apply(), 0, self.err)
        backup = next((self.home.root / "claude/account-switch/backups").iterdir())
        manifest = json.loads((backup / "manifest.json").read_text())
        self.assertTrue(manifest["complete"])
        for part in (
            f"sessions/{SOURCE}",
            f"sessions/{TARGET}",
            "app/claude_desktop_config.json",
            "app/config.json",
            "claude/CLAUDE.md",
            "claude/scheduled-tasks/renewal-check/SKILL.md",
            "claude/projects/-Users-seb-code-flow/cli-self.jsonl",
        ):
            self.assertTrue((backup / part).exists(), part)
        self.assertEqual(manifest["projects"], "clone")
        self.assertTrue((backup / "quarantine/waiting-input" / SELF).exists())

    def test_apply_refuses_while_the_app_runs(self):
        self.arm()
        self.running = True
        self.assertEqual(self.run_cli("apply"), 5)
        self.assertEqual(list(self.operations().values())[0]["state"], "armed")

    def test_apply_refuses_when_the_signed_in_scope_changed(self):
        self.arm()
        config = json.loads((self.home.app / "config.json").read_text())
        config["sshTransportFlagLastAnswer"]["orgUuid"] = TARGET_ORG
        (self.home.app / "config.json").write_text(json.dumps(config))
        self.assertEqual(self.apply(), 5)
        self.assertEqual(list(self.operations().values())[0]["state"], "armed")

    def test_apply_refuses_when_the_target_changed_after_the_preview(self):
        self.arm()
        self.home.write_record(TARGET, "local_new_on_target", "New", cli="cli-self")
        self.assertEqual(self.apply(), 5)
        self.assertIn("changed", self.err)

    def test_a_live_lock_stops_and_a_stale_lock_is_replaced(self):
        self.arm()
        lock = self.home.root / "claude/account-switch/lock"
        lock.write_text(str(os.getpid()))
        self.assertEqual(self.apply(), 5)
        lock.write_text("999999")
        self.assertEqual(self.apply(), 0, self.err)
        self.assertIn("stale lock", self.out + self.err)

    def test_unsupported_cloning_stops_unless_a_full_copy_is_allowed(self):
        self.arm()
        self.clone_supported = False
        self.assertEqual(self.apply(), 6)
        self.assertEqual(list(self.operations().values())[0]["state"], "armed")
        self.assertEqual(self.apply("--allow-full-copy"), 0, self.err)

    def test_nothing_armed_means_nothing_to_apply(self):
        self.assertEqual(self.apply(), 2)


class InterruptionTest(SwitchTestCase):
    def test_a_crash_at_every_boundary_ends_in_the_old_or_the_new_state(self):
        for checkpoint in self.module.APPLY_CHECKPOINTS:
            with self.subTest(checkpoint=checkpoint):
                self.setUp()
                original = self.home.snapshot(TARGET)
                original_groups = self.home.groups()[TARGET]
                self.arm()
                self.crash_at = checkpoint
                with self.assertRaises(Crash):
                    self.apply()
                self.crash_at = None
                code = self.apply()
                states = [journal["state"] for journal in self.operations().values()]
                if code == 0:
                    # Crashed before anything live changed: the operation was still armed and applied now.
                    self.assertEqual(states, ["complete"])
                else:
                    self.assertEqual(code, 4, self.err)
                    self.assertIn(states, (["complete"], ["rolled-back"]))
                if states == ["complete"]:
                    self.assertEqual(set(self.home.records(TARGET)), set(self.home.records(SOURCE)))
                    self.assertEqual(self.home.groups()[TARGET], self.home.groups()[SOURCE])
                else:
                    self.assertEqual(self.home.snapshot(TARGET), original)
                    self.assertEqual(self.home.groups()[TARGET], original_groups)
                self.assertEqual(sorted(path.name for path in self.home.scope(TARGET).parent.iterdir()), [TARGET_ORG])

    def test_a_verification_failure_rolls_back(self):
        original = self.home.snapshot(TARGET)
        self.arm()

        def failing_verify(*args, **kwargs):
            raise self.module.SwitchError("verification failed")

        self.module.verify = failing_verify
        self.assertEqual(self.apply(), 2)
        self.assertEqual(self.home.snapshot(TARGET), original)
        self.assertEqual(list(self.operations().values())[0]["state"], "rolled-back")

    def test_an_interrupted_operation_blocks_arming_and_preview(self):
        self.arm()
        self.crash_at = "after:move-live-out"
        with self.assertRaises(Crash):
            self.apply()
        self.crash_at = None
        self.assertEqual(self.run_cli("preview", *self.identity_args()), 5)
        self.assertIn("apply", self.err)
        self.assertEqual(self.run_cli("arm", *self.identity_args()), 5)


class ArmingTest(SwitchTestCase):
    def test_two_arms_in_one_second_get_distinct_ids_and_only_armed_ones_are_cancelled(self):
        self.arm()
        self.arm()
        states = sorted(journal["state"] for journal in self.operations().values())
        self.assertEqual(states, ["armed", "cancelled"])
        self.assertEqual(len(self.operations()), 2)

    def test_arm_prints_the_apply_command(self):
        payload = self.arm()
        self.assertIn("apply", payload["applyCommand"])
        self.assertIn(str(SCRIPT), payload["applyCommand"])


class RetentionTest(SwitchTestCase):
    def test_only_the_newest_three_complete_backups_are_kept(self):
        for _ in range(4):
            self.arm()
            self.assertEqual(self.apply(), 0, self.err)
        backups = self.home.root / "claude/account-switch/backups"
        pending = backups / "29990101T000000Z-pending"
        pending.mkdir()
        (pending / "manifest.json").write_text(json.dumps({"complete": False}))
        self.arm()
        self.assertEqual(self.apply(), 0, self.err)
        complete = [path for path in backups.iterdir() if json.loads((path / "manifest.json").read_text())["complete"]]
        self.assertEqual(len(complete), 3)
        self.assertTrue(pending.exists())


class RestoreTest(SwitchTestCase):
    def switch(self):
        self.arm()
        self.assertEqual(self.apply(), 0, self.err)
        return sorted(path.name for path in (self.home.root / "claude/account-switch/backups").iterdir())[-1]

    def test_restore_puts_back_only_the_target_scope_and_its_groups(self):
        original = self.home.snapshot(TARGET)
        original_groups = self.home.groups()[TARGET]
        operation = self.switch()
        self.home.write_record(SOURCE, "local_newer", "Newer source work", cli="cli-self")
        self.assertEqual(self.run_cli("restore", operation, "--yes", "--no-reopen"), 0, self.err)
        self.assertEqual(self.home.snapshot(TARGET), original)
        self.assertEqual(self.home.groups()[TARGET], original_groups)
        self.assertIn("local_newer", self.home.records(SOURCE))

    def test_restore_never_overwrites_shared_files_and_recovers_missing_ones(self):
        operation = self.switch()
        (self.home.claude / "CLAUDE.md").write_text("# Newer\n")
        task = self.home.claude / "scheduled-tasks/renewal-check"
        import shutil

        shutil.rmtree(task)
        transcript = self.home.claude / "projects/-Users-seb-code-flow/cli-self.jsonl"
        transcript.write_text("newer\n")
        self.assertEqual(self.run_cli("restore", operation, "--yes", "--no-reopen"), 0, self.err)
        self.assertEqual((self.home.claude / "CLAUDE.md").read_text(), "# Newer\n")
        self.assertFalse((task / "SKILL.md").exists(), "restored target has no scheduled tasks")
        self.assertEqual(transcript.read_text(), "newer\n")

    def test_restore_recovers_missing_instructions_and_transcripts_on_request(self):
        # Restore a backup whose target had the source's sessions (a second switch), so tasks reference instructions.
        self.switch()
        second = self.switch()
        import shutil

        shutil.rmtree(self.home.claude / "scheduled-tasks/renewal-check")
        (self.home.claude / "projects/-Users-seb-code-flow/cli-child.jsonl").unlink()
        self.assertEqual(
            self.run_cli("restore", second, "--yes", "--no-reopen", "--recover-missing-transcripts"), 0, self.err
        )
        self.assertTrue((self.home.claude / "scheduled-tasks/renewal-check/SKILL.md").exists())
        self.assertTrue((self.home.claude / "projects/-Users-seb-code-flow/cli-child.jsonl").exists())

    def test_an_interrupted_restore_rolls_back_without_mixing_snapshots(self):
        self.module.KEEP_BACKUPS = 100  # restore from the same backup at every checkpoint
        operation = self.switch()
        for checkpoint in self.module.APPLY_CHECKPOINTS:
            with self.subTest(checkpoint=checkpoint):
                before = self.home.snapshot(TARGET)
                before_groups = self.home.groups()[TARGET]
                self.crash_at = checkpoint
                with self.assertRaises(Crash):
                    self.run_cli("restore", operation, "--yes", "--no-reopen")
                self.crash_at = None
                # The next run of either command reconciles first.
                self.apply()
                latest = list(self.operations().values())[-1]["state"]
                self.assertIn(latest, ("complete", "rolled-back", "cancelled"))
                if latest != "complete":
                    self.assertEqual(self.home.snapshot(TARGET), before)
                    self.assertEqual(self.home.groups()[TARGET], before_groups)

    def test_apply_and_restore_share_the_lock(self):
        operation = self.switch()
        lock = self.home.root / "claude/account-switch/lock"
        lock.write_text(str(os.getpid()))
        self.assertEqual(self.run_cli("restore", operation, "--yes", "--no-reopen"), 5)
        self.arm()
        self.assertEqual(self.apply(), 5)


class PackageContractTest(unittest.TestCase):
    def test_the_skill_is_claude_only(self):
        self.assertTrue((ROOT / "session/skills/account-switch/SKILL.md").is_file())
        self.assertFalse((ROOT / "plugins/session/skills/account-switch").exists())

    def test_the_skill_requires_the_target_email(self):
        contents = (ROOT / "session/skills/account-switch/SKILL.md").read_text()
        self.assertIn("--target-email", contents)
        self.assertIn("python3 -I", contents)
        self.assertNotIn("/Users/", contents)


if __name__ == "__main__":
    unittest.main()
