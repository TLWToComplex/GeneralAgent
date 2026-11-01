<!--
  表格视图 —— 等价迁移自原型 console.js renderList 559–588。

  八列：会话 / 智能体 / workspace / 状态 / 进度 / CPU·GPU / 已运行 / 归属。
  点任意一行选中会话并展开详情抽屉（原型 data-id 委托 + selectSession(id, true)）。
-->
<script setup lang="ts">
import { computed } from 'vue'
import { useSessionStore } from '@/stores/session'
import { useOverlayStore } from '@/stores/overlay'
import { ST } from '@/data/sessions'

const session = useSessionStore()
const overlay = useOverlayStore()

const rows = computed(() => session.filtered)

function onRow(id: string): void {
  session.selectSession(id)
  overlay.openDrawer('session', id, session.byId(id)?.name ?? id)
}
</script>

<template>
  <div class="view view--list" :class="{ 'is-on': session.view === 'list' }" role="tabpanel">
    <p v-if="!rows.length" class="view__empty">
      没有匹配的会话，换个关键词或切回「全部」。
    </p>

    <table v-else class="ltable">
      <thead>
        <tr>
          <th>会话</th><th>智能体</th><th>workspace</th><th>状态</th>
          <th>进度</th><th>CPU / GPU</th><th>已运行</th><th>归属</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="s in rows"
          :key="s.id"
          :class="[ST[s.state].cls, { 'is-active': session.selId === s.id }]"
          :data-id="s.id"
          @click="onRow(s.id)"
        >
          <td class="is-key">{{ s.code }} · {{ s.name }}</td>
          <td class="is-mono">{{ s.agent }}</td>
          <td class="is-mono">{{ s.ws }}</td>
          <td>
            <span class="stchip" :class="{ 'is-blink': ST[s.state].blink }">
              {{ ST[s.state].cn }}
            </span>
          </td>
          <td><div class="lbar"><i data-role="prog" :style="{ width: `${s.prog}%` }" /></div></td>
          <td class="is-mono">{{ s.cpu }} · {{ s.gpu }}</td>
          <td class="is-mono" data-role="dur">{{ session.fmtDur(s.elapsed) }}</td>
          <td class="is-mono">{{ s.owner }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>