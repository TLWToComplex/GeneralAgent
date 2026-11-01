<template>
  <div class="kg-container">
    <!-- 满屏图谱 -->
    <div class="kg-graph" ref="chartRef"></div>

    <!-- 悬浮操作盘 (操作环) -->
    <div v-if="actionRing.visible" class="action-ring-container"
      :style="{ left: actionRing.x + 'px', top: actionRing.y + 'px' }">
      <div class="action-ring" :class="actionRing.closing ? 'ring-exit' : 'ring-enter'" :key="actionRing.renderKey">
        <div class="ring-zoom-layer" :style="{ transform: `scale(${ringVisualScale})` }">
          <svg class="ring-svg" :width="ringSize" :height="ringSize"
            :viewBox="`-${ringSize / 2} -${ringSize / 2} ${ringSize} ${ringSize}`">
            <path v-for="(sector, index) in sectors" :key="'path-' + index" :d="sector.path" class="ring-sector-path"
              :class="{ 'hovered': hoveredSector === index }" @click.stop="handleRingAction(sector.action)"
              @mouseenter="hoveredSector = index" @mouseleave="hoveredSector = null">
              <title>{{ sector.title }}</title>
            </path>
          </svg>
          <div v-for="(sector, index) in sectors" :key="'icon-' + index" class="ring-icon-wrapper"
            :style="{ transform: `translate(${sector.iconX}px, ${sector.iconY}px)` }">
            <div class="ring-icon" :class="{ 'hovered': hoveredSector === index }"
              :style="{ transform: `scale(${hoveredSector === index ? 1.2 : 1})` }">
              <component :is="sector.icon" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 知识图谱缩略图 (Minimap) -->
    <div class="kg-minimap" 
         @mousedown="handleMinimapMouseDown"
         @click="handleMinimapClick">
      <div class="kg-minimap-content" ref="minimapRef">
        <canvas ref="minimapCanvasRef" style="width: 100%; height: 100%; display: block;"></canvas>
      </div>
      <div class="kg-minimap-viewport" :style="minimapViewportStyle"></div>
    </div>

    <!-- 缩放控制面板 -->
    <div class="kg-controls">
      <button class="kg-control-btn" style="margin-right: 8px;" @click="zoomIn" title="放大" :disabled="!canZoomIn">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </button>
      <button class="kg-control-btn" @click="zoomOut" title="缩小" :disabled="!canZoomOut">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </button>
      <button class="kg-control-btn" @click="resetZoom" title="适应屏幕">
        <img :src="FitToScreenSvg" class="control-icon" alt="Fit to Screen" />
      </button>
      <div class="kg-controls-divider"></div>
      <button class="kg-control-btn" @click="restoreHiddenNodes" title="恢复隐藏节点" :disabled="hiddenNodeIds.size === 0">
        <EyeOutlined />
      </button>
      <button class="kg-control-btn" @click="downloadGraph('png')" title="下载图谱">
        <DownloadOutlined />
      </button>
    </div>

    <!-- 右侧悬浮信息面板 -->
    <div class="kg-floating-panel-wrapper" :class="{ 'is-collapsed': isPanelCollapsed }">
      <div class="panel-toggle-btn" @click="isPanelCollapsed = !isPanelCollapsed" :title="isPanelCollapsed ? '展开面板' : '收起面板'">
        <LeftOutlined v-if="isPanelCollapsed" />
        <RightOutlined v-else />
      </div>
      <div class="kg-floating-panel" ref="floatingPanelRef">
        <div class="panel-section">
        <div class="section-header">
          <SettingOutlined /> <span>图谱设置</span>
        </div>
        <div class="setting-row">
          <span class="setting-label">渲染节点上限</span>
          <div class="setting-actions">
            <a-input-number v-model:value="graphSize" :min="1" :max="5000" style="width: 120px"
              @pressEnter="loadGraph" />
            <button class="action-btn primary" @click="loadGraph" :disabled="loading" style="height: 32px; padding: 0 16px;">
              <ReloadOutlined v-if="!loading" />
              <LoadingOutlined v-else spin />
              刷新
            </button>
          </div>
        </div>
      </div>

      <div class="panel-divider"></div>

      <div class="panel-section props-section">
        <div class="section-header">
          <ProfileOutlined /> <span>节点详情</span>
        </div>

        <div v-if="selectedNode" class="node-details">
          <div class="node-summary-card">
            <div class="node-summary-head">
              <div class="node-avatar" :style="{ backgroundColor: getColorForType(selectedNode.type).fill }">
                {{ selectedNode.name ? selectedNode.name.charAt(0).toUpperCase() : '?' }}
              </div>
              <div class="node-title-box">
                <div class="node-name" :title="selectedNode.name">{{ selectedNode.name }}</div>
                <div class="node-type-tag"
                  :style="{ color: getColorForType(selectedNode.type).border, borderColor: getColorForType(selectedNode.type).border }">
                  {{ selectedNode.type || 'Unknown' }}
                </div>
              </div>
            </div>
            <div class="node-meta-row">
              <span class="node-meta-pill">属性 {{ nodePropertyCount }}</span>
              <span v-if="nodeSourceLabel" class="node-meta-pill node-meta-source" :title="nodeSourceLabel">{{
                nodeSourceLabel }}</span>
            </div>
            <div v-if="selectedNode.id" class="node-id-line" :title="selectedNode.id">{{ selectedNode.id }}</div>
          </div>

          <div v-if="nodeDetailEntries.length" class="props-list">
            <div class="prop-item" v-for="([key, value]) in nodeDetailEntries" :key="key">
              <div class="prop-key">{{ key }}</div>
              <div class="prop-value" :title="String(value)">{{ value === '' ? '-' : value }}</div>
            </div>
          </div>
          <div v-else class="node-props-empty">该节点暂无可展示属性</div>
        </div>

        <div v-else class="empty-state">
          <SelectOutlined class="empty-icon" />
          <p>请在左侧图谱中点击节点<br />查看详细属性</p>
        </div>
      </div>
    </div>
  </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed, reactive, nextTick, shallowReactive, shallowRef } from 'vue'
import { useThrottleFn } from '@vueuse/core'
import * as echarts from 'echarts'
import { showKnowledgeBaseGraph } from '@/services/knowledgeBase'
import NotificationService from '@/utils/NotificationService'
import FitToScreenSvg from '@/assets/image/svg/fit_to_screen.svg'
import {
  ShareAltOutlined,
  EyeInvisibleOutlined,
  EyeOutlined,
  PushpinOutlined,
  AimOutlined,
  SettingOutlined,
  ProfileOutlined,
  ReloadOutlined,
  SelectOutlined,
  CloseOutlined,
  LeftOutlined,
  RightOutlined,
  DownloadOutlined,
  LoadingOutlined
} from '@ant-design/icons-vue'

const props = defineProps<{
  knowledgeBaseName: string
}>()

const isPanelCollapsed = ref(false)


const chartRef = ref<HTMLElement | null>(null)
const floatingPanelRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const loading = ref(false)
const graphSize = ref(300)
const selectedNode = shallowRef<any>(null)
const MAX_CHART_ZOOM = 3
const ZOOM_EPSILON = 0.0001
const VIEW_ANIMATION_DURATION = 260
const MINIMAP_OFFSET_LEFT = 24
const MINIMAP_WIDTH = 223
const FLOATING_PANEL_OFFSET_RIGHT = 24
const FLOATING_PANEL_WIDTH = 340
const LEGEND_SAFE_GAP = 20
const LEGEND_BOTTOM_OFFSET = 20
const LARGE_GRAPH_NODE_THRESHOLD = 900
const AUTO_FIT_SAMPLE_LIMIT = 900
const currentMinChartZoom = ref(0.4)
const currentChartZoom = ref(1)
const currentGraphNodeCount = ref(0)
let viewAnimationFrame: number | null = null
const isViewAnimating = ref(false)

