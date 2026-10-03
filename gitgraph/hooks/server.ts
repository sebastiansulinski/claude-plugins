export const PORT = 47321
export const SERVER_VERSION = 'gitgraph-server-3'

/**
 * The page bridge: a small Python server on 127.0.0.1 that serves the
 * generated pages and holds "add to prompt" requests until the session that
 * owns them collects them. A request is keyed by session and token, so only
 * the session that wrote the page (and knows its token) receives it, and the
 * session only ever fills the prompt box, never submits. It exits after thirty
 * minutes without a request.
 *
 * It also answers `/changes` for a commit's files and patches, read on demand
 * with git from a repository the mod registered in `repos.json` (a page names
 * the repository by key, never by path), and `/touching` for the commits whose
 * changed paths (either side of a rename; a merge against its first parent)
 * contain a piece of text.
 */
export const SERVER_SOURCE = String.raw`
import json, os, re, subprocess, sys, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

VERSION = '${SERVER_VERSION}'
ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1])
IDLE_SECONDS = 1800
queues = {}
lock = threading.Lock()
last_seen = [time.time()]
EMPTY_TREE = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'
HASH = re.compile(r'^[0-9a-f]{7,40}$')
FILE_LINES = 3000
TOTAL_CHARS = 3000000


def registered(key):
    try:
        with open(os.path.join(ROOT, 'repos.json')) as handle:
            path = json.load(handle).get(key)
    except Exception:
        return None
    return path if isinstance(path, str) and os.path.isdir(path) else None


def git(path, *args):
    done = subprocess.run(['git', '-C', path, '-c', 'core.quotepath=off'] + list(args), capture_output=True, timeout=60)
    return done.stdout.decode('utf-8', 'replace')


def changes(path, commit):
    parents = git(path, 'rev-list', '--parents', '-n', '1', commit).split()
    if not parents:
        return {'error': 'unknown commit'}
    base = parents[1] if len(parents) > 1 else EMPTY_TREE
    files = []
    tokens = git(path, 'diff', '--name-status', '-M', '-z', base, commit).split('\0')
    index = 0
    while index < len(tokens) and tokens[index]:
        code = tokens[index]
        if code[0] in 'RC':
            files.append({'status': code[0], 'from': tokens[index + 1], 'path': tokens[index + 2]})
            index += 3
        else:
            files.append({'status': code[0], 'from': None, 'path': tokens[index + 1]})
            index += 2
    tokens = git(path, 'diff', '--numstat', '-M', '-z', base, commit).split('\0')
    index = 0
    stats = []
    while index < len(tokens) and tokens[index]:
        added, deleted, name = tokens[index].split('\t', 2)
        index += 3 if name == '' else 1
        stats.append((added, deleted))
    patch = git(path, 'diff', '-M', '--no-color', '--no-ext-diff', base, commit)
    chunks = re.split(r'^diff --git ', patch, flags=re.M)[1:]
    spent = 0
    for position, entry in enumerate(files):
        added, deleted = stats[position] if position < len(stats) else ('0', '0')
        entry['binary'] = added == '-'
        entry['added'] = 0 if added == '-' else int(added)
        entry['deleted'] = 0 if deleted == '-' else int(deleted)
        chunk = chunks[position] if position < len(chunks) else ''
        start = chunk.find('\n@@')
        hunks = chunk[start + 1:] if start >= 0 else ''
        lines = hunks.split('\n')
        entry['truncated'] = len(lines) > FILE_LINES or spent > TOTAL_CHARS
        hunks = '' if spent > TOTAL_CHARS else '\n'.join(lines[:FILE_LINES])
        spent += len(hunks)
        entry['hunks'] = hunks
    return {'isMerge': len(parents) > 2, 'isRoot': len(parents) == 1, 'files': files}


touched = {}


def touching(key, path, needle):
    cached = touched.get(key)
    if not cached or time.time() - cached[0] > 30:
        output = git(path, 'log', '--all', '--diff-merges=first-parent', '--name-status', '-M', '--format=%x1e%H')
        commits = []
        for record in output.split('\x1e')[1:]:
            lines = record.split('\n')
            paths = []
            for line in lines[1:]:
                parts = line.split('\t')
                if len(parts) > 1:
                    paths.extend(parts[1:])
            commits.append((lines[0].strip(), paths))
        cached = (time.time(), commits)
        touched[key] = cached
    needle = needle.lower()
    matches = {}
    for commit, paths in cached[1]:
        hits = [name for name in paths if needle in name.lower()]
        if hits:
            matches[commit] = hits[:20]
    return {'matches': matches}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, body=b'', kind='text/plain; charset=utf-8'):
        self.send_response(code)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        last_seen[0] = time.time()
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if url.path == '/ping':
            return self.reply(200, VERSION.encode())
        if url.path == '/quit':
            self.reply(200, b'bye')
            threading.Thread(target=self.server.shutdown).start()
            return
        if url.path == '/changes':
            path = registered(query.get('repo', [''])[0])
            commit = query.get('hash', [''])[0]
            if not path or not HASH.match(commit):
                return self.reply(404, b'{"error":"unknown repository or commit"}', 'application/json')
            try:
                body = json.dumps(changes(path, commit)).encode()
            except Exception as error:
                body = json.dumps({'error': str(error)}).encode()
            return self.reply(200, body, 'application/json')
        if url.path == '/touching':
            key = query.get('repo', [''])[0]
            path = registered(key)
            needle = query.get('q', [''])[0]
            if not path or not needle:
                return self.reply(404, b'{"error":"unknown repository or empty search"}', 'application/json')
            try:
                body = json.dumps(touching(key, path, needle)).encode()
            except Exception as error:
                body = json.dumps({'error': str(error)}).encode()
            return self.reply(200, body, 'application/json')
        if url.path == '/inbox':
            key = (query.get('session', [''])[0], query.get('token', [''])[0])
            with lock:
                items = queues.pop(key, [])
            return self.reply(200, json.dumps(items).encode(), 'application/json')
        name = os.path.basename(url.path)
        path = os.path.join(ROOT, name)
        if name.endswith('.html') and os.path.isfile(path):
            with open(path, 'rb') as page:
                return self.reply(200, page.read(), 'text/html; charset=utf-8')
        self.reply(404, b'not found')

    def do_POST(self):
        last_seen[0] = time.time()
        if urlparse(self.path).path != '/prompt':
            return self.reply(404)
        length = min(int(self.headers.get('Content-Length', 0) or 0), 65536)
        try:
            data = json.loads(self.rfile.read(length))
            key = (str(data['session']), str(data['token']))
            text = str(data['text'])[:4000]
        except Exception:
            return self.reply(400)
        with lock:
            if key in queues or len(queues) < 100:
                queues.setdefault(key, []).append(text)
        self.reply(204)


def watch(server):
    while True:
        time.sleep(60)
        if time.time() - last_seen[0] > IDLE_SECONDS:
            server.shutdown()
            return


server = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
threading.Thread(target=watch, args=(server,), daemon=True).start()
server.serve_forever()
`
