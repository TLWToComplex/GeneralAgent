<!--
  卡片视图 —— 等价迁移自原型 console.js renderCards 525–557。

  每张卡：编号 + 名称（含 agent · workspace）+ 状态徽标 → 当前任务气泡
           → 进度条 → 四项元信息 → 三个操作（详情 / 定位工位 / 日志）。
-->
<script setup lang="ts">
import { computed } from 'vue'
import IconSprite from '@/components/IconSprite.vue'
import { useSessionStore } from '@/stores/session'
import { useOverlayStore } from '@/stores/overlay'
import { ST } from '@/data/sessions'

const session = useSessionStore()
const overlay = useOverlayStore()

const cards = computed(() => session.filtered)

/** 三个操作（原型 data-act 委托） */
function onAct(e: MouseEvent): void {
  const btn = (e.target as HTMLElement | null)?.closest('[data-act]')
  if (!btn) return
  const id = btn.closest('[data-id]')?.getAttribute('data-id')
  if (!id) return
  switch (btn.getAttribute('data-act')) {
    case 'open':
      session.selectSession(id)
      overlay.openDrawer('session', id, session.byId(id)?.name ?? id)
      break
    case 'focus':
      /* 定位工位：切回平面并选中（原型 switchView('floor') + selectSession） */
      session.selectSession(id)
      session.setView('floor')
      break
    case 'log':
      session.selectSession(id)
      overlay.openDrawer('logs', id, session.byId(id)?.name ?? id)
      break
  }
}
</script>

<template>
  <div class="view view--cards" :class="{ 'is-on': session.view === 'cards' }" role="tabpanel">
    <p v-if="!cards.length" class="view__empty">
      没有匹配的会话，换个关键词或切回「全部」。
    </p>

    <div v-else class="wcards" @click="onAct">
      <article
        v-for="s in cards"
        :key="s.id"
        class="wcard"
        :class="[ST[s.state].cls, { 'is-active': session.selId === s.id }]"
        :data-id="s.id"
      >
        <div class="wcard__top">
          <span class="wcard__id">{{ s.code }}</span>
          <span class="wcard__name">
            <b>{{ s.name }}</b>
            <i>{{ s.agent }} · {{ s.ws }}</i>
          </span>
          <span class="stchip" :class="{ 'is-blink': ST[s.state].blink }">
            {{ ST[s.state].cn }}
          </span>
        </div>

        <div class="wcard__bubble" data-role="task">
          {{ s.task }} <span>· {{ session.fmtDur(s.elapsed) }}</span>
        </div>

        <div class="wcard__bar"><i data-role="prog" :style="{ width: `${s.prog}%` }" /></div>

        <div class="wcard__meta">
          <span><i>CPU / GPU</i><b>{{ s.cpu }} · {{ s.gpu }}</b></span>
          <span><i>显存水位</i><b>{{ s.gpuPct }}%</b></span>
          <span><i>已运行</i><b>{{ session.fmtDur(s.elapsed) }}</b></span>
          <span><i>优先级</i><b>{{ s.prio }}</b></span>
        </div>

        <div class="wcard__acts">
          <button type="button" data-act="open"><IconSprite name="i-eye" cls="ic" />详情</button>
          <button type="button" data-act="focus"><IconSprite name="i-cube" cls="ic" />定位工位</button>
          <button type="button" data-act="log"><IconSprite name="i-term" cls="ic" />日志</button>
        </div>
      </article>
    </div>
  </div>
</template>