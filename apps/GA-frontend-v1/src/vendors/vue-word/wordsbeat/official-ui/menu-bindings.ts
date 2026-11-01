
import { Dialog } from './components/dialog/Dialog';
import { Signature } from './components/signature/Signature';
import { debounce, nextTick, scrollIntoView } from './utils';
import prism from 'prismjs';
import { formatPrismToken } from './utils/prism';
import {
  BlockType,
  Command,
  ControlState,
  ControlType,
  EditorMode,
  EditorZone,
  ElementType,
  IBlock,
  ICatalogItem,
  IElement,
  KeyMap,
  ListStyle,
  ListType,
  PageMode,
  PaperDirection,
  RowFlex,
  TextDecorationStyle,
  TitleLevel,
  splitText
} from '../canvas-editor';

export function bindEditorUI(instance: any) {
  const isApple =
    typeof navigator !== 'undefined' && /Mac OS X/.test(navigator.userAgent)

  // 1. 模拟批注列表
  const commentList: any[] = []

  // 统一处理下拉框打开/关闭：互斥 + 点击外部关闭（包含顶部菜单和底部 footer）
  const dropdownSelector = '.menu-item .options.visible, .footer .options.visible'
  const closeAllOptions = () => {
    document.querySelectorAll<HTMLElement>(dropdownSelector).forEach(opt => {
      opt.classList.remove('visible')
    })
  }
  const toggleOption = (el: HTMLElement) => {
    const isVisible = el.classList.contains('visible')
    closeAllOptions()
    if (!isVisible) {
      el.classList.add('visible')
    }
  }

  const setSelectText = (selectEl: HTMLElement, value: string) => {
    const labelEl = selectEl.querySelector<HTMLElement>('.select__label')
    if (labelEl) {
      labelEl.innerText = value
      return
    }
    selectEl.innerText = value
  }

  document.addEventListener('click', (evt) => {
    const target = evt.target as HTMLElement
    // 点击下拉触发区域之外时，关闭所有下拉
    if (!target.closest('.menu-item, .page-mode, .paper-size, .paper-direction')) {
      closeAllOptions()
    }
  })

  // 覆盖获取 document.querySelector 的方法为我们当前组件内的，或者默认用 document
  // 因为 vue 模板里直接用了相同的 class

  // 2. | 撤销 | 重做 | 格式刷 | 清除格式 |
  const undoDom = document.querySelector<HTMLDivElement>('.menu-item__undo')!
  undoDom.title = `撤销(${isApple ? '⌘' : 'Ctrl'}+Z)`
  undoDom.onclick = function () {
    console.log('undo')
    instance.command.executeUndo()
  }

  const redoDom = document.querySelector<HTMLDivElement>('.menu-item__redo')!
  redoDom.title = `重做(${isApple ? '⌘' : 'Ctrl'}+Y)`
  redoDom.onclick = function () {
    console.log('redo')
    instance.command.executeRedo()
  }

  const painterDom = document.querySelector<HTMLDivElement>(
    '.menu-item__painter'
  )!

  let isFirstClick = true
  let painterTimeout: number
  painterDom.onclick = function () {
    if (isFirstClick) {
      isFirstClick = false
      painterTimeout = window.setTimeout(() => {
        console.log('painter-click')
        isFirstClick = true
        instance.command.executePainter({
          isDblclick: false
        })
      }, 200)
    } else {
      window.clearTimeout(painterTimeout)
    }
  }

  painterDom.ondblclick = function () {
    console.log('painter-dblclick')
    isFirstClick = true
    window.clearTimeout(painterTimeout)
    instance.command.executePainter({
      isDblclick: true
    })
  }

  document.querySelector<HTMLDivElement>('.menu-item__format')!.onclick =
    function () {
      console.log('format')
      instance.command.executeFormat()
    }

  // 3. | 字体 | 字体变大 | 字体变小 | 加粗 | 斜体 | 下划线 | 删除线 | 上标 | 下标 | 字体颜色 | 背景色 |
  const fontDom = document.querySelector<HTMLDivElement>('.menu-item__font')!
  const fontSelectDom = fontDom.querySelector<HTMLDivElement>('.select')!
  const fontOptionDom = fontDom.querySelector<HTMLDivElement>('.options')!
  fontDom.onclick = function () {
    console.log('font')
    toggleOption(fontOptionDom)
  }
  fontOptionDom.onclick = function (evt) {
    const li = evt.target as HTMLLIElement
    instance.command.executeFont(li.dataset.family!)
  }

  const sizeSetDom = document.querySelector<HTMLDivElement>('.menu-item__size')!
  const sizeSelectDom = sizeSetDom.querySelector<HTMLDivElement>('.select')!
  const sizeOptionDom = sizeSetDom.querySelector<HTMLDivElement>('.options')!
  sizeSetDom.title = `设置字号`
  sizeSetDom.onclick = function () {
    console.log('size')
    toggleOption(sizeOptionDom)
  }
  sizeOptionDom.onclick = function (evt) {
    const li = evt.target as HTMLLIElement
    instance.command.executeSize(Number(li.dataset.size!))
  }

  const sizeAddDom = document.querySelector<HTMLDivElement>(
    '.menu-item__size-add'
  )!
  sizeAddDom.title = `增大字号(${isApple ? '⌘' : 'Ctrl'}+[)`
  sizeAddDom.onclick = function () {
    console.log('size-add')
    instance.command.executeSizeAdd()
  }

  const sizeMinusDom = document.querySelector<HTMLDivElement>(
    '.menu-item__size-minus'
  )!
  sizeMinusDom.title = `减小字号(${isApple ? '⌘' : 'Ctrl'}+])`
  sizeMinusDom.onclick = function () {
    console.log('size-minus')
    instance.command.executeSizeMinus()
  }

  const boldDom = document.querySelector<HTMLDivElement>('.menu-item__bold')!
  boldDom.title = `加粗(${isApple ? '⌘' : 'Ctrl'}+B)`
  boldDom.onclick = function () {
    console.log('bold')
    instance.command.executeBold()
  }

  const italicDom =
    document.querySelector<HTMLDivElement>('.menu-item__italic')!
  italicDom.title = `斜体(${isApple ? '⌘' : 'Ctrl'}+I)`
  italicDom.onclick = function () {
    console.log('italic')
    instance.command.executeItalic()
  }

  const underlineDom = document.querySelector<HTMLDivElement>(
    '.menu-item__underline'
  )!
  underlineDom.title = `下划线(${isApple ? '⌘' : 'Ctrl'}+U)`
  const underlineOptionDom =
    underlineDom.querySelector<HTMLDivElement>('.options')!
  underlineDom.querySelector<HTMLSpanElement>('.select')!.onclick =
    function () {
      toggleOption(underlineOptionDom)
    }
  underlineDom.querySelector<HTMLElement>('i')!.onclick = function () {
    console.log('underline')
    instance.command.executeUnderline()
    underlineOptionDom.classList.remove('visible')
  }
  underlineDom.querySelector<HTMLUListElement>('ul')!.onmousedown = function (
    evt
  ) {
    const li = evt.target as HTMLLIElement
    const decorationStyle = <TextDecorationStyle>li.dataset.decorationStyle
    instance.command.executeUnderline({
      style: decorationStyle
    })
    underlineOptionDom.classList.remove('visible')
  }

  const strikeoutDom = document.querySelector<HTMLDivElement>(
    '.menu-item__strikeout'
  )!
  strikeoutDom.onclick = function () {
    console.log('strikeout')
    instance.command.executeStrikeout()
  }

  const superscriptDom = document.querySelector<HTMLDivElement>(
    '.menu-item__superscript'
  )!
  superscriptDom.title = `上标(${isApple ? '⌘' : 'Ctrl'}+Shift+,)`
  superscriptDom.onclick = function () {
    console.log('superscript')
    instance.command.executeSuperscript()
  }

  const subscriptDom = document.querySelector<HTMLDivElement>(
    '.menu-item__subscript'
  )!
  subscriptDom.title = `下标(${isApple ? '⌘' : 'Ctrl'}+Shift+.)`
  subscriptDom.onclick = function () {
    console.log('subscript')
    instance.command.executeSubscript()
  }

  const colorControlDom = document.querySelector<HTMLInputElement>('#color')!
  colorControlDom.oninput = function () {
    instance.command.executeColor(colorControlDom.value)
  }
  const colorDom = document.querySelector<HTMLDivElement>('.menu-item__color')!
  const colorSpanDom = colorDom.querySelector('span')!
  colorDom.onclick = function () {
    console.log('color')
    colorControlDom.click()
  }

  const highlightControlDom =
    document.querySelector<HTMLInputElement>('#highlight')!
  highlightControlDom.oninput = function () {
    instance.command.executeHighlight(highlightControlDom.value)
  }
  const highlightDom = document.querySelector<HTMLDivElement>(
    '.menu-item__highlight'
  )!
  const highlightSpanDom = highlightDom.querySelector('span')!
  highlightDom.onclick = function () {
    console.log('highlight')
    highlightControlDom?.click()
  }

  const titleDom = document.querySelector<HTMLDivElement>('.menu-item__title')!
  const titleSelectDom = titleDom.querySelector<HTMLDivElement>('.select')!
  const titleOptionDom = titleDom.querySelector<HTMLDivElement>('.options')!
  titleOptionDom.querySelectorAll('li').forEach((li, index) => {
    li.title = `Ctrl+${isApple ? 'Option' : 'Alt'}+${index}`
  })

  titleDom.onclick = function () {
    console.log('title')
    toggleOption(titleOptionDom)
  }
  titleOptionDom.onclick = function (evt) {
    const li = evt.target as HTMLLIElement
    const level = <TitleLevel>li.dataset.level
    instance.command.executeTitle(level || null)
  }

  const leftDom = document.querySelector<HTMLDivElement>('.menu-item__left')!
  leftDom.title = `左对齐(${isApple ? '⌘' : 'Ctrl'}+L)`
  leftDom.onclick = function () {
    console.log('left')
    instance.command.executeRowFlex(RowFlex.LEFT)
  }

  const centerDom =
    document.querySelector<HTMLDivElement>('.menu-item__center')!
  centerDom.title = `居中对齐(${isApple ? '⌘' : 'Ctrl'}+E)`
  centerDom.onclick = function () {
    console.log('center')
    instance.command.executeRowFlex(RowFlex.CENTER)
  }

  const rightDom = document.querySelector<HTMLDivElement>('.menu-item__right')!
  rightDom.title = `右对齐(${isApple ? '⌘' : 'Ctrl'}+R)`
  rightDom.onclick = function () {
    console.log('right')
    instance.command.executeRowFlex(RowFlex.RIGHT)
  }

  const alignmentDom = document.querySelector<HTMLDivElement>(
    '.menu-item__alignment'
  )!
  alignmentDom.title = `两端对齐(${isApple ? '⌘' : 'Ctrl'}+J)`
  alignmentDom.onclick = function () {
    console.log('alignment')
    instance.command.executeRowFlex(RowFlex.ALIGNMENT)
  }

  const justifyDom = document.querySelector<HTMLDivElement>(
    '.menu-item__justify'
  )!
  justifyDom.title = `分散对齐(${isApple ? '⌘' : 'Ctrl'}+Shift+J)`
  justifyDom.onclick = function () {
    console.log('justify')
    instance.command.executeRowFlex(RowFlex.JUSTIFY)
  }

  const rowMarginDom = document.querySelector<HTMLDivElement>(
    '.menu-item__row-margin'
  )!
  const rowOptionDom = rowMarginDom.querySelector<HTMLDivElement>('.options')!
  rowMarginDom.onclick = function () {
    console.log('row-margin')
    toggleOption(rowOptionDom)
  }
  rowOptionDom.onclick = function (evt) {
    const li = evt.target as HTMLLIElement
    instance.command.executeRowMargin(Number(li.dataset.rowmargin!))
  }

  const firstLineIndentDom = document.querySelector<HTMLDivElement>(
    '.menu-item__first-line-indent'
  )!
  const firstLineIndentOptionDom =
    firstLineIndentDom.querySelector<HTMLDivElement>('.options')!
  firstLineIndentDom.onclick = function (evt) {
    console.log('first-line-indent click')
    evt.stopPropagation()
    toggleOption(firstLineIndentOptionDom)
  }
  firstLineIndentOptionDom.onmousedown = function (evt) {
    console.log('first-line-indent option mousedown')
    evt.stopPropagation()
    const li = (evt.target as HTMLElement).closest('li')
    if (li && li.dataset.firstlineindent !== undefined) {
      const indentValue = Number(li.dataset.firstlineindent)
      const range = instance.command.getRange()
      const { startIndex, endIndex } = range
      const zone = range.zone || 'main'
      const elementList = instance.command.getValue().data[zone]
      if (startIndex >= 0 && elementList) {
        // 1. 寻找选区涉及的所有段落的起始字符索引
        const pStarts: number[] = []
        let cur = startIndex
        // 这里的 elementList[i].value 可能是多字符，需要累加长度匹配
        // 但寻找段首简单的 backtracking 通常足够，只要确保 \n 没被漏掉
        while (cur > 0) {
          // 寻找前一个字符是否为换行符
          // 比较稳妥的方式是获取当时的文本数据进行查找
          const fullTextObj = instance.command.getText()
          const fullText = fullTextObj[zone]
          const prevChar = fullText[cur - 1]
          if (prevChar === '\n' || prevChar === '\r') break
          cur--
        }
        pStarts.push(cur)

        const fullTextObj = instance.command.getText()
        const fullText = fullTextObj[zone]
        for (let i = startIndex; i < endIndex; i++) {
          if (fullText[i] === '\n') {
            if (i + 1 < fullText.length && i + 1 <= endIndex) {
              pStarts.push(i + 1)
            }
          }
        }

        // 2. 从后往前处理段落
        pStarts.reverse().forEach(startCharIdx => {
          const currentList = instance.command.getValue().data[zone]

          // 映射：字符索引 -> 元素下标
          let charAcc = 0
          let elementIdx = -1
          for (let i = 0; i < currentList.length; i++) {
            if (charAcc === startCharIdx) {
              elementIdx = i
              break
            }
            charAcc += (currentList[i].value || '').length
          }

          if (elementIdx !== -1) {
            const firstEl = currentList[elementIdx]
            // 如果第一个元素是缩进标记 (检查 extension)
            if (firstEl && firstEl.extension && (firstEl.extension as any).isFirstLineIndent) {
              const elLen = (firstEl.value || '').length
              instance.command.executeSetRange(startCharIdx, startCharIdx + elLen)
              // 关键：对已选中的缩进块执行退格删除
              instance.command.executeBackspace()
            }
          }

          // 3. 插入新缩进
          if (indentValue > 0) {
            instance.command.executeSetRange(startCharIdx, startCharIdx)
            instance.command.executeInsertElementList([{
              value: '\u3000'.repeat(indentValue),
              extension: { isFirstLineIndent: true }
            } as any])
          }
        })
      }
      firstLineIndentOptionDom.classList.remove('visible')
    }
  }

  const indentMinusDom = document.querySelector<HTMLDivElement>(
    '.menu-item__indent-minus'
  )!
  indentMinusDom.onclick = function () {
    console.log('indent-minus')
    adjustIndent(-1)
  }

  const indentAddDom = document.querySelector<HTMLDivElement>(
    '.menu-item__indent-add'
  )!
  indentAddDom.onclick = function () {
    console.log('indent-add')
    adjustIndent(1)
  }

  const adjustIndent = (delta: number) => {
    const range = instance.command.getRange()
    const { startIndex, endIndex } = range
    const zone = range.zone || 'main'
    const elementList = instance.command.getValue().data[zone]
    if (startIndex >= 0 && elementList) {
      const fullTextObj = instance.command.getText()
      const fullText = fullTextObj[zone]

      // 1. 寻找选区涉及的所有段落的起始字符索引
      const pStarts: number[] = []
      let cur = startIndex
      while (cur > 0) {
        const prevChar = fullText[cur - 1]
        if (prevChar === '\n' || prevChar === '\r') break
        cur--
      }
      pStarts.push(cur)

      for (let i = startIndex; i < endIndex; i++) {
        if (fullText[i] === '\n') {
          if (i + 1 < fullText.length && i + 1 <= endIndex) {
            pStarts.push(i + 1)
          }
        }
      }

      // 2. 从后往前处理段落以避免前面的变动影响后面的字符索引
      pStarts.reverse().forEach(startCharIdx => {
        const currentList = instance.command.getValue().data[zone]

        let charAcc = 0
        let elementIdx = -1
        for (let i = 0; i < currentList.length; i++) {
          if (charAcc === startCharIdx) {
            elementIdx = i
            break
          }
          charAcc += (currentList[i].value || '').length
        }

        if (elementIdx !== -1) {
          const firstEl = currentList[elementIdx]
          let currentIndentCount = 0
          let elLen = 0

          // 如果第一个元素是缩进标记
          if (firstEl && firstEl.extension && (firstEl.extension as any).isFirstLineIndent) {
            elLen = (firstEl.value || '').length
            currentIndentCount = elLen
          }

          const newIndentCount = Math.max(0, currentIndentCount + delta)

          if (newIndentCount !== currentIndentCount) {
            // 如果原来有，选中并删除
            if (elLen > 0) {
              instance.command.executeSetRange(startCharIdx, startCharIdx + elLen)
              instance.command.executeBackspace()
            }
            // 如果新值 > 0，插入新缩进
            if (newIndentCount > 0) {
              instance.command.executeSetRange(startCharIdx, startCharIdx)
              instance.command.executeInsertElementList([{
                value: '\u3000'.repeat(newIndentCount),
                extension: { isFirstLineIndent: true }
              } as any])
            }
          }
        }
      })
    }
  }

  const adjustParagraphSpacing = (type: 'spacingBefore' | 'spacingAfter', value: number) => {
    // 1. 产生视觉反应：映射到 rowMargin (行间距)
    // 注意：这会改变全段行高，但在当前内核下是产生“反应”的最快方式
    instance.command.executeRowMargin(value)

    // 2. 数据存储：保留原始属性用于 Word 导出
    const range = instance.command.getRange()
    const { startIndex, endIndex } = range
    const zone = range.zone || 'main'
    const elementList = instance.command.getValue().data[zone]

    if (startIndex >= 0 && elementList) {
      const fullTextObj = instance.command.getText()
      const fullText = fullTextObj[zone]

      // 寻找选区涉及的所有段落起始索引
      const pStarts: number[] = []
      let cur = startIndex
      while (cur > 0) {
        const prevChar = fullText[cur - 1]
        if (prevChar === '\n' || prevChar === '\r') break
        cur--
      }
      pStarts.push(cur)

      for (let i = startIndex; i < endIndex; i++) {
        if (fullText[i] === '\n' && i + 1 < fullText.length && i + 1 <= endIndex) {
          pStarts.push(i + 1)
        }
      }

      pStarts.forEach(startCharIdx => {
        let charAcc = 0
        let startElementIdx = -1
        for (let i = 0; i < elementList.length; i++) {
          if (charAcc === startCharIdx) {
            startElementIdx = i
            break
          }
          charAcc += (elementList[i].value || '').length
        }

        if (startElementIdx !== -1) {
          for (let i = startElementIdx; i < elementList.length; i++) {
            const el = elementList[i]
            if (el.id) {
              instance.command.executeUpdateElementById({
                id: el.id,
                properties: { [type]: value } as any
              })
            }
            if (el.value === '\n' || el.value === '\r') break
          }
        }
      })
    }
  }

  const pSpacingBeforeDom = document.querySelector<HTMLDivElement>(
    '.menu-item__p-spacing-before'
  )!
  const pSpacingBeforeOptionDom =
    pSpacingBeforeDom.querySelector<HTMLDivElement>('.options')!
  pSpacingBeforeDom.onclick = function () {
    toggleOption(pSpacingBeforeOptionDom)
  }
  pSpacingBeforeOptionDom.onclick = function (evt) {
    evt.stopPropagation()
    const li = (evt.target as HTMLElement).closest('li')
    if (li) {
      const value = Number(li.dataset.pspacingBefore)
      adjustParagraphSpacing('spacingBefore', value)
    }
    pSpacingBeforeOptionDom.classList.remove('visible')
  }

  const pSpacingAfterDom = document.querySelector<HTMLDivElement>(
    '.menu-item__p-spacing-after'
  )!
  const pSpacingAfterOptionDom =
    pSpacingAfterDom.querySelector<HTMLDivElement>('.options')!
  pSpacingAfterDom.onclick = function () {
    toggleOption(pSpacingAfterOptionDom)
  }
  pSpacingAfterOptionDom.onclick = function (evt) {
    evt.stopPropagation()
    const li = (evt.target as HTMLElement).closest('li')
    if (li) {
      const value = Number(li.dataset.pspacingAfter)
      adjustParagraphSpacing('spacingAfter', value)
    }
    pSpacingAfterOptionDom.classList.remove('visible')
  }


  const listDom = document.querySelector<HTMLDivElement>('.menu-item__list')!
  listDom.title = `列表(${isApple ? '⌘' : 'Ctrl'}+Shift+U)`
  const listOptionDom = listDom.querySelector<HTMLDivElement>('.options')!
  listDom.onclick = function () {
    console.log('list')
    toggleOption(listOptionDom)
  }
  listOptionDom.onclick = function (evt) {
    const li = evt.target as HTMLLIElement
    const listType = <ListType>li.dataset.listType || null
    const listStyle = <ListStyle>(<unknown>li.dataset.listStyle)
    instance.command.executeList(listType, listStyle)
  }

  // 4. | 表格 | 图片 | 超链接 | 分割线 | 水印 | 代码块 | 分隔符 | 控件 | 复选框 | LaTeX | 日期选择器
  const tableDom = document.querySelector<HTMLDivElement>('.menu-item__table')!
  const tablePanelContainer = document.querySelector<HTMLDivElement>(
    '.menu-item__table__collapse'
  )!
  const tableClose = document.querySelector<HTMLButtonElement>('.table-close')!
  const tableTitle = document.querySelector<HTMLDivElement>('.table-select')!
  const tableLabel = document.querySelector<HTMLSpanElement>('.table-label')!
  const tablePanel = document.querySelector<HTMLDivElement>('.table-panel')!
  // 绘制行列
  const tableCellList: HTMLDivElement[][] = []
  for (let i = 0; i < 10; i++) {
    const row = document.createElement('div')
    row.classList.add('table-row')
    const rowCellList: HTMLDivElement[] = []
    for (let j = 0; j < 10; j++) {
      const cell = document.createElement('div')
      cell.classList.add('table-cel')
      row.append(cell)
      rowCellList.push(cell)
    }
    tablePanel.append(row)
    tableCellList.push(rowCellList)
  }
  let colIndex = 0
  let rowIndex = 0
  const updateTablePanelPosition = () => {
    const rect = tableDom.getBoundingClientRect()
    tablePanelContainer.style.position = 'fixed'
    tablePanelContainer.style.left = `${rect.left}px`
    tablePanelContainer.style.top = `${rect.bottom + 4}px`
    tablePanelContainer.style.zIndex = '1305'
  }
  const resetTablePanelPosition = () => {
    tablePanelContainer.style.position = ''
    tablePanelContainer.style.left = ''
    tablePanelContainer.style.top = ''
    tablePanelContainer.style.zIndex = ''
  }
  // 移除所有格选择
  function removeAllTableCellSelect() {
    tableCellList.forEach(tr => {
      tr.forEach(td => td.classList.remove('active'))
    })
  }
  // 设置标题内容
  function setTableTitle(payload: string) {
    tableTitle.innerText = payload
  }
  // 恢复初始状态
  function recoveryTable() {
    // 还原选择样式、标题、选择行列
    removeAllTableCellSelect()
    setTableTitle('')
    tableLabel.innerText = '插入表格'
    colIndex = 0
    rowIndex = 0
    // 隐藏panel
    tablePanelContainer.style.display = 'none'
    resetTablePanelPosition()
  }
  tableDom.onclick = function (evt) {
    evt.stopPropagation()
    if (tablePanelContainer!.style.display === 'block') {
      recoveryTable()
    } else {
      console.log('table')
      tablePanelContainer!.style.display = 'block'
      updateTablePanelPosition()
    }
  }
  // 点击页面其他区域关闭表格下拉窗
  document.addEventListener('click', function (evt) {
    const target = evt.target as HTMLElement
    if (
      tablePanelContainer!.style.display === 'block' &&
      !tablePanelContainer!.contains(target) &&
      !tableDom.contains(target)
    ) {
      recoveryTable()
    }
  })
  tablePanel.onmousemove = function (evt) {
    const celSize = 20
    const gap = 3
    const { offsetX, offsetY } = evt
    // 移除所有选择
    removeAllTableCellSelect()
    colIndex = Math.ceil(offsetX / (celSize + gap)) || 1
    rowIndex = Math.ceil(offsetY / (celSize + gap)) || 1
    // 改变选择样式
    tableCellList.forEach((tr, trIndex) => {
      tr.forEach((td, tdIndex) => {
        if (tdIndex < colIndex && trIndex < rowIndex) {
          td.classList.add('active')
        }
      })
    })
    // 改变表格标题
    setTableTitle(`${rowIndex}×${colIndex}`)
    tableLabel.innerText = '表格'
  }
  tableClose.onclick = function () {
    recoveryTable()
  }
  tablePanel.onclick = function () {
    // 应用选择
    instance.command.executeInsertTable(rowIndex, colIndex)
    recoveryTable()
  }

  // 自定义行列输入
  const customRowsInput = document.querySelector<HTMLInputElement>('.table-custom-rows')!
  const customColsInput = document.querySelector<HTMLInputElement>('.table-custom-cols')!
  const customBtn = document.querySelector<HTMLButtonElement>('.table-custom-btn')!
  const insertCustomTable = () => {
    const rows = Math.min(Math.max(parseInt(customRowsInput.value, 10) || 3, 1), 20)
    const cols = Math.min(Math.max(parseInt(customColsInput.value, 10) || 3, 1), 20)
    instance.command.executeInsertTable(rows, cols)
    recoveryTable()
  }
  customBtn.onclick = insertCustomTable
  customRowsInput.onkeydown = function (evt) {
    if (evt.key === 'Enter') insertCustomTable()
  }
  customColsInput.onkeydown = function (evt) {
    if (evt.key === 'Enter') insertCustomTable()
  }

  const imageDom = document.querySelector<HTMLDivElement>('.menu-item__image')!
  const imageFileDom = document.querySelector<HTMLInputElement>('#image')!
  imageDom.onclick = function () {
    imageFileDom.click()
  }
  imageFileDom.onchange = function () {
    const file = imageFileDom.files![0]!
    const fileReader = new FileReader()
    fileReader.readAsDataURL(file)
    fileReader.onload = function () {
      // 计算宽高
      const image = new Image()
      const value = fileReader.result as string
      image.src = value
      image.onload = function () {
        instance.command.executeImage({
          value,
          width: image.width,
          height: image.height
        })
        imageFileDom.value = ''
      }
    }
  }

  const hyperlinkDom = document.querySelector<HTMLDivElement>(
    '.menu-item__hyperlink'
  )!
  hyperlinkDom.onclick = function () {
    console.log('hyperlink')
    new Dialog({
      title: '超链接',
      data: [
        {
          type: 'text',
          label: '文本',
          name: 'name',
          required: true,
          placeholder: '请输入文本',
          value: instance.command.getRangeText()
        },
        {
          type: 'text',
          label: '链接',
          name: 'url',
          required: true,
          placeholder: '请输入链接'
        }
      ],
      onConfirm: payload => {
        const name = payload.find(p => p.name === 'name')?.value
        if (!name) return
        const url = payload.find(p => p.name === 'url')?.value
        if (!url) return
        instance.command.executeHyperlink({
          url,
          valueList: splitText(name).map(n => ({
            value: n,
            size: 16
          }))
        })
      }
    })
  }

  const separatorDom = document.querySelector<HTMLDivElement>(
    '.menu-item__separator'
  )!
  const separatorOptionDom =
    separatorDom.querySelector<HTMLDivElement>('.options')!
  separatorDom.onclick = function () {
    console.log('separator')
    toggleOption(separatorOptionDom)
  }
  separatorOptionDom.onmousedown = function (evt) {
    let payload: number[] = []
    const li = evt.target as HTMLLIElement
    const separatorDash = li.dataset.separator?.split(',').map(Number)
    if (separatorDash) {
      const isSingleLine = separatorDash.every(d => d === 0)
      if (!isSingleLine) {
        payload = separatorDash
      }
    }
    instance.command.executeSeparator(payload)
  }

  const pageBreakDom = document.querySelector<HTMLDivElement>(
    '.menu-item__page-break'
  )!
  pageBreakDom.onclick = function () {
    console.log('pageBreak')
    instance.command.executePageBreak()
  }

  const watermarkDom = document.querySelector<HTMLDivElement>(
    '.menu-item__watermark'
  )!
  const watermarkOptionDom =
    watermarkDom.querySelector<HTMLDivElement>('.options')!
  watermarkDom.onclick = function () {
    console.log('watermark')
    toggleOption(watermarkOptionDom)
  }
  watermarkOptionDom.onmousedown = function (evt) {
    const li = evt.target as HTMLLIElement
    const menu = li.dataset.menu!
    toggleOption(watermarkOptionDom)
    if (menu === 'add') {
      new Dialog({
        title: '水印',
        data: [
          {
            type: 'text',
            label: '内容',
            name: 'data',
            required: true,
            placeholder: '请输入内容'
          },
          {
            type: 'color',
            label: '颜色',
            name: 'color',
            required: true,
            value: '#AEB5C0'
          },
          {
            type: 'number',
            label: '字体大小',
            name: 'size',
            required: true,
            value: '120'
          },
          {
            type: 'number',
            label: '透明度',
            name: 'opacity',
            required: true,
            value: '0.3'
          },
          {
            type: 'select',
            label: '重复',
            name: 'repeat',
            value: '0',
            required: false,
            options: [
              {
                label: '不重复',
                value: '0'
              },
              {
                label: '重复',
                value: '1'
              }
            ]
          },
          {
            type: 'number',
            label: '水平间隔',
            name: 'horizontalGap',
            required: false,
            value: '10'
          },
          {
            type: 'number',
            label: '垂直间隔',
            name: 'verticalGap',
            required: false,
            value: '10'
          }
        ],
        onConfirm: payload => {
          const nullableIndex = payload.findIndex(p => !p.value)
          if (~nullableIndex) return
          const watermark = payload.reduce(
            (pre, cur) => {
              pre[cur.name] = cur.value
              return pre
            },
            <any>{}
          )
          const repeat = watermark.repeat === '1'
          instance.command.executeAddWatermark({
            data: watermark.data,
            color: watermark.color,
            size: Number(watermark.size),
            opacity: Number(watermark.opacity),
            repeat,
            gap:
              repeat && watermark.horizontalGap && watermark.verticalGap
                ? [
                  Number(watermark.horizontalGap),
                  Number(watermark.verticalGap)
                ]
                : undefined
          })
        }
      })
    } else {
      instance.command.executeDeleteWatermark()
    }
  }

  const codeblockDom = document.querySelector<HTMLDivElement>(
    '.menu-item__codeblock'
  )!
  codeblockDom.onclick = function () {
    console.log('codeblock')
    new Dialog({
      title: '代码块',
      data: [
        {
          type: 'textarea',
          name: 'codeblock',
          placeholder: '请输入代码',
          width: 500,
          height: 300
        }
      ],
      onConfirm: payload => {
        const codeblock = payload.find(p => p.name === 'codeblock')?.value
        if (!codeblock) return
        const tokenList = prism.tokenize(codeblock, prism.languages.javascript)
        const formatTokenList = formatPrismToken(tokenList)
        const elementList: IElement[] = []
        for (let i = 0; i < formatTokenList.length; i++) {
          const formatToken = formatTokenList[i]
          const tokenStringList = splitText(formatToken.content)
          for (let j = 0; j < tokenStringList.length; j++) {
            const value = tokenStringList[j]
            const element: IElement = {
              value
            }
            if (formatToken.color) {
              element.color = formatToken.color
            }
            if (formatToken.bold) {
              element.bold = true
            }
            if (formatToken.italic) {
              element.italic = true
            }
            elementList.push(element)
          }
        }
        elementList.unshift({
          value: '\n'
        })
        instance.command.executeInsertElementList(elementList)
      }
    })
  }

  const controlDom = document.querySelector<HTMLDivElement>(
    '.menu-item__control'
  )!
  const controlOptionDom = controlDom.querySelector<HTMLDivElement>('.options')!
  controlDom.onclick = function () {
    console.log('control')
    toggleOption(controlOptionDom)
  }
  controlOptionDom.onmousedown = function (evt) {
    toggleOption(controlOptionDom)
    const li = evt.target as HTMLLIElement
    const type = <ControlType>li.dataset.control
    switch (type) {
      case ControlType.TEXT:
        new Dialog({
          title: '文本控件',
          data: [
            {
              type: 'text',
              label: '占位符',
              name: 'placeholder',
              required: true,
              placeholder: '请输入占位符'
            },
            {
              type: 'text',
              label: '默认值',
              name: 'value',
              placeholder: '请输入默认值'
            }
          ],
          onConfirm: payload => {
            const placeholder = payload.find(
              p => p.name === 'placeholder'
            )?.value
            if (!placeholder) return
            const value = payload.find(p => p.name === 'value')?.value || ''
            instance.command.executeInsertControl({
              type: ElementType.CONTROL,
              value: '',
              control: {
                type,
                value: value
                  ? [
                    {
                      value
                    }
                  ]
                  : null,
                placeholder
              }
            })
          }
        })
        break
      case ControlType.SELECT:
        new Dialog({
          title: '列举控件',
          data: [
            {
              type: 'text',
              label: '占位符',
              name: 'placeholder',
              required: true,
              placeholder: '请输入占位符'
            },
            {
              type: 'text',
              label: '默认值',
              name: 'code',
              placeholder: '请输入默认值'
            },
            {
              type: 'textarea',
              label: '值集',
              name: 'valueSets',
              required: true,
              height: 100,
              placeholder: `请输入值集JSON，例：\n[{\n"value":"有",\n"code":"98175"\n}]`
            }
          ],
          onConfirm: payload => {
            const placeholder = payload.find(
              p => p.name === 'placeholder'
            )?.value
            if (!placeholder) return
            const valueSets = payload.find(p => p.name === 'valueSets')?.value
            if (!valueSets) return
            const code = payload.find(p => p.name === 'code')?.value
            instance.command.executeInsertControl({
              type: ElementType.CONTROL,
              value: '',
              control: {
                type,
                code,
                value: null,
                placeholder,
                valueSets: JSON.parse(valueSets)
              }
            })
          }
        })
        break
      case ControlType.CHECKBOX:
        new Dialog({
          title: '复选框控件',
          data: [
            {
              type: 'text',
              label: '默认值',
              name: 'code',
              placeholder: '请输入默认值，多个值以英文逗号分割'
            },
            {
              type: 'textarea',
              label: '值集',
              name: 'valueSets',
              required: true,
              height: 100,
              placeholder: `请输入值集JSON，例：\n[{\n"value":"有",\n"code":"98175"\n}]`
            }
          ],
          onConfirm: payload => {
            const valueSets = payload.find(p => p.name === 'valueSets')?.value
            if (!valueSets) return
            const code = payload.find(p => p.name === 'code')?.value
            instance.command.executeInsertControl({
              type: ElementType.CONTROL,
              value: '',
              control: {
                type,
                code,
                value: null,
                valueSets: JSON.parse(valueSets)
              }
            })
          }
        })
        break
      case ControlType.RADIO:
        new Dialog({
          title: '单选框控件',
          data: [
            {
              type: 'text',
              label: '默认值',
              name: 'code',
              placeholder: '请输入默认值'
            },
            {
              type: 'textarea',
              label: '值集',
              name: 'valueSets',
              required: true,
              height: 100,
              placeholder: `请输入值集JSON，例：\n[{\n"value":"有",\n"code":"98175"\n}]`
            }
          ],
          onConfirm: payload => {
            const valueSets = payload.find(p => p.name === 'valueSets')?.value
            if (!valueSets) return
            const code = payload.find(p => p.name === 'code')?.value
            instance.command.executeInsertControl({
              type: ElementType.CONTROL,
              value: '',
              control: {
                type,
                code,
                value: null,
                valueSets: JSON.parse(valueSets)
              }
            })
          }
        })
        break
      case ControlType.DATE:
        new Dialog({
          title: '日期控件',
          data: [
            {
              type: 'text',
              label: '占位符',
              name: 'placeholder',
              required: true,
              placeholder: '请输入占位符'
            },
            {
              type: 'text',
              label: '默认值',
              name: 'value',
              placeholder: '请输入默认值'
            },
            {
              type: 'select',
              label: '日期格式',
              name: 'dateFormat',
              value: 'yyyy-MM-dd hh:mm:ss',
              required: true,
              options: [
                {
                  label: 'yyyy-MM-dd hh:mm:ss',
                  value: 'yyyy-MM-dd hh:mm:ss'
                },
                {
                  label: 'yyyy-MM-dd',
                  value: 'yyyy-MM-dd'
                }
              ]
            }
          ],
          onConfirm: payload => {
            const placeholder = payload.find(
              p => p.name === 'placeholder'
            )?.value
            if (!placeholder) return
            const value = payload.find(p => p.name === 'value')?.value || ''
            const dateFormat =
              payload.find(p => p.name === 'dateFormat')?.value || ''
            instance.command.executeInsertControl({
              type: ElementType.CONTROL,
              value: '',
              control: {
                type,
                dateFormat,
                value: value
                  ? [
                    {
                      value
                    }
                  ]
                  : null,
                placeholder
              }
            })
          }
        })
        break
      case ControlType.NUMBER:
        new Dialog({
          title: '数值控件',
          data: [
            {
              type: 'text',
              label: '占位符',
              name: 'placeholder',
              required: true,
              placeholder: '请输入占位符'
            },
            {
              type: 'text',
              label: '默认值',
              name: 'value',
              placeholder: '请输入默认值'
            }
          ],
          onConfirm: payload => {
            const placeholder = payload.find(
              p => p.name === 'placeholder'
            )?.value
            if (!placeholder) return
            const value = payload.find(p => p.name === 'value')?.value || ''
            instance.command.executeInsertControl({
              type: ElementType.CONTROL,
              value: '',
              control: {
                type,
                value: value
                  ? [
                    {
                      value
                    }
                  ]
                  : null,
                placeholder
              }
            })
          }
        })
        break
      default:
        break
    }
  }

  const checkboxDom = document.querySelector<HTMLDivElement>(
    '.menu-item__checkbox'
  )!
  checkboxDom.onclick = function () {
    console.log('checkbox')
    instance.command.executeInsertElementList([
      {
        type: ElementType.CHECKBOX,
        checkbox: {
          value: false
        },
        value: ''
      }
    ])
  }

  const radioDom = document.querySelector<HTMLDivElement>('.menu-item__radio')!
  radioDom.onclick = function () {
    console.log('radio')
    instance.command.executeInsertElementList([
      {
        type: ElementType.RADIO,
        checkbox: {
          value: false
        },
        value: ''
      }
    ])
  }

  const latexDom = document.querySelector<HTMLDivElement>('.menu-item__latex')!
  latexDom.onclick = function () {
    console.log('LaTeX')
    new Dialog({
      title: 'LaTeX',
      data: [
        {
          type: 'textarea',
          height: 100,
          name: 'value',
          placeholder: '请输入LaTeX文本'
        }
      ],
      onConfirm: payload => {
        const value = payload.find(p => p.name === 'value')?.value
        if (!value) return
        instance.command.executeInsertElementList([
          {
            type: ElementType.LATEX,
            value
          }
        ])
      }
    })
  }

  const dateDom = document.querySelector<HTMLDivElement>('.menu-item__date')!
  const dateDomOptionDom = dateDom.querySelector<HTMLDivElement>('.options')!
  dateDom.onclick = function () {
    console.log('date')
    toggleOption(dateDomOptionDom)
    // 定位调整
    const bodyRect = document.body.getBoundingClientRect()
    const dateDomOptionRect = dateDomOptionDom.getBoundingClientRect()
    if (dateDomOptionRect.left + dateDomOptionRect.width > bodyRect.width) {
      dateDomOptionDom.style.right = '0px'
      dateDomOptionDom.style.left = 'unset'
    } else {
      dateDomOptionDom.style.right = 'unset'
      dateDomOptionDom.style.left = '0px'
    }
    // 当前日期
    const date = new Date()
    const year = date.getFullYear().toString()
    const month = (date.getMonth() + 1).toString().padStart(2, '0')
    const day = date.getDate().toString().padStart(2, '0')
    const hour = date.getHours().toString().padStart(2, '0')
    const minute = date.getMinutes().toString().padStart(2, '0')
    const second = date.getSeconds().toString().padStart(2, '0')
    const dateString = `${year}-${month}-${day}`
    const dateTimeString = `${dateString} ${hour}:${minute}:${second}`
    dateDomOptionDom.querySelector<HTMLLIElement>('li:first-child')!.innerText =
      dateString
    dateDomOptionDom.querySelector<HTMLLIElement>('li:last-child')!.innerText =
      dateTimeString
  }
  dateDomOptionDom.onmousedown = function (evt) {
    const li = evt.target as HTMLLIElement
    const dateFormat = li.dataset.format!
    toggleOption(dateDomOptionDom)
    instance.command.executeInsertElementList([
      {
        type: ElementType.DATE,
        value: '',
        dateFormat,
        valueList: [
          {
            value: li.innerText.trim()
          }
        ]
      }
    ])
  }

  const blockDom = document.querySelector<HTMLDivElement>('.menu-item__block')!
  blockDom.onclick = function () {
    console.log('block')
    new Dialog({
      title: '内容块',
      data: [
        {
          type: 'select',
          label: '类型',
          name: 'type',
          value: 'iframe',
          required: true,
          options: [
            {
              label: '网址',
              value: 'iframe'
            },
            {
              label: '视频',
              value: 'video'
            }
          ]
        },
        {
          type: 'number',
          label: '宽度',
          name: 'width',
          placeholder: '请输入宽度（默认页面内宽度）'
        },
        {
          type: 'number',
          label: '高度',
          name: 'height',
          required: true,
          placeholder: '请输入高度'
        },
        {
          type: 'input',
          label: '地址',
          name: 'src',
          required: false,
          placeholder: '请输入地址'
        },
        {
          type: 'textarea',
          label: 'HTML',
          height: 100,
          name: 'srcdoc',
          required: false,
          placeholder: '请输入HTML代码（仅网址类型有效）'
        }
      ],
      onConfirm: payload => {
        const type = payload.find(p => p.name === 'type')?.value
        if (!type) return
        const width = payload.find(p => p.name === 'width')?.value
        const height = payload.find(p => p.name === 'height')?.value
        if (!height) return
        // 地址或HTML代码至少存在一项
        const src = payload.find(p => p.name === 'src')?.value
        const srcdoc = payload.find(p => p.name === 'srcdoc')?.value
        const block: IBlock = {
          type: <BlockType>type
        }
        if (block.type === BlockType.IFRAME) {
          if (!src && !srcdoc) return
          block.iframeBlock = {
            src,
            srcdoc
          }
        } else if (block.type === BlockType.VIDEO) {
          if (!src) return
          block.videoBlock = {
            src
          }
        }
        const blockElement: IElement = {
          type: ElementType.BLOCK,
          value: '',
          height: Number(height),
          block
        }
        if (width) {
          blockElement.width = Number(width)
        }
        instance.command.executeInsertElementList([blockElement])
      }
    })
  }

  // 5. | 搜索&替换 | 打印 |
  const searchCollapseDom = document.querySelector<HTMLDivElement>(
    '.menu-item__search__collapse'
  )!
  const searchInputDom = document.querySelector<HTMLInputElement>(
    '.menu-item__search__collapse__search input'
  )!
  const replaceInputDom = document.querySelector<HTMLInputElement>(
    '.menu-item__search__collapse__replace input'
  )!
  const searchRegInputDom =
    document.querySelector<HTMLInputElement>('#option-reg')!
  const searchCaseInputDom =
    document.querySelector<HTMLInputElement>('#option-case')!
  const searchSelectionInputDom =
    document.querySelector<HTMLInputElement>('#option-selection')!
  const searchDom =
    document.querySelector<HTMLDivElement>('.menu-item__search')!
  searchDom.title = `搜索与替换(${isApple ? '⌘' : 'Ctrl'}+F)`
  const searchResultDom =
    searchCollapseDom.querySelector<HTMLLabelElement>('.search-result')!
  const updateSearchCollapsePosition = () => {
    const triggerRect = searchDom.getBoundingClientRect()
    const viewportWidth = window.innerWidth
    const panelWidth = searchCollapseDom.offsetWidth || 260
    searchCollapseDom.style.position = 'fixed'
    searchCollapseDom.style.top = `${triggerRect.bottom + 4}px`
    searchCollapseDom.style.zIndex = '1305'
    if (triggerRect.left + panelWidth > viewportWidth - 8) {
      searchCollapseDom.style.left = 'unset'
      searchCollapseDom.style.right = `${Math.max(8, viewportWidth - triggerRect.right)}px`
    } else {
      searchCollapseDom.style.right = 'unset'
      searchCollapseDom.style.left = `${triggerRect.left}px`
    }
  }
  const resetSearchCollapsePosition = () => {
    searchCollapseDom.style.position = ''
    searchCollapseDom.style.top = ''
    searchCollapseDom.style.left = ''
    searchCollapseDom.style.right = ''
    searchCollapseDom.style.zIndex = ''
  }
  function setSearchResult() {
    const result = instance.command.getSearchNavigateInfo()
    if (result) {
      const { index, count } = result
      searchResultDom.innerText = `${index}/${count}`
    } else {
      searchResultDom.innerText = ''
    }
  }
  searchDom.onclick = function () {
    console.log('search')
    searchCollapseDom.style.display = 'block'
    updateSearchCollapsePosition()
    searchInputDom.focus()
  }
  searchCollapseDom.querySelector<HTMLSpanElement>('span')!.onclick =
    function () {
      searchCollapseDom.style.display = 'none'
      resetSearchCollapsePosition()
      searchInputDom.value = ''
      replaceInputDom.value = ''
      instance.command.executeSearch(null)
      setSearchResult()
    }

  function emitSearch() {
    instance.command.executeSearch(searchInputDom.value || null, {
      isRegEnable: searchRegInputDom.checked,
      isIgnoreCase: searchCaseInputDom.checked,
      isLimitSelection: searchSelectionInputDom.checked
    })
    setSearchResult()
  }

  searchInputDom.oninput = emitSearch
  searchRegInputDom.onchange = emitSearch
  searchCaseInputDom.onchange = emitSearch
  searchSelectionInputDom.onchange = emitSearch
  searchInputDom.onkeydown = function (evt) {
    if (evt.key === 'Enter') {
      emitSearch()
    }
  }
  searchCollapseDom.querySelector<HTMLButtonElement>('button')!.onclick =
    function () {
      const searchValue = searchInputDom.value
      const replaceValue = replaceInputDom.value
      if (searchValue && searchValue !== replaceValue) {
        instance.command.executeReplace(replaceValue)
      }
    }
  searchCollapseDom.querySelector<HTMLDivElement>('.arrow-left')!.onclick =
    function () {
      instance.command.executeSearchNavigatePre()
      setSearchResult()
    }
  searchCollapseDom.querySelector<HTMLDivElement>('.arrow-right')!.onclick =
    function () {
      instance.command.executeSearchNavigateNext()
      setSearchResult()
    }

  const printDom = document.querySelector<HTMLDivElement>('.menu-item__print')!
  printDom.title = `打印(${isApple ? '⌘' : 'Ctrl'}+P)`
  printDom.onclick = function () {
    console.log('print')
    instance.command.executePrint()
  }

  // 6. 目录显隐 | 页面模式 | 纸张缩放 | 纸张大小 | 纸张方向 | 页边距 | 全屏 | 设置
  const editorOptionDom =
    document.querySelector<HTMLDivElement>('.editor-option')!
  editorOptionDom.addEventListener('click', function () {
    const options = instance.command.getOptions()
    new Dialog({
      title: '编辑器配置',
      data: [
        {
          type: 'textarea',
          name: 'option',
          height: 300,
          required: true,
          value: JSON.stringify(options, null, 2),
          placeholder: '请输入编辑器配置'
        }
      ],
      onConfirm: payload => {
        const newOptionValue = payload.find(p => p.name === 'option')?.value
        if (!newOptionValue) return
        const newOption = JSON.parse(newOptionValue)
        instance.command.executeUpdateOptions(newOption)
      }
    })
  })

  async function updateCatalog() {
    const catalog = await instance.command.getCatalog()
    const catalogMainDom =
      document.querySelector<HTMLDivElement>('.catalog__main')!
    catalogMainDom.innerHTML = ''
    if (catalog) {
      const appendCatalog = (
        parent: HTMLDivElement,
        catalogItems: ICatalogItem[]
      ) => {
        for (let c = 0; c < catalogItems.length; c++) {
          const catalogItem = catalogItems[c]
          const catalogItemDom = document.createElement('div')
          catalogItemDom.classList.add('catalog-item')
          // 渲染
          const catalogItemContentDom = document.createElement('div')
          catalogItemContentDom.classList.add('catalog-item__content')
          const catalogItemContentSpanDom = document.createElement('span')
          catalogItemContentSpanDom.innerText = catalogItem.name
          catalogItemContentDom.append(catalogItemContentSpanDom)
          // 定位
          catalogItemContentDom.addEventListener('mousedown', (e) => {
            e.preventDefault() // 防止编辑器失去焦点导致选区清空
          })
          catalogItemContentDom.addEventListener('click', () => {
            console.log('【目录点击触发】 catalogItem:', catalogItem.name, ' id:', catalogItem.id)
            instance.command.executeLocationCatalog(catalogItem.id)
          })
          catalogItemDom.append(catalogItemContentDom)
          if (catalogItem.subCatalog && catalogItem.subCatalog.length) {
            appendCatalog(catalogItemDom, catalogItem.subCatalog)
          }
          // 追加
          parent.append(catalogItemDom)
        }
      }
      appendCatalog(catalogMainDom, catalog)
    }
  }
  let isCatalogShow = true
  const catalogDom = document.querySelector<HTMLElement>('.catalog')!
  const catalogModeDoms =
    document.querySelectorAll<HTMLDivElement>('.catalog-mode')!
  const catalogHeaderCloseDom = document.querySelector<HTMLDivElement>(
    '.catalog__header__close'
  )!
  const switchCatalog = () => {
    isCatalogShow = !isCatalogShow
    if (isCatalogShow) {
      catalogDom.style.display = 'block'
      updateCatalog()
    } else {
      catalogDom.style.display = 'none'
    }
  }
  catalogModeDoms.forEach(dom => {
    dom.addEventListener('click', switchCatalog)
  })
  catalogHeaderCloseDom.addEventListener('click', switchCatalog)

  const pageModeDom = document.querySelector<HTMLDivElement>('.page-mode')!
  const pageModeOptionsDom =
    pageModeDom.querySelector<HTMLDivElement>('.options')!
  pageModeDom.onclick = function () {
    toggleOption(pageModeOptionsDom)
  }
  pageModeOptionsDom.onclick = function (evt) {
    const li = evt.target as HTMLLIElement
    instance.command.executePageMode(<PageMode>li.dataset.pageMode!)
  }

  document.querySelectorAll<HTMLDivElement>('.page-scale-percentage').forEach(dom => {
    dom.addEventListener('click', function () {
      console.log('page-scale-recovery')
      instance.command.executePageScaleRecovery()
    })
  })

  document.querySelectorAll<HTMLDivElement>('.page-scale-minus').forEach(dom => {
    dom.addEventListener('click', function () {
      console.log('page-scale-minus')
      instance.command.executePageScaleMinus()
    })
  })

  document.querySelectorAll<HTMLDivElement>('.page-scale-add').forEach(dom => {
    dom.addEventListener('click', function () {
      console.log('page-scale-add')
      instance.command.executePageScaleAdd()
    })
  })

  // 纸张大小
  const paperSizeDom = document.querySelector<HTMLDivElement>('.paper-size')!
  const paperSizeDomOptionsDom =
    paperSizeDom.querySelector<HTMLDivElement>('.options')!
  paperSizeDom.onclick = function () {
    toggleOption(paperSizeDomOptionsDom)
  }
  paperSizeDomOptionsDom.onclick = function (evt) {
    const li = evt.target as HTMLLIElement
    const paperType = li.dataset.paperSize!
    const [width, height] = paperType.split('*').map(Number)
    instance.command.executePaperSize(width, height)
    // 纸张状态回显
    paperSizeDomOptionsDom
      .querySelectorAll('li')
      .forEach(child => child.classList.remove('active'))
    li.classList.add('active')
  }

  // 纸张方向
  const paperDirectionDom =
    document.querySelector<HTMLDivElement>('.paper-direction')!
  const paperDirectionDomOptionsDom =
    paperDirectionDom.querySelector<HTMLDivElement>('.options')!
  paperDirectionDom.onclick = function () {
    toggleOption(paperDirectionDomOptionsDom)
  }
  paperDirectionDomOptionsDom.onclick = function (evt) {
    const li = evt.target as HTMLLIElement
    const paperDirection = li.dataset.paperDirection!
    instance.command.executePaperDirection(<PaperDirection>paperDirection)
    // 纸张方向状态回显
    paperDirectionDomOptionsDom
      .querySelectorAll('li')
      .forEach(child => child.classList.remove('active'))
    li.classList.add('active')
  }

  // 页面边距
  const paperMarginDom =
    document.querySelector<HTMLDivElement>('.paper-margin')!
  paperMarginDom.onclick = function () {
    const [topMargin, rightMargin, bottomMargin, leftMargin] =
      instance.command.getPaperMargin()
    new Dialog({
      title: '页边距',
      data: [
        {
          type: 'text',
          label: '上边距',
          name: 'top',
          required: true,
          value: `${topMargin}`,
          placeholder: '请输入上边距'
        },
        {
          type: 'text',
          label: '下边距',
          name: 'bottom',
          required: true,
          value: `${bottomMargin}`,
          placeholder: '请输入下边距'
        },
        {
          type: 'text',
          label: '左边距',
          name: 'left',
          required: true,
          value: `${leftMargin}`,
          placeholder: '请输入左边距'
        },
        {
          type: 'text',
          label: '右边距',
          name: 'right',
          required: true,
          value: `${rightMargin}`,
          placeholder: '请输入右边距'
        }
      ],
      onConfirm: payload => {
        const top = payload.find(p => p.name === 'top')?.value
        if (!top) return
        const bottom = payload.find(p => p.name === 'bottom')?.value
        if (!bottom) return
        const left = payload.find(p => p.name === 'left')?.value
        if (!left) return
        const right = payload.find(p => p.name === 'right')?.value
        if (!right) return
        instance.command.executeSetPaperMargin([
          Number(top),
          Number(right),
          Number(bottom),
          Number(left)
        ])
      }
    })
  }

  // 全屏（交由外层 Canvas 统一处理，避免整页全屏）
  const fullscreenDom = document.querySelector<HTMLDivElement>('.fullscreen')!
  fullscreenDom.addEventListener('click', toggleCanvasFullscreen)
  window.addEventListener('keydown', evt => {
    if (evt.key === 'F11') {
      toggleCanvasFullscreen()
      evt.preventDefault()
    }
  })
  window.addEventListener('canvas-fullscreen-change', evt => {
    const customEvent = evt as CustomEvent<{ isFullScreen?: boolean }>
    const isCanvasFullscreen = !!customEvent.detail?.isFullScreen
    fullscreenDom.classList.toggle('exist', isCanvasFullscreen)
  })
  function toggleCanvasFullscreen() {
    window.dispatchEvent(new CustomEvent('canvas-fullscreen-toggle-request'))
  }

  // 7. 编辑器使用模式
  let modeIndex = 0
  const modeList = [
    {
      mode: EditorMode.EDIT,
      name: '编辑模式'
    },
    {
      mode: EditorMode.CLEAN,
      name: '清洁模式'
    },
    {
      mode: EditorMode.READONLY,
      name: '只读模式'
    },
    {
      mode: EditorMode.FORM,
      name: '表单模式'
    },
    {
      mode: EditorMode.PRINT,
      name: '打印模式'
    },
    {
      mode: EditorMode.DESIGN,
      name: '设计模式'
    },
    {
      mode: EditorMode.GRAFFITI,
      name: '涂鸦模式'
    }
  ]
  const modeElement = document.querySelector<HTMLDivElement>('.editor-mode')!
  modeElement.onclick = function () {
    // 模式选择循环
    modeIndex === modeList.length - 1 ? (modeIndex = 0) : modeIndex++
    // 设置模式
    const { name, mode } = modeList[modeIndex]
    modeElement.innerText = name
    instance.command.executeMode(mode)
    // 设置菜单栏权限视觉反馈
    const isReadonly = mode === EditorMode.READONLY
    const enableMenuList = ['search', 'print']
    document.querySelectorAll<HTMLDivElement>('.menu-item>div').forEach(dom => {
      const menu = dom.dataset.menu
      isReadonly && (!menu || !enableMenuList.includes(menu))
        ? dom.classList.add('disable')
        : dom.classList.remove('disable')
    })
  }

  // 模拟批注
  const commentDom = document.querySelector<HTMLDivElement>('.comment')!
  async function updateComment() {
    const groupIds = await instance.command.getGroupIds()
    for (const comment of commentList) {
      const activeCommentDom = commentDom.querySelector<HTMLDivElement>(
        `.comment-item[data-id='${comment.id}']`
      )
      // 编辑器是否存在对应成组id
      if (groupIds.includes(comment.id)) {
        // 当前dom是否存在-不存在则追加
        if (!activeCommentDom) {
          const commentItem = document.createElement('div')
          commentItem.classList.add('comment-item')
          commentItem.setAttribute('data-id', comment.id)
          commentItem.onclick = () => {
            instance.command.executeLocationGroup(comment.id)
          }
          commentDom.append(commentItem)
          // 选区信息
          const commentItemTitle = document.createElement('div')
          commentItemTitle.classList.add('comment-item__title')
          commentItemTitle.append(document.createElement('span'))
          const commentItemTitleContent = document.createElement('span')
          commentItemTitleContent.innerText = comment.rangeText
          commentItemTitle.append(commentItemTitleContent)
          const closeDom = document.createElement('i')
          closeDom.onclick = () => {
            instance.command.executeDeleteGroup(comment.id)
          }
          commentItemTitle.append(closeDom)
          commentItem.append(commentItemTitle)
          // 基础信息
          const commentItemInfo = document.createElement('div')
          commentItemInfo.classList.add('comment-item__info')
          const commentItemInfoName = document.createElement('span')
          commentItemInfoName.innerText = comment.userName
          const commentItemInfoDate = document.createElement('span')
          commentItemInfoDate.innerText = comment.createdDate
          commentItemInfo.append(commentItemInfoName)
          commentItemInfo.append(commentItemInfoDate)
          commentItem.append(commentItemInfo)
          // 详细评论
          const commentItemContent = document.createElement('div')
          commentItemContent.classList.add('comment-item__content')
          commentItemContent.innerText = comment.content
          commentItem.append(commentItemContent)
          commentDom.append(commentItem)
        }
      } else {
        // 编辑器内不存在对应成组id则dom则移除
        activeCommentDom?.remove()
      }
    }
  }
  // 8. 内部事件监听
  instance.listener.rangeStyleChange = function (payload: any) {
    try {
      if (!payload) return;
      // 控件类型
      payload.type === ElementType.SUBSCRIPT
        ? subscriptDom.classList.add('active')
        : subscriptDom.classList.remove('active')
      payload.type === ElementType.SUPERSCRIPT
        ? superscriptDom.classList.add('active')
        : superscriptDom.classList.remove('active')
      payload.type === ElementType.SEPARATOR
        ? separatorDom.classList.add('active')
        : separatorDom.classList.remove('active')
      separatorOptionDom
        .querySelectorAll('li')
        .forEach(li => li.classList.remove('active'))
      if (payload.type === ElementType.SEPARATOR) {
        const separator = payload.dashArray.join(',') || '0,0'
        const curSeparatorDom = separatorOptionDom.querySelector<HTMLLIElement>(
          `[data-separator='${separator}']`
        )!
        if (curSeparatorDom) {
          curSeparatorDom.classList.add('active')
        }
      }

      // 富文本
      fontOptionDom
        .querySelectorAll<HTMLLIElement>('li')
        .forEach(li => li.classList.remove('active'))
      const curFontDom = fontOptionDom.querySelector<HTMLLIElement>(
        `[data-family='${payload.font}']`
      )
      if (curFontDom) {
        setSelectText(fontSelectDom, curFontDom.innerText)
        fontSelectDom.style.fontFamily = payload.font
        curFontDom.classList.add('active')
      }
      sizeOptionDom
        .querySelectorAll<HTMLLIElement>('li')
        .forEach(li => li.classList.remove('active'))
      const curSizeDom = sizeOptionDom.querySelector<HTMLLIElement>(
        `[data-size='${payload.size}']`
      )
      if (curSizeDom) {
        setSelectText(sizeSelectDom, curSizeDom.innerText)
        curSizeDom.classList.add('active')
      } else {
        setSelectText(sizeSelectDom, `${payload.size}`)
      }
      payload.bold
        ? boldDom.classList.add('active')
        : boldDom.classList.remove('active')
      payload.italic
        ? italicDom.classList.add('active')
        : italicDom.classList.remove('active')
      payload.underline
        ? underlineDom.classList.add('active')
        : underlineDom.classList.remove('active')
      payload.strikeout
        ? strikeoutDom.classList.add('active')
        : strikeoutDom.classList.remove('active')
      if (payload.color) {
        colorDom.classList.add('active')
        colorControlDom.value = payload.color
        colorSpanDom.style.backgroundColor = payload.color
      } else {
        colorDom.classList.remove('active')
        colorControlDom.value = '#000000'
        colorSpanDom.style.backgroundColor = '#000000'
      }
      if (payload.highlight) {
        highlightDom.classList.add('active')
        highlightControlDom.value = payload.highlight
        highlightSpanDom.style.backgroundColor = payload.highlight
      } else {
        highlightDom.classList.remove('active')
        highlightControlDom.value = '#ffff00'
        highlightSpanDom.style.backgroundColor = '#ffff00'
      }

      // 行布局
      leftDom.classList.remove('active')
      centerDom.classList.remove('active')
      rightDom.classList.remove('active')
      alignmentDom.classList.remove('active')
      justifyDom.classList.remove('active')
      if (payload.rowFlex && payload.rowFlex === 'right') {
        rightDom.classList.add('active')
      } else if (payload.rowFlex && payload.rowFlex === 'center') {
        centerDom.classList.add('active')
      } else if (payload.rowFlex && payload.rowFlex === 'alignment') {
        alignmentDom.classList.add('active')
      } else if (payload.rowFlex && payload.rowFlex === 'justify') {
        justifyDom.classList.add('active')
      } else {
        leftDom.classList.add('active')
      }

      // 行间距
      rowOptionDom
        .querySelectorAll<HTMLLIElement>('li')
        .forEach(li => li.classList.remove('active'))
      const curRowMarginDom = rowOptionDom.querySelector<HTMLLIElement>(
        `[data-rowmargin='${payload.rowMargin}']`
      )!
      if (curRowMarginDom) {
        curRowMarginDom.classList.add('active')
      }

      // 首行缩进 (原生属性方案)
      firstLineIndentOptionDom
        .querySelectorAll<HTMLLIElement>('li')
        .forEach(li => li.classList.remove('active'))

      const range = instance.command.getRange()
      const { startIndex } = range
      const zone = range.zone || 'main'
      const elementList = instance.command.getValue().data[zone]

      let firstLineIndent = 0
      if (elementList && startIndex >= 0) {
        // 精准定位当前段首
        const fullTextObj = instance.command.getText()
        const fullText = fullTextObj[zone]
        let pStart = startIndex
        while (pStart > 0 && fullText[pStart - 1] !== '\n') {
          pStart--
        }

        // 映射到元素
        let charAcc = 0
        let elementIdx = -1
        for (let i = 0; i < elementList.length; i++) {
          if (charAcc === pStart) {
            elementIdx = i
            break
          }
          charAcc += (elementList[i].value || '').length
        }

        if (elementIdx !== -1) {
          const el = elementList[elementIdx]
          if (el && el.extension && (el.extension as any).isFirstLineIndent) {
            // 通过内容长度反推缩进倍数
            firstLineIndent = (el.value || '').length
          }
        }
      }

      const curFirstLineIndentDom = firstLineIndentOptionDom.querySelector<HTMLLIElement>(
        `[data-firstlineindent='${firstLineIndent}']`
      )
      if (curFirstLineIndentDom) {
        curFirstLineIndentDom.classList.add('active')
      }

      // 功能
      payload.undo
        ? undoDom.classList.remove('no-allow')
        : undoDom.classList.add('no-allow')
      payload.redo
        ? redoDom.classList.remove('no-allow')
        : redoDom.classList.add('no-allow')
      payload.painter
        ? painterDom.classList.add('active')
        : painterDom.classList.remove('active')

      // 标题
      titleOptionDom
        .querySelectorAll<HTMLLIElement>('li')
        .forEach(li => li.classList.remove('active'))
      if (payload.level) {
        const curTitleDom = titleOptionDom.querySelector<HTMLLIElement>(
          `[data-level='${payload.level}']`
        )!
        setSelectText(titleSelectDom, curTitleDom.innerText)
        curTitleDom.classList.add('active')
      } else {
        setSelectText(titleSelectDom, '正文')
        titleOptionDom.querySelector('li:first-child')!.classList.add('active')
      }

      // 列表
      listOptionDom
        .querySelectorAll<HTMLLIElement>('li')
        .forEach(li => li.classList.remove('active'))
      if (payload.listType) {
        listDom.classList.add('active')
        const listType = payload.listType
        const listStyle =
          payload.listType === ListType.OL ? ListStyle.DECIMAL : payload.listType
        const curListDom = listOptionDom.querySelector<HTMLLIElement>(
          `[data-list-type='${listType}'][data-list-style='${listStyle}']`
        )
        if (curListDom) {
          curListDom.classList.add('active')
        }
      } else {
        listDom.classList.remove('active')
      }

      // 批注
      commentDom
        .querySelectorAll<HTMLDivElement>('.comment-item')
        .forEach(commentItemDom => {
          commentItemDom.classList.remove('active')
        })
      if (payload.groupIds) {
        const [id] = payload.groupIds
        const activeCommentDom = commentDom.querySelector<HTMLDivElement>(
          `.comment-item[data-id='${id}']`
        )
        if (activeCommentDom) {
          activeCommentDom.classList.add('active')
          scrollIntoView(commentDom, activeCommentDom)
        }
      }

      // 行列信息
      const rangeContext = instance.command.getRangeContext()
      if (rangeContext) {
        const rowNoDom = document.querySelector<HTMLSpanElement>('.row-no');
        const colNoDom = document.querySelector<HTMLSpanElement>('.col-no');
        if (rowNoDom) rowNoDom.innerText = `${rangeContext.startRowNo + 1}`;
        if (colNoDom) colNoDom.innerText = `${rangeContext.startColNo + 1}`;
      }
    } catch (e) {
      console.warn('RangeStyleChange UI Update Error:', e);
    }
  }

  instance.listener.visiblePageNoListChange = function (payload: number[]) {
    const text = payload.map((i: number) => i + 1).join('、')
    document.querySelector<HTMLSpanElement>('.page-no-list')!.innerText = text
  }

  instance.listener.pageSizeChange = function (payload: number | string) {
    document.querySelector<HTMLSpanElement>('.page-size')!.innerText =
      `${payload}`
  }

  instance.listener.intersectionPageNoChange = function (payload: number) {
    document.querySelector<HTMLSpanElement>('.page-no')!.innerText = `${payload + 1
      }`
  }

  instance.listener.pageScaleChange = function (payload: number) {
    const value = `${Math.floor(payload * 10 * 10)}%`
    document.querySelectorAll<HTMLSpanElement>(
      '.page-scale-percentage'
    ).forEach(dom => {
      dom.innerText = value
    })
  }

  instance.listener.controlChange = function (payload: any) {
    const disableMenusInControlContext = [
      'table',
      'hyperlink',
      'separator',
      'page-break',
      'control'
    ]
    // 菜单操作权限
    disableMenusInControlContext.forEach(menu => {
      const menuDom = document.querySelector<HTMLDivElement>(
        `.menu-item__${menu}`
      )!
      payload.state === ControlState.ACTIVE
        ? menuDom.classList.add('disable')
        : menuDom.classList.remove('disable')
    })
  }

  instance.listener.pageModeChange = function (payload: any) {
    const activeMode = pageModeOptionsDom.querySelector<HTMLLIElement>(
      `[data-page-mode='${payload}']`
    )!
    pageModeOptionsDom
      .querySelectorAll('li')
      .forEach(li => li.classList.remove('active'))
    activeMode.classList.add('active')
  }

  const handleContentChange = async function () {
    // 字数
    const wordCount = await instance.command.getWordCount()
    document.querySelector<HTMLSpanElement>('.word-count')!.innerText = `${wordCount || 0
      }`
    // 目录
    if (isCatalogShow) {
      nextTick(() => {
        updateCatalog()
      })
    }
    // 批注
    nextTick(() => {
      updateComment()
    })
  }
  instance.listener.contentChange = debounce(handleContentChange, 200)
  handleContentChange()

  instance.listener.saved = function (payload: any) {
    console.log('elementList: ', payload)
  }

  // 9. 右键菜单注册
  instance.register.contextMenuList([
    {
      name: '批注',
      when: (payload: any) => {
        return (
          !payload.isReadonly &&
          payload.editorHasSelection &&
          payload.zone === EditorZone.MAIN
        )
      },
      callback: (command: Command) => {
        new Dialog({
          title: '批注',
          data: [
            {
              type: 'textarea',
              label: '批注',
              height: 100,
              name: 'value',
              required: true,
              placeholder: '请输入批注'
            }
          ],
          onConfirm: payload => {
            const value = payload.find(p => p.name === 'value')?.value
            if (!value) return
            const groupId = command.executeSetGroup()
            if (!groupId) return
            commentList.push({
              id: groupId,
              content: value,
              userName: 'Hufe',
              rangeText: command.getRangeText(),
              createdDate: new Date().toLocaleString()
            })
          }
        })
      }
    },
    {
      name: '新增题注',
      icon: 'caption',
      when: (payload: any) => {
        return (
          !payload.isReadonly &&
          payload.startElement?.type === ElementType.IMAGE &&
          !payload.startElement?.imgCaption
        )
      },
      callback: (command: Command) => {
        new Dialog({
          title: '新增题注',
          data: [
            {
              type: 'text',
              label: '题注内容',
              name: 'value',
              required: true,
              placeholder: '请输入题注内容，使用{imageNo}表示图片序号'
            }
          ],
          onConfirm: payload => {
            const value = payload.find(p => p.name === 'value')?.value
            if (!value) return
            command.executeSetImageCaption({
              value
            })
          }
        })
      }
    },
    {
      name: '修改题注',
      icon: 'caption',
      when: (payload: any) => {
        return (
          !payload.isReadonly &&
          payload.startElement?.type === ElementType.IMAGE &&
          !!payload.startElement?.imgCaption
        )
      },
      callback: (command: Command, context: any) => {
        const currentCaption = context.startElement?.imgCaption
        new Dialog({
          title: '修改题注',
          data: [
            {
              type: 'text',
              label: '题注内容',
              name: 'value',
              required: true,
              value: currentCaption?.value,
              placeholder: '请输入题注内容，使用{imageNo}表示图片序号'
            }
          ],
          onConfirm: payload => {
            const value = payload.find(p => p.name === 'value')?.value
            command.executeSetImageCaption({
              ...currentCaption,
              value: value || ''
            })
          }
        })
      }
    },
    {
      name: '签名',
      icon: 'signature',
      when: (payload: any) => {
        return !payload.isReadonly && payload.editorTextFocus
      },
      callback: (command: Command) => {
        new Signature({
          onConfirm(payload) {
            if (!payload) return
            const { value, width, height } = payload
            if (!value || !width || !height) return
            command.executeInsertElementList([
              {
                value,
                width,
                height,
                type: ElementType.IMAGE
              }
            ])
          }
        })
      }
    },
    {
      name: '格式整理',
      icon: 'word-tool',
      when: (payload: any) => {
        return !payload.isReadonly
      },
      callback: (command: Command) => {
        command.executeWordTool()
      }
    },
    {
      name: '清空涂鸦信息',
      when: (payload: any) => {
        return payload.options.mode === EditorMode.GRAFFITI
      },
      callback: (command: Command) => {
        command.executeClearGraffiti()
      }
    }
  ])

  // 10. 快捷键注册
  instance.register.shortcutList([
    {
      key: KeyMap.P,
      mod: true,
      isGlobal: true,
      callback: (command: Command) => {
        command.executePrint()
      }
    },
    {
      key: KeyMap.F,
      mod: true,
      isGlobal: true,
      callback: (command: Command) => {
        const text = command.getRangeText()
        searchDom.click()
        if (text) {
          searchInputDom.value = text
          instance.command.executeSearch(text)
          setSearchResult()
        }
      }
    },
    {
      key: KeyMap.MINUS,
      ctrl: true,
      isGlobal: true,
      callback: (command: Command) => {
        command.executePageScaleMinus()
      }
    },
    {
      key: KeyMap.EQUAL,
      ctrl: true,
      isGlobal: true,
      callback: (command: Command) => {
        command.executePageScaleAdd()
      }
    },
    {
      key: KeyMap.ZERO,
      ctrl: true,
      isGlobal: true,
      callback: (command: Command) => {
        command.executePageScaleRecovery()
      }
    }
  ])

}
