"""Executable packaging checks; all Git mutations use disposable fixtures."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "plugins/worktree"
CANONICAL = ROOT / "worktree/scripts/worktree.sh"
SYNC = ROOT / "scripts/sync-codex-worktree.py"


class WorktreePackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="codex-worktree-test-")
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name).resolve()
        self.environment = dict(os.environ)
        self.environment.update({
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_AUTHOR_NAME": "Fixture",
            "GIT_AUTHOR_EMAIL": "fixture@example.test",
            "GIT_COMMITTER_NAME": "Fixture",
            "GIT_COMMITTER_EMAIL": "fixture@example.test",
        })

    def run_command(self, command, cwd=None, payload=None, success=True):
        result = subprocess.run(
            [str(argument) for argument in command],
            cwd=cwd or self.workspace,
            env=self.environment,
            input=payload,
            capture_output=True,
            text=True,
        )
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def repository(self, name="application"):
        repository = self.workspace / name
        repository.mkdir()
        self.run_command(["git", "init", "-q", "-b", "main"], repository)
        (repository / "tracked.txt").write_text("original\n")
        self.run_command(["git", "add", "."], repository)
        self.run_command(["git", "commit", "-qm", "Initial fixture"], repository)
        self.run_command(["git", "branch", "develop"], repository)
        return repository

    def install(self):
        destination = self.workspace / "installed plugins/worktree"
        self.assertTrue(PACKAGE.is_dir(), "native worktree package is missing")
        shutil.copytree(PACKAGE, destination)
        return destination

    def runtime(self, installed, repository, *arguments, payload=None, success=True):
        return self.run_command(
            ["bash", installed / "scripts/worktree.sh", *arguments],
            repository,
            payload=payload,
            success=success,
        )

    def snapshot(self, repository):
        return tuple(self.run_command(["git", *arguments], repository).stdout for arguments in (
            ["status", "--porcelain"],
            ["rev-parse", "HEAD"],
            ["branch", "--show-current"],
        ))

    def test_runtime_is_identical_and_executable(self):
        packaged = PACKAGE / "scripts/worktree.sh"
        self.assertTrue(packaged.is_file(), "packaged shell runtime is missing")
        self.assertEqual(packaged.read_bytes(), CANONICAL.read_bytes())
        self.assertTrue(os.access(packaged, os.X_OK))
        self.assertFalse(packaged.is_symlink())

    def test_skills_resolve_runtime_inside_an_independent_install(self):
        installed = self.install()
        for skill_name in ("create", "init", "list", "remove"):
            skill = installed / "skills" / skill_name / "SKILL.md"
            self.assertTrue(skill.is_file(), f"missing {skill_name} skill")
            links = re.findall(r"\]\(([^)]+)\)", skill.read_text())
            runtime_links = [link for link in links if link.endswith("scripts/worktree.sh")]
            self.assertTrue(runtime_links, f"{skill_name} lacks a package-relative runtime reference")
            for link in runtime_links:
                target = (skill.parent / link).resolve()
                self.assertTrue(target.is_relative_to(installed))
                self.assertTrue(target.is_file())
                result = self.run_command(["bash", target, "--help"])
                self.assertIn("worktree.sh create", result.stdout)

    def test_sync_check_and_repair_are_deterministic(self):
        fixture = self.workspace / "source"
        source = fixture / "worktree/scripts/worktree.sh"
        packaged = fixture / "plugins/worktree/scripts/worktree.sh"
        helper = fixture / "scripts/sync-codex-worktree.py"
        source.parent.mkdir(parents=True)
        helper.parent.mkdir(parents=True)
        source.write_bytes(CANONICAL.read_bytes())
        source.chmod(0o755)
        self.assertTrue(SYNC.is_file(), "runtime synchronization helper is missing")
        shutil.copy2(SYNC, helper)
        self.run_command([sys.executable, helper, "--check"], success=False)
        self.run_command([sys.executable, helper])
        first_stat = packaged.stat()
        self.assertEqual(packaged.read_bytes(), source.read_bytes())
        self.assertTrue(os.access(packaged, os.X_OK))
        self.run_command([sys.executable, helper, "--check"])
        self.run_command([sys.executable, helper])
        self.assertEqual(packaged.stat().st_mtime_ns, first_stat.st_mtime_ns)
        packaged.write_text("stale runtime\n")
        self.run_command([sys.executable, helper, "--check"], success=False)
        self.assertEqual(packaged.read_text(), "stale runtime\n")
        self.run_command([sys.executable, helper])
        self.assertEqual(packaged.read_bytes(), source.read_bytes())

    def test_plain_install_preserves_original_checkout(self):
        installed = self.install()
        repository = self.repository()
        (repository / "tracked.txt").write_text("unfinished source work\n")
        before = self.snapshot(repository)
        created = json.loads(self.runtime(installed, repository, "create", "alpha", "--json").stdout)
        self.assertEqual(created["branch"], "wt/alpha")
        self.assertEqual(created["base"], "develop")
        self.assertEqual(Path(created["path"]), self.workspace / "application-worktrees/alpha")
        self.assertEqual((Path(created["path"]) / "tracked.txt").read_text(), "original\n")
        self.assertEqual(created["bootstrap"], dict.fromkeys(("env", "composer", "npm", "postSetup"), "skipped"))
        removed = json.loads(self.runtime(installed, repository, "remove", "alpha", "--delete-branch", "--json").stdout)
        self.assertTrue(removed["branchDeleted"])
        self.assertEqual(self.snapshot(repository), before)

    def test_supported_config_prefix_and_flags_override_conventions(self):
        installed = self.install()
        repository = self.repository()
        settings = {"branchPrefix": "plan/", "baseBranch": "main", "bootstrap": {"copyEnv": False}}
        self.runtime(installed, repository, "config", "--write", payload=json.dumps(settings))
        before = self.snapshot(repository)
        config_before = (repository / ".worktree.json").read_bytes()
        destination = self.workspace / "custom destination"
        created = json.loads(self.runtime(
            installed, repository, "create", "configured", "--from", "develop", "--dest", destination, "--json",
        ).stdout)
        self.assertEqual(created["branch"], "plan/configured")
        self.assertEqual(created["base"], "develop")
        self.assertEqual(Path(created["path"]), destination / "configured")
        self.assertEqual((repository / ".worktree.json").read_bytes(), config_before)
        self.runtime(installed, repository, "remove", "configured", "--delete-branch", "--json")
        self.assertEqual(self.snapshot(repository), before)
        settings["branchPrefix"] = "codex/"
        self.runtime(installed, repository, "config", "--write", payload=json.dumps(settings))
        native = json.loads(self.runtime(installed, repository, "create", "native", "--json").stdout)
        self.assertEqual(native["branch"], "codex/native")
        self.runtime(installed, repository, "remove", "native", "--delete-branch", "--json")

    def test_dirty_unmerged_and_unmanaged_removal_guards(self):
        installed = self.install()
        repository = self.repository()
        created = json.loads(self.runtime(installed, repository, "create", "guarded", "--json").stdout)
        target = Path(created["path"])
        (target / "tracked.txt").write_text("uncommitted work\n")
        dirty = self.runtime(installed, repository, "remove", "guarded", "--json", success=False)
        self.assertIn("uncommitted changes", dirty.stderr)
        self.assertTrue(target.is_dir())
        self.run_command(["git", "commit", "-qam", "Unmerged fixture"], target)
        unmerged = self.runtime(installed, repository, "remove", "guarded", "--delete-branch", "--json", success=False)
        self.assertIn("not merged into 'develop'", unmerged.stderr)
        listed = json.loads(self.runtime(installed, repository, "list", "--json").stdout)
        entry = next(entry for entry in listed if entry["path"] == str(target))
        self.assertFalse(entry["canDeleteBranch"])
        self.assertFalse(entry["mergedIntoBase"])
        self.assertTrue(target.is_dir())
        self.runtime(installed, repository, "remove", "guarded", "--json")
        self.run_command(["git", "show-ref", "--verify", "refs/heads/wt/guarded"], repository)
        manual = self.workspace / "manual"
        self.run_command(["git", "worktree", "add", "-q", "-b", "manual", manual, "main"], repository)
        refused = self.runtime(installed, repository, "remove", "manual", "--json", success=False)
        self.assertIn("not created by this tool", refused.stderr)
        self.assertTrue(manual.is_dir())
        self.runtime(installed, repository, "remove", "manual", "--unmanaged", "--json")

    def test_submodule_install_preserves_both_checkouts_and_rejects_unsafe_destination(self):
        installed = self.install()
        upstream = self.repository("upstream")
        superproject = self.repository("superproject")
        self.run_command([
            "git", "-c", "protocol.file.allow=always", "submodule", "add", "-q", upstream, "sub",
        ], superproject)
        self.run_command(["git", "commit", "-qam", "Add fixture submodule"], superproject)
        submodule = superproject / "sub"
        before_submodule, before_superproject = self.snapshot(submodule), self.snapshot(superproject)
        created = json.loads(self.runtime(installed, submodule, "create", "sub-work", "--json").stdout)
        self.assertEqual(created["base"], "origin/develop")
        self.assertEqual(Path(created["path"]), self.workspace / "sub-worktrees/sub-work")
        refused = self.runtime(
            installed, submodule, "create", "unsafe", "--dest", superproject / "worktrees", "--json", success=False,
        )
        self.assertIn("inside the superproject", refused.stderr)
        self.assertFalse((superproject / "worktrees").exists())
        self.runtime(installed, submodule, "remove", "sub-work", "--delete-branch", "--json")
        self.assertEqual(self.snapshot(submodule), before_submodule)
        self.assertEqual(self.snapshot(superproject), before_superproject)


if __name__ == "__main__":
    unittest.main()
