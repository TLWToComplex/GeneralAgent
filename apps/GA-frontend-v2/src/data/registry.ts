/* ============================================================================
   镜像中心数据 —— 等价迁移自原型 console.js 第 1313–1365 行。
   ========================================================================== */

/** 镜像同步状态键（REG 的键 + all 筛选项） */
export type RegState = 'all' | 'synced' | 'outdated' | 'syncing' | 'failed'

/** 镜像自身的状态（不含 all） */
export type ImageStatus = 'synced' | 'outdated' | 'syncing' | 'failed'

export interface RegMeta {
  cn: string
  cls: string
}

export const REG: Record<RegState, RegMeta> = {
  all:      { cn: '已同步',  cls: 's-idle'    },
  synced:   { cn: '已同步',  cls: 's-idle'    },
  outdated: { cn: '待更新',  cls: 's-queue'   },
  syncing:  { cn: '同步中',  cls: 's-running' },
  failed:   { cn: '同步失败', cls: 's-fail'   },
}

export const RSTATES: readonly RegState[] = ['all', 'synced', 'outdated', 'syncing', 'failed']

export interface RegFilter {
  filter: RegState
  repo: string
  q: string
}

export const Reg: RegFilter = { filter: 'all', repo: 'all', q: '' }

export interface ImageTag {
  v: string
  size: string
  latest?: boolean
}

export interface RegistryImage {
  id: string
  name: string
  ns: string
  repo: string
  tags: ImageTag[]
  arch: string
  layers: number
  base: string
  pulls: number
  copies: string[]
  status: ImageStatus
  digest: string
  elapsed: number
  prog: number
  ago: string
}

export const IMAGES: RegistryImage[] = [
  { id: 'img-01', name: 'agent-runtime', ns: 'internal/agents', repo: 'registry.internal',
    tags: [{ v: '24.09', size: '1.42 GB', latest: true }, { v: '24.07', size: '1.38 GB' }, { v: '24.05', size: '1.35 GB' }],
    arch: 'amd64 / arm64', layers: 31, base: 'ubuntu:22.04', pulls: 4821, copies: ['cluster-a', 'cluster-b'],
    status: 'synced', digest: 'sha256:9f2ab7…c41d', elapsed: 0, prog: 100, ago: '12 分钟前' },
  { id: 'img-02', name: 'infer-gateway-qwen', ns: 'internal/serving', repo: 'registry.internal',
    tags: [{ v: 'v3.2-2411', size: '7.86 GB', latest: true }, { v: 'v3.1-2409', size: '7.71 GB' }],
    arch: 'amd64', layers: 68, base: 'nvidia/cuda:12.4', pulls: 1264, copies: ['cluster-a'],
    status: 'syncing', digest: 'sha256:4c81de…0a77', elapsed: 0, prog: 42, ago: '同步中' },
  { id: 'img-03', name: 'vector-retriever', ns: 'internal/serving', repo: 'harbor.corp',
    tags: [{ v: '1.9.4', size: '2.11 GB', latest: true }, { v: '1.9.2', size: '2.05 GB' }],
    arch: 'amd64', layers: 44, base: 'debian:12-slim', pulls: 2980, copies: ['cluster-a', 'cluster-b', 'cluster-c'],
    status: 'synced', digest: 'sha256:77be41…3f90', elapsed: 0, prog: 100, ago: '1 小时前' },
  { id: 'img-04', name: 'skill-sandbox', ns: 'internal/skills', repo: 'registry.internal',
    tags: [{ v: '3.14.0', size: '1.08 GB', latest: true }, { v: '3.13.2', size: '1.04 GB' }],
    arch: 'amd64 / arm64', layers: 26, base: 'python:3.12-slim', pulls: 3512, copies: ['cluster-a'],
    status: 'outdated', digest: 'sha256:1d90ac…8b52', elapsed: 0, prog: 0, ago: '2 天前' },
  { id: 'img-05', name: 'kb-indexer', ns: 'internal/data', repo: 'harbor.corp',
    tags: [{ v: '2.3.1', size: '1.64 GB', latest: true }],
    arch: 'amd64', layers: 37, base: 'debian:12-slim', pulls: 1043, copies: ['cluster-b'],
    status: 'failed', digest: 'sha256:8e4011…77ca', elapsed: 0, prog: 0, ago: '18 分钟前' },
  { id: 'img-06', name: 'a100-inference', ns: 'internal/serving', repo: 'registry-2.internal',
    tags: [{ v: '2.4.0', size: '12.40 GB', latest: true }, { v: '2.3.8', size: '12.10 GB' }],
    arch: 'amd64', layers: 92, base: 'nvidia/cuda:12.4', pulls: 726, copies: ['cluster-c'],
    status: 'synced', digest: 'sha256:b2f7c3…1de4', elapsed: 0, prog: 100, ago: '3 小时前' },
  { id: 'img-07', name: 'embed-bge-m3', ns: 'internal/models', repo: 'registry.internal',
    tags: [{ v: '1.2.0', size: '4.35 GB', latest: true }],
    arch: 'amd64', layers: 52, base: 'nvidia/cuda:12.4', pulls: 1876, copies: ['cluster-a', 'cluster-b'],
    status: 'syncing', digest: 'sha256:c53a90…4b18', elapsed: 0, prog: 68, ago: '同步中' },
  { id: 'img-08', name: 'flow-orchestrator', ns: 'internal/flow', repo: 'registry-2.internal',
    tags: [{ v: '0.9.7', size: '0.86 GB', latest: true }, { v: '0.9.5', size: '0.82 GB' }],
    arch: 'amd64 / arm64', layers: 19, base: 'alpine:3.20', pulls: 934, copies: ['cluster-c'],
    status: 'outdated', digest: 'sha256:5a0d2e…6c71', elapsed: 0, prog: 0, ago: '5 天前' },
  { id: 'img-09', name: 'mcp-fs-browser', ns: 'internal/tools', repo: 'harbor.corp',
    tags: [{ v: '4.1.0', size: '0.52 GB', latest: true }],
    arch: 'amd64', layers: 14, base: 'node:22-slim', pulls: 2415, copies: ['cluster-a'],
    status: 'synced', digest: 'sha256:e91b40…2087', elapsed: 0, prog: 100, ago: '6 小时前' },
  { id: 'img-10', name: 'eval-harness', ns: 'internal/quality', repo: 'harbor.corp',
    tags: [{ v: '1.6.3', size: '1.20 GB', latest: true }, { v: '1.6.0', size: '1.17 GB' }],
    arch: 'amd64', layers: 29, base: 'python:3.12-slim', pulls: 688, copies: ['cluster-b'],
    status: 'outdated', digest: 'sha256:3c7f55…aa10', elapsed: 0, prog: 0, ago: '1 天前' },
]