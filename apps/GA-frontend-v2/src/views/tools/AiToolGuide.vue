<!--
  AI 工具 · 安装使用流程（工具平台 AI 工具标签页点进某个工具后看到的页面）

  这是一个**钻取视图**，不是新的路由：工具平台页仍然是同一个 .subpage，
  点卡片 → store 的 aiView 切成 'guide' → 这里整块替换掉卡片区。
  与项目其它 tab 的处理方式一致（「子 tab 都是 store 内部状态，不是嵌套路由」）。

  页面结构（左右两栏）：
    左  安装流程 · 步骤导航（可点跳转、当前步高亮、已完成打勾）
    右  全部步骤纵向铺开（可整段滚动阅读，不藏内容），每步：标题 / 目标 / 耗时 /
        标记完成 + 内容块（AiBlocks 渲染）
    顶  工具身份 + 三个工具的快速切换 + 装机进度 + 主按钮（领包 / 复制安装命令）

  注意：左下角原本有一块「官方入口」（指向 github / zed.dev 的外链），按内网发放的要求
  已整块去掉 —— 本页所有内容都不依赖外网，安装包一律指向平台内置的 public/ai-tools/。

  为什么全部步骤都渲染出来而不是一步一页：
    装机时经常要「往回翻一条命令」，向导式会把它藏起来；这里用滚动 + 左侧导航，
    既像一份完整手册，又能一步步跟着做（每步可勾掉，顶上有进度条）。

  当前步的高亮不靠 store：滚动容器里用各 .aistep 的 getBoundingClientRect 算，
  切工具时重置到第 1 步。
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import IconSprite from '@/components/IconSprite.vue'
import AiBlocks from '@/components/AiBlocks.vue'
import { AIKIND, AIST, AI_TOOLS, quickConfigText } from '@/data/aitools'
import type { AiFile, AiTool } from '@/data/aitools'
import { copyText } from '@/lib/clipboard'
import { useToolsStore } from '@/stores/tools'

const props = defineProps<{ tool: AiTool }>()
const emit = defineEmits<{ (e: 'back'): void }>()

const tools = useToolsStore()

const mainEl = ref<HTMLElement | null>(null)
/** 当前读到的第几步（左侧导航高亮） */
const active = ref(0)

const kind = computed(() => AIKIND[props.tool.kind])
const state = computed(() => AIST[props.tool.state])
const prog = computed(() => tools.progressOf(props.tool))

/* ---------------------------------------------------------------- 步骤导航 */

/** 跳转到第 i 步：滚动容器内定位（各 .aistep 的 offsetTop 相对 .aiguide__main） */
function jump(i: number): void {
  const root = mainEl.value
  if (!root) return
  const sec = root.querySelectorAll<HTMLElement>('.aistep')[i]
  if (!sec) return
  root.scrollTo({ top: Math.max(0, sec.offsetTop - 10), behavior: 'smooth' })
  active.value = i
}

/** 滚动时更新当前步：取「顶部已经越过容器顶线」的最后一步 */
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

/* 切工具（顶部三个 tab）时回到第一步、滚回顶部 */
watch(
  () => props.tool.id,
  () => {
    active.value = 0
    mainEl.value?.scrollTo({ top: 0 })
  },
)

/* ---------------------------------------------------------------- 主按钮 */

const primaryLabel = computed(() => (props.tool.files.length ? '领取安装包' : '复制安装命令'))

async function copy(text: string, label: string): Promise<void> {
  const ok = await copyText(text)
  tools.notifyCopy(label, ok)
}

function onPrimary(): void {
  const f = props.tool.files[0]
  if (f) {
    tools.claimFile(props.tool, f.url)
    return
  }
  void copy(props.tool.quickCmd ?? 'npx @deepseek-ai/dsh web', `${props.tool.name}的安装命令`)
}

/* ---------------------------------------------------------------- 块事件 */

function onCopy(text: string, label: string): void {
  void copy(text, label)
}

function onFile(file: AiFile): void {
  tools.claimFile(props.tool, file.url)
}

/** 复制接入配置（settings.yaml / settings.json + 密钥环境变量） */
function onCopyConfig(): void {
  void copy(quickConfigText(props.tool.id), `${props.tool.name}的接入配置`)
}

/* ---------------------------------------------------------------- 完成态 */

function onMarkAll(): void {
  tools.markAllSteps(props.tool)
}

