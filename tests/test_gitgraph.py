"""The gitgraph runtime: history parsing and layout, the helper, and the page's capabilities.

Every repository here is a disposable fixture; every helper listens on a free port of its own and
is stopped by the test that started it.
"""

import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import re
import select
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
# Every page revision the helper version has stood for. A change to the page's code changes the
# fingerprint: add a new entry under the next number and raise VERSION to it; never edit an entry.
PAGE_FINGERPRINTS = {
    6: "7309c674c069799b9ffec6a821d10ea83e51d0f0387965458952254d08a9a5fb",
}
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
    match = re.search(r"<script>var DATA = (.*?); var PALETTE = .*?; var REPO = (.*?); var PROMPT = (.*?); var RERUN = (.*?); var PAGE = \d+;</script>", html)
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

        helper = self.runtime.Helper(str(self.workspace / "pages"), 0)
        self.addCleanup(helper.server_close)
        status, answer = self.runtime.refresh(helper, built["key"], 6)
        self.assertEqual((status, answer), (200, {"commits": 20000, "isTruncated": True}))
        self.assertIn("20000 most recent commits", Path(built["file"]).read_text())


class RefreshTest(Fixture):
    """POST /refresh rebuilds a page from the details its last build recorded."""

    def post(self, port, path, body, origin="same", host=None, headers=None):
        """Sends a POST as a page served by the helper would; answers (status, parsed body or None)."""
        request = Request(f"http://127.0.0.1:{port}{path}", data=body if isinstance(body, bytes) else json.dumps(body).encode())
        if origin == "same":
            origin = f"http://127.0.0.1:{port}"
        if origin is not None:
            request.add_header("Origin", origin)
        if host is not None:
            request.add_header("Host", host)
        for name, value in (headers or {}).items():
            request.add_header(name, value)
        try:
            with urlopen(request, timeout=30) as response:
                text = response.read()
                return response.status, json.loads(text) if text else None
        except HTTPError as error:
            text = error.read()
            try:
                return error.code, json.loads(text)
            except ValueError:
                return error.code, None

    def built(self, repository, root, *extra):
        return self.run_runtime("build", "--repo", repository, "--out", root, *extra)

    def test_refresh_rebuilds_with_the_last_builds_details(self):
        repository = self.history()
        root = self.workspace / "pages"
        port = self.start_helper(root)
        built = self.built(repository, root, "--prompt", json.dumps({"session": "A", "token": "a"}), "--rerun", "/gitgraph")
        self.assertEqual(json.loads((root / f"{built['key']}.page.json").read_text()), {
            "label": "project", "path": str(repository), "prompt": {"session": "A", "token": "a"}, "rerun": "/gitgraph",
        })
        registrations = (root / "repos.json").read_bytes()
        (repository / "late.txt").write_text("late\n")
        self.git(repository, "add", "late.txt")
        self.git(repository, "commit", "-qm", "A late commit")

        status, answer = self.post(port, "/refresh", {"repo": built["key"], "page": 6})
        self.assertEqual((status, answer), (200, {"commits": 5, "isTruncated": False}))
        data, repo, prompt, rerun = page_data(Path(built["file"]).read_text())
        self.assertEqual(data["commits"][0]["subject"], "A late commit")
        self.assertEqual((repo, prompt, rerun), ("project", {"session": "A", "token": "a"}, "/gitgraph"))
        self.assertEqual((root / "repos.json").read_bytes(), registrations, "a refresh never re-registers")

    def test_refusals(self):
        repository = self.history()
        root = self.workspace / "pages"
        port = self.start_helper(root)
        built = self.built(repository, root)
        self.assertEqual(self.post(port, "/refresh", {"repo": "nothing", "page": 6})[0], 404)
        self.assertEqual(self.post(port, "/refresh", {"repo": built["key"], "page": 7})[0], 409, "a newer page")
        self.assertEqual(self.post(port, "/refresh", b"not json")[0], 400)
        self.assertEqual(self.post(port, "/refresh", {"repo": built["key"]})[0], 400)
        self.assertEqual(self.post(port, "/refresh", {"repo": built["key"], "page": 6, "pad": "x" * 70000})[0], 400)
        sidecar = root / f"{built['key']}.page.json"
        details = sidecar.read_text()
        sidecar.unlink()
        self.assertEqual(self.post(port, "/refresh", {"repo": built["key"], "page": 6})[0], 409, "built by an older runtime")
        sidecar.write_text(details)

        moved = self.workspace / "moved"
        repository.rename(moved)
        self.assertEqual(self.post(port, "/refresh", {"repo": built["key"], "page": 6})[0], 410)
        moved.rename(repository)

        parent = self.workspace / "parent"
        parent.mkdir()
        self.git(parent, "init", "-q", "-b", "main")
        self.git(parent, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(repository), "libs/project")
        self.git(parent, "commit", "-qm", "Add submodule")
        inner = self.built(parent, root, "--submodule", "project")
        self.assertEqual(inner["key"], "parent-libs-project")
        status, answer = self.post(port, "/refresh", {"repo": inner["key"], "page": 6})
        self.assertEqual(status, 200)
        self.assertEqual(page_data(Path(inner["file"]).read_text())[1], "parent-libs-project")
        self.assertIn("<title>Git graph · parent/libs/project</title>", Path(inner["file"]).read_text())
        page = Path(inner["file"]).read_bytes()
        self.git(parent, "submodule", "deinit", "-q", "-f", "libs/project")
        status, answer = self.post(port, "/refresh", {"repo": inner["key"], "page": 6})
        self.assertEqual(status, 200)
        self.assertIn("is no longer a Git repository", answer["error"])
        self.assertEqual(Path(inner["file"]).read_bytes(), page, "the page is left as it was")

    def test_only_the_pages_own_origin_and_host(self):
        repository = self.history()
        root = self.workspace / "pages"
        port = self.start_helper(root)
        built = self.built(repository, root)
        asked = {"repo": built["key"], "page": 6}
        for origin in (None, "null", "https://example.com", "http://127.0.0.1:47322", f"http://127.0.0.1:{port}.example.com"):
            with self.subTest(origin=origin):
                self.assertEqual(self.post(port, "/refresh", asked, origin=origin)[0], 403)
        self.assertEqual(self.post(port, "/refresh", asked, origin=f"http://localhost:{port}")[0], 200)
        self.assertEqual(self.post(port, "/refresh", asked, host=f"evil.test:{port}")[0], 403)
        note = {"session": "S", "token": "T", "text": "abc"}
        self.assertEqual(self.post(port, "/prompt", note, origin="https://example.com")[0], 403)
        self.assertEqual(self.post(port, "/prompt", note)[0], 204)
        request = Request(f"http://127.0.0.1:{port}/ping", headers={"Host": f"evil.test:{port}"})
        with self.assertRaises(HTTPError) as refused:
            urlopen(request, timeout=10)
        self.assertEqual(refused.exception.code, 403)
        request = Request(f"http://127.0.0.1:{port}/quit", headers={"Sec-Fetch-Site": "cross-site"})
        with self.assertRaises(HTTPError) as refused:
            urlopen(request, timeout=10)
        self.assertEqual(refused.exception.code, 403)
        with urlopen(f"http://127.0.0.1:{port}/ping", timeout=10) as response:
            self.assertEqual(response.read().decode(), self.runtime.VERSION, "the helper is still up")

    def test_ensure_replaces_an_older_helper_and_an_older_helper_refuses_newer_pages(self):
        older = self.workspace / "older.py"
        older.write_text(RUNTIME.read_text().replace(f"VERSION = '{self.runtime.VERSION}'", "VERSION = 'gitgraph-server-5'"))
        repository = self.history()
        root = self.workspace / "pages"
        port = free_port()
        self.addCleanup(self.stop_helper, root, port)
        result = subprocess.run([sys.executable, str(older), "ensure", "--root", str(root), "--port", str(port)],
                                env=self.environment, capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout), {"isUp": True})
        built = self.built(repository, root)
        self.assertEqual(self.post(port, "/refresh", {"repo": built["key"], "page": 6})[0], 409)
        older_pid = (root / "helper.pid").read_text()
        self.assertEqual(self.run_runtime("ensure", "--root", root, "--port", port), {"isUp": True})
        self.assertNotEqual((root / "helper.pid").read_text(), older_pid)
        with urlopen(f"http://127.0.0.1:{port}/ping", timeout=10) as response:
            self.assertEqual(response.read().decode(), self.runtime.VERSION)
        self.assertEqual(self.post(port, "/refresh", {"repo": built["key"], "page": 6})[0], 200)

    def test_the_page_fingerprint_is_recorded_under_the_helper_version(self):
        current = self.runtime.version_number(self.runtime.VERSION)
        self.assertEqual(max(PAGE_FINGERPRINTS), current, "VERSION is the newest recorded page revision")
        self.assertEqual(self.runtime.page_fingerprint(), PAGE_FINGERPRINTS[current],
                         "the page's code changed: record its fingerprint under a new number and raise VERSION")

    def slow_graphs(self, seconds):
        """Makes every history read take `seconds` longer; answers the list of labels read."""
        original = self.runtime.load_graph
        reads = []

        def slow(label, path):
            reads.append(label)
            time.sleep(seconds)
            return original(label, path)

        self.runtime.load_graph = slow
        self.addCleanup(setattr, self.runtime, "load_graph", original)
        return reads

    def test_clicks_while_the_repository_is_locked_share_one_rebuild(self):
        repository = self.history()
        root = self.workspace / "pages"
        built = self.built(repository, root)
        helper = self.runtime.Helper(str(root), 0)
        self.addCleanup(helper.server_close)
        reads = self.slow_graphs(0.2)
        answers = []
        with self.runtime.key_lock(str(root), built["key"]):
            workers = [threading.Thread(target=lambda: answers.append(self.runtime.refresh(helper, built["key"], 6)))
                       for _ in range(2)]
            for worker in workers:
                worker.start()
            time.sleep(0.3)
        for worker in workers:
            worker.join()
        self.assertEqual(answers, [(200, {"commits": 4, "isTruncated": False})] * 2)
        self.assertEqual(len(reads), 1)

    def test_refreshes_of_two_repositories_at_once(self):
        first = self.history()
        second = self.workspace / "second"
        shutil.copytree(first, second)
        root = self.workspace / "pages"
        keys = [self.built(first, root)["key"], self.built(second, root)["key"]]
        registrations = json.loads((root / "repos.json").read_text())
        helper = self.runtime.Helper(str(root), 0)
        self.addCleanup(helper.server_close)
        self.slow_graphs(0.2)
        answers = {}
        workers = [threading.Thread(target=lambda key=key: answers.update({key: self.runtime.refresh(helper, key, 6)}))
                   for key in keys]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        self.assertEqual(answers, {key: (200, {"commits": 4, "isTruncated": False}) for key in keys})
        self.assertEqual(json.loads((root / "repos.json").read_text()), registrations)
        for key in keys:
            page_data((root / f"{key}.html").read_text())
        self.assertEqual([path.name for path in root.iterdir() if path.name.endswith(".tmp")], [])

    def test_a_build_racing_a_refresh_keeps_its_newer_prompt(self):
        repository = self.history()
        root = self.workspace / "pages"
        built = self.built(repository, root, "--prompt", json.dumps({"session": "old", "token": "o"}))
        helper = self.runtime.Helper(str(root), 0)
        self.addCleanup(helper.server_close)
        self.slow_graphs(0.4)
        refreshing = threading.Thread(target=lambda: self.runtime.refresh(helper, built["key"], 6))
        refreshing.start()
        time.sleep(0.1)
        newer = SimpleNamespace(repo=str(repository), submodule=None, out=str(root), rerun="gitgraph",
                                prompt=json.dumps({"session": "new", "token": "n"}))
        self.runtime.build(newer)
        refreshing.join()
        self.assertEqual(page_data(Path(built["file"]).read_text())[2], {"session": "new", "token": "n"})
        self.assertEqual(json.loads((root / f"{built['key']}.page.json").read_text())["prompt"],
                         {"session": "new", "token": "n"})

    def test_a_refresh_clears_the_file_search_history(self):
        repository = self.history()
        root = self.workspace / "pages"
        port = self.start_helper(root)
        built = self.built(repository, root)
        base = f"http://127.0.0.1:{port}"
        with urlopen(f"{base}/touching?repo={built['key']}&path=new.txt") as response:
            self.assertEqual(len(json.loads(response.read())["matches"]), 1)
        (repository / "new.txt").write_text("changed again\n")
        self.git(repository, "commit", "-qam", "Change new again")
        self.assertEqual(self.post(port, "/refresh", {"repo": built["key"], "page": 6})[0], 200)
        with urlopen(f"{base}/touching?repo={built['key']}&path=new.txt") as response:
            matches = json.loads(response.read())["matches"]
        self.assertIn(self.git(repository, "rev-parse", "HEAD"), matches)

    def test_a_git_failure_inside_a_refresh_is_an_error_answer(self):
        repository = self.history()
        root = self.workspace / "pages"
        built = self.built(repository, root)
        helper = self.runtime.Helper(str(root), 0)
        self.addCleanup(helper.server_close)
        original = self.runtime.load_graph

        def failing(label, path):
            raise self.runtime.Failure("git log failed.")

        self.runtime.load_graph = failing
        self.addCleanup(setattr, self.runtime, "load_graph", original)
        self.assertEqual(self.runtime.refresh(helper, built["key"], 6), (200, {"error": "git log failed."}))

    def test_a_repositorys_own_programs_never_run(self):
        """A textconv driver in the repository's configuration would run on reading diffs or stats."""
        repository = self.history()
        marker = self.workspace / "ran"
        self.git(repository, "config", "diff.marker.textconv", f"touch '{marker}' && cat")
        (repository / ".gitattributes").write_text("*.txt diff=marker\n")
        (repository / "new.txt").write_text("changed by the textconv commit\n")
        self.git(repository, "add", ".")
        self.git(repository, "commit", "-qm", "Configure textconv")
        self.git(repository, "diff", "HEAD~1", "HEAD")
        self.assertTrue(marker.exists(), "the fixture's driver runs when git is not told otherwise")
        marker.unlink()

        root = self.workspace / "pages"
        port = self.start_helper(root)
        built = self.built(repository, root)
        head = self.git(repository, "rev-parse", "HEAD")
        base = f"http://127.0.0.1:{port}"
        for path in (f"/changes?repo={built['key']}&hash={head}", f"/touching?repo={built['key']}&q=new",
                     f"/paths?repo={built['key']}&q=new"):
            with urlopen(base + path) as response:
                response.read()
        self.assertEqual(self.post(port, "/refresh", {"repo": built["key"], "page": 6})[0], 200)
        self.assertFalse(marker.exists())


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

        posted = Request(f"{base}/prompt", data=json.dumps({"session": "S", "token": "T", "text": "abc"}).encode(),
                         headers={"Origin": base})
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
            "refresh": 'data-refresh="on"' in root and re.search(r'<button class="mode" id="refresh"[^>]*hidden', dump) is None,
        }

    def test_served_and_from_disk_with_and_without_prompt(self):
        repository = self.history()
        root = self.workspace / "pages"
        port = self.start_helper(root)
        prompt = json.dumps({"session": "S", "token": "T"})

        claude = self.run_runtime("build", "--repo", repository, "--out", root, "--prompt", prompt, "--rerun", "/gitgraph")
        self.assertEqual(self.capabilities(f"http://127.0.0.1:{port}/{claude['key']}.html"),
                         {"helper": True, "prompt": True, "findByFile": True, "refresh": True})
        self.assertEqual(self.capabilities(Path(claude["file"]).as_uri()),
                         {"helper": False, "prompt": False, "findByFile": False, "refresh": False})

        codex = self.run_runtime("build", "--repo", repository, "--out", root)
        self.assertEqual(self.capabilities(f"http://127.0.0.1:{port}/{codex['key']}.html"),
                         {"helper": True, "prompt": False, "findByFile": True, "refresh": True})
        self.assertEqual(self.capabilities(Path(codex["file"]).as_uri()),
                         {"helper": False, "prompt": False, "findByFile": False, "refresh": False})

    def test_an_older_helper_shows_no_refresh_button(self):
        """A page served by a version 5 helper keeps its Changes tab and file search, with no button."""
        repository = self.history()
        root = self.workspace / "pages"
        built = self.run_runtime("build", "--repo", repository, "--out", root)
        page = Path(built["file"]).read_bytes()

        class Older(BaseHTTPRequestHandler):
            def log_message(self, *arguments):
                pass

            def do_GET(self):
                body = b"gitgraph-server-5" if self.path == "/ping" else page
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Older)
        self.addCleanup(server.server_close)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        self.assertEqual(self.capabilities(f"http://127.0.0.1:{server.server_address[1]}/{built['key']}.html"),
                         {"helper": True, "prompt": False, "findByFile": True, "refresh": False})


