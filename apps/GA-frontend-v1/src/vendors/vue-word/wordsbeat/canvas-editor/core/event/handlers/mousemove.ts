import { ImageDisplay } from '../../../dataset/enum/Common'
import { ControlComponent } from '../../../dataset/enum/Control'
import { ElementType } from '../../../dataset/enum/Element'
import { CanvasEvent } from '../CanvasEvent'
import { Draw } from '../../draw/Draw'

let renderRafId: number | null = null

function scheduleRender(draw: Draw) {
  if (renderRafId !== null) return
  renderRafId = window.requestAnimationFrame(() => {
    renderRafId = null
    draw.render({
      isSubmitHistory: false,
      isSetCursor: false,
      isCompute: false
    })
  })
}

function getPointerInCanvas(evt: MouseEvent) {
  const target = evt.target as HTMLElement | null
  const canvas = target?.closest('canvas[data-index]') as HTMLCanvasElement | null
  if (!canvas) {
    return {
      x: evt.offsetX,
      y: evt.offsetY,
      pageNo: null as number | null
    }
  }
  const rect = canvas.getBoundingClientRect()
  const width = rect.width || canvas.width
  const height = rect.height || canvas.height
  const x = Math.max(0, Math.min(evt.clientX - rect.left, width))
  const y = Math.max(0, Math.min(evt.clientY - rect.top, height))
  const pageNo = Number(canvas.dataset.index)
  return { x, y, pageNo: Number.isNaN(pageNo) ? null : pageNo }
}

export function mousemove(evt: MouseEvent, host: CanvasEvent) {
  const draw = host.getDraw()
  const { x, y, pageNo } = getPointerInCanvas(evt)
  if (pageNo !== null) {
    draw.setPageNo(pageNo)
  }
  // 是否是拖拽文字
  if (host.isAllowDrag) {
    // 是否允许拖拽到选区
    const { startIndex, endIndex } = host.cacheRange!
    const positionList = host.cachePositionList!
    for (let p = startIndex + 1; p <= endIndex; p++) {
      const {
        coordinate: { leftTop, rightBottom }
      } = positionList[p]
      if (
        x >= leftTop[0] &&
        x <= rightBottom[0] &&
        y >= leftTop[1] &&
        y <= rightBottom[1]
      ) {
        return
      }
    }
    const cacheStartIndex = host.cacheRange?.startIndex
    if (cacheStartIndex) {
      // 浮动元素拖拽调整位置
      const dragElement = host.cacheElementList![cacheStartIndex]
      if (
        dragElement?.type === ElementType.IMAGE &&
        (dragElement.imgDisplay === ImageDisplay.SURROUND ||
          dragElement.imgDisplay === ImageDisplay.FLOAT_TOP ||
          dragElement.imgDisplay === ImageDisplay.FLOAT_BOTTOM)
      ) {
        draw.getPreviewer().clearResizer()
        draw.getImageParticle().dragFloatImage(evt.movementX, evt.movementY)
      }
    }
    host.dragover(evt)
    host.isAllowDrop = true
    return
  }
  if (!host.isAllowSelection || !host.mouseDownStartPosition) return
  // 结束位置
  const position = draw.getPosition()
  const positionResult = position.getPositionByXY({
    x,
    y
  })
  if (!~positionResult.index) return
  const {
    index,
    isTable,
    tdValueIndex,
    tdIndex,
    trIndex,
    tableId,
    trId,
    tdId
  } = positionResult
  const {
    index: startIndex,
    isTable: startIsTable,
    tdIndex: startTdIndex,
    trIndex: startTrIndex,
    tableId: startTableId
  } = host.mouseDownStartPosition
  const endIndex = isTable ? tdValueIndex! : index
  // 判断是否是表格跨行/列
  const rangeManager = draw.getRange()
  if (
    isTable &&
    startIsTable &&
    (tdIndex !== startTdIndex || trIndex !== startTrIndex)
  ) {
    rangeManager.setRange(
      endIndex,
      endIndex,
      tableId,
      startTdIndex,
      tdIndex,
      startTrIndex,
      trIndex
    )
    position.setPositionContext({
      isTable,
      index,
      trIndex,
      tdIndex,
      tdId,
      trId,
      tableId
    })
  } else {
    let end = ~endIndex ? endIndex : 0
    // 开始或结束位置存在表格，但是非相同表格则忽略选区设置
    if ((startIsTable || isTable) && startTableId !== tableId) return
    // 开始位置
    let start = startIndex
    if (start > end) {
      // eslint-disable-next-line @typescript-eslint/no-extra-semi
      ;[start, end] = [end, start]
    }
    if (start === end) return
    // 背景文本禁止选区
    const elementList = draw.getElementList()
    const startElement = elementList[start + 1]
    const endElement = elementList[end]
    if (
      startElement?.controlComponent === ControlComponent.PLACEHOLDER &&
      endElement?.controlComponent === ControlComponent.PLACEHOLDER &&
      startElement.controlId === endElement.controlId
    ) {
      return
    }
    rangeManager.setRange(start, end)
  }
  // 绘制
  scheduleRender(draw)
}
