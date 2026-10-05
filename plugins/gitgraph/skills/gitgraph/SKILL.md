---
name: gitgraph
description: Open the whole Git commit history of the repository, or of one of its submodules, as a browsable graph page in the default browser or Codex's in-app browser.
---

# Open the git graph

Use the request to decide two things: the **target** (the repository you are in, or a submodule named by
its name, its path, or the last segment of its path) and the **browser** (the default browser, unless the
request asks for Codex's in-app browser, internal browser, or "here").

Resolve the bundled [gitgraph runtime](../../scripts/gitgraph.py) relative to this skill file and use its
absolute path, `$runtime` below. It needs `python3`. Run every command from the repository you are in,
passing arguments as separately quoted values.

1. **Start the helper**, which serves the page and answers its Changes tab and find-by-file search. The
   sandbox always refuses listening on `127.0.0.1`, so request escalation straight away, with the
   justification "start the local gitgraph helper on 127.0.0.1:47322 so the page can show diffs":

   ```bash
   python3 "$runtime" ensure --root /tmp/gitgraph --port 47322
   ```

   It prints `{"isUp": true}` or `{"isUp": false}`. If escalation is declined or it prints `false`, carry
   on without the helper. Never use port 47321 or Claude Code's gitgraph folder: they belong to Claude Code.
2. **Build the page** inside the sandbox (`/tmp` is writable), adding `--submodule "<name>"` only for a
   submodule:

   ```bash
   python3 "$runtime" build --repo . --out /tmp/gitgraph
   ```

   It prints `{"file", "key", "repository", "commits", "isTruncated"}`, or `{"error"}` with a non-zero
   exit. On an error, report it as it is and stop; for an unknown submodule it lists the known ones.
3. **Open the page.** Its address is `http://127.0.0.1:47322/<key>.html` when the helper is up, otherwise
   the `file` path.
   - **Default browser:** run `open "<address>"` (`xdg-open` on Linux), requesting escalation straight
     away with the justification "open the gitgraph page in the default browser"; the sandbox refuses
     it.
   - **In-app browser**, when asked for: load the address with the bundled browser plugin, then show it
     with `open_in_codex` (`{"target": {"type": "browser", "url": "<address>"}}`); loading alone does
     not show the tab. The in-app browser accepts only `http:` and `https:` addresses, so it needs the
     helper: without it, open the default browser instead and say why.
4. **Reply in one line:** the repository, the number of commits (say "most recent" when `isTruncated`
   is true), and where the page opened. When the helper is not up, add that the Changes tab and find by
   file are off until it runs.

The page is read-only: it never changes the repository. It holds the 20,000 most recent commits on every
branch, remote and tag (not the stash). A page opened from the helper reads diffs on demand, and its
Refresh button rebuilds it from the current history without another run of this skill. An open page
keeps the helper awake; once it has stopped (30 idle minutes), running this skill again starts it.
`/tmp/gitgraph` is cleared on reboot; running the skill again rebuilds the page.
