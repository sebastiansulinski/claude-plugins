import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { GitGraph } from '../types'
import { LOG_ARGUMENTS, layoutGraph, parseLog } from './layout'
import { buildPage } from './page'
import { PORT, SERVER_SOURCE, SERVER_VERSION } from './server'

const LIMIT = 20_000
const BASE = `http://127.0.0.1:${PORT}`

const bridgeToken = atom({ plugin: 'gitgraph', key: 'token' } as const, '')

type Target = { repository: string; path: string } | { error: string }

/**
 * Resolves what to draw: the current repository, or the submodule named by
 * `argument` (its name, its path, or the last segment of its path), or any
 * other directory that is a Git repository.
 */
async function resolveTarget($: EngineInterface, argument: string | undefined): Promise<Target> {
  const top = await $.process.run(['git', 'rev-parse', '--show-toplevel'])
  if (top.exitCode !== 0) {
    return { error: 'Not inside a Git repository.' }
  }
  const root = top.stdout.trim()
  const rootName = root.split('/').pop() ?? root

  if (!argument) {
    return { repository: rootName, path: root }
  }

  const listed = await $.process.run(
    ['git', 'config', '--file', '.gitmodules', '--get-regexp', '^submodule\\..*\\.path$'],
    { cwd: root },
  )
  const submodules = listed.stdout
    .split('\n')
    .filter(line => line.length > 0)
    .map(line => {
      const [key = '', path = ''] = line.split(' ')

      return { name: key.replace(/^submodule\./, '').replace(/\.path$/, ''), path }
    })
  const wanted = argument.replace(/\/+$/, '')
  const submodule = submodules.find(
    one => one.name === wanted || one.path === wanted || one.path.split('/').pop() === wanted,
  )
  const path = submodule ? `${root}/${submodule.path}` : wanted.startsWith('/') ? wanted : `${root}/${wanted}`
  const inner = await $.process.run(['git', 'rev-parse', '--show-toplevel'], { cwd: path }).catch(() => null)

  if (!inner || inner.exitCode !== 0 || (submodule && inner.stdout.trim() !== path)) {
    if (submodule) {
      return { error: `Submodule "${submodule.name}" is not initialised (git submodule update --init ${submodule.path}).` }
    }
    const known = submodules.map(one => one.path).join(', ')

    return { error: `"${argument}" is not a submodule or Git repository.${known ? ` Submodules: ${known}.` : ''}` }
  }

  return { repository: `${rootName}/${submodule?.path ?? wanted}`, path: inner.stdout.trim() }
}

async function loadGraph(
  $: EngineInterface,
  target: Pick<GitGraph, 'repository' | 'path'>,
): Promise<GitGraph | { error: string }> {
  const log = await $.process.run(
    ['git', 'log', '--exclude=refs/stash', '--all', `--max-count=${LIMIT + 1}`, ...LOG_ARGUMENTS],
    { cwd: target.path, timeoutMs: 120_000 },
  )
  if (log.exitCode !== 0) {
    return { error: log.stderr.trim() || 'git log failed.' }
  }

  const raw = parseLog(log.stdout)
  const isTruncated = raw.length > LIMIT || log.isStdoutTruncated
  const { commits, edges, lanes } = layoutGraph(raw.slice(0, LIMIT))

  return { ...target, commits, edges, lanes, isTruncated }
}

/**
 * Opens a page or file in the default browser: `open` on macOS, `xdg-open` elsewhere.
 */
async function openInBrowser($: EngineInterface, target: string): Promise<boolean> {
  for (const opener of ['open', 'xdg-open']) {
    const opened = await $.process.run([opener, target]).catch(() => null)
    if (opened?.exitCode === 0) {
      return true
    }
  }

  return false
}

/**
 * Whether this session has the desktop app's built-in browser pane (its tools are
 * offered to the model); the terminal and other hosts do not.
 */
async function hasBrowserPane($: EngineInterface): Promise<boolean> {
  const tools = await $.tool.list().catch(() => [])

  return tools.some(tool => tool.name === 'mcp__Claude_Browser__preview_start')
}