// 操作环状态
const actionRing = shallowReactive({
  visible: false,
  x: 0,
  y: 0,
  zoom: 1,
  closing: false,
  renderKey: 0,
  nodeData: null as any,
  dataIndex: -1
})

const hoveredSector = ref<number | null>(null)
const RING_SWITCH_DURATION = 180
let ringSwitchTimer: ReturnType<typeof setTimeout> | null = null

const clampZoom = (zoom: number) => {
  return Math.min(MAX_CHART_ZOOM, Math.max(currentMinChartZoom.value, zoom))
}

const getNodeVisualScale = (zoom: number) => {
  return Math.pow(clampZoom(zoom), 0.6)
}

const getRingMetrics = (zoom: number) => {
  const nodeScale = getNodeVisualScale(zoom)
  const baseNodeRadius = 25
  const baseGap = 4
  const baseThickness = 34

  const innerRadius = (baseNodeRadius + baseGap) * nodeScale
  const outerRadius = (baseNodeRadius + baseGap + baseThickness) * nodeScale

  return {
    nodeScale,
    innerRadius,
    outerRadius
  }
}

const getGraphSeriesModel = () => {
  if (!chartInstance) return null

  try {
    const chartAny = chartInstance as any
    if (typeof chartAny.isDisposed === 'function' && chartAny.isDisposed()) {
      return null
    }
    const model = typeof chartAny.getModel === 'function' ? chartAny.getModel() : null
    if (!model || typeof model.getSeriesByIndex !== 'function') {
      return null
    }
    return model.getSeriesByIndex(0) || null
  } catch {
    return null
  }
}

const getGraphSeriesData = () => {
  const seriesModel = getGraphSeriesModel()
  if (!seriesModel || typeof seriesModel.getData !== 'function') {
    return null
  }

  try {
    return seriesModel.getData()
  } catch {
    return null
  }
}

const getChartZoom = () => {
  if (!chartInstance) return currentChartZoom.value

  try {
    const seriesModel = getGraphSeriesModel()
    if (seriesModel?.coordinateSystem && typeof seriesModel.coordinateSystem.getZoom === 'function') {
      return clampZoom(seriesModel.coordinateSystem.getZoom())
    }
  } catch (e) {
    console.error('Get chart zoom error:', e)
  }

  const option = chartInstance.getOption() as any
  const optionZoom = option?.series?.[0]?.zoom
  if (typeof optionZoom === 'number') {
    return clampZoom(optionZoom)
  }

  return currentChartZoom.value
}

const syncZoomState = (zoom?: number, syncRingZoom = true) => {
  const nextZoom = clampZoom(typeof zoom === 'number' ? zoom : getChartZoom())
  currentChartZoom.value = nextZoom
  if (syncRingZoom) {
    actionRing.zoom = nextZoom
  }
  updateMinimapViewport()
}

const canZoomIn = computed(() => currentChartZoom.value < MAX_CHART_ZOOM - ZOOM_EPSILON)
const canZoomOut = computed(() => currentChartZoom.value > currentMinChartZoom.value + ZOOM_EPSILON)

const updateDynamicMinZoom = () => {
  const nextMin = 0.05
  currentMinChartZoom.value = nextMin
  if (!chartInstance) return
  const option = chartInstance.getOption() as any
  const hasGraphSeries = Array.isArray(option?.series) && option.series.length > 0
  if (!hasGraphSeries) return
  chartInstance.setOption({
    series: [{
      scaleLimit: {
        min: nextMin,
        max: MAX_CHART_ZOOM
      }
    }]
  })
  syncZoomState()
}

const stopViewAnimation = () => {
  if (viewAnimationFrame !== null) {
    cancelAnimationFrame(viewAnimationFrame)
    viewAnimationFrame = null
  }
  isViewAnimating.value = false
}

const easeOutCubic = (progress: number) => 1 - Math.pow(1 - progress, 3)

const getCurrentSeriesCenter = (): [number | string, number | string] | null => {
  if (!chartInstance) return null
  const option = chartInstance.getOption() as any
  const center = option?.series?.[0]?.center
  if (
    Array.isArray(center) &&
    center.length >= 2 &&
    (typeof center[0] === 'number' || typeof center[0] === 'string') &&
    (typeof center[1] === 'number' || typeof center[1] === 'string')
  ) {
    return [center[0], center[1]]
  }
  return null
}

const getNumericSeriesCenter = (): [number, number] => {
  const center = getCurrentSeriesCenter()
  if (center && typeof center[0] === 'number' && typeof center[1] === 'number') {
    return [center[0], center[1]]
  }
  const bounds = getGraphBounds(600)
  if (bounds) {
    return [(bounds.minX + bounds.maxX) / 2, (bounds.minY + bounds.maxY) / 2]
  }
  return [0, 0]
}

const panDragState = reactive({
  active: false,
  lastClientX: 0,
  lastClientY: 0,
  centerX: 0,
  centerY: 0
})

const beginPanDrag = (event: MouseEvent) => {
  if (!chartInstance || event.button !== 0) return
  const [centerX, centerY] = getNumericSeriesCenter()
  panDragState.active = true
  panDragState.lastClientX = event.clientX
  panDragState.lastClientY = event.clientY
  panDragState.centerX = centerX
  panDragState.centerY = centerY
  chartRef.value?.classList.add('is-panning')
}

const endPanDrag = () => {
  if (!panDragState.active) return
  panDragState.active = false
  chartRef.value?.classList.remove('is-panning')
}

const isMinimapDragging = ref(false)
let minimapHasDragged = false
let minimapDragStartX = 0
let minimapDragStartY = 0
let minimapDragStartCenter: [number, number] = [0, 0]

const handleMinimapMouseDown = (e: MouseEvent) => {
  if (!minimapRef.value || !chartInstance) return
  isMinimapDragging.value = true
  minimapHasDragged = false
  minimapDragStartX = e.clientX
  minimapDragStartY = e.clientY

  const center = getCurrentSeriesCenter()
  let cx = 0, cy = 0
  if (center && typeof center[0] === 'number' && typeof center[1] === 'number') {
    cx = center[0]
    cy = center[1]
  } else {
    const bounds = getGraphBounds()
    if (bounds) {
      cx = (bounds.minX + bounds.maxX) / 2
      cy = (bounds.minY + bounds.maxY) / 2
    }
  }
  minimapDragStartCenter = [cx, cy]
  
  e.preventDefault()
}

const handleGlobalMouseMove = (event: MouseEvent) => {
  if (isMinimapDragging.value && minimapRef.value && chartInstance) {
    const dx = event.clientX - minimapDragStartX
    const dy = event.clientY - minimapDragStartY
    
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
      minimapHasDragged = true
    }
    
    const bounds = getGraphBounds()
    if (bounds) {
      const rect = minimapRef.value.getBoundingClientRect()
      const w = rect.width
      const h = rect.height
      const padding = 12
      const bw = bounds.maxX - bounds.minX || 1
      const bh = bounds.maxY - bounds.minY || 1
      const scale = Math.max(0.0001, Math.min((w - padding * 2) / bw, (h - padding * 2) / bh))
      
      const logicalDx = dx / scale
      const logicalDy = dy / scale
      
      const newCx = minimapDragStartCenter[0] + logicalDx
      const newCy = minimapDragStartCenter[1] + logicalDy
      
      applyZoom(currentChartZoom.value, [newCx, newCy], false)
    }
    return
  }

  if (!panDragState.active || !chartInstance) return
  const deltaX = event.clientX - panDragState.lastClientX
  const deltaY = event.clientY - panDragState.lastClientY
  if (!deltaX && !deltaY) return

  panDragState.lastClientX = event.clientX
  panDragState.lastClientY = event.clientY

  const zoom = Math.max(getChartZoom(), ZOOM_EPSILON)
  panDragState.centerX -= deltaX / zoom
  panDragState.centerY -= deltaY / zoom

  chartInstance.setOption({
    series: [{
      center: [panDragState.centerX, panDragState.centerY]
    }]
  })
  updateRingPosition()
}

