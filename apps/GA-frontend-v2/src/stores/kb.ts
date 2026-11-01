/* ============================================================================
   知识库中心 store —— 文档库 / 问答库 / 表格库 / 图谱库

   等价迁移自原型 console.js 的这几处：
     · 2557–2644  KBST / KBSTCN / KBKIND / KBCLS / KBS / Kb（UI 状态）
     · 2647–2669  kbList / kbHay / kbFiltered / kbCounts / kbById / kbNum
     · 2672–2723  renderKbKpis / updateKbKpis
     · 2726–2736  fillKbOwners        归属下拉
     · 2739–2822  renderKbCards（计数、tab 徽标、页头、试跑面板的当前库锁定）
     · 2824–2850  kbAskOpen / kbAskClose / updateKbAskCur     检索试跑面板
     · 2852–2914  kbRetrieve / kbAskRun                       离线假检索
     · 2917–2998  kbFormOpen / kbFormSubmit                   新建 / 编辑
     · 3001–3023  startKbIndex                                重建索引演示
     · 5335–5359  心跳里的知识库页分支
   ========================================================================== */

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { KBKIND, KBS, KBST, KBSTCN } from '@/data/kb'
import type { KbItem, KbKind, KbState } from '@/data/kb'
import { clamp, esc, rand } from '@/lib/util'
import { useUiStore } from '@/stores/ui'
import { useOverlayStore } from '@/stores/overlay'

export { KBKIND, KBST, KBSTCN }
export type { KbItem, KbKind, KbState }

export type KbFilter = 'all' | KbState

/** tab 元信息（原型 renderKbCards 里的 tab 徽标与新建按钮文案） */
export const KB_TABS: Record<KbKind, { item: string; icon: string | null }> = {
  doc: { item: '文档知识库', icon: 'i-book' },
  qa: { item: '问答知识库', icon: 'i-chat' },
  sheet: { item: '表格知识库', icon: 'i-table' },
  graph: { item: '图谱知识库', icon: 'i-graph' },
}

/** 原型 kbNum()：万位折算 */
export function kbNum(n: number): string {
  return n >= 10000 ? `${(n / 10000).toFixed(1)}w` : String(n)
}

/** 一条召回结果（kbRetrieve 的输出） */
export interface KbHit {
  title: string
  at: string
  text: string
  score: number
}

/** 检索试跑表单模型 */
export interface KbFormModel {
  kbName: string
  kbOwner: string
  kbLang: string
  kbChunk: string
  kbOverlap: string
  kbEmbed: string
  kbStore: string
  kbStatus: KbState
  kbScope: string
}

