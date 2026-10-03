/** What `gitgraph.py ensure` prints: whether the helper listens on the port. */
export type EnsureResult = { isUp: boolean }

/** What `gitgraph.py build` prints: the page written and what it holds. */
export type BuildResult = {
  file: string
  key: string
  repository: string
  commits: number
  isTruncated: boolean
}

declare module 'claude-code' {
  interface PluginState {
    gitgraph: { token: string }
  }
}