class Chrome:
    """Headless Chrome driven over its DevTools Protocol pipe (file descriptors 3 and 4)."""

    def __init__(self, test, url):
        profile = tempfile.mkdtemp(prefix="gitgraph-chrome-")
        test.addCleanup(shutil.rmtree, profile, True)
        commands, self.to_chrome = os.pipe()
        self.from_chrome, answers = os.pipe()

        def wire():
            os.dup2(commands, 3)
            os.dup2(answers, 4)

        self.process = subprocess.Popen(
            [CHROME, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={profile}",
             "--remote-debugging-pipe", "about:blank"],
            preexec_fn=wire, pass_fds=(3, 4), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
        )
        os.close(commands)
        os.close(answers)
        test.addCleanup(self.close)
        self.buffer = b""
        self.number = 0
        self.errors = []
        target = self.send("Target.createTarget", {"url": "about:blank"})["targetId"]
        self.session = self.send("Target.attachToTarget", {"targetId": target, "flatten": True})["sessionId"]
        self.send("Runtime.enable", session=self.session)
        self.send("Page.navigate", {"url": url}, session=self.session)

    def close(self):
        with contextlib.suppress(OSError):
            os.killpg(self.process.pid, signal.SIGKILL)
        self.process.wait()
        for descriptor in (self.to_chrome, self.from_chrome):
            with contextlib.suppress(OSError):
                os.close(descriptor)

    def receive(self, deadline):
        while b"\0" not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([self.from_chrome], [], [], remaining)[0]:
                raise TimeoutError("Chrome did not answer")
            chunk = os.read(self.from_chrome, 1 << 20)
            if not chunk:
                raise ConnectionError("Chrome closed its pipe")
            self.buffer += chunk
        message, self.buffer = self.buffer.split(b"\0", 1)
        message = json.loads(message)
        if message.get("method") == "Runtime.exceptionThrown":
            self.errors.append(message["params"]["exceptionDetails"].get("exception", {}).get("description", "error"))
        return message

    def send(self, method, params=None, session=None, timeout=30):
        self.number += 1
        message = {"id": self.number, "method": method, "params": params or {}}
        if session:
            message["sessionId"] = session
        os.write(self.to_chrome, json.dumps(message).encode() + b"\0")
        deadline = time.monotonic() + timeout
        while True:
            answer = self.receive(deadline)
            if answer.get("id") == self.number:
                if "error" in answer:
                    raise RuntimeError(answer["error"])
                return answer["result"]

    def evaluate(self, expression):
        result = self.send("Runtime.evaluate", {"expression": expression, "awaitPromise": True, "returnByValue": True},
                           session=self.session)
        if "exceptionDetails" in result:
            raise RuntimeError(result["exceptionDetails"])
        return result["result"].get("value")

    def wait(self, expression, timeout=20):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                value = self.evaluate(expression)
            except RuntimeError:
                value = None
            if value:
                return value
            time.sleep(0.1)
        raise AssertionError(f"timed out waiting for {expression}")


