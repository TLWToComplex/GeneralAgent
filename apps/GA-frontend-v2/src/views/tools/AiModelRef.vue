<!--
  AI 工具 · 内网模型参数速查（工具平台 AI 工具标签页的页头主按钮）

  三个 AI 工具接的是**同一个内网大模型端点**，所以把「照着填的那几项参数 + 三段配置 +
  网络与代理」集中成一页：装任何一个工具时都可以在这里复制现成片段，
  不用在三个流程页之间来回找。

  与 AiToolGuide 共用同一套容器类名（.aiguide / .aistep / AiBlocks），
  所以两页的观感完全一致，样式只有一份。
-->
<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import IconSprite from '@/components/IconSprite.vue'
import AiBlocks from '@/components/AiBlocks.vue'
import { AI_REF_SECTIONS, INTERNAL_LLM, quickConfigText } from '@/data/aitools'
import type { AiFile, AiToolId } from '@/data/aitools'
import { copyText } from '@/lib/clipboard'
import { useToolsStore } from '@/stores/tools'

const emit = defineEmits<{ (e: 'back'): void }>()

const tools = useToolsStore()

const mainEl = ref<HTMLElement | null>(null)
const active = ref(0)

function jump(i: number): void {
  const root = mainEl.value
  if (!root) return
  const sec = root.querySelectorAll<HTMLElement>('.aistep')[i]
  if (!sec) return
  root.scrollTo({ top: Math.max(0, sec.offsetTop - 10), behavior: 'smooth' })
  active.value = i
}

let raf = 0
function onScroll(): void {
  if (raf) return
  raf = window.requestAnimationFrame(() => {
    raf = 0
    const root = mainEl.value
    if (!root) return
    const top = root.getBoundingClientRect().top + 24
    let idx = 0
    root.querySelectorAll<HTMLElement>('.aistep').forEach((s, i) => {
      if (s.getBoundingClientRect().top <= top) idx = i
    })
    active.value = idx
  })
}

onBeforeUnmount(() => {
  if (raf) window.cancelAnimationFrame(raf)
})

async function copy(text: string, label: string): Promise<void> {
  const ok = await copyText(text)
  tools.notifyCopy(label, ok)
}

/** 三个工具的接入配置一次复制到位（dsh 侧两份、Zed 侧一份） */
function onCopyAll(): void {
  const ids: AiToolId[] = ['dsh-desktop', 'dsh-cli', 'zed']
  const text = ids
    .map((id) => quickConfigText(id))
    .join('\n\n' + '='.repeat(64) + '\n\n')
  void copy(text, 'dsh 与 Zed 的接入配置')
}

/* 参考页里目前没有下载条目，转发一下保持 emit 契约一致；真出现 files 块时走同一套下载逻辑 */
function onFile(file: AiFile): void {
  tools.downloadFrom('内网模型参数', file.url)
}
</script>

<template>
  <div class="aiguide">
    <header class="aiguide__bar">
      <button class="aiguide__back" type="button" @click="emit('back')">
        <IconSprite name="i-chev" cls="ic" />返回 AI 工具
      </button>

      <div class="aiguide__id">
        <span class="aiguide__ico"><IconSprite name="i-model" cls="ic" /></span>
        <span class="aiguide__name">
          <b>内网模型参数速查</b>
          <i>dsh 桌面版 / dsh 终端版 / Zed 共用同一组端点与密钥</i>
        </span>
        <span class="stchip" style="--st:var(--teal)">已验证可用</span>
      </div>

      <div class="aiguide__prog">
        <span>模型 <b>{{ INTERNAL_LLM.model }}</b></span>
        <span class="aiguide__host">{{ INTERNAL_LLM.host }} · 需连 {{ INTERNAL_LLM.network }}</span>
      </div>

      <button class="reg__sync" type="button" @click="onCopyAll">
        <IconSprite name="i-tool" cls="ic" /><span>复制全部配置</span>
      </button>
    </header>

    <div class="aiguide__body">
      <nav class="aiguide__rail" aria-label="参数速查目录">
        <p class="aiguide__railhead">速查 · {{ AI_REF_SECTIONS.length }} 节</p>
        <button
          v-for="(s, i) in AI_REF_SECTIONS"
          :key="s.id"
          class="aiguide__railitem"
          :class="{ 'is-on': i === active }"
          type="button"
          @click="jump(i)"
        >
          <em>{{ i + 1 }}</em>
          <span>{{ s.title }}</span>
        </button>
      </nav>

      <div ref="mainEl" class="aiguide__main" @scroll="onScroll">
        <section v-for="(s, i) in AI_REF_SECTIONS" :key="s.id" class="aistep">
          <header class="aistep__head">
            <em class="aistep__no">{{ i + 1 }}</em>
            <div class="aistep__title">
              <b>{{ s.title }}</b>
              <i>{{ s.goal }}</i>
            </div>
          </header>

          <AiBlocks :blocks="s.blocks" @copy="copy" @file="onFile" />
        </section>
      </div>
    </div>
  </div>
</template>