import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { BuildResult, EnsureResult } from '../types'
import { RUNTIME_SOURCE } from './runtime'

const PORT = 47321
const BASE = `http://127.0.0.1:${PORT}`
const PYTHON_MISSING =
  'gitgraph needs Python 3 to build the page, and python3 was not found. ' +
  'On macOS, install the command line tools (xcode-select --install); elsewhere, install python3.'

const bridgeToken = atom({ plugin: 'gitgraph', key: 'token' } as const, '')

/**
 * Runs the gitgraph runtime (gitgraph/runtime/gitgraph.py, written beside the pages): it
 * answers one line of JSON, or {"error"} with a reason to show as it is.
 */
async function runRuntime<Result>(
  $: EngineInterface,
  argv: string[],
  timeoutMs: number,
): Promise<Result | { error: string }> {
  const ran = await $.process.run(['python3', ...argv], { timeoutMs }).catch(() => null)
  if (!ran || ran.exitCode === 127) {
    return { error: PYTHON_MISSING }
  }
  try {
    return JSON.parse(ran.stdout) as Result | { error: string }
  } catch {
    return { error: ran.stderr.trim().split('\n').pop() || 'The gitgraph runtime failed.' }
  }
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

    const home = (await $.env.get('HOME')) ?? '/tmp'
    const directory = `${home}/.claude/gitgraph`
    const runtime = `${directory}/gitgraph.py`
    await $.process.run(['mkdir', '-p', directory]).catch(() => null)
    await $.fs.write(runtime, RUNTIME_SOURCE)

    const ensured = await runRuntime<EnsureResult>($, [runtime, 'ensure', '--root', directory, '--port', String(PORT)], 30_000)
    if ('error' in ensured && ensured.error === PYTHON_MISSING) {
      return { text: PYTHON_MISSING }
    }
    const isServed = 'isUp' in ensured && ensured.isUp
    let token = await read($, bridgeToken)
    if (!token) {
      token = randomToken()
      await update($, bridgeToken, () => token)
    }
    const prompt = JSON.stringify({ session: await $.session.id(), token })
    const built = await runRuntime<BuildResult>(
      $,
      [
        runtime,
        'build',
        '--repo',
        '.',
        ...(argument ? ['--submodule', argument] : []),
        '--out',
        directory,
        '--prompt',
        prompt,
        '--rerun',
        '/gitgraph',
      ],
      180_000,
    )
    if ('error' in built) {
      return { text: built.error }
    }

    const name = built.file.split('/').pop() ?? ''
    const location = isServed ? `${BASE}/${name}` : built.file
    const count = `${built.commits}${built.isTruncated ? ' most recent' : ''} commits`
    const note = isServed ? '' : ' (the gitgraph helper did not start, so changes, find by file and "Add to prompt" are off)'

    // Asked for the built-in browser pane (-i): the background loop asks the model to open
    // it once this command has finished. Without the pane (the terminal, other hosts) the
    // default browser opens.
    if (wantsBuiltInBrowser && isServed && poller && (await hasBrowserPane($))) {
      pendingPane = location

      return {
        text: `Git graph of ${built.repository} (${count}) is ready; opening it in the built-in browser: ${location}`,
      }
    }

    const isOpened = await openInBrowser($, location)

    return {
      text: isOpened
        ? `Git graph of ${built.repository} (${count}) opened in your browser: ${location}${note}`
        : `Git graph of ${built.repository} (${count}) is at ${location}; open it in a browser.${note}`,
    }
  })
}
