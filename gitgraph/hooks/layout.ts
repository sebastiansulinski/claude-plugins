import type { GitGraph, GraphCommit, GraphEdge, GraphRef } from '../types'

const FIELD = '\x1f'
const RECORD = '\x1e'
const END = '\x1d'

// Each record opens with RECORD and its fields close with END, so the --shortstat
// line git prints after the format lands inside the record it belongs to.
export const LOG_ARGUMENTS = [
  '--topo-order',
  '--decorate=full',
  '--abbrev=8',
  '--shortstat',
  `--format=%x1e${['%H', '%h', '%P', '%p', '%D', '%an', '%ae', '%cn', '%ce', '%at', '%ct', '%s', '%b'].join('%x1f')}%x1d`,
]

const statOf = (text: string, word: RegExp): number => Number(word.exec(text)?.[1] ?? 0)

export const PALETTE = ['#a855f7', '#22c55e', '#f59e0b', '#3b82f6', '#ec4899', '#14b8a6', '#ef4444', '#84cc16']

type RawCommit = Omit<GraphCommit, 'row' | 'lane'> & { parents: string[] }

/**
 * Orders and names one commit's refs, from a `--decorate=full` decoration:
 * the checked-out branch first, then local branches, tags and remote
 * branches. A remote branch of the same name as a local one joins it
 * (`origin & main`); each remote's HEAD is dropped.
 */
function parseRefs(
  decoration: string,
): Pick<GraphCommit, 'refs' | 'isHead' | 'branches' | 'remotes' | 'tags' | 'headBranch'> {
  let isHead = false
  let head: string | null = null
  const locals: string[] = []
  const tags: string[] = []
  const remotes: string[] = []

  for (const entry of decoration.split(', ').filter(part => part.length > 0)) {
    if (entry === 'HEAD') {
      isHead = true
    } else if (entry.startsWith('HEAD -> refs/heads/')) {
      isHead = true
      head = entry.slice('HEAD -> refs/heads/'.length)
    } else if (entry.startsWith('refs/heads/')) {
      locals.push(entry.slice('refs/heads/'.length))
    } else if (entry.startsWith('tag: refs/tags/')) {
      tags.push(entry.slice('tag: refs/tags/'.length))
    } else if (entry.startsWith('refs/remotes/') && !entry.endsWith('/HEAD')) {
      remotes.push(entry.slice('refs/remotes/'.length))
    }
  }

  const raw = {
    branches: head === null ? locals : [head, ...locals],
    remotes: [...remotes],
    tags: [...tags],
    headBranch: head,
  }

  const withRemotes = (branch: string): string => {
    const matching = remotes.filter(remote => remote.slice(remote.indexOf('/') + 1) === branch)
    for (const remote of matching) {
      remotes.splice(remotes.indexOf(remote), 1)
    }

    return [...matching.map(remote => remote.slice(0, remote.indexOf('/'))), branch].join(' & ')
  }

  const refs: GraphRef[] = [
    ...(head === null ? [] : [{ label: withRemotes(head), kind: 'head' as const }]),
    ...locals.map(branch => ({ label: withRemotes(branch), kind: 'branch' as const })),
    ...tags.map(tag => ({ label: tag, kind: 'tag' as const })),
  ]

  return { refs: [...refs, ...remotes.map(remote => ({ label: remote, kind: 'remote' as const }))], isHead, ...raw }
}

/**
 * Splits `git log` output written with LOG_ARGUMENTS into commits, newest
 * first.
 */
export function parseLog(stdout: string): RawCommit[] {
  return stdout
    .split(RECORD)
    .filter(record => record.includes(END))
    .map(record => {
      const [fieldsText = '', statText = ''] = record.split(END)
      const [
        fullHash = '',
        hash = '',
        parents = '',
        parentHashes = '',
        decoration = '',
        author = '',
        authorEmail = '',
        committer = '',
        committerEmail = '',
        time = '0',
        commitTime = '0',
        subject = '',
        body = '',
      ] = fieldsText.split(FIELD)

      return {
        fullHash,
        hash,
        parents: parents.split(' ').filter(parent => parent.length > 0),
        parentHashes: parentHashes.split(' ').filter(parent => parent.length > 0),
        ...parseRefs(decoration),
        author,
        authorEmail,
        committer,
        committerEmail,
        isCommittedByOther: committer !== author,
        time: Number(time),
        commitTime: Number(commitTime),
        subject,
        body: body.trim(),
        stats: {
          files: statOf(statText, /(\d+) files? changed/),
          insertions: statOf(statText, /(\d+) insertions?/),
          deletions: statOf(statText, /(\d+) deletions?/),
        },
      }
    })
}

/**
 * Assigns every commit a lane (a column of the graph) and every parent link
 * an edge: the edge leaves the child, may bend once at the child's row into
 * the lane it runs down, and may bend again at the parent's row.
 *
 * Commits arrive newest first and keep that order as rows. A parent outside
 * the loaded set leaves an edge with parentRow -1, drawn running off the
 * bottom.
 */
export function layoutGraph(raw: RawCommit[]): Pick<GitGraph, 'commits' | 'edges' | 'lanes'> {
  const slots: (string | null)[] = []
  const pending: number[][] = []
  const edges: GraphEdge[] = []

  const freeSlot = (): number => {
    const index = slots.indexOf(null)

    return index === -1 ? slots.length : index
  }

  const commits = raw.map((commit, row): GraphCommit => {
    const matching = slots.flatMap((hash, slot) => (hash === commit.fullHash ? [slot] : []))
    const lane = matching[0] ?? freeSlot()

    for (const slot of matching) {
      for (const edgeIndex of pending[slot] ?? []) {
        const edge = edges[edgeIndex]
        if (edge) {
          edge.parentRow = row
          edge.parentLane = lane
        }
      }
      slots[slot] = null
      pending[slot] = []
    }

    slots[lane] = null
    commit.parents.forEach((parent, position) => {
      let slot = lane

      if (position > 0) {
        slot = slots.indexOf(parent)
        if (slot === -1) {
          slot = freeSlot()
        }
      }

      slots[slot] = parent
      edges.push({ childRow: row, childLane: lane, lane: slot, parentRow: -1, parentLane: slot })
      pending[slot] = [...(pending[slot] ?? []), edges.length - 1]
    })

    const { parents, ...rest } = commit

    return { ...rest, row, lane }
  })

  const lanes = Math.max(slots.length, ...commits.map(commit => commit.lane + 1), 0)

  return { commits, edges, lanes }
}
