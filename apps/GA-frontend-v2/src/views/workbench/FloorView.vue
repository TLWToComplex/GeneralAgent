<!--
  工位平面图 —— 等价迁移自原型 console.js buildFloor 282–417 / paintFloorState 434–491。

  平面是等距（isometric）投影的工作区：
    · 等距地面网格（t = -3…9，t % 3 === 0 的线是主线）
    · 中央大厅平台 + 两条分隔线
    · 24 个工位：地垫 → 桌面 → 小人 → 编号头像 → 状态气泡
    · 选中工位旁挂 agent / workspace 双节点标签（fl-tether + fl-node）

  相机模型（这是踩过坑的地方，别改）：
    #floor 的 viewBox 固定 `0 0 1344 752`，内容横向中心 = 672 = VB.cx，
    所以 #flRoot 的变换写成
        translate(cx+pan.x, cy+pan.y) scale(z) translate(-cx, -cy)
    时，pan=(0,0) 在任何缩放下都是「内容中心钉在画布中心」= 视觉居中。
    默认 z = 180%（FLOOR_ZOOM），下限 60%，上限 200%。
-->
<script setup lang="ts">
import { computed } from 'vue'
import { BUB, VB, FLOOR_ZOOM, FLOOR_ZOOM_MAX, FLOOR_ZOOM_MIN, useSessionStore } from '@/stores/session'
import { useOverlayStore } from '@/stores/overlay'
import { ST, type Session } from '@/data/sessions'
import { wrap2 } from '@/lib/util'

const session = useSessionStore()
const overlay = useOverlayStore()

/* 工位阵列几何（原型 266）：ox/oy 是原点偏移，cs/rs 是等距两步长 */
const F = { ox: 528, oy: 122, cs: 144, rs: 72, cols: 6, rows: 4 }
const px = (i: number, j: number): number => F.ox + (i - j) * F.cs
const py = (i: number, j: number): number => F.oy + (i + j) * F.rs

/** st(alpha, kind)：状态色按透明度叠出来，--st 由工位自身的类提供 */
function st(alpha: number, kind = 'fill'): string {
  return `${kind}:color-mix(in srgb, var(--st) ${alpha}%, transparent)`
}

/* ---------------------------------------------------------------- 地面网格 */
const gridLines = computed(() => {
  const out: { x1: number; y1: number; x2: number; y2: number; major: boolean }[] = []
  for (let t = -3; t <= 9; t++) {
    out.push({
      x1: px(-3, t), y1: py(-3, t), x2: px(9, t), y2: py(9, t),
      major: t % 3 === 0,
    })
    out.push({
      x1: px(t, -3), y1: py(t, -3), x2: px(t, 9), y2: py(t, 9),
      major: t % 3 === 0,
    })
  }
  return out
})

/* ---------------------------------------------------------------- 中央大厅 */
const HM = 0.28
const hallPoints = computed(() => {
  const hi = F.cols - 1 + HM
  const hj = F.rows - 1 + HM
  const pt = (i: number, j: number): string => `${px(i, j)},${py(i, j)}`
  return [pt(-HM, -HM), pt(hi, -HM), pt(hi, hj), pt(-HM, hj)].join(' ')
})
const hallLines = computed(() => [
  { x1: px(-HM, 1.5), y1: py(-HM, 1.5), x2: px(F.cols - 1 + HM, 1.5), y2: py(F.cols - 1 + HM, 1.5) },
  { x1: px(2.5, -HM), y1: py(2.5, -HM), x2: px(2.5, F.rows - 1 + HM), y2: py(2.5, F.rows - 1 + HM) },
])

/* ---------------------------------------------------------------- 工位 */
interface Booth {
  s: Session
  x: number
  y: number
  cls: string
  bubble: string[]
}

/** 按等距深度排序：i+j 小的先画，后画的更靠前（原型 325–329） */
const booths = computed<Booth[]>(() =>
  session.sessions
    .slice()
    .sort((m, n) => (m.idx % F.cols) + Math.floor(m.idx / F.cols) - ((n.idx % F.cols) + Math.floor(n.idx / F.cols)))
    .map((s) => {
      const i = s.idx % F.cols
      const j = Math.floor(s.idx / F.cols)
      const x = px(i, j)
      const y = py(i, j)
      return { s, x, y, cls: ST[s.state].cls, bubble: wrap2(s.task, 10) }
    }),
)