export const useKbStore = defineStore('kb', () => {
  const ui = useUiStore()
  const overlay = useOverlayStore()

  /* ---------------------------------------------------------------- 可变副本 */
  const items = ref<KbItem[]>(structuredClone(KBS) as KbItem[])

  /* ---------------------------------------------------------------- UI 状态 */
  const tab = ref<KbKind>('doc')
  const filter = ref<KbFilter>('all')
  const owner = ref<'all' | string>('all')
  const q = ref('')
  let seq = 0

  function setTab(t: KbKind): void {
    tab.value = t
    filter.value = 'all'
    q.value = ''
    owner.value = 'all'
  }

  function setQuery(v: string): void {
    q.value = v
    if (ui.query !== v) ui.query = v
  }

  function setOwner(o: string): void {
    owner.value = o
  }

  /** 状态筛选条的点击（原型 console.html 知识库页的 data-kst） */
  function setFilter(f: KbFilter): void {
    filter.value = f
  }

  /* ---------------------------------------------------------------- 查询 */
  /** 原型 kbList()：按当前 tab 的类型过滤 */
  const list = computed<KbItem[]>(() => items.value.filter((k) => k.kind === tab.value))

  function byId(id: string | null): KbItem | null {
    if (!id) return null
    return items.value.find((k) => k.id === id) ?? null
  }

  function hay(k: KbItem): string {
    return (
      `${k.name} ${k.owner} ${k.desc} ${k.scope} ${k.embed} ${k.store} ` +
      `${KBKIND[k.kind]} ${k.index}`
    ).toLowerCase()
  }

  function filteredOf(byState: boolean): KbItem[] {
    return list.value.filter((k) => {
      if (byState && filter.value !== 'all' && k.status !== filter.value) return false
      if (owner.value !== 'all' && k.owner !== owner.value) return false
      if (q.value && hay(k).indexOf(q.value.toLowerCase()) < 0) return false
      return true
    })
  }

  const filtered = computed<KbItem[]>(() => filteredOf(true))

  const counts = computed(() => {
    const c = { all: 0, ready: 0, indexing: 0, paused: 0, failed: 0 }
    filteredOf(false).forEach((k) => {
      c.all++
      c[k.status]++
    })
    return c
  })

  const tabCounts = computed(() => ({
    doc: items.value.filter((k) => k.kind === 'doc').length,
    qa: items.value.filter((k) => k.kind === 'qa').length,
    sheet: items.value.filter((k) => k.kind === 'sheet').length,
    graph: items.value.filter((k) => k.kind === 'graph').length,
  }))

  /** 归属下拉的选项：当前 tab 出现过的归属（去重） */
  const owners = computed<string[]>(() => {
    const out: string[] = []
    list.value.forEach((k) => {
      if (out.indexOf(k.owner) < 0) out.push(k.owner)
    })
    return out
  })

  /** 页头汇总文案：'8 个知识库 · 文档知识库 4 个' */
  const headCount = computed(
    () => `${items.value.length} 个知识库 · ${KBKIND[tab.value]} ${list.value.length} 个`,
  )
  const newLabel = computed(() => `新建${KBKIND[tab.value]}`)

  /* ---------------------------------------------------------------- KPI */
  const kpis = computed(() => {
    let docs = 0
    let chunks = 0
    let calls = 0
    let hit = 0
    let ms = 0
    let n = 0
    let busy = 0
    items.value.forEach((k) => {
      docs += k.docs
      chunks += k.chunks
      calls += k.calls
      const h = parseFloat(k.hit)
      if (!isNaN(h)) hit += h
      const m = parseInt(String(k.recall).replace(/[^\d]/g, ''), 10)
      if (!isNaN(m)) {
        ms += m
        n++
      }
      if (k.status === 'indexing' || k.status === 'failed') busy++
    })
    return {
      total: items.value.length,
      ready: items.value.filter((k) => k.status === 'ready').length,
      docs: kbNum(docs),
      chunks: kbNum(chunks),
      hit: `${(hit / (items.value.length || 1)).toFixed(1)}%`,
      recall: `${Math.round(ms / (n || 1))} ms`,
      calls: calls >= 1000 ? `${(calls / 1000).toFixed(1)}k` : String(calls),
      busy,
    }
  })

  /* ---------------------------------------------------------------- 检索试跑 */
  const askOpen = ref(false)
  /** 当前锁定的库（原型 Kb.cur） */
  const curId = ref<string | null>(null)
  /** 用户输入的问题 */
  const askQ = ref('')
  /** Top-K 选择（原型 #kbAskTopk） */
  const askTopk = ref(3)
  /** 是否已试跑过（原型 out 上的 data-done） */
  const askDone = ref(false)

  const cur = computed<KbItem | null>(() => byId(curId.value) ?? list.value[0] ?? null)

  /** 面板头部「当前库：…」（原型 updateKbAskCur） */
  const askCurText = computed(() => {
    const k = cur.value
    return k
      ? `当前库：${k.name} · ${KBKIND[k.kind]}（${kbNum(k.chunks)} 个分片 · 命中率 ${k.hit}）`
      : '当前库：—'
  })

  function openAsk(preset?: string): void {
    if (preset) {
      const k = byId(preset)
      if (k) curId.value = k.id
    }
    askOpen.value = true
    /* 面板打开时把当前库的示例问题填进输入框（仅当用户还没输入过） */
    const k = cur.value
    if (k && !askDone.value && !askQ.value.trim()) askQ.value = k.sample.q
  }

  function closeAsk(): void {
    askOpen.value = false
  }

  /**
   * 离线假检索：命中的分片由库的样例 + 语料规模确定性派生，
   * 避免每次刷新都变（原型 kbRetrieve，逐条照搬）。
   */
  function retrieve(k: KbItem, query: string, topk: number): KbHit[] {
    const base = k.sample
    const words = String(query || '')
      .replace(/[？?。，,、；;：:！!]/g, ' ')
      .split(/\s+/)
      .filter((w) => w.length >= 2)
    const pool: KbHit[] = [
      { title: base.cites[0]![0], at: base.cites[0]![1], text: base.a, score: 0.94 },
      {
        title: base.cites[1] ? base.cites[1][0] : base.cites[0]![0],
        at: base.cites[1] ? base.cites[1][1] : base.cites[0]![1],
        text: k.desc,
        score: 0.87,
      },
      {
        title: '切片元数据',
        at: `chunk ${1 + (k.chunks % 97)} / ${kbNum(k.chunks)}`,
        text:
          `切片长度 ${k.size}，重叠 ${k.overlap}，切分方式 ${k.win}，` +
          `向量模型 ${k.embed}，索引 ${k.index}。`,
        score: 0.81,
      },
      {
        title: '语料范围说明',
        at: k.owner,
        text: `本库覆盖：${k.scope}；累计 ${kbNum(k.docs)} 份语料，最近更新 ${k.updated}。`,
        score: 0.74,
      },
      {
        title: '检索配置',
        at: 'Top-K / 阈值',
        text:
          '默认 Top-K 3、相似度阈值 0.62；' +
          '跨库检索先按命中率排序再合并去重，单次最多返回 8 个分片。',
        score: 0.68,
      },
      {
        title: '同义词扩展',
        at: '归一化词典',
        text:
          `与「${words[0] || '该问题'}」相关的同义表述已在归一化词典内建映射，` +
          '命中时按权重 0.8 折算后参与排序。',
        score: 0.63,
      },
      {
        title: '历史标注',
        at: '人工反馈',
        text:
          `该问题近 30 天被标注为「回答准确」${12 + (k.docs % 40)} 次，` +
          '未出现「答非所问」反馈。',
        score: 0.58,
      },
      {
        title: '相邻分片',
        at: 'chunk +1',
        text:
          '紧邻的下一个分片包含例外情况与操作示例，' +
          '长回答拼接时会一并带上以便读者核对边界条件。',
        score: 0.52,
      },
    ]
    return pool.slice(0, clamp(topk, 1, 8))
  }

  /** 最近一次试跑的召回结果 */
  const askHits = ref<KbHit[]>([])
  const askEmpty = ref(false)

  /** 原型 kbAskRun() */
  function runAsk(): boolean {
    const k = cur.value
    if (!k) {
      askEmpty.value = true
      askHits.value = []
      return false
    }
    const question = askQ.value.trim()
    if (!question) {
      ui.pushText('先输入一个问题再检索')
      return false
    }
    askEmpty.value = false
    askDone.value = true
    askHits.value = retrieve(k, question, askTopk.value)
    k.calls += rand(1, 4)
    return true
  }

  /** 面板里「合成答案」用的引用列表 */
  const askCites = computed(() => cur.value?.sample.cites ?? [])

  /* ---------------------------------------------------------------- 表单 */
  const formSub = computed(() => {
    const kind = overlay.modalEditingId ? kindOf(overlay.modalEditingId) : tab.value
    return `类型：${KBKIND[kind]}。切片与向量化参数会决定召回质量，保存后按新参数重建索引。`
  })
  const formHint = computed(() =>
    overlay.modalEditingId
      ? '修改切片或向量模型会触发一次全量重建，期间检索自动走旧索引，不影响线上。'
      : '新建后用卡片上的「试跑」验证召回，再挂载到需要的智能体上。',
  )

  /** 编辑时该走哪种类型（新建时看当前 tab） */
  function kindOf(id: string | null): KbKind {
    return byId(id)?.kind ?? tab.value
  }

  function formModel(id: string | null): KbFormModel {
    const item = id ? byId(id) : null
    const kind = item?.kind ?? tab.value
    return {
      kbName: item?.name ?? '',
      kbOwner: item?.owner ?? '',
      kbLang: item?.lang ?? '中文',
      kbChunk:
        item?.size ?? (kind === 'qa' ? '一问一答' : kind === 'sheet' ? '一条一口径' : '512 字'),
      kbOverlap: item?.overlap ?? (kind === 'doc' ? '64 字' : '—'),
      kbEmbed: item?.embed ?? 'bge-m3-1024',
      kbStore: item?.store ?? 'milvus-corp',
      kbStatus: item?.status ?? 'ready',
      kbScope: item?.scope ?? '',
    }
  }

  function submitForm(v: KbFormModel): boolean {
    const name = v.kbName.trim()
    if (!name) {
      ui.pushHtml('请先填写知识库名称')
      return false
    }
    const kind = overlay.modalEditingId ? kindOf(overlay.modalEditingId) : tab.value
    const status = v.kbStatus
    const data = {
      name,
      owner: v.kbOwner.trim() || '平台公共',
      lang: v.kbLang,
      size: v.kbChunk.trim() || '512 字',
      overlap: v.kbOverlap.trim() || '64 字',
      embed: v.kbEmbed,
      store: v.kbStore,
      metric: v.kbStore === 'elasticsearch-knn' ? '混合检索' : '余弦相似度',
      scope: v.kbScope.trim() || '待补充语料范围',
      status,
      prog: status === 'indexing' ? 12 : status === 'ready' ? 100 : 0,
      updated: '刚刚',
    }

    const editingId = overlay.modalEditingId
    const editing = editingId ? byId(editingId) : null
    if (editing) {
      Object.assign(editing, data)
      ui.pushText(`知识库 ${name} 已更新`, [`${editing.size} / ${editing.embed} · ${editing.store}`])
      return true
    }

    seq++
    const fresh: KbItem = {
      id: `kb-n${seq}`,
      kind,
      name,
      owner: data.owner,
      desc: `新建的${KBKIND[kind]}，尚未接入正式语料`,
      docs: 0,
      chunks: 0,
      size: data.size,
      overlap: data.overlap,
      win: '语义段落',
      embed: data.embed,
      store: data.store,
      index:
        data.store === 'milvus-corp'
          ? 'HNSW · M32 / ef256'
          : data.store === 'pgvector-ha'
            ? 'IVF-Flat · nlist 4096'
            : 'HNSW + BM25 融合',
      metric: data.metric,
      hit: '—',
      recall: '—',
      calls: 0,
      updated: '刚刚',
      lang: data.lang,
      status: data.status,
      prog: data.prog,
      scope: data.scope,
      rows: 0,
      sample: {
        q: '这个库暂时还没有语料，检索会返回什么？',
        a: '语料为空时检索只会返回切片元数据与配置说明；接入语料并完成首次索引后才会产出正式召回结果。',
        cites: [
          ['新建向导', '第 1 步 · 语料接入'],
          ['索引说明', '首次重建'],
        ],
      },
    }
    items.value = [fresh, ...items.value]
    curId.value = fresh.id
    ui.pushText(`${KBKIND[kind]} ${name} 已创建`, ['已排入首次索引重建队列'])
    return true
  }

  /* ---------------------------------------------------------------- 重建索引 */
  const indexTimers = new Map<string, number>()

  /** 原型 startKbIndex：状态切 indexing，进度按节奏推到 100 再回 ready */
  function startIndex(id: string): void {
    const k = byId(id)
    if (!k || k.status === 'indexing') return
    k.status = 'indexing'
    k.prog = 6
    k.updated = '索引中'
    ui.pushText(`开始重建 ${k.name} 索引`, [
      `${k.size} / ${k.overlap} · ${k.embed} → ${k.store}`,
    ])
    const old = indexTimers.get(id)
    if (old !== undefined) window.clearInterval(old)
    const timer = window.setInterval(() => {
      k.prog = clamp(k.prog + rand(8, 19), 6, 100)
      if (k.prog >= 100) {
        window.clearInterval(timer)
        indexTimers.delete(id)
        k.status = 'ready'
        k.prog = 100
        k.updated = '刚刚'
        const h = parseFloat(k.hit)
        k.hit = `${(isNaN(h) ? 88 : clamp(h + rand(-3, 4) / 10, 70, 99.4)).toFixed(1)}%`
        ui.pushText(`${k.name} 索引重建完成`, [`${kbNum(k.chunks)} 个分片 · 命中率 ${k.hit}`])
      }
    }, 600)
    indexTimers.set(id, timer)
    ui.registerTimer(timer)
  }

  function stopAllIndexTimers(): void {
    indexTimers.forEach((t) => window.clearInterval(t))
    indexTimers.clear()
  }

  /* ---------------------------------------------------------------- 行内动作 */
  function toggle(id: string): void {
    const item = byId(id)
    if (!item) return
    if (item.status === 'paused') {
      item.status = 'ready'
      ui.pushHtml(`<b>${esc(item.name)}</b> 已启用`)
    } else {
      item.status = 'paused'
      ui.pushHtml(`<b>${esc(item.name)}</b> 已暂停`)
    }
  }

  function askDelete(id: string): void {
    const item = byId(id)
    if (!item) return
    overlay.askConfirm({
      title: `删除${KBKIND[item.kind]}`,
      text:
        `确认删除 <b>${esc(item.name)}</b>？` +
        '删除后已挂载该库的智能体会立即失去这部分语料，索引与分片一并回收；' +
        '操作会记入审计流水，不可恢复。',
      mode: 'kb',
      id: item.id,
      name: item.name,
    })
  }

  function doDelete(id: string): void {
    const item = byId(id)
    if (!item) return
    items.value = items.value.filter((k) => k.id !== id)
    if (curId.value === id) curId.value = null
    ui.pushText(`${item.name} 已删除`, ['审计流水已记录'])
  }

  /* ---------------------------------------------------------------- 心跳 */
  /** 累加检索量、抖动命中率与召回耗时（原型 5335–5359） */
  function beat(): void {
    items.value.forEach((k) => {
      if (k.status === 'paused') return
      k.calls += rand(1, 9)
      if (Math.random() < 0.14) {
        const h = parseFloat(k.hit)
        if (!isNaN(h)) k.hit = `${clamp(h + rand(-3, 3) / 10, 70, 99.4).toFixed(1)}%`
      }
      if (Math.random() < 0.12) {
        const ms = parseInt(String(k.recall).replace(/[^\d]/g, ''), 10)
        if (!isNaN(ms)) k.recall = `P95 ${Math.round(ms * (1 + rand(-10, 10) / 100))} ms`
      }
    })
  }

  return {
    items,
    list,

    tab,
    filter,
    owner,
    q,
    setTab,
    setQuery,
    setFilter,
    setOwner,

    byId,
    kindOf,
    filtered,
    counts,
    tabCounts,
    owners,
    headCount,
    newLabel,
    kpis,

    askOpen,
    curId,
    cur,
    askQ,
    askTopk,
    askDone,
    askEmpty,
    askHits,
    askCites,
    askCurText,
    openAsk,
    closeAsk,
    retrieve,
    runAsk,

    formSub,
    formHint,
    formModel,
    submitForm,

    startIndex,
    stopAllIndexTimers,
    toggle,
    askDelete,
    doDelete,
    beat,
  }
})