const handleGlobalMouseUp = () => {
  endPanDrag()
  isMinimapDragging.value = false
}

const applyZoom = (targetZoom: number, center?: any, animate = true) => {
  if (!chartInstance) return
  const nextZoom = clampZoom(targetZoom)
  if (Math.abs(nextZoom - currentChartZoom.value) < ZOOM_EPSILON && center === undefined) return
  stopViewAnimation()
  if (!animate) {
    const startCenter = getCurrentSeriesCenter()
    const normalizedCenter = center === null
      ? ['50%', '50%']
      : (Array.isArray(center) && center.length >= 2 ? [center[0], center[1]] : null)
    const targetCenter = normalizedCenter || startCenter || ['50%', '50%']
    chartInstance.setOption({
      series: [{
        zoom: nextZoom,
        center: targetCenter
      }]
    })
    syncZoomState(nextZoom)
    updateRingPosition()
    return
  }
  isViewAnimating.value = true

  const startZoom = currentChartZoom.value
  const startCenter = getCurrentSeriesCenter()
  const normalizedCenter = center === null
    ? ['50%', '50%']
    : (Array.isArray(center) && center.length >= 2 ? [center[0], center[1]] : null)
  const targetCenter = normalizedCenter || startCenter || ['50%', '50%']
  const fromCenter = startCenter || targetCenter
  const canInterpolateCenter =
    typeof fromCenter[0] === 'number' &&
    typeof fromCenter[1] === 'number' &&
    typeof targetCenter[0] === 'number' &&
    typeof targetCenter[1] === 'number'

  const startTime = performance.now()
  const runAnimationFrame = (now: number) => {
    if (!chartInstance) {
      viewAnimationFrame = null
      isViewAnimating.value = false
      return
    }

    const rawProgress = Math.min(1, (now - startTime) / VIEW_ANIMATION_DURATION)
    const progress = easeOutCubic(rawProgress)
    const frameZoom = startZoom + (nextZoom - startZoom) * progress
    const seriesOption: Record<string, any> = {
      zoom: frameZoom,
      center: targetCenter
    }

    if (canInterpolateCenter) {
      seriesOption.center = [
        fromCenter[0] + (targetCenter[0] - fromCenter[0]) * progress,
        fromCenter[1] + (targetCenter[1] - fromCenter[1]) * progress
      ]
    }

    chartInstance.setOption({
      series: [seriesOption]
    })
    syncZoomState(frameZoom)
    updateRingPosition()

    if (rawProgress < 1) {
      viewAnimationFrame = requestAnimationFrame(runAnimationFrame)
      return
    }

    viewAnimationFrame = null
    isViewAnimating.value = false
    syncZoomState(nextZoom)
    updateRingPosition()
  }

  viewAnimationFrame = requestAnimationFrame(runAnimationFrame)
}

const sectors = computed(() => {
  const { innerRadius, outerRadius } = getRingMetrics(1)

  const actions = [
    { action: 'expand', title: '展开', icon: ShareAltOutlined },
    { action: 'hide', title: '隐藏', icon: EyeInvisibleOutlined },
    { action: 'pin', title: '固定/取消固定', icon: PushpinOutlined },
    { action: 'focus', title: '聚焦', icon: AimOutlined },
    { action: 'close', title: '关闭菜单', icon: CloseOutlined }
  ]

  const numSectors = actions.length
  const angleStep = 360 / numSectors

  return actions.map((item, i) => {
    const startAngle = i * angleStep - 90
    const endAngle = (i + 1) * angleStep - 90
    const midAngle = startAngle + angleStep / 2

    const startRad = startAngle * Math.PI / 180
    const endRad = endAngle * Math.PI / 180
    const midRad = midAngle * Math.PI / 180

    const x1 = Math.cos(startRad) * outerRadius
    const y1 = Math.sin(startRad) * outerRadius
    const x2 = Math.cos(endRad) * outerRadius
    const y2 = Math.sin(endRad) * outerRadius

    const x3 = Math.cos(endRad) * innerRadius
    const y3 = Math.sin(endRad) * innerRadius
    const x4 = Math.cos(startRad) * innerRadius
    const y4 = Math.sin(startRad) * innerRadius

    const largeArcFlag = angleStep > 180 ? 1 : 0

    const path = `
      M ${x1} ${y1}
      A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${x2} ${y2}
      L ${x3} ${y3}
      A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${x4} ${y4}
      Z
    `

    const midRadius = (innerRadius + outerRadius) / 2
    const iconX = Math.cos(midRad) * midRadius
    const iconY = Math.sin(midRad) * midRadius

    return {
      ...item,
      path,
      iconX,
      iconY
    }
  })
})

const ringSize = computed(() => {
  const { outerRadius } = getRingMetrics(1)
  return outerRadius * 2 + 10
})

const ringVisualScale = computed(() => getNodeVisualScale(actionRing.zoom || 1))

const clearRingSwitchTimer = () => {
  if (ringSwitchTimer !== null) {
    clearTimeout(ringSwitchTimer)
    ringSwitchTimer = null
  }
}

const closeActionRing = (animate = true, clearSelection = true, onClosed?: () => void) => {
  clearRingSwitchTimer()
  hoveredSector.value = null

  if (!actionRing.visible) {
    if (clearSelection) selectedNode.value = null
    onClosed?.()
    return
  }

  const finalizeClose = () => {
    actionRing.visible = false
    actionRing.closing = false
    actionRing.nodeData = null
    actionRing.dataIndex = -1
    if (clearSelection) selectedNode.value = null
    onClosed?.()
  }

  if (!animate) {
    finalizeClose()
    return
  }

  actionRing.closing = true
  ringSwitchTimer = setTimeout(() => {
    finalizeClose()
  }, RING_SWITCH_DURATION)
}

const openActionRingForNode = (params: any) => {
  clearRingSwitchTimer()
  selectedNode.value = params.data
  actionRing.nodeData = params.data
  actionRing.dataIndex = params.dataIndex
  actionRing.visible = true
  actionRing.closing = false
  actionRing.renderKey += 1
  hoveredSector.value = null
  isPanelCollapsed.value = false
  nextTick(() => {
    updateRingPosition()
  })
}

const switchActionRingNode = (params: any) => {
  const currentId = actionRing.nodeData?.id
  const nextId = params?.data?.id

  if (actionRing.visible && currentId && nextId && currentId !== nextId) {
    closeActionRing(true, false, () => {
      openActionRingForNode(params)
    })
    return
  }

  openActionRingForNode(params)
}

// 图谱原始数据
const graphData = shallowReactive({
  nodes: [] as any[],
  links: [] as any[]
})

const fullGraphData = {
  nodes: [] as any[],
  links: [] as any[]
}

const hiddenNodeIds = ref<Set<string>>(new Set())

const restoreHiddenNodes = () => {
  if (hiddenNodeIds.value.size === 0) return
  hiddenNodeIds.value.clear()
  
  graphData.nodes = [...fullGraphData.nodes]
  graphData.links = [...fullGraphData.links]

  if (chartInstance) {
    chartInstance.setOption({
      series: [{
        data: graphData.nodes,
        links: graphData.links
      }]
    })
    updateDynamicMinZoom()
  }
  NotificationService.success('已恢复所有隐藏节点')
}