/** 选中工位：平移焦点节点（原型 paintFloorState 457–478） */
const focus = computed(() => {
  const id = session.selId
  if (!id) return null
  const s = session.sessions.find((x) => x.id === id)
  if (!s) return null
  const i = s.idx % F.cols
  const j = Math.floor(s.idx / F.cols)
  const x = px(i, j)
  const y = py(i, j)
  const right = x < VB.cx
  const dir = right ? 1 : -1
  const anchor = right ? 'start' : 'end'
  const lx = right ? x + 62 : x - 62
  return {
    x,
    y,
    dir,
    anchor,
    lx,
    tether: `M${x} ${y}L${x + dir * 54} ${y - 14}M${x} ${y}L${x + dir * 54} ${y + 16}`,
    chips: [
      { y: y - 34, cls: 'is-agent', label: `agent · ${s.agent}` },
      { y: y + 2, cls: 'is-ws', label: `workspace · ${s.ws}` },
    ],
  }
})

/** 节点标签宽度（原型 nodeChip：字数 × 6.1 + 18） */
const chipW = (label: string): number => label.length * 6.1 + 18

/* ---------------------------------------------------------------- 相机 */
const rootTransform = computed(
  () =>
    `translate(${VB.cx + session.pan.x} ${VB.cy + session.pan.y}) ` +
    `scale(${session.zoom}) translate(${-VB.cx} ${-VB.cy})`,
)

const zoomPct = computed(() => `${Math.round(session.zoom * 100)}%`)

function zoomBy(step: number): void {
  session.setZoom(session.zoom + step)
}
function zoomReset(): void {
  session.resetView()
}

/* 拖动平移（原型 floorCamera 的 pointer 逻辑）：按住平面拖动，换算成屏幕像素 */
let drag: { x: number; y: number; ox: number; oy: number } | null = null

function onDown(e: PointerEvent): void {
  drag = { x: e.clientX, y: e.clientY, ox: session.pan.x, oy: session.pan.y }
  ;(e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId)
}
function onMove(e: PointerEvent): void {
  if (!drag) return
  session.setPan(drag.ox + (e.clientX - drag.x), drag.oy + (e.clientY - drag.y))
}
function onUp(): void {
  drag = null
}

/* 点工位：选中 + 巡航暂停（原型 selectSession） */
function onBooth(id: string): void {
  session.selectSession(id)
}
function onBoothOpen(id: string): void {
  session.selectSession(id)
  overlay.openDrawer('session', id, session.byId(id)?.name ?? id)
}
</script>