async function serverVersion($: EngineInterface): Promise<string | null> {
  const response = await $.http.fetch(`${BASE}/ping`).catch(() => null)

  return response?.ok ? response.text : null
}

/**
 * Makes sure this version of the page bridge listens on PORT: starts it, or
 * replaces an older one. Answers whether it is up; pages open from disk when not.
 */
async function ensureServer($: EngineInterface, directory: string): Promise<boolean> {
  const running = await serverVersion($)
  const versionOf = (version: string | null) => Number(/(\d+)$/.exec(version ?? '')?.[1] ?? 0)
  // A newer helper (started by a session running a newer copy of this mod) serves
  // everything an older page needs, so it is kept rather than replaced.
  if (running !== null && running.startsWith('gitgraph-server-') && versionOf(running) >= versionOf(SERVER_VERSION)) {
    return true
  }
  if (running !== null) {
    await $.http.fetch(`${BASE}/quit`).catch(() => null)
    await $.clock.sleep(300)
  }

  const script = `${directory}/server.py`
  await $.fs.write(script, SERVER_SOURCE)
  const started = await $.process
    .run(['/bin/sh', '-c', 'nohup python3 "$1" "$2" >/dev/null 2>&1 &', 'sh', script, String(PORT)])
    .catch(() => null)
  if (started?.exitCode !== 0) {
    return false
  }
  for (let attempt = 0; attempt < 20; attempt++) {
    if ((await serverVersion($)) === SERVER_VERSION) {
      return true
    }
    await $.clock.sleep(150)
  }

  return false
}

/**
 * Collects what this session's pages asked to add to the prompt and puts it in
 * the prompt box at the cursor. Where the box cannot take it, it is copied.
 */
async function collect($: EngineInterface, session: string, token: string): Promise<void> {
  const response = await $.http
    .fetch(`${BASE}/inbox?session=${encodeURIComponent(session)}&token=${encodeURIComponent(token)}`)
    .catch(() => null)
  if (!response?.ok) {
    return
  }
  const texts: unknown = JSON.parse(response.text)
  if (!Array.isArray(texts)) {
    return
  }
  for (const text of texts.filter((item): item is string => typeof item === 'string' && item.length > 0)) {
    const box = await $.prompt.read()
    const before = box.text.length > 0 && !/\s$/.test(box.text.slice(0, box.cursor)) ? ' ' : ''
    const filled = await $.prompt.fill({ text: `${before}${text} `, mode: 'insert' })
    if (!filled.isFilled) {
      await $.ui.copy({ text })
      $.ui.toast(`gitgraph: the prompt box could not take ${text}; copied it instead`)
    }
  }
}

/**
 * Records which repository a page's key names, so the bridge reads changes only
 * from repositories a /gitgraph run opened.
 */
async function registerRepository($: EngineInterface, directory: string, key: string, path: string): Promise<void> {
  const file = `${directory}/repos.json`
  const known: unknown = await $.fs
    .read(file)
    .then(text => JSON.parse(typeof text === 'string' ? text : '{}'))
    .catch(() => ({}))
  const repositories = typeof known === 'object' && known !== null ? (known as Record<string, string>) : {}
  await $.fs.write(file, JSON.stringify({ ...repositories, [key]: path }, null, 2))
}

function randomToken(): string {
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)

  return [...bytes].map(byte => byte.toString(16).padStart(2, '0')).join('')
}

// One background loop per load of this module, started from session.start (whose `$`
// outlives any one dispatch); a reload drops its timer and starts it again.
let poller: { cancel: () => void } | null = null

// A page waiting to be opened in the built-in browser pane, handed over by the command.
let pendingPane: string | null = null

/**
 * Asks the model to open a page in the built-in browser pane, in a turn of its own once
 * the session is idle: the pane only takes actions auto mode can review, which a mod's
 * own call is not. Falls back to the default browser, saying why, if the ask fails.
 */
