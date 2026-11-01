<!--
  运维明细表 —— 网关与权限中心共用的 .gtable（等价迁移自原型 console.js renderTable 3889–3922）

  原型是「列定义数组 + 两个 innerHTML 赋值」：
      gwCols(tab) / pzCols(tab) 给出每列的 { k, t, cls, w, num, v(row) }
      renderTable() 把表头与表体拼进 #ogTableHead / #ogTableBody
  这里把它拆成一个组件：列定义由父级传入，本组件只负责表头 / 表体 / 空态 / 行数，
  行内容仍然是列定义里的字符串（父级已 esc 过），用 v-html 输出。
-->
<script setup lang="ts">
import IconSprite from '@/components/IconSprite.vue'
import { opsOf } from '@/lib/util'
import type { OpsCol } from '@/lib/util'

const props = defineProps<{
  /** 表格标题前缀，如 "路由" → "路由明细" */
  title: string
  /** 明细行的中文名，用于空态文案 */
  itemName: string
  /**
   * 列定义。这里刻意用 OpsCol<any> 而不是泛型：
   * 网关与权限中心各自的行类型（GwTableRow / PzTableRow）都是「四表字段并集」，
   * 两个不同组件实例化的泛型在 SFC 里推不干净，反而会互相不兼容；
   * 列定义本身的类型安全由各自的 gwcols.ts / pzcols.ts 保证。
   */
  cols: readonly OpsCol<any>[]
  rows: readonly any[]
  /** 操作列的 data 前缀：gact → data-gact，pact → data-pact */
  actKey: string
}>()

const emit = defineEmits<{
  (e: 'act', id: string, act: string): void
}>()

/** 行点击：把最近一次点到的按钮动作抛上去（原型用事件委托） */
function onRowClick(e: MouseEvent): void {
  const el = e.target as HTMLElement | null
  const btn = el?.closest('[data-gact],[data-pact]')
  if (!btn) return
  const row = btn.closest('[data-id]')
  const id = row?.getAttribute('data-id')
  if (!id) return
  const act = btn.getAttribute(`data-${props.actKey}`)
  if (act) emit('act', id, act)
}

/** 行状态类（原型 opsOf(g.status)） */
function rowClass(status: unknown): string {
  return opsOf(String(status)).cls
}
function rowVar(status: unknown): string {
  return opsOf(String(status)).v
}
</script>

<template>
  <section class="gtable" aria-label="明细列表">
    <header class="gtable__head">
      <h3>{{ title }}</h3>
      <span class="gtable__meta"><span>{{ rows.length }}</span> 行 · 点击任意一行看详情</span>
    </header>

    <div class="gtable__scroll">
      <div class="gtable__inner">
        <div class="gtable__thead" role="row">
          <span
            v-for="c in cols"
            :key="c.k"
            class="gcell"
            :class="[c.num ? 'is-num' : '', c.cls ?? '']"
            :style="c.w ? { '--w': c.w } : undefined"
          >{{ c.t }}</span>
        </div>

        <div class="gtable__tbody" role="rowgroup">
          <p v-if="!rows.length" class="gtable__empty">
            没有匹配的{{ itemName }}，换个关键词、切个筛选，或点右上角新建一条。
          </p>

          <template v-else>
            <!-- 注意：Vue 模板里的 :key / :class 表达式是 JS 而非 TS，
                 不能写 `(r as { id: string }).id`，直接取属性即可
                 （行的形状由各页 pzcols/gwcols 的列定义负责） -->
            <div
              v-for="(r, i) in rows"
              :key="r.id ?? i"
              class="grow"
              :class="rowClass(r.status)"
              :data-id="r.id"
              role="row"
              :style="{ '--st': rowVar(r.status) }"
              @click="onRowClick"
            >
              <span
                v-for="c in cols"
                :key="c.k"
                class="gcell"
                :class="[c.num ? 'is-num' : '', c.cls ?? '']"
                :style="c.w ? { '--w': c.w } : undefined"
                v-html="c.v(r)"
              />
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- 兼容层：离屏卡片渲染，供导出 / 打印与回归测试复用（原型 595 行） -->
    <div class="reg__grid reggrid gwcardbin" role="list" hidden>
      <slot name="bin" />
    </div>
  </section>
</template>