<template>
  <div class="view view--floor" :class="{ 'is-on': session.view === 'floor' }" role="tabpanel">
    <svg
      id="floor"
      :viewBox="`0 0 ${VB.w} ${VB.h}`"
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="工作区工位平面图"
      @pointerdown="onDown"
      @pointermove="onMove"
      @pointerup="onUp"
      @pointercancel="onUp"
    >
      <g id="flRoot" :transform="rootTransform">
        <!-- ① 等距地面网格 -->
        <g class="fl-grid">
          <line
            v-for="(l, i) in gridLines"
            :key="i"
            :class="{ 'is-major': l.major }"
            :x1="l.x1"
            :y1="l.y1"
            :x2="l.x2"
            :y2="l.y2"
          />
        </g>

        <!-- ② 中央大厅 -->
        <polygon class="fl-hall" :points="hallPoints" />
        <line
          v-for="(l, i) in hallLines"
          :key="`h${i}`"
          class="fl-hall-line"
          :x1="l.x1"
          :y1="l.y1"
          :x2="l.x2"
          :y2="l.y2"
        />

        <!-- ③ 工位阵列 -->
        <g id="flScene">
          <g
            v-for="b in booths"
            :key="b.s.id"
            class="fl-booth"
            :class="[b.cls, { 'is-active': session.selId === b.s.id }]"
            :data-id="b.s.id"
            :style="{ opacity: session.isVis(b.s) ? '' : '.16' }"
            @click="onBooth(b.s.id)"
            @dblclick="onBoothOpen(b.s.id)"
          >
            <!-- 悬停 / 选中光环 -->
            <ellipse
              class="fl-ring"
              :cx="b.x"
              :cy="b.y"
              rx="58"
              ry="32"
              fill="none"
              :style="`${st(70, 'stroke')};stroke-width:1.4`"
            />

            <!-- 工位地垫 -->
            <polygon
              class="fl-pad"
              :points="`${b.x},${b.y - 26} ${b.x + 46},${b.y} ${b.x},${b.y + 26} ${b.x - 46},${b.y}`"
              :style="`${st(13)};${st(30, 'stroke')};stroke-width:1`"
            />

            <!-- 桌面（等距小方台，三块面拼出立体） -->
            <g class="fl-desk">
              <polygon
                :points="`${b.x},${b.y - 25} ${b.x + 30},${b.y - 8} ${b.x},${b.y + 9} ${b.x - 30},${b.y - 8}`"
                :style="`${st(24)};${st(46, 'stroke')};stroke-width:1`"
              />
              <polygon
                :points="`${b.x - 30},${b.y - 8} ${b.x},${b.y + 9} ${b.x},${b.y + 15} ${b.x - 30},${b.y - 2}`"
                :style="st(11)"
              />
              <polygon
                :points="`${b.x + 30},${b.y - 8} ${b.x},${b.y + 9} ${b.x},${b.y + 15} ${b.x + 30},${b.y - 2}`"
                :style="st(16)"
              />
            </g>

            <!-- 坐在桌后的小人 -->
            <g class="fl-figure">
              <circle :cx="b.x" :cy="b.y - 34" r="6.4" :style="st(78)" />
              <path :d="`M${b.x - 12} ${b.y - 18}a12 12 0 0 1 24 0z`" :style="st(52)" />
            </g>

            <!-- 编号头像 -->
            <circle :cx="b.x" :cy="b.y + 14" r="10.5" :style="st(88)" />
            <text class="fl-avatar-txt" :x="b.x" :y="b.y + 17.5">{{ b.s.code }}</text>

            <!-- 执行中的呼吸脉冲（提示工位仍在推进） -->
            <circle
              v-if="b.s.state === 'running'"
              class="fl-pulse"
              :cx="b.x"
              :cy="b.y"
              r="9"
              fill="none"
              :style="`${st(75, 'stroke')};stroke-width:1.2`"
            />

            <!-- 状态气泡：两行任务文案 + 时长 + 状态标签 -->
            <g class="fl-bubble" :class="{ 'is-live': b.s.state === 'running' }">
              <rect
                :x="b.x - BUB.w / 2"
                :y="b.y - BUB.off"
                :width="BUB.w"
                :height="BUB.h"
                rx="12"
                ry="12"
              />
              <path
                :d="`M${b.x - 6} ${b.y - BUB.off + BUB.h}l6 7 6-7z`"
                style="fill: #fff"
              />
              <title>{{ b.s.name }} · {{ b.s.task }}</title>
              <text :x="b.x - BUB.w / 2 + 11" :y="b.y - BUB.off + 16" style="font-size: 12px">
                {{ b.bubble[0] }}
              </text>
              <text :x="b.x - BUB.w / 2 + 11" :y="b.y - BUB.off + 30" style="font-size: 12px">
                {{ b.bubble[1] }}
              </text>
              <text
                class="fl-bubble-time"
                :x="b.x - BUB.w / 2 + 11"
                :y="b.y - BUB.off + 42"
              >{{ session.fmtDur(b.s.elapsed) }}</text>
              <text
                class="fl-bubble-tag"
                :x="b.x + BUB.w / 2 - 11"
                :y="b.y - BUB.off + 42"
                text-anchor="end"
                style="fill: var(--st)"
              >{{ ST[b.s.state].cn }}</text>
            </g>
          </g>
        </g>

        <!-- ④ 选中工位的 agent / workspace 双节点 -->
        <g v-if="focus" id="flFocus">
          <path class="fl-tether" :d="focus.tether" fill="none" />
          <g
            v-for="c in focus.chips"
            :key="c.cls"
            class="fl-node"
            :class="c.cls"
          >
            <rect
              :x="focus.anchor === 'end' ? focus.lx - chipW(c.label) : focus.lx"
              :y="c.y - 11"
              :width="chipW(c.label)"
              height="22"
              rx="7"
              ry="7"
            />
            <text
              :x="focus.anchor === 'end' ? focus.lx - 9 : focus.lx + 9"
              :y="c.y + 3.6"
              :text-anchor="focus.anchor"
            >{{ c.label }}</text>
          </g>
        </g>
      </g>
    </svg>

    <!-- 工作区状态：竖排贴在平面上方右侧 -->
    <div class="floor__legend">
      <span><i style="--c: var(--azure)" />执行中</span>
      <span><i style="--c: var(--gold)" />排队</span>
      <span><i style="--c: var(--slate)" />空闲</span>
      <span><i style="--c: var(--violet)" />降级</span>
      <span><i style="--c: var(--coral)" />中断</span>
    </div>

    <!-- 缩放控件：复位按钮同时显示当前百分比 -->
    <div class="floor__zoom">
      <button type="button" aria-label="缩小" @click="zoomBy(-0.2)">
        <svg class="ic" aria-hidden="true"><use href="#i-minus" /></svg>
      </button>
      <button
        type="button"
        title="复位到 180% 并居中"
        :disabled="session.zoom <= FLOOR_ZOOM_MIN"
        @click="zoomReset"
      >{{ zoomPct }}</button>
      <button type="button" aria-label="放大" @click="zoomBy(0.2)">
        <svg class="ic" aria-hidden="true"><use href="#i-plus" /></svg>
      </button>
    </div>
  </div>
</template>