// 图表缩放等控制
const downloadGraph = (type: 'png' | 'svg') => {
  if (!chartInstance) return
  
  try {
    const url = chartInstance.getDataURL({
      type: type,
      pixelRatio: 2,
      backgroundColor: '#f8f9fa'
    })
    
    const link = document.createElement('a')
    link.href = url
    link.download = `${props.knowledgeBaseName || '知识图谱'}.${type}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    NotificationService.success(`图谱已成功下载为 ${type.toUpperCase()} 格式`)
  } catch (error) {
    console.error('Download graph failed:', error)
    NotificationService.error('下载图谱失败，请重试')
  }
}

const zoomIn = () => {
  if (!chartInstance) return
  if (!canZoomIn.value) return
  applyZoom(currentChartZoom.value * 1.2)
}

const zoomOut = () => {
  if (!chartInstance) return
  if (!canZoomOut.value) return
  applyZoom(currentChartZoom.value * 0.8)
}

const resetZoom = () => {
  if (!chartInstance) return
  const isLargeGraph = currentGraphNodeCount.value >= LARGE_GRAPH_NODE_THRESHOLD
  fitGraphToView(!isLargeGraph, isLargeGraph ? AUTO_FIT_SAMPLE_LIMIT : Number.POSITIVE_INFINITY)
}

// 隐藏/固定/展开等操作
const handleRingAction = (action: string) => {
  if (!actionRing.nodeData || !chartInstance) return

  const nodeId = actionRing.nodeData.id

  if (action === 'hide') {
    // 隐藏节点：将其置为不可见，同时隐藏相关连线
    hiddenNodeIds.value.add(nodeId)
    const newNodes = graphData.nodes.filter(n => n.id !== nodeId)
    const newLinks = graphData.links.filter(l => l.source !== nodeId && l.target !== nodeId)

    graphData.nodes = newNodes
    graphData.links = newLinks

    chartInstance.setOption({
      series: [{
        data: newNodes,
        links: newLinks
      }]
    })
    updateDynamicMinZoom()
    closeActionRing(false, true)
    NotificationService.success(`已隐藏节点: ${actionRing.nodeData.name}`)
  } else if (action === 'pin') {
    // 固定/取消固定
    const nodeIndex = graphData.nodes.findIndex(n => n.id === nodeId)
    if (nodeIndex !== -1) {
      // 切换 fixed 状态
      const isFixed = graphData.nodes[nodeIndex].fixed || false
      graphData.nodes[nodeIndex].fixed = !isFixed

      // 更新 ECharts 的配置以应用新的固定状态
      chartInstance.setOption({
        series: [{
          data: graphData.nodes
        }]
      })

      // 更新当前选中的节点数据，保持面板状态同步
      actionRing.nodeData = { ...graphData.nodes[nodeIndex] }

      NotificationService.success(isFixed ? `已取消固定: ${actionRing.nodeData.name}` : `已固定: ${actionRing.nodeData.name}`)
    }
  } else if (action === 'focus') {
    const data = getGraphSeriesData()
    if (data) {
      const rawIndex = graphData.nodes.findIndex(n => n.id === actionRing.nodeData.id)
      let currentDataIndex = actionRing.dataIndex
      if (rawIndex !== -1 && typeof data.indexOfRawIndex === 'function') {
        currentDataIndex = data.indexOfRawIndex(rawIndex)
      }
      
      if (currentDataIndex !== -1) {
        const layout = data.getItemLayout(currentDataIndex)
        if (layout && Array.isArray(layout) && layout.length >= 2) {
          applyZoom(clampZoom(2), [layout[0], layout[1]])
        }
      }
    }
  } else if (action === 'expand') {
    // 展开节点：恢复被隐藏的相邻节点
    let restoredCount = 0
    const neighborIds = new Set<string>()
    
    // 从完整的连线数据中找出所有与当前节点相连的节点ID
    fullGraphData.links.forEach(link => {
      if (link.source === nodeId) neighborIds.add(link.target as string)
      if (link.target === nodeId) neighborIds.add(link.source as string)
    })
    
    // 检查这些相邻节点是否在隐藏列表中
    const nodesToRestore = Array.from(neighborIds).filter(id => hiddenNodeIds.value.has(id))
    
    if (nodesToRestore.length > 0) {
      nodesToRestore.forEach(id => hiddenNodeIds.value.delete(id))
      
      // 重新计算需要显示的节点和连线
      const newNodes = fullGraphData.nodes.filter(n => !hiddenNodeIds.value.has(n.id))
      const newLinks = fullGraphData.links.filter(l => 
        !hiddenNodeIds.value.has(l.source as string) && !hiddenNodeIds.value.has(l.target as string)
      )
      
      graphData.nodes = newNodes
      graphData.links = newLinks
      
      chartInstance.setOption({
        series: [{
          data: newNodes,
          links: newLinks
        }]
      })
      updateDynamicMinZoom()
      restoredCount = nodesToRestore.length
      NotificationService.success(`已展开 ${restoredCount} 个相邻节点`)
    } else {
      NotificationService.info('该节点周围没有被隐藏的节点')
    }
    closeActionRing(true, false)
  } else if (action === 'close') {
    closeActionRing(true, true)
  }
}

// 更新操作环位置
const updateRingPosition = () => {
  if (!actionRing.visible || !chartInstance || actionRing.dataIndex === -1) return

  try {
    const seriesModel = getGraphSeriesModel()
    const data = getGraphSeriesData()
    if (seriesModel && data) {

      // 力导向图的节点坐标在实时更新，我们需要直接从节点的属性中获取 x, y，而不是 getItemLayout
      // 因为 ECharts 5 内部数据结构有变，推荐在 option.series.data 中读取
      const nodeIndex = graphData.nodes.findIndex(n => n.id === actionRing.nodeData.id)
      if (nodeIndex !== -1) {
        // 获取当前节点最新的位置
        const layout = chartInstance.getOption() as any
        if (layout && layout.series && layout.series[0] && layout.series[0].data) {
          // 力导向图在渲染后，节点数据中会有自动计算的 x, y
          let currentDataIndex = actionRing.dataIndex
          
          if (typeof data.indexOfRawIndex === 'function') {
            currentDataIndex = data.indexOfRawIndex(nodeIndex)
          }

          if (currentDataIndex === -1) {
            // 节点可能被图例过滤隐藏了
            closeActionRing(false, false)
            return
          }

          const pt = data.getItemLayout(currentDataIndex)

          if (pt && Array.isArray(pt)) {
            // 转换为屏幕像素坐标
            const pixelPos = chartInstance.convertToPixel({ seriesIndex: 0 }, pt as number[])
            if (pixelPos && Array.isArray(pixelPos)) {
              actionRing.x = pixelPos[0]
              actionRing.y = pixelPos[1]

              // 获取真实的缩放比例
              let zoom = 1
              if (seriesModel.coordinateSystem && typeof seriesModel.coordinateSystem.getZoom === 'function') {
                zoom = seriesModel.coordinateSystem.getZoom()
              } else {
                const option = chartInstance.getOption() as any
                if (option && option.series && option.series[0] && option.series[0].zoom) {
                  zoom = option.series[0].zoom
                }
              }

              if (!isViewAnimating.value) {
                syncZoomState(zoom)
              }
            }
          }
        }
      }
    }
  } catch (e) {
    console.error('Update ring position error:', e)
    actionRing.visible = false
  }
}

const filteredSelectedNode = computed(() => {
  if (!selectedNode.value) return {}
  const filtered: Record<string, any> = {}
  const excludedKeys = ['itemStyle', 'category', 'symbolSize', 'x', 'y', 'vx', 'vy', 'fixed']
  for (const key in selectedNode.value) {
    if (!excludedKeys.includes(key) && typeof selectedNode.value[key] !== 'object') {
      filtered[key] = selectedNode.value[key]
    }
  }
  return filtered
})

const nodeDetailEntries = computed(() => Object.entries(filteredSelectedNode.value))
const nodePropertyCount = computed(() => nodeDetailEntries.value.length)
const nodeSourceLabel = computed(() => {
  const source = selectedNode.value?.source || selectedNode.value?.kb_source
  return typeof source === 'string' ? source : ''
})

// 颜色分配 (Neo4j Bloom 风格的柔和色彩)
const colorPalette = [
  { fill: '#84cd87', border: '#54b65d' },
  { fill: '#ef7a2e', border: '#de6112' },
  { fill: '#b77acb', border: '#9e5fba' },
  { fill: '#6da8e8', border: '#4d8fd6' },
  { fill: '#e8cf78', border: '#d4b75a' },
  { fill: '#79cde0', border: '#4cb6cf' },
  { fill: '#db91b2', border: '#c86894' },
  { fill: '#a8cd76', border: '#7db04a' }
]
const typeColorMap = new Map<string, { fill: string; border: string }>()

const getColorForType = (type: string) => {
  if (!type) return { fill: '#d1d5db', border: '#9ca3af' }
  if (!typeColorMap.has(type)) {
    const colorIndex = typeColorMap.size % colorPalette.length
    typeColorMap.set(type, colorPalette[colorIndex])
  }
  return typeColorMap.get(type) || { fill: '#d1d5db', border: '#9ca3af' }
}

const getReadableNodeTextColor = (hexColor: string) => {
  const hex = hexColor.replace('#', '')
  if (!/^[0-9A-Fa-f]{6}$/.test(hex)) return '#374151'
  const r = parseInt(hex.slice(0, 2), 16)
  const g = parseInt(hex.slice(2, 4), 16)
  const b = parseInt(hex.slice(4, 6), 16)
  const brightness = (r * 299 + g * 587 + b * 114) / 1000
  return brightness > 160 ? '#374151' : '#f9fafb'
}

const getLegendLayout = () => ({
  left: MINIMAP_OFFSET_LEFT + MINIMAP_WIDTH + LEGEND_SAFE_GAP,
  right: isPanelCollapsed.value
    ? MINIMAP_OFFSET_LEFT
    : FLOATING_PANEL_OFFSET_RIGHT + FLOATING_PANEL_WIDTH + LEGEND_SAFE_GAP,
  bottom: LEGEND_BOTTOM_OFFSET,
  orient: 'horizontal' as const
})

const updateLegendLayout = () => {
  if (!chartInstance) return
  chartInstance.setOption({
    legend: [getLegendLayout()]
  })
}

const getGraphSafeViewMetrics = () => {
  if (!chartInstance || !chartRef.value) {
    return {
      width: 0,
      height: 0,
      centerX: 0,
      centerY: 0
    }
  }

  const width = chartInstance.getWidth()
  const height = chartInstance.getHeight()
  let safeWidth = width
  let safeCenterX = width / 2

  if (floatingPanelRef.value) {
    const chartRect = chartRef.value.getBoundingClientRect()
    const panelRect = floatingPanelRef.value.getBoundingClientRect()
    const overlapWidth = Math.max(0, chartRect.right - panelRect.left)
    safeWidth = Math.max(1, width - overlapWidth)
    safeCenterX = safeWidth / 2
  }

  return {
    width: safeWidth,
    height,
    centerX: safeCenterX,
    centerY: height / 2
  }
}

const getGraphBounds = (sampleLimit = Number.POSITIVE_INFINITY): { minX: number; minY: number; maxX: number; maxY: number } | null => {
  const data = getGraphSeriesData()
  if (!data) return null

  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity

  const count = typeof data.count === 'function' ? data.count() : 0
  const step = Number.isFinite(sampleLimit) && sampleLimit > 0 && count > sampleLimit
    ? Math.ceil(count / sampleLimit)
    : 1
  for (let i = 0; i < count; i += step) {
    const layout = data.getItemLayout(i)
    if (layout && Array.isArray(layout) && layout.length >= 2) {
      const x = layout[0]
      const y = layout[1]
      if (typeof x === 'number' && typeof y === 'number' && Number.isFinite(x) && Number.isFinite(y)) {
        minX = Math.min(minX, x)
        minY = Math.min(minY, y)
        maxX = Math.max(maxX, x)
        maxY = Math.max(maxY, y)
      }
    }
  }

  if (!Number.isFinite(minX) || !Number.isFinite(minY) || !Number.isFinite(maxX) || !Number.isFinite(maxY)) {
    return null
  }

  return { minX, minY, maxX, maxY }
}

const fitGraphToView = (animate = true, sampleLimit = Number.POSITIVE_INFINITY) => {
  if (!chartInstance) return

  const bounds = getGraphBounds(sampleLimit)
  if (!bounds) {
    applyZoom(1, null, animate)
    return
  }

  const { width: safeWidthPx, height: safeHeightPx, centerX: safeCenterPxX, centerY: safeCenterPxY } =
    getGraphSafeViewMetrics()

  const paddingPx = 72
  const viewWidthPx = Math.max(1, safeWidthPx - paddingPx * 2)
  const viewHeightPx = Math.max(1, safeHeightPx - paddingPx * 2)

  const boundsWidth = Math.max(1, bounds.maxX - bounds.minX)
  const boundsHeight = Math.max(1, bounds.maxY - bounds.minY)

  const zoomX = viewWidthPx / boundsWidth
  const zoomY = viewHeightPx / boundsHeight
  const nextZoom = clampZoom(Math.min(zoomX, zoomY))

  const boundsCenterX = (bounds.minX + bounds.maxX) / 2
  const boundsCenterY = (bounds.minY + bounds.maxY) / 2

  const canvasCenterX = chartInstance.getWidth() / 2
  const canvasCenterY = chartInstance.getHeight() / 2
  const offsetPxX = canvasCenterX - safeCenterPxX
  const offsetPxY = canvasCenterY - safeCenterPxY
  const targetCenter: [number, number] = [
    boundsCenterX + offsetPxX / Math.max(nextZoom, ZOOM_EPSILON),
    boundsCenterY + offsetPxY / Math.max(nextZoom, ZOOM_EPSILON)
  ]

  applyZoom(nextZoom, targetCenter, animate)
}

const loadGraph = async () => {
  if (!props.knowledgeBaseName || !chartInstance) return

  loading.value = true
  chartInstance.showLoading('default', {
    text: '加载中',
    color: '#3b82f6',
    textColor: '#4b5563',
    maskColor: 'rgba(255, 255, 255, 0.8)'
  })

  try {
    const data = await showKnowledgeBaseGraph({
      knowledge_base_name: props.knowledgeBaseName,
      graph_size: graphSize.value
    })

    // 解析数据
    const nodesMap = new Map<string, any>()
    const links: any[] = []

    // data 应该是一个元组列表 [[node1, rel, node2], ...]
    if (Array.isArray(data)) {
      data.forEach(tuple => {
        if (Array.isArray(tuple) && tuple.length >= 3) {
          const source = tuple[0]
          const rel = tuple[1]
          const target = tuple[2]

          if (source && source.id) {
            if (!nodesMap.has(source.id)) {
              nodesMap.set(source.id, { ...source, name: source.name || source.id, symbolSize: 50 })
            }
          }

          if (target && target.id) {
            if (!nodesMap.has(target.id)) {
              nodesMap.set(target.id, { ...target, name: target.name || target.id, symbolSize: 50 })
            }
          }

          if (source && source.id && target && target.id) {
            // Avoid duplicate links
            const linkId = `${source.id}-${rel}-${target.id}`
            links.push({
              id: linkId,
              source: source.id,
              target: target.id,
              value: rel,
              rawLabel: rel
            })
          }
        }
      })
    }

    const rawNodes = Array.from(nodesMap.values())
    const nodeCount = rawNodes.length
    currentGraphNodeCount.value = nodeCount
    updateDynamicMinZoom()
    const simplifiedMode = nodeCount >= 700
    const useCircularLayout = nodeCount >= 1200
    const shouldAnimateGraph = nodeCount < 450
    const showEdgeLabel = nodeCount <= 250
    const showNodeLabel = nodeCount <= 600

    const nodes = rawNodes.map(node => {
      const nodeColor = getColorForType(node.type)
      const baseSymbolSize = simplifiedMode ? 26 : 50
      return {
        ...node,
        symbolSize: typeof node.symbolSize === 'number' ? node.symbolSize : baseSymbolSize,
        itemStyle: {
          color: nodeColor.fill,
          borderColor: nodeColor.border,
          borderWidth: simplifiedMode ? 2 : 3,
          shadowBlur: simplifiedMode ? 0 : 6,
          shadowColor: simplifiedMode ? 'transparent' : 'rgba(30, 41, 59, 0.12)'
        },
        label: {
          show: showNodeLabel,
          position: 'inside',
          color: getReadableNodeTextColor(nodeColor.fill),
          fontSize: simplifiedMode ? 10 : 12,
          formatter: showNodeLabel
            ? function (params: any) {
              const name = params.name || ''
              return typeof name === 'string' && name.length > 5 ? name.substring(0, 4) + '...' : name
            }
            : undefined
        },
        category: node.type
      }
    })

    const styledLinks = links.map(link => {
      if (!showEdgeLabel) return link
      return {
        ...link,
        label: {
          show: true,
          formatter: link.rawLabel,
          fontSize: 11,
          color: '#5C6370',
          backgroundColor: 'rgba(255, 255, 255, 0.8)',
          padding: [3, 5],
          borderRadius: 4
        }
      }
    })

    // 缓存数据以便后续操作
    graphData.nodes = nodes
    graphData.links = styledLinks
    
    fullGraphData.nodes = [...nodes]
    fullGraphData.links = [...styledLinks]
    hiddenNodeIds.value.clear()

    const categories = Array.from(typeColorMap.entries()).map(([name, style]) => ({
      name,
      itemStyle: {
        color: style.fill,
        borderColor: style.border,
        borderWidth: 2
      }
    }))

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      hoverLayerThreshold: 1000, // 优化：节点多时启用独立hover层，提升交互性能
      tooltip: {
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        borderColor: '#e5e7eb',
        textStyle: { color: '#374151' },
        formatter: function (params: any) {
          if (params.dataType === 'node') {
            return `<div style="padding: 4px;">
              <strong style="color: ${params.data.itemStyle?.borderColor || params.color}; font-size: 14px;">${params.data.name}</strong><br/>
              <span style="color: #6b7280; font-size: 12px;">Type: ${params.data.type || 'Unknown'}</span>
            </div>`
          }
          return `${params.data.source} > <strong>${params.data.value}</strong> > ${params.data.target}`
        }
      },
      legend: [{
        ...getLegendLayout(),
        data: categories.map(a => a.name),
        textStyle: { color: '#4b5563' },
        itemWidth: 12,
        itemHeight: 12,
        icon: 'circle'
      }],
      animation: shouldAnimateGraph,
      animationDurationUpdate: shouldAnimateGraph ? 800 : 0,
      animationEasingUpdate: shouldAnimateGraph ? 'cubicOut' : 'linear',
      series: [
        {
          type: 'graph',
          layout: useCircularLayout ? 'circular' : 'force',
          progressive: 4000,
          progressiveThreshold: 2000,
          data: nodes,
          links: styledLinks,
          categories: categories,
          roam: false,
          zoom: 1,
          scaleLimit: {
            min: currentMinChartZoom.value,
            max: MAX_CHART_ZOOM
          },
          nodeScaleRatio: 0.6, // TypeScript要求必须是 0.6，我们顺应Echarts默认值，去修改上层圆环缩放的逻辑
          label: {
            show: showNodeLabel,
            position: 'inside',
            formatter: '{b}'
          },
          edgeSymbol: ['none', 'arrow'],
          edgeSymbolSize: simplifiedMode ? [2, 6] : [4, 8],
          edgeLabel: {
            fontSize: 12
          },
          draggable: !simplifiedMode,
          force: useCircularLayout
            ? undefined
            : {
              repulsion: simplifiedMode ? 260 : 800,
              edgeLength: simplifiedMode ? [60, 140] : [100, 250],
              gravity: simplifiedMode ? 0.2 : 0.1,
              friction: simplifiedMode ? 0.25 : 0.1,
              layoutAnimation: !simplifiedMode
            },
          lineStyle: {
            color: '#A5ABB6',
            width: simplifiedMode ? 1 : 1.5,
            curveness: 0.15,
            opacity: simplifiedMode ? 0.45 : 0.8
          },
          emphasis: {
            focus: simplifiedMode ? 'none' : 'adjacency',
            lineStyle: {
              width: 3,
              color: '#3b82f6'
            },
            itemStyle: {
              shadowBlur: simplifiedMode ? 0 : 20,
              borderWidth: simplifiedMode ? 2 : 3
            }
          }
        } as any
      ]
    }

    chartInstance.setOption(option, { notMerge: true, lazyUpdate: true })
    syncZoomState(1)
    closeActionRing(false, true)
    nextTick(() => {
      if (!chartInstance) return
      chartInstance.resize()
      updateLegendLayout()
    })

  } catch (error: any) {
    console.error('Failed to load graph', error)
    NotificationService.error(error.message || '加载知识图谱失败')
  } finally {
    loading.value = false
    chartInstance.hideLoading()
  }
}

const handleGraphWheel = (e: WheelEvent) => {
  if (!chartInstance) return

  const isAtMax = currentChartZoom.value >= MAX_CHART_ZOOM - ZOOM_EPSILON
  const isAtMin = currentChartZoom.value <= currentMinChartZoom.value + ZOOM_EPSILON

  // 在极限位置且继续向该方向滚动时直接忽略，避免触发不必要的平移
  if ((isAtMax && e.deltaY < 0) || (isAtMin && e.deltaY > 0)) {
    e.preventDefault()
    e.stopPropagation()
    return
  }

  // 始终手动接管滚轮缩放，避免与 ECharts roam 的事件处理冲突导致断触
  e.preventDefault()
  e.stopPropagation()

  const rect = chartRef.value?.getBoundingClientRect()
  if (!rect) return

  const mouseX = e.clientX - rect.left
  const mouseY = e.clientY - rect.top

  // 获取鼠标所在逻辑坐标
  const logicalPt = chartInstance.convertFromPixel({ seriesIndex: 0 }, [mouseX, mouseY])
  const currentCenter = getNumericSeriesCenter()

  const zoomFactor = e.deltaY > 0 ? 0.8 : 1.2
  const nextZoom = clampZoom(currentChartZoom.value * zoomFactor)

  if (logicalPt && Array.isArray(logicalPt) && currentCenter) {
    const z1 = currentChartZoom.value
    const z2 = nextZoom
    const newCenterX = currentCenter[0] * (z1 / z2) + logicalPt[0] * (1 - z1 / z2)
    const newCenterY = currentCenter[1] * (z1 / z2) + logicalPt[1] * (1 - z1 / z2)

    applyZoom(nextZoom, [newCenterX, newCenterY], false)
  } else {
    applyZoom(nextZoom, null, false)
  }
}

onMounted(() => {
  if (chartRef.value) {
    chartInstance = echarts.init(chartRef.value)
    const zr = chartInstance.getZr()

    // 绑定滚轮事件以修复极限缩放卡死问题
    chartRef.value.addEventListener('wheel', handleGraphWheel, { passive: false })

    chartInstance.on('click', (params: any) => {
      if (params.dataType === 'node') {
        switchActionRingNode(params)
      } else {
        closeActionRing(true, true)
      }
    })

    // 节流小地图更新，避免在力导向图动画期间引发严重的性能问题
    const throttledUpdateMinimap = useThrottleFn(() => {
      drawMinimapCanvas()
      updateMinimapViewport()
    }, 100)

    // 添加力导向图实时更新事件，让操作环跟随节点
    chartInstance.on('rendered', () => {
      if (actionRing.visible) {
        updateRingPosition()
      }
      throttledUpdateMinimap()
    })

    chartInstance.on('graphRoam', () => {
      syncZoomState()
      if (actionRing.visible) {
        updateRingPosition()
      }
      updateMinimapViewport()
    })

    // ECharts的空白处点击
    chartInstance.getZr().on('click', (e) => {
      if (!e.target) {
        closeActionRing(true, true)
      }
    })
    zr.on('mousedown', (e: any) => {
      if (e.target) return
      const nativeEvent = e.event as MouseEvent | undefined
      if (!nativeEvent) return
      beginPanDrag(nativeEvent)
    })
    
    window.addEventListener('resize', handleResize)
    window.addEventListener('mousemove', handleGlobalMouseMove)
    window.addEventListener('mouseup', handleGlobalMouseUp)

    // Load initial graph
    loadGraph()
  }
})

const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
    updateLegendLayout()
  }
}

const minimapCanvasRef = ref<HTMLCanvasElement | null>(null)
const minimapRef = ref<HTMLElement | null>(null)
const minimapViewportStyle = reactive({
  left: '0%',
  top: '0%',
  width: '100%',
  height: '100%'
})

function drawMinimapCanvas() {
  if (!minimapCanvasRef.value || !chartInstance || !minimapRef.value) return
  const canvas = minimapCanvasRef.value
  const container = minimapRef.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  const bounds = getGraphBounds()
  if (!bounds) return
  
  const padding = 12
  const rect = container.getBoundingClientRect()
  if (rect.width === 0 || rect.height === 0) return
  
  const dpr = window.devicePixelRatio || 1
  canvas.width = rect.width * dpr
  canvas.height = rect.height * dpr
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  
  const w = rect.width
  const h = rect.height
  
  const bw = bounds.maxX - bounds.minX || 1
  const bh = bounds.maxY - bounds.minY || 1
  const scale = Math.max(0.0001, Math.min((w - padding * 2) / bw, (h - padding * 2) / bh))
  
  ctx.clearRect(0, 0, w, h)
  
  const data = getGraphSeriesData()
  if (!data) return
  
  const count = data.count()
  ctx.fillStyle = 'rgba(96, 165, 250, 0.75)'
  
  ctx.beginPath()
  for (let i = 0; i < count; i++) {
    const layout = data.getItemLayout(i)
    if (layout && layout.length >= 2) {
      const x = (layout[0] - bounds.minX - bw/2) * scale + w/2
      const y = (layout[1] - bounds.minY - bh/2) * scale + h/2
      ctx.moveTo(x + 1.5, y)
      ctx.arc(x, y, 1.5, 0, Math.PI * 2)
    }
  }
  ctx.fill()
}

function updateMinimapViewport() {
  if (!minimapRef.value || !chartInstance) return
  const bounds = getGraphBounds()
  if (!bounds) return
  
  const canvasW = chartInstance.getWidth()
  const canvasH = chartInstance.getHeight()
  
  const zoom = currentChartZoom.value || 1
  let cx = (bounds.minX + bounds.maxX) / 2
  let cy = (bounds.minY + bounds.maxY) / 2
  
  const center = getCurrentSeriesCenter()
  if (center && Array.isArray(center)) {
    if (typeof center[0] === 'number') cx = center[0]
    if (typeof center[1] === 'number') cy = center[1]
  }
  
  const visW = canvasW / zoom
  const visH = canvasH / zoom
  
  const visMinX = cx - visW / 2
  const visMinY = cy - visH / 2
  
  const bw = bounds.maxX - bounds.minX || 1
  const bh = bounds.maxY - bounds.minY || 1
  
  const padding = 12
  const w = minimapRef.value.clientWidth
  const h = minimapRef.value.clientHeight
  if (w === 0 || h === 0) return
  const scale = Math.max(0.0001, Math.min((w - padding * 2) / bw, (h - padding * 2) / bh))
  
  const mapVisW = w / scale
  const mapVisH = h / scale
  const mapMinX = (bounds.minX + bounds.maxX) / 2 - mapVisW / 2
  const mapMinY = (bounds.minY + bounds.maxY) / 2 - mapVisH / 2
  
  let left = (visMinX - mapMinX) / mapVisW * 100
  let top = (visMinY - mapMinY) / mapVisH * 100
  let width = visW / mapVisW * 100
  let height = visH / mapVisH * 100
  
  left = Math.max(0, left)
  top = Math.max(0, top)
  width = Math.min(100 - left, width)
  height = Math.min(100 - top, height)
  
  minimapViewportStyle.left = `${left}%`
  minimapViewportStyle.top = `${top}%`
  minimapViewportStyle.width = `${width}%`
  minimapViewportStyle.height = `${height}%`
}

const handleMinimapClick = (e: MouseEvent) => {
  if (minimapHasDragged) return
  if (!minimapRef.value || !chartInstance) return
  const bounds = getGraphBounds()
  if (!bounds) return
  
  const rect = minimapRef.value.getBoundingClientRect()
  const clickX = e.clientX - rect.left
  const clickY = e.clientY - rect.top
  
  const w = rect.width
  const h = rect.height
  const padding = 12
  const bw = bounds.maxX - bounds.minX || 1
  const bh = bounds.maxY - bounds.minY || 1
  const scale = Math.max(0.0001, Math.min((w - padding * 2) / bw, (h - padding * 2) / bh))
  
  const logicalX = (clickX - w/2) / scale + (bounds.minX + bounds.maxX) / 2
  const logicalY = (clickY - h/2) / scale + (bounds.minY + bounds.maxY) / 2
  
  applyZoom(currentChartZoom.value, [logicalX, logicalY], true)
}

onUnmounted(() => {
  if (chartRef.value) {
    chartRef.value.removeEventListener('wheel', handleGraphWheel)
  }
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('mousemove', handleGlobalMouseMove)
  window.removeEventListener('mouseup', handleGlobalMouseUp)
  endPanDrag()
  clearRingSwitchTimer()
  stopViewAnimation()
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})

// watch knowledge base name changes
watch(() => props.knowledgeBaseName, (newVal) => {
  if (newVal) {
    selectedNode.value = null
    loadGraph()
  }
})

watch(isPanelCollapsed, () => {
  nextTick(() => {
    updateLegendLayout()
  })
})
</script>

<style scoped>
.kg-container {
  position: relative;
  height: 100%;
  width: 100%;
  background-color: #f8f9fa;
  background-image: radial-gradient(#d1d5db 1px, transparent 1px);
  background-size: 20px 20px;
  border-radius: 14px;
  overflow: hidden;
}

.kg-graph {
  width: 100%;
  height: 100%;
  position: absolute;
  inset: 0;
  cursor: grab;
}

.kg-graph.is-panning {
  cursor: grabbing;
}

.kg-graph :deep(canvas) {
  border-radius: 14px;
  border: none;
  outline: none;
  cursor: grab !important;
}

.kg-graph.is-panning :deep(canvas) {
  cursor: grabbing !important;
}

/* 缩略图 */
.kg-minimap {
  position: absolute;
  bottom: 84px;
  left: 24px;
  width: 223px;
  height: 125px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.42), rgba(255, 255, 255, 0.18));
  backdrop-filter: blur(18px) saturate(170%);
  -webkit-backdrop-filter: blur(18px) saturate(170%);
  border-radius: 18px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.48);
  z-index: 10;
  overflow: hidden;
  transition: all 0.3s ease;
  cursor: pointer;
}

.kg-minimap:hover {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.55), rgba(255, 255, 255, 0.25));
  border-color: rgba(255, 255, 255, 0.7);
}

.kg-minimap-content {
  width: 100%;
  height: 100%;
  opacity: 1;
  z-index: 0;
  pointer-events: none;
}

.minimap-placeholder-icon {
  font-size: 24px;
}

.minimap-text {
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 1px;
}

.kg-minimap-viewport {
  position: absolute;
  top: 25%;
  left: 20%;
  width: 40%;
  height: 35%;
  border: 1.5px solid rgba(59, 130, 246, 0.6);
  background: rgba(59, 130, 246, 0.15);
  border-radius: 16px;
  z-index: 1;
  pointer-events: none;
  box-shadow: 0 0 0 999px rgba(255, 255, 255, 0.1);
}

/* 缩放控制 */
.kg-controls {
  position: absolute;
  bottom: 24px;
  left: 24px;
  display: flex;
  align-items: center;
  gap: 4px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.42), rgba(255, 255, 255, 0.18));
  backdrop-filter: blur(18px) saturate(170%);
  -webkit-backdrop-filter: blur(18px) saturate(170%);
  padding: 6px;
  border-radius: 9999px;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.16), inset 0 1px 0 rgba(255, 255, 255, 0.72), inset 0 -1px 0 rgba(255, 255, 255, 0.22);
  border: 1px solid rgba(255, 255, 255, 0.48);
  z-index: 10;
  overflow: hidden;
  isolation: isolate;
}

.kg-controls::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 58%;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.62), rgba(255, 255, 255, 0.08));
  pointer-events: none;
}

.kg-controls-divider {
  width: 1px;
  height: 15px;
  margin: 0 2px;
  background: rgba(0, 0, 0, 0.671);
  margin-left: 10px;
  margin-right: 10px;
}

.kg-control-btn {
  position: relative;
  z-index: 10;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  color: #334155;
  cursor: pointer;
  transition: all 0.3s ease;
  overflow: hidden;
}

.kg-control-btn:hover {
  background: rgba(255, 255, 255, 0.6);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.kg-control-btn:active {
  transform: translateY(0);
  background: rgba(255, 255, 255, 0.8);
}

.kg-control-btn[disabled] {
  background: transparent;
  color: #9ca3af;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.control-icon {
  width: 16px;
  height: 16px;
  object-fit: contain;
}

/* 操作环 */
.action-ring-container {
  position: absolute;
  width: 0;
  height: 0;
  z-index: 20;
  pointer-events: none;
  /* 让事件穿透容器 */
}

.action-ring {
  position: absolute;
  top: 0;
  left: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

.ring-zoom-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 0;
  height: 0;
  transform-origin: center center;
}

.action-ring.ring-enter {
  animation: ring-pop 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
}

.action-ring.ring-exit {
  animation: ring-push-out 0.18s ease-out forwards;
  pointer-events: none;
}

@keyframes ring-pop {
  0% {
    transform: scale(0.5);
    opacity: 0;
  }

  100% {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes ring-push-out {
  0% {
    transform: scale(1);
    opacity: 1;
  }

  100% {
    transform: scale(0.65);
    opacity: 0;
  }
}

.ring-svg {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.ring-sector-path {
  fill: rgba(229, 231, 235, 0.85);
  stroke: #ffffff;
  stroke-width: 3px;
  cursor: pointer;
  pointer-events: auto;
  transition: all 0.2s ease;
}

.ring-sector-path:hover,
.ring-sector-path.hovered {
  fill: rgba(209, 213, 219, 0.95);
}

.ring-icon-wrapper {
  position: absolute;
  top: 0;
  left: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

.ring-icon {
  position: absolute;
  top: -10px;
  left: -10px;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: #4b5563;
  transition: all 0.2s ease;
  transform-origin: center center;
}

.ring-icon.hovered {
  color: #111827;
}

/* 悬浮面板包装器 */
.kg-floating-panel-wrapper {
  position: absolute;
  top: 24px;
  right: 24px;
  bottom: 24px;
  width: 340px;
  z-index: 30;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.kg-floating-panel-wrapper.is-collapsed {
  transform: translateX(calc(100% + 24px));
}

/* 收起/展开按钮 */
.panel-toggle-btn {
  position: absolute;
  left: -24px;
  top: 50%;
  transform: translateY(-50%);
  width: 24px;
  height: 64px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.85), rgba(255, 255, 255, 0.75));
  backdrop-filter: blur(12px) saturate(155%);
  -webkit-backdrop-filter: blur(12px) saturate(155%);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-right: none;
  border-radius: 12px 0 0 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #4b5563;
  box-shadow: -4px 0 12px rgba(15, 23, 42, 0.05);
  transition: all 0.3s ease;
  z-index: 11;
}

.panel-toggle-btn:hover {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(255, 255, 255, 0.85));
  color: #111827;
  width: 28px;
  left: -28px;
}

.kg-floating-panel {
  width: 100%;
  height: 100%;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.85), rgba(255, 255, 255, 0.75));
  backdrop-filter: blur(12px) saturate(155%);
  -webkit-backdrop-filter: blur(12px) saturate(155%);
  border-radius: 16px;
  box-shadow: 0 10px 34px rgba(15, 23, 42, 0.14), inset 0 1px 0 rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.5);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.3s ease;
}

.panel-section {
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.props-section {
  flex: 1;
  overflow-y: auto;
  gap: 12px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 14px;
}

.section-header .anticon {
  color: #3b82f6;
}

.setting-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.setting-label {
  font-size: 13px;
  color: #4b5563;
  font-weight: 500;
}

.setting-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.panel-divider {
  height: 1px;
  background: linear-gradient(to right, transparent, rgba(229, 231, 235, 0.8), transparent);
  margin: 0 12px;
}

.node-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.node-summary-card {
  padding: 12px;
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.92));
  border: 1px solid rgba(226, 232, 240, 0.85);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
}

.node-summary-head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.node-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 700;
  color: white;
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.16);
  flex-shrink: 0;
}

.node-title-box {
  flex: 1;
  min-width: 0;
}

.node-name {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 6px;
}

.node-type-tag {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid;
  background: rgba(255, 255, 255, 0.92);
  font-weight: 600;
}

.node-meta-row {
  margin-top: 9px;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.node-meta-pill {
  max-width: 160px;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 10px;
  line-height: 1.7;
  color: #475569;
  background: rgba(241, 245, 249, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.95);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.node-meta-source {
  max-width: 185px;
}

.node-id-line {
  margin-top: 7px;
  font-size: 11px;
  color: #94a3b8;
  padding: 6px 8px;
  border-radius: 8px;
  background: rgba(248, 250, 252, 0.85);
  border: 1px dashed rgba(226, 232, 240, 0.9);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.props-list {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.85);
  padding: 4px 10px;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.prop-item {
  display: grid;
  grid-template-columns: 78px minmax(0, 1fr);
  gap: 8px;
  align-items: start;
  padding: 9px 2px;
  border-bottom: 1px solid rgba(241, 245, 249, 0.95);
}

.prop-item:last-child {
  border-bottom: none;
}

.prop-key {
  font-size: 11px;
  color: #64748b;
  letter-spacing: 0;
  font-weight: 600;
  word-break: break-word;
  text-transform: none;
}

.prop-value {
  font-size: 12px;
  color: #0f172a;
  word-break: break-word;
  line-height: 1.6;
}

.node-props-empty {
  padding: 18px 14px;
  text-align: center;
  border-radius: 10px;
  border: 1px dashed rgba(203, 213, 225, 0.9);
  background: rgba(248, 250, 252, 0.75);
  color: #94a3b8;
  font-size: 12px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  color: #9ca3af;
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state p {
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 10px;
  font-weight: 500;
  font-size: 14px;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn.primary {
  background: #3b82f6;
  color: white;
}

.action-btn.primary:hover {
  background: #2563eb;
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