async function askToOpenInPane($: EngineInterface, url: string): Promise<void> {
  try {
    await $.prompt.submit({
      text:
        `Open ${url} in the built-in browser pane (my /gitgraph page). Reuse a tab already ` +
        `showing ${BASE} if there is one. Do nothing else, and answer in one short line.`,
      asUser: true,
    })
  } catch (error) {
    $.ui.toast(`gitgraph: could not ask for the built-in browser (${String(error).slice(0, 120)}); opening your browser`)
    await openInBrowser($, url)
  }
}

/**
 * Starts the background loop: it hands a waiting page to the built-in browser pane and
 * collects this session's "add to prompt" requests once the session has a page token.
 */
async function startPolling($: EngineInterface): Promise<void> {
  if (poller) {
    return
  }
  const session = await $.session.id()
  let isBusy = false
  poller = $.clock.every(500, () => {
    if (isBusy) {
      return
    }
    isBusy = true
    const work = async () => {
      if (pendingPane) {
        const url = pendingPane
        pendingPane = null
        await askToOpenInPane($, url)
      }
      const token = await read($, bridgeToken)
      if (token) {
        await collect($, session, token)
      }
    }
    void work()
      .catch(() => undefined)
      .finally(() => {
        isBusy = false
      })
  })
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'gitgraph',
      description: 'Open the whole Git commit history as a graph page in your browser (-i: the built-in browser)',
      argumentHint: '[submodule] [-i|--internal]',
      immediate: true,
    })
    // A reload keeps the token in session state, so pages opened before it still reach us.
    await startPolling($)

    return next(e)
  })

  on('command.run', { command: 'gitgraph' }, async ($, e) => {
    const words = e.args.trim().split(/\s+/).filter(word => word.length > 0)
    const argument = words.find(word => !word.startsWith('-'))
    const wantsBuiltInBrowser = words.includes('-i') || words.includes('--internal')

    const target = await resolveTarget($, argument)
    if ('error' in target) {
      return { text: target.error }
    }

    const loaded = await loadGraph($, target)
    if ('error' in loaded) {
      return { text: loaded.error }
    }
    if (loaded.commits.length === 0) {
      return { text: `${target.repository} has no commits.` }
    }

    const home = (await $.env.get('HOME')) ?? '/tmp'
    const directory = `${home}/.claude/gitgraph`
    const name = `${loaded.repository.replace(/[^\w.-]+/g, '-')}.html`
    const isServed = await ensureServer($, directory)
    let token = await read($, bridgeToken)
    if (!token) {
      token = randomToken()
      await update($, bridgeToken, () => token)
    }
    const repo = name.replace(/\.html$/, '')
    if (isServed) {
      await registerRepository($, directory, repo, loaded.path)
    }
    const bridge = isServed ? { session: await $.session.id(), token, repo } : null
    const generatedAt = new Date(await $.clock.now()).toLocaleString('en-GB', { dateStyle: 'short', timeStyle: 'short' })
    await $.fs.write(`${directory}/${name}`, buildPage(loaded, generatedAt, bridge))

    const location = isServed ? `${BASE}/${name}` : `${directory}/${name}`
    const count = `${loaded.commits.length}${loaded.isTruncated ? ' most recent' : ''} commits`
    const note = isServed ? '' : ' (the page bridge did not start, so "Add to prompt" copies instead)'

    // Asked for the built-in browser pane (-i): the background loop asks the model to open
    // it once this command has finished. Without the pane (the terminal, other hosts) the
    // default browser opens.
    if (wantsBuiltInBrowser && isServed && poller && (await hasBrowserPane($))) {
      pendingPane = location

      return {
        text: `Git graph of ${loaded.repository} (${count}) is ready; opening it in the built-in browser: ${location}`,
      }
    }

    const isOpened = await openInBrowser($, location)

    return {
      text: isOpened
        ? `Git graph of ${loaded.repository} (${count}) opened in your browser: ${location}${note}`
        : `Git graph of ${loaded.repository} (${count}) is at ${location}; open it in a browser.${note}`,
    }
  })
}
