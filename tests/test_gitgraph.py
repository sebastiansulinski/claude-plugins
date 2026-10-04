"""The gitgraph runtime: history parsing and layout, the helper, and the page's capabilities.

Every repository here is a disposable fixture; every helper listens on a free port of its own and
is stopped by the test that started it.
"""

import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "gitgraph/runtime/gitgraph.py"
CHROME_CANDIDATES = (
    os.environ.get("GITGRAPH_TEST_CHROME", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
)
CHROME = next((candidate for candidate in CHROME_CANDIDATES if candidate and os.path.isfile(candidate)), None)


def load_runtime():
    specification = importlib.util.spec_from_file_location("gitgraph_runtime", RUNTIME)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def page_data(html):
    match = re.search(r"<script>var DATA = (.*?); var PALETTE = .*?; var REPO = (.*?); var PROMPT = (.*?); var RERUN = (.*?);</script>", html)
    return json.loads(match.group(1)), json.loads(match.group(2)), json.loads(match.group(3)), json.loads(match.group(4))


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="gitgraph-test-")
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
        self.runtime = load_runtime()

    def git(self, repository, *arguments, payload=None):
        result = subprocess.run(
            ["git", *arguments], cwd=repository, env=self.environment, input=payload,
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def run_runtime(self, *arguments, success=True):
        result = subprocess.run(
            [sys.executable, str(RUNTIME), *[str(argument) for argument in arguments]],
            env=self.environment, capture_output=True, text=True, timeout=120,
        )
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return json.loads(result.stdout)

    def history(self):
        """main: add old.txt, rename it to new.txt (tag v1), merge feature (adds feature.txt); a remote and a stash."""
        repository = self.workspace / "project"
        repository.mkdir()
        self.git(repository, "init", "-q", "-b", "main")
        (repository / "old.txt").write_text("".join(f"line {number}\n" for number in range(20)))
        self.git(repository, "add", ".")
        self.git(repository, "commit", "-qm", "Add old")
        self.git(repository, "switch", "-qc", "feature")
        (repository / "feature.txt").write_text("feature\n")
        self.git(repository, "add", ".")
        self.git(repository, "commit", "-qm", "Add feature")
        self.git(repository, "switch", "-q", "main")
        self.git(repository, "mv", "old.txt", "new.txt")
        self.git(repository, "commit", "-qm", "Rename old to new")
        self.git(repository, "tag", "v1")
        self.git(repository, "merge", "-q", "--no-ff", "-m", "Merge feature", "feature")
        remote = self.workspace / "remote.git"
        self.git(self.workspace, "init", "-q", "--bare", str(remote))
        self.git(repository, "remote", "add", "origin", str(remote))
        self.git(repository, "push", "-q", "origin", "main")
        self.git(repository, "fetch", "-q", "origin")
        (repository / "new.txt").write_text("stashed work\n")
        self.git(repository, "stash", "-q")
        return repository

    def start_helper(self, root):
        port = free_port()
        self.assertEqual(self.run_runtime("ensure", "--root", root, "--port", port), {"isUp": True})
        self.addCleanup(self.stop_helper, root, port)
        return port

    def stop_helper(self, root, port):
        try:
            urlopen(f"http://127.0.0.1:{port}/quit", timeout=2).close()
        except OSError:
            pass
        pid_file = Path(root) / "helper.pid"
        for _ in range(50):
            if not pid_file.exists():
                return
            time.sleep(0.1)
        os.kill(int(pid_file.read_text()), 15)


class HistoryTest(Fixture):
    def test_lanes_edges_refs_and_the_stash_exclusion(self):
        repository = self.history()
        out = self.workspace / "pages"
        built = self.run_runtime("build", "--repo", repository, "--out", out)
        self.assertEqual(built["repository"], "project")
        self.assertEqual(built["key"], "project")
        self.assertEqual(built["commits"], 4)
        self.assertFalse(built["isTruncated"])
        self.assertEqual(json.loads((out / "repos.json").read_text()), {"project": str(repository)})

        data, repo, prompt, rerun = page_data(Path(built["file"]).read_text())
        self.assertEqual((repo, prompt, rerun), ("project", None, "the gitgraph skill"))
        commits = {commit["subject"]: commit for commit in data["commits"]}
        self.assertEqual(set(commits), {"Add old", "Add feature", "Rename old to new", "Merge feature"})

        merge = commits["Merge feature"]
        self.assertEqual(merge["row"], 0)
        self.assertEqual(merge["lane"], 0)
        self.assertTrue(merge["isHead"])
        self.assertEqual(merge["headBranch"], "main")
        self.assertEqual(merge["refs"], [{"label": "origin & main", "kind": "head"}])
        self.assertEqual(merge["remotes"], ["origin/main"])
        self.assertEqual(commits["Add feature"]["refs"], [{"label": "feature", "kind": "branch"}])
        self.assertEqual(commits["Rename old to new"]["tags"], ["v1"])
        self.assertEqual(commits["Rename old to new"]["refs"], [{"label": "v1", "kind": "tag"}])
        self.assertEqual(commits["Rename old to new"]["stats"], {"files": 1, "insertions": 0, "deletions": 0})

        rows = {commit["fullHash"]: commit["row"] for commit in data["commits"]}
        self.assertEqual(len(data["edges"]), 4)
        for edge in data["edges"]:
            child = data["commits"][edge["childRow"]]
            self.assertEqual(edge["childLane"], child["lane"])
            self.assertNotEqual(edge["parentRow"], -1)
            parent = data["commits"][edge["parentRow"]]
            self.assertEqual(edge["parentLane"], parent["lane"])
            self.assertIn(parent["hash"], child["parentHashes"])
        merge_edges = [edge for edge in data["edges"] if edge["childRow"] == 0]
        self.assertEqual([edge["parentRow"] for edge in merge_edges],
                         [rows[commits["Rename old to new"]["fullHash"]], rows[commits["Add feature"]["fullHash"]]])
        self.assertEqual([edge["lane"] for edge in merge_edges], [0, 1])
        self.assertEqual(max(commit["lane"] for commit in data["commits"]), 1)

    def test_a_submodule_is_named_after_its_parent(self):
        repository = self.history()
        parent = self.workspace / "parent"
        parent.mkdir()
        self.git(parent, "init", "-q", "-b", "main")
        self.git(parent, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(repository), "libs/project")
        self.git(parent, "commit", "-qm", "Add submodule")
        built = self.run_runtime("build", "--repo", parent, "--submodule", "project", "--out", self.workspace / "pages")
        self.assertEqual(built["repository"], "parent/libs/project")
        self.assertEqual(built["key"], "parent-libs-project")
        missing = self.run_runtime("build", "--repo", parent, "--submodule", "nothing", "--out", self.workspace / "pages",
                                   success=False)
        self.assertEqual(missing, {"error": '"nothing" is not a submodule or Git repository. Submodules: libs/project.'})

    def test_outside_a_repository_and_an_empty_one(self):
        plain = self.workspace / "plain"
        plain.mkdir()
        self.assertEqual(self.run_runtime("build", "--repo", plain, "--out", self.workspace, success=False),
                         {"error": "Not inside a Git repository."})
        self.git(plain, "init", "-q")
        self.assertEqual(self.run_runtime("build", "--repo", plain, "--out", self.workspace, success=False),
                         {"error": "plain has no commits."})

    def test_changes_and_file_matches(self):
        repository = self.history()
        commits = dict(line.split(" ", 1)[::-1] for line in self.git(repository, "log", "--format=%H %s").splitlines())

        renamed = self.runtime.changes(str(repository), commits["Rename old to new"])
        self.assertEqual([(file["status"], file["from"], file["path"]) for file in renamed["files"]],
                         [("R", "old.txt", "new.txt")])
        self.assertFalse(renamed["isMerge"] or renamed["isRoot"])
        merged = self.runtime.changes(str(repository), commits["Merge feature"])
        self.assertTrue(merged["isMerge"])
        self.assertEqual([file["path"] for file in merged["files"]], ["feature.txt"])
        first = self.runtime.changes(str(repository), commits["Add old"])
        self.assertTrue(first["isRoot"])
        self.assertEqual(first["files"][0]["added"], 20)
        self.assertTrue(first["files"][0]["hunks"].startswith("@@ -0,0 +1,20 @@\n+line 0"))

        history, _ = self.runtime.read_history(str(repository))
        matches = self.runtime.touching(history, "OLD")["matches"]
        self.assertEqual(matches, {
            commits["Add old"]: ["old.txt"],
            commits["Rename old to new"]: ["old.txt"],
        })


class FilePathsTest(Fixture):
    """The helper's list of file paths, and its filter by one exact path, read file names literally."""

    NAMES = ('a"b.txt', "back\\slash.txt", "tab\tname.txt", "new\nline.txt")

    def unusual(self):
        """Adds four awkward names; renames the quoted one; deletes the tab one; changes the backslash one."""
        repository = self.workspace / "names"
        repository.mkdir()
        self.git(repository, "init", "-q", "-b", "main")
        for name in self.NAMES:
            (repository / name).write_text(name + "\n")
        self.git(repository, "add", ".")
        self.git(repository, "commit", "-qm", "Add awkward names")
        self.git(repository, "mv", 'a"b.txt', 'c"d.txt')
        self.git(repository, "commit", "-qm", "Rename the quoted name")
        self.git(repository, "rm", "-q", "tab\tname.txt")
        self.git(repository, "commit", "-qm", "Delete the tab name")
        (repository / "back\\slash.txt").write_text("changed\n")
        self.git(repository, "commit", "-qam", "Change the backslash name")
        hashes = dict(line.split(" ", 1)[::-1] for line in self.git(repository, "log", "--format=%H %s").splitlines())
        return repository, hashes

    def test_paths_are_listed_literally_newest_first(self):
        """A rename lists its new name before its old one."""
        repository, _ = self.unusual()
        history, at_head = self.runtime.read_history(str(repository))
        self.assertEqual(at_head, {'c"d.txt', "back\\slash.txt", "new\nline.txt"})
        listed = self.runtime.list_paths(history, at_head, ".TXT")
        self.assertEqual(listed["total"], 5)
        self.assertEqual(listed["paths"], [
            {"path": "back\\slash.txt", "commits": 2, "isInHead": True},
            {"path": "tab\tname.txt", "commits": 2, "isInHead": False},
            {"path": 'c"d.txt', "commits": 1, "isInHead": True},
            {"path": 'a"b.txt', "commits": 2, "isInHead": False},
            {"path": "new\nline.txt", "commits": 1, "isInHead": True},
        ])
        self.assertEqual([entry["path"] for entry in self.runtime.list_paths(history, at_head, "\n")["paths"]],
                         ["new\nline.txt"])

    def test_exact_path_catches_both_sides_of_a_rename(self):
        repository, hashes = self.unusual()
        history, _ = self.runtime.read_history(str(repository))
        self.assertEqual(self.runtime.touching(history, exact='a"b.txt')["matches"], {
            hashes["Rename the quoted name"]: ['a"b.txt'],
            hashes["Add awkward names"]: ['a"b.txt'],
        })
        self.assertEqual(self.runtime.touching(history, exact='c"d.txt')["matches"],
                         {hashes["Rename the quoted name"]: ['c"d.txt']})
        self.assertEqual(self.runtime.touching(history, exact="b.txt")["matches"], {})
        self.assertEqual(self.runtime.touching(history, "TAB\t")["matches"], {
            hashes["Delete the tab name"]: ["tab\tname.txt"],
            hashes["Add awkward names"]: ["tab\tname.txt"],
        })

    def test_the_list_is_capped_at_fifty_and_ignores_the_stash(self):
        repository = self.history()
        for number in range(60):
            (repository / f"many-{number:02}.txt").write_text("x\n")
        self.git(repository, "add", ".")
        self.git(repository, "commit", "-qm", "Add many")
        history, at_head = self.runtime.read_history(str(repository))
        listed = self.runtime.list_paths(history, at_head, "many-")
        self.assertEqual((len(listed["paths"]), listed["total"]), (50, 60))
        new = self.runtime.list_paths(history, at_head, "new.txt")["paths"]
        self.assertEqual(new, [{"path": "new.txt", "commits": 1, "isInHead": True}], "the stash changed new.txt too")

    def test_concurrent_requests_share_one_history_read(self):
        repository = self.history()
        helper = self.runtime.Helper(str(self.workspace), 0)
        self.addCleanup(helper.server_close)
        original = self.runtime.read_history
        reads = []

        def slow_read(path):
            reads.append(path)
            time.sleep(0.3)
            return original(path)

        self.runtime.read_history = slow_read
        self.addCleanup(setattr, self.runtime, "read_history", original)
        answers = []
        workers = [
            threading.Thread(target=lambda: answers.append(self.runtime.load_history(helper, "project", str(repository))))
            for _ in range(6)
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        self.assertEqual(len(reads), 1)
        self.assertEqual(len(answers), 6)
        self.assertTrue(all(answer == answers[0] for answer in answers))
        helper.histories["project"].read_at -= self.runtime.HISTORY_SECONDS + 1
        self.runtime.load_history(helper, "project", str(repository))
        self.assertEqual(len(reads), 2, "an expired history is read again")


class LimitTest(Fixture):
    def test_the_twenty_thousand_commit_cap(self):
        repository = self.workspace / "long"
        repository.mkdir()
        self.git(repository, "init", "-q", "-b", "main")
        stream = []
        for mark in range(1, 20002):
            message = f"commit {mark}\n"
            stream.append(f"commit refs/heads/main\nmark :{mark}\ncommitter Fixture <fixture@example.test> {1700000000 + mark} +0000\n")
            stream.append(f"data {len(message)}\n{message}")
            if mark > 1:
                stream.append(f"from :{mark - 1}\n")
            stream.append("\n")
        self.git(repository, "fast-import", "--quiet", payload="".join(stream))
        built = self.run_runtime("build", "--repo", repository, "--out", self.workspace / "pages")
        self.assertEqual(built["commits"], 20000)
        self.assertTrue(built["isTruncated"])
        data, *_ = page_data(Path(built["file"]).read_text())
        self.assertEqual(data["commits"][0]["subject"], "commit 20001")
        self.assertEqual(data["commits"][-1]["subject"], "commit 2")
        self.assertEqual(data["edges"][-1]["parentRow"], -1)
        self.assertIn("20000 most recent commits", Path(built["file"]).read_text())


class HelperTest(Fixture):
    def test_ensure_then_build_into_a_fresh_root(self):
        repository = self.history()
        root = self.workspace / "fresh root"
        port = self.start_helper(root)
        pid = (root / "helper.pid").read_text()
        self.assertEqual(self.run_runtime("ensure", "--root", root, "--port", port), {"isUp": True})
        self.assertEqual((root / "helper.pid").read_text(), pid, "a running helper of this version is kept")

        built = self.run_runtime("build", "--repo", repository, "--out", root)
        base = f"http://127.0.0.1:{port}"
        head = self.git(repository, "rev-parse", "main")
        with urlopen(f"{base}/ping") as response:
            self.assertEqual(response.read().decode(), self.runtime.VERSION)
        with urlopen(f"{base}/{built['key']}.html") as response:
            self.assertIn("<title>Git graph · project</title>", response.read().decode())
        with urlopen(f"{base}/changes?repo={built['key']}&hash={head}") as response:
            self.assertEqual([file["path"] for file in json.loads(response.read())["files"]], ["feature.txt"])
        with urlopen(f"{base}/touching?repo={built['key']}&q=feature") as response:
            matches = json.loads(response.read())["matches"]
        self.assertEqual(matches, {head: ["feature.txt"], self.git(repository, "rev-parse", "feature"): ["feature.txt"]})
        with urlopen(f"{base}/touching?repo={built['key']}&path=old.txt") as response:
            self.assertEqual(len(json.loads(response.read())["matches"]), 2)
        with urlopen(f"{base}/paths?repo={built['key']}&q=TXT") as response:
            listed = json.loads(response.read())
        self.assertEqual([entry["path"] for entry in listed["paths"]], ["feature.txt", "new.txt", "old.txt"])
        self.assertEqual(listed["paths"][2]["isInHead"], False)

        posted = Request(f"{base}/prompt", data=json.dumps({"session": "S", "token": "T", "text": "abc"}).encode())
        with urlopen(posted) as response:
            self.assertEqual(response.status, 204)
        with urlopen(f"{base}/inbox?session=S&token=T") as response:
            self.assertEqual(json.loads(response.read()), ["abc"])
        with urlopen(f"{base}/inbox?session=S&token=T") as response:
            self.assertEqual(json.loads(response.read()), [])


@unittest.skipUnless(CHROME, "needs Google Chrome or Chromium (set GITGRAPH_TEST_CHROME)")
class PageModesTest(Fixture):
    """What a page offers depends on where it was opened from, and on whether it carries PROMPT."""

    def capabilities(self, url):
        profile = tempfile.mkdtemp(prefix="gitgraph-chrome-")
        self.addCleanup(shutil.rmtree, profile, True)
        # Chrome prints the page as it stands once the script and its /ping have run, but does not
        # always exit afterwards, so the dump is read up to its end and Chrome is stopped.
        browser = subprocess.Popen(
            [CHROME, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={profile}",
             "--virtual-time-budget=5000", "--dump-dom", url],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, start_new_session=True,
        )
        dump = []
        timer = threading.Timer(90, os.killpg, (browser.pid, signal.SIGKILL))
        timer.start()
        try:
            for line in browser.stdout:
                dump.append(line)
                if "</html>" in line:
                    break
        finally:
            timer.cancel()
            os.killpg(browser.pid, signal.SIGKILL)
            browser.stdout.close()
            browser.wait()
        dump = "".join(dump)
        root = re.search(r"<html[^>]*>", dump).group(0)
        files = re.search(r'<button data-mode="files"[^>]*>', dump).group(0)
        self.assertIn('id="list"', dump)
        return {
            "helper": 'data-helper="on"' in root,
            "prompt": 'data-prompt="on"' in root,
            "findByFile": "disabled" not in files,
        }

    def test_served_and_from_disk_with_and_without_prompt(self):
        repository = self.history()
        root = self.workspace / "pages"
        port = self.start_helper(root)
        prompt = json.dumps({"session": "S", "token": "T"})

        claude = self.run_runtime("build", "--repo", repository, "--out", root, "--prompt", prompt, "--rerun", "/gitgraph")
        self.assertEqual(self.capabilities(f"http://127.0.0.1:{port}/{claude['key']}.html"),
                         {"helper": True, "prompt": True, "findByFile": True})
        self.assertEqual(self.capabilities(Path(claude["file"]).as_uri()),
                         {"helper": False, "prompt": False, "findByFile": False})

        codex = self.run_runtime("build", "--repo", repository, "--out", root)
        self.assertEqual(self.capabilities(f"http://127.0.0.1:{port}/{codex['key']}.html"),
                         {"helper": True, "prompt": False, "findByFile": True})
        self.assertEqual(self.capabilities(Path(codex["file"]).as_uri()),
                         {"helper": False, "prompt": False, "findByFile": False})


if __name__ == "__main__":
    unittest.main()