@unittest.skipUnless(CHROME, "needs Google Chrome or Chromium (set GITGRAPH_TEST_CHROME)")
class RefreshPageTest(Fixture):
    """The Refresh button rebuilds the page and brings back what was in view."""

    VIEW = """JSON.stringify((function () {
      var list = document.getElementById('list'), selected = document.querySelector('#list .r.sel');
      var on = document.querySelector('#detail .files .file.on'), tab = document.querySelector('#detail .tabs .on');
      var leaf = document.querySelector('#refs .leaf.on');
      return {
        first: DATA.commits[0].subject,
        isFirstMatched: !document.querySelector('#list .r[data-row="0"]').classList.contains('miss'),
        find: document.getElementById('find').value,
        mode: document.querySelector('#modes .on').getAttribute('data-mode'),
        count: document.getElementById('count').textContent,
        leaf: leaf ? leaf.getAttribute('data-kind') + ':' + leaf.getAttribute('data-name') : null,
        selected: selected ? DATA.commits[Number(selected.getAttribute('data-row'))].fullHash : null,
        isDetailOpen: !document.getElementById('detail').hidden,
        tab: tab ? tab.getAttribute('data-tab') : null,
        file: on ? on.getAttribute('title') : null,
        scroll: list.scrollTop,
        commits: DATA.commits.length
      };
    })())"""

    def repository_of_many(self):
        """125 commits: each changes one of ten notes, every seventh also composer.json; topic and v1 refs."""
        repository = self.workspace / "many"
        repository.mkdir()
        self.git(repository, "init", "-q", "-b", "main")
        stream = []
        for mark in range(1, 126):
            message = f"Commit {mark}\n"
            stream.append(f"commit refs/heads/main\nmark :{mark}\ncommitter Fixture <fixture@example.test> {1700000000 + mark * 60} +0000\n")
            stream.append(f"data {len(message)}\n{message}")
            if mark > 1:
                stream.append(f"from :{mark - 1}\n")
            note = f"note {mark}\n"
            stream.append(f"M 644 inline notes/n{mark % 10}.txt\ndata {len(note)}\n{note}")
            if mark % 7 == 0 or mark == 1:
                stream.append(f"M 644 inline composer.json\ndata {len(note)}\n{note}")
            stream.append("\n")
        stream.append("reset refs/heads/topic\nfrom :60\n\nreset refs/tags/v1\nfrom :30\n\n")
        self.git(repository, "fast-import", "--quiet", payload="".join(stream))
        self.git(repository, "reset", "-q", "--hard")
        return repository

    def test_refresh_keeps_the_view_and_shows_the_new_commit(self):
        repository = self.repository_of_many()
        root = self.workspace / "pages"
        port = self.start_helper(root)
        built = self.run_runtime("build", "--repo", repository, "--out", root, "--rerun", "/gitgraph")
        chrome = Chrome(self, f"http://127.0.0.1:{port}/{built['key']}.html")
        chrome.wait("document.documentElement.getAttribute('data-refresh') === 'on'")

        chrome.evaluate("document.querySelector('#refs .leaf[data-kind=\"branches\"][data-name=\"topic\"]').click()")
        chrome.evaluate("""(function () {
          document.querySelector('[data-mode="files"]').click();
          var find = document.getElementById('find');
          find.value = 'composer';
          find.dispatchEvent(new Event('input'));
        })()""")
        chrome.wait("Array.prototype.some.call(document.querySelectorAll('#suggest .o'), function (o) { return o.title === 'composer.json'; })")
        chrome.evaluate("""Array.prototype.filter.call(document.querySelectorAll('#suggest .o'), function (o) {
          return o.title === 'composer.json';
        })[0].dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))""")
        chrome.wait("document.getElementById('count').textContent === '18 commits'")
        chrome.evaluate("document.querySelectorAll('#list .r:not(.miss)')[4].querySelector('.s').click()")
        chrome.wait("(document.querySelector('#detail .files .file.on') || {}).title === 'composer.json'")
        chrome.evaluate("document.getElementById('list').scrollTop = 40 * 28 + 7")
        before = json.loads(chrome.evaluate(self.VIEW))
        self.assertEqual((before["mode"], before["find"], before["leaf"], before["tab"]),
                         ("files", "composer.json", "branches:topic", "changes"))

        (repository / "composer.json").write_text("late\n")
        self.git(repository, "commit", "-qam", "A late composer change")
        chrome.evaluate("window.beforeRefresh = true; document.getElementById('refresh').click()")
        chrome.wait("!window.beforeRefresh && document.getElementById('count').textContent === '19 commits' && "
                    "(document.querySelector('#detail .files .file.on') || {}).title === 'composer.json'")
        after = json.loads(chrome.evaluate(self.VIEW))
        self.assertEqual(after["first"], "A late composer change")
        self.assertTrue(after["isFirstMatched"], "the new commit is matched by the restored filter")
        self.assertEqual(after["commits"], before["commits"] + 1)
        for field in ("mode", "find", "leaf", "selected", "tab", "file"):
            self.assertEqual(after[field], before[field], field)
        self.assertTrue(after["isDetailOpen"])
        self.assertEqual(after["scroll"], before["scroll"] + 28, "the same commit stays at the top of the view")
        self.assertEqual(chrome.errors, [])

        # A branch and its only commit that vanish before the next refresh are skipped.
        tip = self.git(repository, "commit-tree", "-p", "HEAD", "-m", "Only on gone", f"{self.git(repository, 'rev-parse', 'HEAD')}^{{tree}}")
        self.git(repository, "branch", "gone", tip)
        chrome.evaluate("window.beforeRefresh = true; document.getElementById('refresh').click()")
        chrome.wait("!window.beforeRefresh && document.querySelector('#refs .leaf[data-name=\"gone\"]') !== null")
        chrome.evaluate("document.querySelector('#refs .leaf[data-name=\"gone\"]').click()")
        chrome.evaluate("document.querySelector('#list .r.sel .s').click()")
        chrome.wait("!document.getElementById('detail').hidden")
        self.git(repository, "branch", "-D", "-q", "gone")
        chrome.evaluate("window.beforeRefresh = true; document.getElementById('refresh').click()")
        chrome.wait("!window.beforeRefresh && document.documentElement.getAttribute('data-refresh') === 'on'")
        time.sleep(1.5)
        gone = json.loads(chrome.evaluate(self.VIEW))
        self.assertIsNone(gone["leaf"])
        self.assertIsNone(gone["selected"])
        self.assertFalse(gone["isDetailOpen"])
        self.assertEqual(chrome.errors, [])


if __name__ == "__main__":
    unittest.main()
