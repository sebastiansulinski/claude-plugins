export type GraphRef = { label: string; kind: 'head' | 'branch' | 'tag' | 'remote' }

export type GraphCommit = {
  row: number
  lane: number
  fullHash: string
  hash: string
  refs: GraphRef[]
  branches: string[]
  remotes: string[]
  tags: string[]
  headBranch: string | null
  isHead: boolean
  parentHashes: string[]
  author: string
  authorEmail: string
  committer: string
  committerEmail: string
  isCommittedByOther: boolean
  time: number
  commitTime: number
  subject: string
  body: string
  stats: { files: number; insertions: number; deletions: number }
}

export type GraphEdge = {
  childRow: number
  childLane: number
  lane: number
  parentRow: number
  parentLane: number
}

export type GitGraph = {
  repository: string
  path: string
  commits: GraphCommit[]
  edges: GraphEdge[]
  lanes: number
  isTruncated: boolean
}

declare module 'claude-code' {
  interface PluginState {
    gitgraph: { token: string }
  }
}
