"""Distribution contracts: match Claude workflows and ship self-contained Codex packages."""
import json
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
    "review": {"scrutinise", "plan-review"},
    "session": {"good-morning", "call-it-a-day"},
    "repo": {"deprecate"},
    "release": {"publish"},
    "requirements": {"interrogate"},
    "db": {"query-analysis"},
    "dead-code": {"purge"},
    "worktree": {"create", "init", "list", "remove"},
}


class CodexPackagesTest(unittest.TestCase):
    def test_catalogue_preserves_all_eight_plugin_groups(self):
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
                self.assertEqual({path.stem for path in (ROOT / plugin / "commands").glob("*.md")}, expected)
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

    def test_manifest_identity_and_resources_are_self_contained(self):
        for plugin in EXPECTED:
            with self.subTest(plugin=plugin):
                package = ROOT / "plugins" / plugin
                manifest = json.loads((package / ".codex-plugin/plugin.json").read_text())
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


if __name__ == "__main__":
    unittest.main()
