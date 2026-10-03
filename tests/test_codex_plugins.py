"""Distribution contracts: match Claude workflows and ship self-contained Codex packages."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "review": {"scrutinise", "plan-review", "plan-verify"},
    "session": {"good-morning", "call-it-a-day"},
    "repo": {"deprecate"},
    "release": {"publish"},
    "requirements": {"interrogate"},
    "db": {"query-analysis"},
    "dead-code": {"purge"},
    "worktree": {"create", "init", "list", "remove", "cleanup"},
    "explain": {"explain"},
    "gitgraph": {"gitgraph"},
}
# Claude Code plugins that ship a function-hooks module instead of skills. Their Codex package is a
# skill that runs the same runtime (gitgraph/runtime/gitgraph.py).
CLAUDE_HOOK_PACKAGES = {"gitgraph"}


class CodexPackagesTest(unittest.TestCase):
    def test_catalogue_preserves_all_plugin_groups(self):
        catalogue = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
        original = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
        self.assertEqual(catalogue["name"], "sebastiansulinski-codex")
        self.assertEqual(
            [entry["name"] for entry in catalogue["plugins"]],
            [entry["name"] for entry in original["plugins"]],
        )
        self.assertEqual(set(EXPECTED), {entry["name"] for entry in catalogue["plugins"]})
        for entry in catalogue["plugins"]:
            self.assertEqual(entry["source"], {"source": "local", "path": f"./plugins/{entry['name']}"})
            self.assertEqual(entry["policy"], {"installation": "AVAILABLE", "authentication": "ON_INSTALL"})
            self.assertTrue(entry["category"])
            self.assertTrue((ROOT / entry["source"]["path"] / ".codex-plugin/plugin.json").is_file())

    def test_all_commands_have_native_skill_entrypoints(self):
        for plugin, expected in EXPECTED.items():
            with self.subTest(plugin=plugin):
                if plugin not in CLAUDE_HOOK_PACKAGES:
                    claude_skills = list((ROOT / plugin / "skills").glob("*/SKILL.md"))
                    for path in claude_skills:
                        self.assertEqual(yaml.safe_load(path.read_text().split("---", 2)[1])["name"], path.parent.name)
                    entrypoints = {path.stem for path in (ROOT / plugin / "commands").glob("*.md")}
                    self.assertEqual(entrypoints | {path.parent.name for path in claude_skills}, expected)
                skills = list((ROOT / "plugins" / plugin / "skills").glob("*/SKILL.md"))
                self.assertEqual({path.parent.name for path in skills}, expected)
                for path in skills:
                    contents = path.read_text()
                    self.assertTrue(contents.startswith("---\n"))
                    metadata = yaml.safe_load(contents.split("---", 2)[1])
                    self.assertEqual(metadata["name"], path.parent.name)
                    self.assertIsInstance(metadata["description"], str)
                    self.assertTrue(metadata["description"].strip())
                    self.assertNotIn("CLAUDE_PLUGIN_ROOT", contents)
                    self.assertNotIn("$ARGUMENTS", contents)
                    self.assertNotIn("~/.claude/", contents)

    def test_claude_packages_use_the_skills_layout_only(self):
        for plugin, expected in EXPECTED.items():
            if plugin in CLAUDE_HOOK_PACKAGES:
                continue
            with self.subTest(plugin=plugin):
                self.assertFalse((ROOT / plugin / "commands").exists(), f"{plugin} still has a commands/ directory")
                skills = {path.parent.name for path in (ROOT / plugin / "skills").glob("*/SKILL.md")}
                self.assertEqual(skills, expected)

    def test_manifest_identity_and_resources_are_self_contained(self):
        for plugin in EXPECTED:
            with self.subTest(plugin=plugin):
                package = ROOT / "plugins" / plugin
                manifest_path = package / ".codex-plugin/plugin.json"
                self.assertTrue(manifest_path.is_file(), plugin)
                manifest = json.loads(manifest_path.read_text())
                self.assertEqual(manifest["name"], plugin)
                self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")
                self.assertEqual(manifest["author"]["name"], "Sebastian Sulinski")
                self.assertEqual(manifest["skills"], "./skills/")
                self.assertTrue(manifest["description"])
                self.assertNotIn("mcpServers", manifest)
                self.assertNotIn("apps", manifest)
                self.assertFalse((package / ".claude-plugin").exists())
                self.assertFalse((package / "commands").exists())
                for path in package.rglob("*"):
                    self.assertFalse(path.is_symlink(), str(path))
                    if path.is_file() and path.suffix == ".md":
                        for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text()):
                            if "://" in link or link.startswith("#"):
                                continue
                            target = (path.parent / link.split("#", 1)[0]).resolve()
                            self.assertTrue(target.is_relative_to(package.resolve()), str(target))
                            self.assertTrue(target.exists(), str(target))

    def test_release_archives_install_without_source_checkout(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/package-codex.py"), "--output", temporary],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            archives = list(Path(temporary).glob("*.zip"))
            self.assertEqual(len(archives), len(EXPECTED))
            for archive in archives:
                with zipfile.ZipFile(archive) as bundle:
                    manifest = json.loads(bundle.read(".codex-plugin/plugin.json"))
                    self.assertEqual(archive.name, f"{manifest['name']}-{manifest['version']}.zip")
                    expected_files = {
                        path.relative_to(ROOT / "plugins" / manifest["name"]).as_posix()
                        for path in (ROOT / "plugins" / manifest["name"]).rglob("*")
                        if path.is_file()
                    }
                    self.assertEqual(set(bundle.namelist()), expected_files)
                    for member in bundle.namelist():
                        self.assertFalse(member.startswith("/") or ".." in Path(member).parts)
                        source = ROOT / "plugins" / manifest["name"] / member
                        self.assertEqual(bundle.read(member), source.read_bytes())


class ClaudeHookPackagesTest(unittest.TestCase):
    def test_gitgraph_is_a_self_contained_function_hooks_plugin(self):
        package = ROOT / "gitgraph"
        manifest = json.loads((package / ".claude-plugin/plugin.json").read_text())
        self.assertEqual(manifest["name"], "gitgraph")
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(manifest["author"]["name"], "Sebastian Sulinski")
        self.assertTrue((package / manifest["types"]).is_file())
        hooks = json.loads((package / "hooks/hooks.json").read_text())
        for module in hooks["modules"]:
            self.assertTrue((package / "hooks" / module).resolve().is_file(), module)
        self.assertFalse((package / "commands").exists())
        self.assertFalse((package / "skills").exists())
        for generated in ("tsconfig.json", ".claude-plugin/types"):
            self.assertFalse((package / generated).exists(), f"{generated} is written per machine by Claude Code")

    def test_gitgraph_runtime_copies_match_the_canonical_runtime(self):
        runtime = ROOT / "gitgraph/runtime/gitgraph.py"
        module = (ROOT / "gitgraph/hooks/runtime.ts").read_text()
        prefix = "export const RUNTIME_SOURCE = "
        line = next(line for line in module.splitlines() if line.startswith(prefix))
        self.assertEqual(json.loads(line[len(prefix):]), runtime.read_text())
        packaged = ROOT / "plugins/gitgraph/scripts/gitgraph.py"
        self.assertFalse(packaged.is_symlink())
        self.assertEqual(packaged.read_bytes(), runtime.read_bytes())
        self.assertTrue(os.access(packaged, os.X_OK))
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/sync-gitgraph.py"), "--check"], capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        skill = ROOT / "plugins/gitgraph/skills/gitgraph/SKILL.md"
        links = re.findall(r"\]\(([^)]+)\)", skill.read_text())
        self.assertIn("../../scripts/gitgraph.py", links)


if __name__ == "__main__":
    unittest.main()