function onResetSteps(): void {
  tools.resetSteps(props.tool)
}
</script>

<template>
  <div class="aiguide">
    <!-- 顶部：身份 + 工具切换 + 进度 + 主按钮 -->
    <header class="aiguide__bar">
      <button class="aiguide__back" type="button" @click="emit('back')">
        <IconSprite name="i-chev" cls="ic" />返回 AI 工具
      </button>

      <div class="aiguide__id">
        <span class="aiguide__ico"><IconSprite :name="kind.icon" cls="ic" /></span>
        <span class="aiguide__name">
          <b>{{ tool.name }}</b>
          <i>{{ tool.sub }} · 全流程 {{ tool.eta }}</i>
        </span>
        <span class="stchip" :style="`--st:${state.v}`">{{ state.cn }}</span>
      </div>

      <nav class="aiguide__switch" aria-label="切换 AI 工具">
        <button
          v-for="t in AI_TOOLS"
          :key="t.id"
          class="aiguide__sw"
          :class="{ 'is-on': t.id === tool.id }"
          type="button"
          @click="tools.openAiGuide(t.id)"
        >
          {{ t.name }}
        </button>
      </nav>

      <div class="aiguide__prog">
        <span>装机进度 <b>{{ prog.done }}/{{ prog.total }}</b></span>
        <div class="aiguide__meter"><i :style="`width:${prog.pct}%`" /></div>
      </div>

      <button class="reg__sync" type="button" @click="onPrimary">
        <IconSprite name="i-download" cls="ic" /><span>{{ primaryLabel }}</span>
      </button>
    </header>

    <div class="aiguide__body">
      <!-- 左：步骤导航 -->
      <nav class="aiguide__rail" aria-label="安装流程步骤">
        <p class="aiguide__railhead">安装流程 · {{ tool.steps.length }} 步</p>
        <button
          v-for="(s, i) in tool.steps"
          :key="s.id"
          class="aiguide__railitem"
          :class="{ 'is-on': i === active, 'is-done': tools.isStepDone(tool.id, s.id) }"
          type="button"
          @click="jump(i)"
        >
          <em>{{ tools.isStepDone(tool.id, s.id) ? '✓' : i + 1 }}</em>
          <span>{{ s.title }}</span>
        </button>
      </nav>

      <!-- 右：全部步骤 -->
      <div ref="mainEl" class="aiguide__main" @scroll="onScroll">
        <section
          v-for="(s, i) in tool.steps"
          :key="s.id"
          class="aistep"
          :class="{ 'is-done': tools.isStepDone(tool.id, s.id) }"
        >
          <header class="aistep__head">
            <em class="aistep__no">{{ i + 1 }}</em>
            <div class="aistep__title">
              <b>{{ s.title }}</b>
              <i>{{ s.goal }} · 约 {{ s.eta }}</i>
            </div>
            <button
              class="aistep__done"
              :class="{ 'is-on': tools.isStepDone(tool.id, s.id) }"
              type="button"
              @click="tools.toggleStep(tool.id, s.id)"
            >
              {{ tools.isStepDone(tool.id, s.id) ? '已完成' : '标记完成' }}
            </button>
          </header>

          <AiBlocks :blocks="s.blocks" @copy="onCopy" @file="onFile" />
        </section>

        <footer class="aiguide__foot">
          <p>
            走完这 {{ tool.steps.length }} 步，<b>{{ tool.name }}</b> 就能用内网模型
            <b>qwen3.8-27b</b> 干活了。配置都在
            <code>{{ tool.kind === 'ide' ? 'settings.json' : 'settings.yaml' }}</code>
            ，换机器时照着本页重做一遍即可。
          </p>
          <div class="aiguide__footacts">
            <button class="btn btn--ghost" type="button" @click="onCopyConfig">
              <IconSprite name="i-tool" cls="ic" />复制接入配置
            </button>
            <button class="btn btn--ghost" type="button" @click="jump(0)">回到第 1 步</button>
            <button
              v-if="prog.done < prog.total"
              class="btn btn--main"
              type="button"
              @click="onMarkAll"
            >
              <span>标记全部完成</span>
            </button>
            <button v-else class="btn btn--ghost" type="button" @click="onResetSteps">
              <IconSprite name="i-restart" cls="ic" />重走一遍
            </button>
          </div>
        </footer>
      </div>
    </div>
  </div>
</template>