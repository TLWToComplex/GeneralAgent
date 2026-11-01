import MarkdownIt from 'markdown-it'
import katex from 'markdown-it-katex'
import hljs from 'highlight.js'
import type { ChatMessage } from '@/types'
import type { Message } from '@/types/mcp'
import { ROLE_CONFIG, EXPORT_CONTAINER_CONFIG } from './constants'
import 'katex/dist/katex.min.css'
import StorageService from '@/utils/StorageService'
import { getSystemName } from '@/utils/RuntimeConfig'
import bgPoster from '@/assets/image/jpg/background.jpg'
import { getImagePreviewUrl, isImageFile } from '@/utils/conversationImages'
import { parseArtifactsFromContent } from '@/utils/artifactParser'
import { sanitizeMarkdownInlineCode } from '@/utils/markdownInlineCode'
import ToolsSvg from '@/assets/image/svg/tools.svg'
import WordSvg from '@/assets/image/svg/Word.svg'
import PdfSvg from '@/assets/image/svg/pdf-icon.svg'
import TxtSvg from '@/assets/image/svg/Txt.svg'
import MarkdownSvg from '@/assets/image/svg/Markdown.svg'
import ExcelSvg from '@/assets/image/svg/Excel.svg'
import PptSvg from '@/assets/image/svg/PPT.svg'

type PdfRenderableMessage = ChatMessage & Pick<Partial<Message>, 'display_content' | 'files' | 'orchestratorBlocks'>

/**
 * PDF渲染服务类
 * 负责将聊天消息渲染为可导出的HTML结构
 */
export default class PdfRenderer {
  // Markdown渲染器实例
  private static md = new MarkdownIt({
    html: true,
    linkify: true,
    typographer: true,
    breaks: true,
    highlight: function (str, lang) {
      if (lang && hljs.getLanguage(lang)) {
        try {
          return hljs.highlight(str, { language: lang }).value
        } catch (__) {}
      }
      return '' // 使用额外的默认转义
    }
  }).use(katex, {
    // KaTeX 配置选项
    throwOnError: false, // 遇到错误时不抛出异常，而是显示错误信息
    errorColor: '#cc0000', // 错误信息颜色
    strict: false, // 关闭严格模式以提高兼容性
    trust: true, // 允许更多LaTeX命令
    fleqn: false, // 不强制左对齐
    leqno: false, // 不将公式编号放在左边
    minRuleThickness: 0.04, // 最小规则厚度
    colorIsTextColor: false, // 颜色不影响文本颜色
    maxSize: Infinity, // 不限制最大尺寸
    maxExpand: 1000, // 增加宏展开限制
    globalGroup: false, // 不使用全局组
    macros: {
      // 常用数学符号宏定义
      '\\RR': '\\mathbb{R}',
      '\\NN': '\\mathbb{N}',
      '\\ZZ': '\\mathbb{Z}',
      '\\QQ': '\\mathbb{Q}',
      '\\CC': '\\mathbb{C}',
      '\\PP': '\\mathbb{P}',
      '\\EE': '\\mathbb{E}',
      '\\FF': '\\mathbb{F}',
      '\\HH': '\\mathbb{H}',
      // 常用运算符
      '\\implies': '\\Rightarrow',
      '\\iff': '\\Leftrightarrow',
      '\\land': '\\wedge',
      '\\lor': '\\vee',
      '\\lnot': '\\neg',
      // 常用函数
      '\\argmax': '\\operatorname{argmax}',
      '\\argmin': '\\operatorname{argmin}',
      '\\sgn': '\\operatorname{sgn}',
      '\\Tr': '\\operatorname{Tr}',
      '\\rank': '\\operatorname{rank}',
      '\\diag': '\\operatorname{diag}',
      // 微积分
      '\\dd': '\\mathrm{d}',
      '\\dv': '\\frac{\\mathrm{d}#1}{\\mathrm{d}#2}',
      '\\pdv': '\\frac{\\partial#1}{\\partial#2}',
      // 概率统计
      '\\Var': '\\operatorname{Var}',
      '\\Cov': '\\operatorname{Cov}',
      '\\Corr': '\\operatorname{Corr}'
    }
  })

  // 设置自定义代码块渲染器
  static {
    this.setupCodeBlockRenderer()
    this.setupInlineCodeRenderer()
  }

  /**
   * 设置自定义代码块渲染器
   */
  private static setupCodeBlockRenderer(): void {
    this.md.renderer.rules.fence = (tokens: any, idx: any) => {
      const token = tokens[idx]
      const info = token.info ? token.info.trim() : ''
      let lang = info.split(/\s+/g)[0] || ''
      if (lang === 'md') lang = 'markdown'
      const code = token.content.trim()
      
      const copyButton = `<button class="code-copy-button" data-copy-state="ready">复制</button>`
      const languageLabel = lang ? `<span class="code-language">${lang}</span>` : `<span class="code-language-empty">&nbsp;</span>`
      
      // 高亮代码
      let codeContent: string
      try {
        if (lang && hljs.getLanguage(lang)) {
          codeContent = hljs.highlight(code, { language: lang }).value
        } else {
          const result = hljs.highlightAuto(code)
          codeContent = result.value
        }
      } catch (e) {
        codeContent = this.md.utils.escapeHtml(code)
      }
      
      return `<div class="code-block-wrapper" data-lang="${lang}" data-code="${encodeURIComponent(code)}">
        <div class="code-block-header">${languageLabel}${copyButton}</div>
        <pre class="code-pre"><code class="chat-hljs ${lang}">${codeContent}</code></pre>
      </div>`
    }
  }

  private static setupInlineCodeRenderer(): void {
    this.md.renderer.rules.code_inline = (tokens: any, idx: any) => {
      const token = tokens[idx]
      return `<code class="inline-code">${this.md.utils.escapeHtml(token.content)}</code>`
    }
  }

  /**
   * 创建导出容器
   */
  static createExportContainer(
    messages: PdfRenderableMessage[],
    includeThinking: boolean,
    includeSystemMessages: boolean = true,
    allMessages?: PdfRenderableMessage[],
    includeToolCalls: boolean = true
  ): HTMLElement {
    const container = this.createBaseContainer()
    
    if (messages.length === 0) {
      container.appendChild(this.createNoContentElement())
      return container
    }

    // 渲染每条消息
    messages.forEach(message => {
      if (message.role === 'system' && !includeSystemMessages) {
        return
      }
      
      // 跳过Tool类型的消息，因为它们的内容已经在工具调用结果中显示
      if (message.role === 'tool') {
        return
      }
      
      const messageElement = this.createMessageElement(message, includeThinking, allMessages || messages, includeToolCalls)
      container.appendChild(messageElement)
    })

    return container
  }

  /**
   * 创建基础容器
   */
  private static createBaseContainer(): HTMLElement {
    const container = document.createElement('div')
    container.className = 'pdf-export-container'
    
    // 应用基础样式
    Object.assign(container.style, {
      width: `${EXPORT_CONTAINER_CONFIG.width}px`,
      backgroundColor: EXPORT_CONTAINER_CONFIG.backgroundColor,
      padding: `${EXPORT_CONTAINER_CONFIG.padding}px`,
      boxSizing: 'border-box',
      position: 'absolute',
      left: '-9999px',
      top: '0',
      zIndex: '-1000',
      fontFamily: EXPORT_CONTAINER_CONFIG.fontFamily,
      minHeight: '100%',
      textRendering: 'optimizeLegibility',
      WebkitFontSmoothing: 'antialiased',
      MozOsxFontSmoothing: 'grayscale'
    })

    return container
  }

  /**
   * 创建无内容提示元素
   */
  private static createNoContentElement(): HTMLElement {
    const element = document.createElement('div')
    element.textContent = '没有找到对话内容'
    Object.assign(element.style, {
      textAlign: 'center',
      color: '#999',
      padding: '20px',
      border: '1px dashed #ccc',
      borderRadius: '8px'
    })
    return element
  }

  /**
   * 创建消息元素
   */
  private static createMessageElement(
    message: PdfRenderableMessage,
    includeThinking: boolean,
    allMessages?: PdfRenderableMessage[],
    includeToolCalls: boolean = true
  ): HTMLElement {
    const messageContainer = document.createElement('div')
    Object.assign(messageContainer.style, {
      display: 'flex',
      margin: '0 0 8px 0', // 行104: 从6px改为8px
      padding: '14px', // 行105: 从12px改为14px
      borderRadius: '12px',
      width: '100%',
      boxSizing: 'border-box',
      position: 'relative'
    })

    // 添加头像
    const avatarContainer = this.createAvatarContainer(message)
    messageContainer.appendChild(avatarContainer)

    // 添加内容容器
    const contentContainer = this.createContentContainer(message, includeThinking, allMessages, includeToolCalls)
    messageContainer.appendChild(contentContainer)

    return messageContainer
  }

  /**
   * 创建头像容器
   */
  private static createAvatarContainer(message: PdfRenderableMessage): HTMLElement {
    const container = document.createElement('div')
    Object.assign(container.style, {
      marginRight: '16px',
      flexShrink: '0'
    })

    const role = message.role

    // 用户头像：优先使用图片头像，否则使用文字头像（首字母）
    if (role === 'user') {
      try {
        const raw = localStorage.getItem('user-profile')
        const profile = raw ? JSON.parse(raw) : {}
        const isAllEmpty = !profile.avatar && !profile.avatarBackground && !profile.avatarTextColor
        const avatarUrl: string = profile.avatar || (isAllEmpty ? (bgPoster as unknown as string) : '')
        const bg: string = profile.avatarBackground || (avatarUrl ? '#ffffff' : ROLE_CONFIG.user.color)
        const textColor: string = profile.avatarTextColor || '#fff'
        const username: string = profile.username || 'user'

        if (avatarUrl) {
          const img = document.createElement('img')
          img.src = avatarUrl
          Object.assign(img.style, {
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            objectFit: 'cover',
            display: 'block'
          })
          container.appendChild(img)
          return container
        }

        const initial = (username || 'U').trim().charAt(0).toUpperCase()
        const avatar = document.createElement('div')
        Object.assign(avatar.style, {
          width: '32px',
          height: '32px',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: textColor,
          fontWeight: 'bold',
          backgroundColor: bg
        })
        avatar.textContent = initial
        container.appendChild(avatar)
        return container
      } catch (e) {
        // 解析失败时回退到默认配置
      }
    }

    const assistantIdentity = role === 'assistant' ? this.getAssistantIdentity(message) : null
    if (assistantIdentity?.useAgentIdentity) {
      if (assistantIdentity.avatar) {
        const img = document.createElement('img')
        img.src = assistantIdentity.avatar
        Object.assign(img.style, {
          width: '32px',
          height: '32px',
          borderRadius: '50%',
          objectFit: 'cover',
          display: 'block'
        })
        container.appendChild(img)
        return container
      }

      const avatar = document.createElement('div')
      Object.assign(avatar.style, {
        width: '32px',
        height: '32px',
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#fff',
        fontWeight: 'bold',
        backgroundColor: assistantIdentity.themeColor
      })
      avatar.textContent = assistantIdentity.name.trim().charAt(0).toUpperCase() || 'A'
      container.appendChild(avatar)
      return container
    }

    // 其他角色沿用默认图标与颜色，保持样式一致
    const avatar = document.createElement('div')
    const config = ROLE_CONFIG[role as keyof typeof ROLE_CONFIG] || { icon: '?', color: '#f56a00' }
    Object.assign(avatar.style, {
      width: '32px',
      height: '32px',
      borderRadius: '50%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: '#fff',
      fontWeight: 'bold',
      backgroundColor: config.color
    })
    avatar.textContent = config.icon
    container.appendChild(avatar)
    return container
  }

  private static getAssistantIdentity(message: PdfRenderableMessage): {
    useAgentIdentity: boolean
    name: string
    avatar: string
    themeColor: string
  } {
    try {
      const activeAgent = StorageService.getActiveAgent()
      const agentType = activeAgent?.basic?.type || activeAgent?.config?.basic?.type
      const useAgentIdentity = message.role === 'assistant'
        && (agentType === 'assistant' || agentType === 'orchestrator' || agentType === 'deepagent')

      return {
        useAgentIdentity,
        name: activeAgent?.basic?.name || activeAgent?.config?.basic?.name || 'Assistant',
        avatar: activeAgent?.basic?.avatar || activeAgent?.config?.basic?.avatar || '',
        themeColor: activeAgent?.basic?.themeColor || activeAgent?.config?.basic?.themeColor || '#722ed1'
      }
    } catch {
      return {
        useAgentIdentity: false,
        name: 'Assistant',
        avatar: '',
        themeColor: '#722ed1'
      }
    }
  }

  /**
   * 创建内容容器
   */
  private static createContentContainer(
    message: PdfRenderableMessage,
    includeThinking: boolean,
    allMessages?: PdfRenderableMessage[],
    includeToolCalls: boolean = true
  ): HTMLElement {
    const container = document.createElement('div')
    Object.assign(container.style, {
      flex: '1',
      minWidth: '0',
      overflowWrap: 'break-word',
      wordWrap: 'break-word',
      wordBreak: 'break-word',
      width: '100%'
    })

    // 添加角色标签
    const roleLabel = this.createRoleLabel(message)
    container.appendChild(roleLabel)

    // 添加图片附件
    const imageFilesElement = this.createMessageImageFilesElement(message)
    if (imageFilesElement) {
      container.appendChild(imageFilesElement)
    }

    const documentFilesElement = this.createMessageDocumentFilesElement(message)
    if (documentFilesElement) {
      container.appendChild(documentFilesElement)
    }

    const hasInlineReasoningBlocks = Array.isArray(message.orchestratorBlocks)
      && message.orchestratorBlocks.some(block => block.type === 'reasoning' && !!block.content?.trim())

    // 兼容旧消息：没有分块思考过程时，仍然输出聚合后的思考内容
    if (
      includeThinking
      && message.role === 'assistant'
      && message.reasoning_content
      && message.reasoning_content.trim()
      && !hasInlineReasoningBlocks
    ) {
      const reasoningElement = this.createReasoningElement(message.reasoning_content)
      container.appendChild(reasoningElement)
    }

    const messageId = String(message.id || message.timestamp || 'pdf-message')
    const shouldUseAgentToolStyle = this.shouldUseAgentToolCallStyle(message)
    const useOrchestratorBlocks = shouldUseAgentToolStyle
      && message.role === 'assistant'
      && Array.isArray(message.orchestratorBlocks)
      && message.orchestratorBlocks.length > 0

    if (useOrchestratorBlocks) {
      const toolCallMap = new Map((message.tool_calls || []).map(toolCall => [toolCall.id, toolCall]))
      message.orchestratorBlocks?.forEach((block, index) => {
        if (includeThinking && block.type === 'reasoning') {
          if (!block.content?.trim()) {
            return
          }
          container.appendChild(this.createReasoningElement(block.content))
          return
        }

        if (block.type === 'content') {
          if (!block.content?.trim()) {
            return
          }
          const contentElement = this.createMessageContent(block.content, `${messageId}-block-${index}`)
          container.appendChild(contentElement)
          return
        }

        if (includeToolCalls && block.type === 'tools') {
          const blockToolCalls = block.toolCallIds
            .map(id => toolCallMap.get(id))
            .filter(Boolean) as any[]

          if (blockToolCalls.length > 0) {
            container.appendChild(this.createToolCallsElement(blockToolCalls, allMessages, true))
          }
        }
      })

      return container
    }

    if (includeToolCalls && shouldUseAgentToolStyle && message.tool_calls?.length) {
      container.appendChild(this.createToolCallsElement(message.tool_calls, allMessages, true))
    }

    if (message.content) {
      const contentElement = this.createMessageContent(message.content, messageId)
      container.appendChild(contentElement)
    }

    if (includeToolCalls && !shouldUseAgentToolStyle && message.tool_calls?.length) {
      container.appendChild(this.createToolCallsElement(message.tool_calls, allMessages, false))
    }

    return container
  }

  /**
   * 创建角色标签
   */
  private static createRoleLabel(message: PdfRenderableMessage): HTMLElement {
    const label = document.createElement('div')

    let text = ''
    if (message.role === 'user') {
      try {
        const raw = localStorage.getItem('user-profile')
        const profile = raw ? JSON.parse(raw) : {}
        text = profile.username || 'user'
      } catch (e) {
        text = 'user'
      }
    } else if (message.role === 'assistant') {
      text = getSystemName()
    } else {
      text = message.role
    }

    label.textContent = text
    Object.assign(label.style, {
      fontSize: '12px',
      color: '#888',
      marginBottom: '6px',
      letterSpacing: '0.5px',
      fontWeight: '500'
    })
    return label
  }

  /**
   * 创建消息中的图片附件元素
   */
  private static createMessageImageFilesElement(message: PdfRenderableMessage): HTMLElement | null {
    const files = Array.isArray(message.files) ? message.files : []
    const imageFiles = files
      .filter(file => isImageFile(file))
      .map(file => ({
        file,
        previewUrl: getImagePreviewUrl(file)
      }))
      .filter(item => !!item.previewUrl)

    if (imageFiles.length === 0) {
      return null
    }

    const isMultiImage = imageFiles.length > 1

    const section = document.createElement('div')
    Object.assign(section.style, {
      marginBottom: message.content?.trim() ? '14px' : '8px',
      width: '100%'
    })

    const grid = document.createElement('div')
    Object.assign(grid.style, {
      display: 'grid',
      gap: '12px',
      width: '100%',
      maxWidth: isMultiImage ? '520px' : '340px',
      gridTemplateColumns: isMultiImage ? 'repeat(2, minmax(0, 1fr))' : 'minmax(0, 1fr)',
      alignItems: 'stretch'
    })

    imageFiles.forEach(({ file, previewUrl }) => {
      const card = document.createElement('div')
      Object.assign(card.style, {
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        borderRadius: '18px',
        overflow: 'hidden',
        background: 'linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98))',
        border: '1px solid rgba(226, 232, 240, 0.95)',
        boxShadow: '0 8px 22px rgba(15, 23, 42, 0.08)'
      })

      const imageFrame = document.createElement('div')
      Object.assign(imageFrame.style, {
        height: isMultiImage ? '200px' : '260px',
        overflow: 'hidden',
        background: '#f8fafc'
      })

      const image = document.createElement('img')
      image.src = previewUrl
      image.alt = String(file?.name || '图片')
      image.loading = 'eager'
      image.decoding = 'sync'
      if (!previewUrl.startsWith('data:')) {
        image.crossOrigin = 'anonymous'
      }
      Object.assign(image.style, {
        display: 'block',
        width: '100%',
        height: '100%',
        objectFit: 'cover',
        objectPosition: 'center',
        background: '#f8fafc'
      })

      const meta = document.createElement('div')
      meta.textContent = String(file?.name || '图片')
      Object.assign(meta.style, {
        display: 'flex',
        alignItems: 'center',
        boxSizing: 'border-box',
        minHeight: '42px',
        padding: '10px 12px',
        fontSize: '12px',
        color: '#64748b',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis'
      })

      imageFrame.appendChild(image)
      card.appendChild(imageFrame)
      card.appendChild(meta)
      grid.appendChild(card)
    })

    section.appendChild(grid)
    return section
  }

  private static createMessageDocumentFilesElement(message: PdfRenderableMessage): HTMLElement | null {
    const files = Array.isArray(message.files) ? message.files : []
    const documentFiles = files.filter(file => !isImageFile(file))

    if (documentFiles.length === 0) {
      return null
    }

    const section = document.createElement('div')
    Object.assign(section.style, {
      marginBottom: message.content?.trim() ? '14px' : '8px',
      width: '100%'
    })

    const list = document.createElement('div')
    Object.assign(list.style, {
      display: 'flex',
      flexWrap: 'wrap',
      gap: '10px',
      width: '100%'
    })

    documentFiles.forEach(file => {
      const fileName = String(file?.name || '文件').trim() || '文件'
      const type = this.getDocumentArtifactType(fileName)
      list.appendChild(this.createArtifactCardElement({
        type,
        title: fileName
      }))
    })

    section.appendChild(list)
    return section
  }

  /**
   * 创建思考过程元素
   */
  private static createReasoningElement(content: string): HTMLElement {
    const container = document.createElement('div')
    Object.assign(container.style, {
      marginBottom: '14px', // 行214: 从12px改为14px
      borderRadius: '8px',
      overflow: 'hidden'
    })

    // 标题（与 Web 端思考面板头部色值保持一致）
    const header = document.createElement('div')
    header.textContent = '已深度思考'
    Object.assign(header.style, {
      backgroundColor: '#f2f8fe',
      padding: '9px 15px', // 行225: 从8px 14px改为9px 15px
      color: '#334155',
      fontWeight: '500',
      fontSize: '13px',
      borderTopLeftRadius: '8px',
      borderTopRightRadius: '8px',
      border: '1px solid rgba(200, 220, 240, 0.55)'
    })

    // 内容
    const contentElement = document.createElement('div')
    Object.assign(contentElement.style, {
      fontSize: '12px',
      color: '#64748b',
      backgroundColor: '#fcfdff',
      padding: '14px', // 行240: 从12px改为14px
      borderBottomLeftRadius: '8px',
      borderBottomRightRadius: '8px',
      border: '1px solid rgba(200, 220, 240, 0.55)',
      marginTop: '-1px'
    })

    contentElement.innerHTML = this.md.render(sanitizeMarkdownInlineCode(content))
    this.applyMarkdownStyles(contentElement)

    container.appendChild(header)
    container.appendChild(contentElement)
    
    return container
  }

  /**
   * 创建消息内容元素
   */
  private static createMessageContent(content: string, messageId: string): HTMLElement {
    const element = document.createElement('div')
    Object.assign(element.style, {
      lineHeight: '1.6', // 减小行高
      fontSize: '13px',
      width: '100%'
    })

    const artifactTypes = new Set(['mermaid', 'html', 'svg', 'markdown', 'docx', 'pdf', 'text', 'csv', 'xlsx', 'pptx'])
    const artifacts = parseArtifactsFromContent(content, messageId)
      .filter(artifact => artifactTypes.has(artifact.type) && !artifact.isInThinking)
      .sort((a, b) => (a.startIndex || 0) - (b.startIndex || 0))

    if (artifacts.length === 0) {
      element.innerHTML = this.md.render(sanitizeMarkdownInlineCode(content))
      this.applyMarkdownStyles(element)
      return element
    }

    let cursor = 0
    artifacts.forEach(artifact => {
      const start = artifact.startIndex ?? 0
      const end = artifact.endIndex ?? start
      if (start < cursor) {
        return
      }

      const leadingContent = content.slice(cursor, start)
      this.appendMarkdownContent(element, leadingContent)
      element.appendChild(this.createArtifactCardElement({
        type: artifact.type,
        title: artifact.title,
        linkUrl: typeof artifact.content === 'string' ? artifact.content : undefined
      }))
      cursor = end
    })

    this.appendMarkdownContent(element, content.slice(cursor))
    
    return element
  }

  private static appendMarkdownContent(container: HTMLElement, content: string): void {
    if (!content.trim()) {
      return
    }

    const fragment = document.createElement('div')
    fragment.innerHTML = this.md.render(sanitizeMarkdownInlineCode(content))
    this.applyMarkdownStyles(fragment)

    while (fragment.firstChild) {
      container.appendChild(fragment.firstChild)
    }
  }

  private static normalizeArtifactLinkUrl(linkUrl?: string): string {
    if (!linkUrl) {
      return ''
    }

    const trimmed = linkUrl.trim()
    if (!trimmed || !/^https?:\/\//i.test(trimmed)) {
      return ''
    }

    return trimmed
  }

  private static getArtifactLinkLabel(linkUrl: string): string {
    try {
      return decodeURIComponent(linkUrl)
    } catch {
      return linkUrl
    }
  }

  private static createArtifactCardElement(params: { type: string; title?: string; linkUrl?: string }): HTMLElement {
    const normalizedLinkUrl = this.normalizeArtifactLinkUrl(params.linkUrl)
    const container = document.createElement('div')
    Object.assign(container.style, {
      display: 'flex',
      flexDirection: 'column',
      gap: '6px',
      width: '100%'
    })

    const card = document.createElement('div')
    Object.assign(card.style, {
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      padding: '12px',
      margin: '0 0',
      backgroundColor: '#fff',
      border: '1px solid #e2e8f0',
      borderRadius: '18px',
      width: '300px',
      maxWidth: '100%',
      minWidth: '290px',
      alignSelf: 'flex-start',
      boxSizing: 'border-box'
    })

    const iconBox = document.createElement('div')
    Object.assign(iconBox.style, {
      width: '40px',
      height: '40px',
      backgroundColor: '#f8fafc',
      border: '1px solid #f1f5f9',
      borderRadius: '12px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: '#64748b',
      flexShrink: '0',
      boxShadow: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
      overflow: 'hidden'
    })
    iconBox.appendChild(this.createArtifactIconElement(params.type))

    const content = document.createElement('div')
    Object.assign(content.style, {
      flex: '1',
      minWidth: '0'
    })

    const title = document.createElement('div')
    title.textContent = params.title || this.getArtifactDefaultTitle(params.type)
    Object.assign(title.style, {
      fontSize: '14px',
      fontWeight: '500',
      color: '#334155',
      whiteSpace: 'nowrap',
      overflow: 'hidden',
      textOverflow: 'ellipsis'
    })

    const meta = document.createElement('div')
    Object.assign(meta.style, {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      marginTop: '2px'
    })

    const typeTag = document.createElement('span')
    typeTag.textContent = `CANVAS-${this.getArtifactDisplayLabel(params.type)}`
    Object.assign(typeTag.style, {
      fontSize: '12px',
      color: '#94a3b8',
      textTransform: 'uppercase',
      letterSpacing: '0.05em'
    })

    content.appendChild(title)
    meta.appendChild(typeTag)
    content.appendChild(meta)

    const action = document.createElement('div')
    action.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>'

    card.appendChild(iconBox)
    card.appendChild(content)
    card.appendChild(action)
    container.appendChild(card)

    if (normalizedLinkUrl) {
      const link = document.createElement('div')
      const linkLabel = `[${this.getArtifactLinkLabel(normalizedLinkUrl)}]`
      link.textContent = linkLabel
      link.setAttribute('data-pdf-copy-text', linkLabel)
      Object.assign(link.style, {
        display: 'block',
        width: '100%',
        boxSizing: 'border-box',
        fontSize: '11px',
        lineHeight: '1.5',
        color: '#2563eb',
        textDecoration: 'none',
        wordBreak: 'break-all',
        overflowWrap: 'anywhere',
        whiteSpace: 'normal',
        padding: '0 4px'
      })
      container.appendChild(link)
    }

    return container
  }

  private static createArtifactIconElement(type: string): HTMLElement {
    const normalizedType = type.toLowerCase()
    const image = document.createElement('img')
    image.alt = normalizedType
    Object.assign(image.style, {
      width: '24px',
      height: '24px',
      display: 'block'
    })

    if (normalizedType === 'docx') {
      image.src = WordSvg
      return image
    }
    if (normalizedType === 'pdf') {
      image.src = PdfSvg
      return image
    }
    if (normalizedType === 'text') {
      image.src = TxtSvg
      return image
    }
    if (normalizedType === 'markdown') {
      image.src = MarkdownSvg
      return image
    }
    if (normalizedType === 'csv' || normalizedType === 'xlsx') {
      image.src = ExcelSvg
      return image
    }
    if (normalizedType === 'pptx') {
      image.src = PptSvg
      return image
    }

    const icon = document.createElement('div')
    Object.assign(icon.style, {
      width: '24px',
      height: '24px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: '#64748b'
    })

    if (normalizedType === 'mermaid') {
      icon.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="3" width="6" height="6" rx="1"></rect><rect x="3" y="15" width="6" height="6" rx="1"></rect><rect x="15" y="15" width="6" height="6" rx="1"></rect><path d="M12 9v3"></path><path d="M12 12H6v3"></path><path d="M12 12h6v3"></path></svg>'
      return icon
    }
    if (normalizedType === 'html') {
      icon.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>'
      return icon
    }
    if (normalizedType === 'svg') {
      icon.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="14.31" y1="8" x2="20.05" y2="17.94"></line><line x1="9.69" y1="8" x2="21.17" y2="8"></line><line x1="7.38" y1="12" x2="13.12" y2="2.06"></line><line x1="9.69" y1="16" x2="3.95" y2="6.06"></line><line x1="14.31" y1="16" x2="2.83" y2="16"></line><line x1="16.62" y1="12" x2="10.88" y2="21.94"></line></svg>'
      return icon
    }

    icon.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>'
    return icon
  }

  private static getDocumentArtifactType(fileName: string): string {
    const normalized = fileName.trim().toLowerCase()
    if (normalized.endsWith('.doc') || normalized.endsWith('.docx')) return 'docx'
    if (normalized.endsWith('.pdf')) return 'pdf'
    if (normalized.endsWith('.txt')) return 'text'
    if (normalized.endsWith('.md') || normalized.endsWith('.markdown')) return 'markdown'
    if (normalized.endsWith('.csv') || normalized.endsWith('.xls') || normalized.endsWith('.xlsx')) return 'xlsx'
    if (normalized.endsWith('.ppt') || normalized.endsWith('.pptx')) return 'pptx'
    return 'file'
  }

  private static getArtifactDefaultTitle(type: string): string {
    const normalizedType = type.toLowerCase()
    if (normalizedType === 'docx') return 'Word 文档'
    if (normalizedType === 'pdf') return 'PDF 文档'
    if (normalizedType === 'text') return 'TXT 文档'
    if (normalizedType === 'markdown') return 'Markdown'
    if (normalizedType === 'csv' || normalizedType === 'xlsx') return 'Excel 文档'
    if (normalizedType === 'pptx') return 'PPT 文档'
    if (normalizedType === 'mermaid') return 'Mermaid'
    if (normalizedType === 'html') return 'Web Preview'
    if (normalizedType === 'svg') return 'SVG Image'
    return '文件'
  }

  private static getArtifactDisplayLabel(type: string): string {
    const normalizedType = type.toLowerCase()
    if (normalizedType === 'docx') return 'DOCX'
    if (normalizedType === 'pdf') return 'PDF'
    if (normalizedType === 'text') return 'TEXT'
    if (normalizedType === 'markdown') return 'MARKDOWN'
    if (normalizedType === 'csv') return 'CSV'
    if (normalizedType === 'xlsx') return 'XLSX'
    if (normalizedType === 'pptx') return 'PPTX'
    return normalizedType.toUpperCase()
  }

  private static shouldUseAgentToolCallStyle(message: PdfRenderableMessage): boolean {
    if (message.role !== 'assistant') {
      return false
    }

    if (Array.isArray(message.orchestratorBlocks) && message.orchestratorBlocks.length > 0) {
      return true
    }

    try {
      const activeAgent = StorageService.getActiveAgent()
      const agentType = activeAgent?.basic?.type || activeAgent?.config?.basic?.type
      return agentType === 'orchestrator' || agentType === 'assistant' || agentType === 'deepagent'
    } catch {
      return false
    }
  }

  /**
   * 创建工具调用元素
   */
  private static createToolCallsElement(toolCalls: any[], allMessages?: ChatMessage[], agentMode: boolean = false): HTMLElement {
    if (agentMode) {
      return this.createAgentToolCallsElement(toolCalls, allMessages)
    }

    const container = document.createElement('div')
    Object.assign(container.style, {
      marginTop: '15px',
      marginBottom: '5px',
      borderRadius: '12px',
      overflow: 'hidden',
      background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
      border: '1px solid #e2e8f0',
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)'
    })

    // 工具调用头部
    const header = document.createElement('div')
    Object.assign(header.style, {
      padding: '10px 20px',
      background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
      borderBottom: '1px solid rgba(255, 255, 255, 0.2)',
      position: 'relative',
      overflow: 'hidden'
    })

    const headerTitle = document.createElement('div')
    Object.assign(headerTitle.style, {
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      color: 'white',
      fontWeight: '600',
      fontSize: '14px',
      position: 'relative',
      zIndex: '1'
    })

    const titleText = document.createElement('span')
    titleText.textContent = '工具调用'
    Object.assign(titleText.style, {
      flex: '1',
      fontWeight: '700',
      letterSpacing: '0.5px',
      color: '#ffffff'
    })

    const countBadge = document.createElement('span')
    countBadge.textContent = `${toolCalls.length} 个工具`
    Object.assign(countBadge.style, {
      background: 'rgba(255, 255, 255, 0.25)',
      color: 'white',
      padding: '6px 12px',
      borderRadius: '8px',
      fontSize: '11px',
      fontWeight: '600',
      textAlign: 'center',
      border: '1px solid rgba(255, 255, 255, 0.2)',
      backdropFilter: 'blur(4px)'
    })

    headerTitle.appendChild(titleText)
    headerTitle.appendChild(countBadge)
    header.appendChild(headerTitle)
    container.appendChild(header)

    // 工具调用容器
    const toolsContainer = document.createElement('div')
    toolsContainer.style.padding = '10px'

    // 工具调用内容
    toolCalls.forEach(toolCall => {
      const toolElement = this.createSingleToolCallElement(toolCall, allMessages)
      toolsContainer.appendChild(toolElement)
    })

    container.appendChild(toolsContainer)
    return container
  }

  private static createAgentToolCallsElement(toolCalls: any[], allMessages?: ChatMessage[]): HTMLElement {
    const container = document.createElement('div')
    Object.assign(container.style, {
      marginTop: '15px',
      marginBottom: '10px',
      borderRadius: '12px',
      overflow: 'hidden',
      backgroundColor: '#ffffff',
      border: '1px solid rgba(0, 0, 0, 0.06)',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.03)'
    })

    const header = document.createElement('div')
    Object.assign(header.style, {
      height: '45px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '12px 16px',
      backgroundColor: '#ffffff',
      userSelect: 'none',
      boxSizing: 'border-box'
    })

    const headerLeft = document.createElement('div')
    Object.assign(headerLeft.style, {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      marginTop: '-5px',
      marginBottom: '-5px'
    })

    const iconWrap = document.createElement('span')
    Object.assign(iconWrap.style, {
      color: '#1890ff',
      display: 'flex',
      alignItems: 'center'
    })

    const icon = document.createElement('img')
    icon.src = ToolsSvg
    icon.alt = 'tools'
    Object.assign(icon.style, {
      width: '16px',
      height: '14px',
      display: 'block'
    })
    iconWrap.appendChild(icon)

    const titleText = document.createElement('span')
    titleText.textContent = '工具调用'
    Object.assign(titleText.style, {
      fontSize: '14px',
      fontWeight: '500',
      color: '#383838',
      marginLeft: '1px'
    })

    headerLeft.appendChild(iconWrap)
    headerLeft.appendChild(titleText)

    const headerRight = document.createElement('div')
    Object.assign(headerRight.style, {
      display: 'flex',
      alignItems: 'center'
    })

    const countText = document.createElement('span')
    countText.textContent = `${toolCalls.length} 个工具`
    Object.assign(countText.style, {
      fontSize: '13px',
      color: '#5f5f5f',
      fontVariantNumeric: 'tabular-nums',
      fontWeight: '500',
      marginBottom: '-1px'
    })
    headerRight.appendChild(countText)

    header.appendChild(headerLeft)
    header.appendChild(headerRight)
    container.appendChild(header)

    const toolsContainer = document.createElement('div')
    toolsContainer.style.padding = '5px 10px 10px'

    toolCalls.forEach(toolCall => {
      const toolElement = this.createSingleToolCallElement(toolCall, allMessages)
      toolsContainer.appendChild(toolElement)
    })

    container.appendChild(toolsContainer)
    return container
  }

  /**
   * 创建单个工具调用元素
   */
  private static createSingleToolCallElement(toolCall: any, allMessages?: ChatMessage[]): HTMLElement {
    const container = document.createElement('div')
    Object.assign(container.style, {
      background: 'white',
      borderRadius: '10px',
      marginBottom: '8px',
      border: '1px solid #e2e8f0',
      overflow: 'hidden'
    })

    // 工具调用头部
    const header = document.createElement('div')
    Object.assign(header.style, {
      padding: '12px 20px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)',
      position: 'relative',
      overflow: 'hidden'
    })

    // 工具信息容器
    const infoContainer = document.createElement('div')
    Object.assign(infoContainer.style, {
      flex: '1',
      display: 'flex',
      flexDirection: 'column',
      gap: '4px'
    })

    // 工具名称行
    const nameRow = document.createElement('div')
    Object.assign(nameRow.style, {
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
      flexWrap: 'wrap'
    })

    const toolName = document.createElement('span')
    toolName.textContent = toolCall.function.name
    Object.assign(toolName.style, {
      fontWeight: '600',
      color: '#1e293b',
      fontSize: '14px',
      fontFamily: '"SF Mono", "Monaco", "Inconsolata", "Roboto Mono", monospace'
    })

    const typeBadge = document.createElement('span')
    typeBadge.textContent = (toolCall.type || 'function').toUpperCase()
    Object.assign(typeBadge.style, {
      background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
      color: 'white',
      padding: '2px 8px',
      borderRadius: '6px',
      fontSize: '11px',
      fontWeight: '500',
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
      boxShadow: '0 1px 3px rgba(59, 130, 246, 0.3)'
    })

    nameRow.appendChild(toolName)
    nameRow.appendChild(typeBadge)

    // 元数据行
    const metaRow = document.createElement('div')
    Object.assign(metaRow.style, {
      display: 'flex',
      flexDirection: 'column',
      gap: '4px'
    })

    const toolId = document.createElement('div')
    toolId.textContent = `ID: ${toolCall.id}`
    Object.assign(toolId.style, {
      fontSize: '12px',
      color: '#64748b',
      fontFamily: '"SF Mono", "Monaco", "Inconsolata", "Roboto Mono", monospace'
    })

    // 服务信息、状态和耗时信息（在同一行显示）
    const infoRow = document.createElement('div')
    Object.assign(infoRow.style, {
      display: 'flex',
      flexWrap: 'wrap',
      alignItems: 'center',
      gap: '12px',
      fontSize: '11px',
      marginTop: '4px'
    })

    // 服务名称
    const serverName = this.getServerDisplayName(toolCall)
    if (serverName) {
      const serverLabel = document.createElement('span')
      serverLabel.textContent = '服务:'
      Object.assign(serverLabel.style, {
        color: '#94a3b8',
        fontWeight: '500',
        fontSize: '12px'
      })
      
      const serverTag = document.createElement('span')
      serverTag.textContent = serverName
      Object.assign(serverTag.style, {
        background: 'linear-gradient(135deg, #e0f2fe 0%, #b3e5fc 100%)',
        color: '#0277bd',
        padding: '2px 6px',
        borderRadius: '4px',
        fontWeight: '500',
        fontSize: '11px',
        border: '1px solid #81d4fa'
      })
      
      infoRow.appendChild(serverLabel)
      infoRow.appendChild(serverTag)
    }

    // URL信息
    if (toolCall.server_url) {
      const urlLabel = document.createElement('span')
      urlLabel.textContent = 'URL:'
      Object.assign(urlLabel.style, {
        color: '#94a3b8',
        fontWeight: '500',
        fontSize: '12px'
      })
      
      const urlTag = document.createElement('span')
      urlTag.textContent = toolCall.server_url
      Object.assign(urlTag.style, {
        background: 'linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 100%)',
        color: '#7c3aed',
        padding: '2px 6px',
        borderRadius: '4px',
        fontWeight: '500',
        fontSize: '11px',
        border: '1px solid #c4b5fd',
        fontFamily: '"SF Mono", "Monaco", "Inconsolata", "Roboto Mono", monospace',
        maxWidth: '200px',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        cursor: 'help'
      })
      
      infoRow.appendChild(urlLabel)
      infoRow.appendChild(urlTag)
    }

    // 状态信息
    const status = toolCall.status || 'completed'
    const statusLabel = document.createElement('span')
    statusLabel.textContent = '状态:'
    Object.assign(statusLabel.style, {
      color: '#94a3b8',
      fontWeight: '500',
      fontSize: '12px'
    })
    
    const statusTag = document.createElement('span')
    statusTag.textContent = this.getStatusText(status)
    Object.assign(statusTag.style, {
      background: this.getStatusBackground(status),
      color: this.getStatusColor(status),
      padding: '2px 6px',
      borderRadius: '4px',
      fontWeight: '500',
      fontSize: '11px',
      border: `1px solid ${this.getStatusBorderColor(status)}`
    })
    
    infoRow.appendChild(statusLabel)
    infoRow.appendChild(statusTag)

    if (toolCall.duration !== undefined) {
      const durationLabel = document.createElement('span')
      durationLabel.textContent = '耗时:'
      Object.assign(durationLabel.style, {
        color: '#94a3b8',
        fontWeight: '500',
        fontSize: '12px'
      })
      
      const durationTag = document.createElement('span')
      durationTag.textContent = this.formatDuration(toolCall.duration)
      Object.assign(durationTag.style, {
        background: 'linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%)',
        color: '#0e8a67',
        padding: '2px 6px',
        borderRadius: '4px',
        fontWeight: '500',
        fontSize: '11px',
        border: '1px solid #10b981',
        fontFamily: '"SF Mono", "Monaco", "Inconsolata", "Roboto Mono", monospace'
      })
      
      infoRow.appendChild(durationLabel)
      infoRow.appendChild(durationTag)
    }

    metaRow.appendChild(toolId)
    metaRow.appendChild(infoRow)
    infoContainer.appendChild(nameRow)
    infoContainer.appendChild(metaRow)
    header.appendChild(infoContainer)
    container.appendChild(header)

    // 参数部分
    const argsWrapper = document.createElement('div')
    argsWrapper.style.padding = '20px'

    const argsHeader = document.createElement('div')
    Object.assign(argsHeader.style, {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: '12px'
    })

    const argsTitle = document.createElement('span')
    argsTitle.textContent = '参数'
    Object.assign(argsTitle.style, {
      fontSize: '13px',
      fontWeight: '600',
      color: '#475569',
      textTransform: 'uppercase',
      letterSpacing: '0.5px'
    })

    argsHeader.appendChild(argsTitle)
    argsWrapper.appendChild(argsHeader)

    // 参数内容
    const argsContainer = document.createElement('pre')
    Object.assign(argsContainer.style, {
      background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
      border: '1px solid #e2e8f0',
      borderRadius: '8px',
      padding: '16px',
      margin: '0',
      fontSize: '13px',
      fontFamily: '"SF Mono", "Monaco", "Inconsolata", "Roboto Mono", monospace',
      whiteSpace: 'pre-wrap',
      color: '#374151',
      lineHeight: '1.6',
      overflowX: 'auto'
    })

    try {
      const args = JSON.parse(toolCall.function.arguments)
      argsContainer.textContent = JSON.stringify(args, null, 2)
    } catch (e) {
      argsContainer.textContent = toolCall.function.arguments
    }

    argsWrapper.appendChild(argsContainer)
    container.appendChild(argsWrapper)

    // 工具结果部分
    if (allMessages) {
      const toolResult = this.getToolResult(toolCall.id, allMessages)
      if (toolResult) {
        const resultWrapper = document.createElement('div')
        resultWrapper.style.padding = '8px 20px 20px 20px'

        const resultHeader = document.createElement('div')
        Object.assign(resultHeader.style, {
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '12px'
        })

        const resultTitle = document.createElement('span')
        resultTitle.textContent = '调用结果'
        Object.assign(resultTitle.style, {
          fontSize: '13px',
          fontWeight: '600',
          color: '#475569',
          textTransform: 'uppercase',
          letterSpacing: '0.5px'
        })

        resultHeader.appendChild(resultTitle)
        resultWrapper.appendChild(resultHeader)

        // 结果内容
        const resultContainer = document.createElement('pre')
        Object.assign(resultContainer.style, {
          background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
          border: '1px solid #e2e8f0',
          borderRadius: '8px',
          padding: '16px',
          margin: '0',
          fontSize: '13px',
          fontFamily: '"SF Mono", "Monaco", "Inconsolata", "Roboto Mono", monospace',
          whiteSpace: 'pre-wrap',
          color: '#374151',
          lineHeight: '1.6',
          overflowX: 'auto'
        })

        resultContainer.textContent = toolResult
        resultWrapper.appendChild(resultContainer)
        container.appendChild(resultWrapper)
      }
    }
    
    return container
  }

  /**
   * 获取工具调用结果
   */
  private static getToolResult(toolCallId: string, allMessages: ChatMessage[]): string | null {
    // 在所有消息中查找对应的Tool类型消息
    const toolMessage = allMessages.find(
      msg => msg.role === 'tool' && msg.tool_call_id === toolCallId
    )
    return toolMessage?.content || null
  }

  /**
   * 获取状态文本
   */
  private static getStatusText(status: string): string {
    const statusMap: Record<string, string> = {
      'pending': '等待中',
      'executing': '执行中',
      'completed': '已完成',
      'failed': '失败',
      'cancelled': '已取消'
    }
    return statusMap[status] || status
  }

  /**
   * 获取状态颜色
   */
  private static getStatusColor(status: string): string {
    const colorMap: Record<string, string> = {
      'pending': '#f59e0b',
      'executing': '#3b82f6',
      'completed': '#059669',
      'failed': '#dc2626',
      'cancelled': '#6b7280'
    }
    return colorMap[status] || '#6b7280'
  }

  /**
   * 获取状态背景颜色
   */
  private static getStatusBackground(status: string): string {
    const backgroundMap: Record<string, string> = {
      'pending': 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
      'executing': 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)',
      'completed': 'linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%)',
      'failed': 'linear-gradient(135deg, #fecaca 0%, #fca5a5 100%)',
      'cancelled': 'linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%)'
    }
    return backgroundMap[status] || 'linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%)'
  }

  /**
   * 获取状态边框颜色
   */
  private static getStatusBorderColor(status: string): string {
    const borderMap: Record<string, string> = {
      'pending': '#fbbf24',
      'executing': '#60a5fa',
      'completed': '#34d399',
      'failed': '#f87171',
      'cancelled': '#9ca3af'
    }
    return borderMap[status] || '#9ca3af'
  }

  /**
   * 获取服务显示名称
   */
  private static getServerDisplayName(toolCall: any): string | null {
    if (!toolCall.server_id) {
      return null
    }
    
    try {
      // 从本地存储获取服务器数据
      const serverDataStr = localStorage.getItem('mcp-servers-data')
      if (serverDataStr) {
        const serverDataMap = JSON.parse(serverDataStr)
        
        // 通过server_url查找对应的服务器名称
        if (toolCall.server_url) {
          for (const [serverName, serverData] of Object.entries(serverDataMap)) {
            if ((serverData as any).url === toolCall.server_url) {
              return (serverData as any).name || serverName
            }
          }
        }
      }
    } catch (e) {
      console.warn('获取服务器显示名称失败:', e)
    }
    
    // 如果找不到，返回server_id
    return toolCall.server_id
  }

  /**
   * 格式化持续时间
   */
  private static formatDuration(duration: number): string {
    if (duration < 1000) {
      return `${duration}ms`
    } else if (duration < 60000) {
      return `${(duration / 1000).toFixed(1)}s`
    } else {
      const minutes = Math.floor(duration / 60000)
      const seconds = Math.floor((duration % 60000) / 1000)
      return `${minutes}m ${seconds}s`
    }
  }

  /**
   * 等待容器内图片加载完成，避免预览分页和导出截图丢图
   */
  static async waitForImages(container: HTMLElement): Promise<void> {
    const images = Array.from(container.querySelectorAll('img')) as HTMLImageElement[]
    if (images.length === 0) {
      return
    }

    await Promise.all(images.map(image => new Promise<void>((resolve) => {
      if (image.complete) {
        resolve()
        return
      }

      const done = () => resolve()
      image.addEventListener('load', done, { once: true })
      image.addEventListener('error', done, { once: true })
    })))
  }

  /**
   * 应用Markdown样式
   */
  private static applyMarkdownStyles(element: HTMLElement): void {
    // 段落样式
    const paragraphs = element.querySelectorAll('p')
    paragraphs.forEach(p => {
      Object.assign((p as HTMLElement).style, {
        marginTop: '0.08em', // 行369: 从0.05em改为0.08em
        marginBottom: '0.12em', // 行370: 从0.1em改为0.12em
        padding: '0',
        lineHeight: '1.6', // 行372: 从1.5改为1.55
        fontSize: '13px',
        letterSpacing: '0.01em'
      })
    })

    // 标题样式
    const headings = element.querySelectorAll('h1, h2, h3, h4, h5, h6')
    headings.forEach(heading => {
      const h = heading as HTMLElement
      Object.assign(h.style, {
        marginTop: '0.9em', // 行382: 从0.8em改为0.9em
        marginBottom: '0.45em', // 行383: 从0.4em改为0.45em
        fontWeight: '600',
        lineHeight: '1.3', // 行385: 从1.2改为1.22
        color: '#222'
      })

      if (heading.tagName === 'H1') {
        h.style.fontSize = '1.75em' // 行389: 从1.7em改为1.75em
        h.style.borderBottom = '1px solid #eaecef'
        h.style.paddingBottom = '0.25em' // 行391: 从0.2em改为0.25em
      } else if (heading.tagName === 'H2') {
        h.style.fontSize = '1.45em' // 行393: 从1.4em改为1.45em
        h.style.borderBottom = '1px solid #eaecef'
        h.style.paddingBottom = '0.25em' // 行395: 从0.2em改为0.25em
      } else if (heading.tagName === 'H3') {
        h.style.fontSize = '1.22em' // 行397: 从1.2em改为1.22em
      }
    })

    // 代码块样式
    this.applyCodeBlockStyles(element)
    
    // KaTeX数学公式样式
    this.applyKatexStyles(element)
    
    // 其他元素样式
    this.applyOtherElementStyles(element)
  }

  /**
   * 应用代码块样式
   */
  private static applyCodeBlockStyles(element: HTMLElement): void {
    const preBlocks = element.querySelectorAll('pre')
    preBlocks.forEach(block => {
      const el = block as HTMLElement
      Object.assign(el.style, {
        backgroundColor: '#f7f9fc',
        borderRadius: '8px',
        fontSize: '0.9rem',
        lineHeight: '1.5',
        overflow: 'auto',
        padding: '16px',
        margin: '16px 0',
        border: 'none',
        fontFamily: '"Roboto Mono", "Menlo", "Monaco", "Consolas", "Courier New", monospace',
        color: '#333',
        whiteSpace: 'pre',
        display: 'block',
        width: '100%',
        boxSizing: 'border-box',
        WebkitFontSmoothing: 'antialiased',
        MozOsxFontSmoothing: 'grayscale',
        textRendering: 'optimizeLegibility',
        fontVariantLigatures: 'none',
        fontFeatureSettings: '"liga" 0',
        fontKerning: 'none',
        letterSpacing: '0',
        wordSpacing: '0'
      })
    })

    const inlineCodes = element.querySelectorAll('code.inline-code')
    inlineCodes.forEach(code => {
      const el = code as HTMLElement
      Object.assign(el.style, {
        backgroundColor: 'rgba(27, 31, 35, 0.05)',
        borderRadius: '6px',
        fontSize: '0.9em',
        margin: '0',
        padding: '0.15em 0.4em',
        fontFamily: '"Roboto Mono", "Menlo", "Monaco", "Consolas", "Courier New", monospace',
        display: 'inline-block',
        whiteSpace: 'nowrap',
        wordBreak: 'normal',
        overflowWrap: 'normal',
        color: 'inherit',
        verticalAlign: 'baseline',
        lineHeight: '1.3'
      })
    })

    const blockCodes = element.querySelectorAll('pre > code, .code-pre > code, .chat-hljs')
    blockCodes.forEach(code => {
      const el = code as HTMLElement
      Object.assign(el.style, {
        backgroundColor: 'transparent',
        borderRadius: '0',
        fontSize: '14px',
        margin: '0',
        padding: '0',
        lineHeight: '1.6',
        fontFamily: '"Roboto Mono", "Menlo", "Monaco", "Consolas", "Courier New", monospace',
        display: 'block',
        color: '#333',
        whiteSpace: 'pre',
        wordBreak: 'normal',
        overflowWrap: 'normal'
      })
    })

    // 代码块包装器样式
    const wrappers = element.querySelectorAll('.code-block-wrapper')
    wrappers.forEach(wrapper => {
      const w = wrapper as HTMLElement
      Object.assign(w.style, {
        position: 'relative',
        margin: '16px 0', // 匹配对话历史中的外边距
        borderRadius: '10px',
        border: '1px solid rgba(200, 220, 240, 0.4)', // 淡蓝色描边替代阴影
        overflow: 'hidden',
        width: '100%',
        boxSizing: 'border-box',
        transition: 'all 0.3s ease' // 匹配对话历史中的过渡效果
      })

      // 处理代码块头部
      const header = wrapper.querySelector('.code-block-header')
      if (header) {
        const h = header as HTMLElement
        Object.assign(h.style, {
          display: 'flex !important',
          justifyContent: 'space-between !important',
          alignItems: 'center !important',
          background: '#f0f5fa !important', // 确保头部背景色显示
          padding: '10px 20px !important', // 匹配对话历史中的内边距
          borderTopLeftRadius: '10px !important',
          borderTopRightRadius: '10px !important',
          fontSize: '14px !important', // 匹配对话历史中的字体大小
          color: '#333 !important',
          border: 'none !important',
          borderBottom: '1px solid rgba(200, 220, 240, 0.4) !important', // 匹配对话历史中的边框
          fontFamily: '"Roboto Mono", monospace !important',
          fontWeight: '500 !important'
        })

        // 移除复制按钮
        const copyButton = h.querySelector('.code-copy-button')
        if (copyButton) {
          copyButton.remove()
        }
      }

      // 处理代码预格式化元素
      const codePre = wrapper.querySelector('.code-pre')
      if (codePre) {
        const pre = codePre as HTMLElement
        Object.assign(pre.style, {
          marginTop: '0 !important',
          borderTopLeftRadius: '0 !important',
          borderTopRightRadius: '0 !important',
          backgroundColor: '#f7f9fc !important', // 确保淡蓝色背景显示
          border: 'none !important',
          borderTop: 'none',
          overflowX: 'auto',
          whiteSpace: 'pre',
          width: '100%',
          boxSizing: 'border-box',
          padding: '16px !important' // 匹配对话历史中的内边距
        })
      }
    })

    // 应用代码高亮颜色样式，匹配对话历史
    const hljs = element.querySelectorAll('.chat-hljs, .hljs')
    hljs.forEach(codeElement => {
      const el = codeElement as HTMLElement
      
      // 字符串颜色
      const strings = el.querySelectorAll('.hljs-string')
      strings.forEach(str => {
        (str as HTMLElement).style.color = '#0d904f'
      })
      
      // 关键字颜色
      const keywords = el.querySelectorAll('.hljs-keyword')
      keywords.forEach(keyword => {
        (keyword as HTMLElement).style.color = '#7928a1'
      })
      
      // 标题和函数颜色
      const titles = el.querySelectorAll('.hljs-title, .function_')
      titles.forEach(title => {
        (title as HTMLElement).style.color = '#1a56db'
      })
      
      // 内置函数颜色
      const builtins = el.querySelectorAll('.hljs-built_in')
      builtins.forEach(builtin => {
        (builtin as HTMLElement).style.color = '#ca471e'
      })
      
      // 数字颜色
      const numbers = el.querySelectorAll('.hljs-number')
      numbers.forEach(number => {
        (number as HTMLElement).style.color = '#986801'
      })
      
      // 注释颜色
      const comments = el.querySelectorAll('.hljs-comment')
      comments.forEach(comment => {
        const commentEl = comment as HTMLElement
        commentEl.style.color = '#767c77'
        commentEl.style.fontStyle = 'italic'
      })
      
      // 元数据颜色
      const metas = el.querySelectorAll('.hljs-meta')
      metas.forEach(meta => {
        (meta as HTMLElement).style.color = '#ca471e'
      })
      
      // 类型颜色
      const types = el.querySelectorAll('.hljs-type')
      types.forEach(type => {
        (type as HTMLElement).style.color = '#7928a1'
      })
    })
  }

  /**
   * 应用KaTeX数学公式样式
   */
  private static applyKatexStyles(element: HTMLElement): void {
    // KaTeX 数学公式基础样式
    const katexElements = element.querySelectorAll('.katex')
    katexElements.forEach(katex => {
      Object.assign((katex as HTMLElement).style, {
        fontSize: '1.1em',
        lineHeight: 'normal',
        display: 'inline-block',
        verticalAlign: '-0.25em',
        margin: '0',
        padding: '0'
      })
    })

    // KaTeX 显示模式样式
    const katexDisplays = element.querySelectorAll('.katex-display')
    katexDisplays.forEach(display => {
      Object.assign((display as HTMLElement).style, {
        display: 'block',
        textAlign: 'center',
        margin: '1em 0',
        padding: '0.5em 0',
        overflowX: 'auto',
        overflowY: 'hidden'
      })
    })

    // KaTeX 显示模式内部样式
    const katexDisplayInner = element.querySelectorAll('.katex-display > .katex')
    katexDisplayInner.forEach(inner => {
      Object.assign((inner as HTMLElement).style, {
        display: 'inline-block',
        textAlign: 'center',
        whiteSpace: 'nowrap'
      })
    })

    // 基础元素样式
    const baseElements = element.querySelectorAll('.katex .base')
    baseElements.forEach(base => {
      Object.assign((base as HTMLElement).style, {
        display: 'inline-block',
        verticalAlign: 'baseline',
        minHeight: '1em',
        overflow: 'visible'
      })
    })

    // 支撑元素样式
    const strutElements = element.querySelectorAll('.katex .strut')
    strutElements.forEach(strut => {
      Object.assign((strut as HTMLElement).style, {
        display: 'inline-block',
        minHeight: '1em',
        height: 'auto',
        overflow: 'visible'
      })
    })

    // 数学符号样式
    const mathElements = element.querySelectorAll('.katex .mord, .katex .mop, .katex .mbin, .katex .mrel, .katex .mopen, .katex .mclose, .katex .mpunct')
    mathElements.forEach(mathEl => {
      Object.assign((mathEl as HTMLElement).style, {
        display: 'inline',
        verticalAlign: 'baseline'
      })
    })

    // 垂直列表样式
    const vlistElements = element.querySelectorAll('.katex .vlist-t')
    vlistElements.forEach(vlist => {
      Object.assign((vlist as HTMLElement).style, {
        display: 'inline-table',
        tableLayout: 'fixed',
        borderCollapse: 'collapse'
      })
    })

    const vlistRows = element.querySelectorAll('.katex .vlist-r')
    vlistRows.forEach(row => {
      Object.assign((row as HTMLElement).style, {
        display: 'table-row'
      })
    })

    const vlists = element.querySelectorAll('.katex .vlist')
    vlists.forEach(vlist => {
      Object.assign((vlist as HTMLElement).style, {
        display: 'table-cell',
        verticalAlign: 'baseline',
        position: 'relative',
        minHeight: '1em'
      })
    })

    // 分数线样式
    const fracLines = element.querySelectorAll('.katex .frac-line')
    fracLines.forEach(line => {
      Object.assign((line as HTMLElement).style, {
        borderBottomWidth: '0.04em',
        borderBottomStyle: 'solid',
        margin: '0.15em 0'
      })
    })

    // 分数分子分母样式
    const mfracSpans = element.querySelectorAll('.katex .mfrac > span')
    mfracSpans.forEach(span => {
      Object.assign((span as HTMLElement).style, {
        margin: '0.1em 0',
        padding: '0.05em 0'
      })
    })

    // 上标下标中的分数样式 - 简化版本
    const msubsupMfracs = element.querySelectorAll('.katex .msupsub .mfrac')
    msubsupMfracs.forEach(mfrac => {
      Object.assign((mfrac as HTMLElement).style, {
        fontSize: '0.8em',
        lineHeight: '1.6'
      })
    })

    // 上标下标中的分数线样式
    const msubsupFracLines = element.querySelectorAll('.katex .msupsub .frac-line')
    msubsupFracLines.forEach(line => {
      Object.assign((line as HTMLElement).style, {
        margin: '0.1em 0'
      })
    })

    // 上标下标中的分数分子分母样式
    const msubsupMfracSpans = element.querySelectorAll('.katex .msupsub .mfrac > span')
    msubsupMfracSpans.forEach(span => {
      Object.assign((span as HTMLElement).style, {
        margin: '0.08em 0',
        padding: '0.05em 0'
      })
    })

    // 上标下标容器样式 - 简化版本
    const msupsubs = element.querySelectorAll('.katex .msupsub')
    msupsubs.forEach(msupsub => {
      Object.assign((msupsub as HTMLElement).style, {
        lineHeight: '2.2',
        verticalAlign: 'baseline',
        display: 'inline-block'
      })
    })

    // 包含数学公式的段落样式 - 简化版本
    const parasWithKatex = element.querySelectorAll('p:has(.katex)')
    parasWithKatex.forEach(p => {
      Object.assign((p as HTMLElement).style, {
        lineHeight: '1.8'
      })
    })
  }

  /**
   * 应用其他元素样式
   */
  private static applyOtherElementStyles(element: HTMLElement): void {
    // 图片样式 - 与对话页面markdown.css保持一致
    const images = element.querySelectorAll('img')
    images.forEach(img => {
      Object.assign((img as HTMLElement).style, {
        maxWidth: '80%',
        maxHeight: '450px',
        margin: '15px auto',
        display: 'block',
        borderRadius: '12px',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
        transition: 'all 0.35s ease'
      })

      // 设置CORS属性
      if (img.src && !img.src.startsWith('data:')) {
        img.crossOrigin = 'anonymous'
      }
    })

    // 链接样式
    const links = element.querySelectorAll('a')
    links.forEach(link => {
      Object.assign((link as HTMLElement).style, {
        color: '#1890ff',
        textDecoration: 'none'
      })
    })

    // 引用块样式
    const blockquotes = element.querySelectorAll('blockquote')
    blockquotes.forEach(blockquote => {
      Object.assign((blockquote as HTMLElement).style, {
        borderLeft: '4px solid #1890ff',
        color: '#666',
        margin: '0.9em 0', // 行535: 从0.8em改为0.9em
        padding: '0.1em 0 0.1em 0.9em', // 行536: 从0.8em改为0.9em
        backgroundColor: '#f0f8ff',
        borderRadius: '0 4px 4px 0'
      })
    })

    // 列表样式
    const lists = element.querySelectorAll('ul, ol')
    lists.forEach(list => {
      Object.assign((list as HTMLElement).style, {
        paddingLeft: '1.9em', // 行547: 从1.8em改为1.9em
        margin: '0.45em 0' // 行548: 从0.4em改为0.45em
      })
    })

    // 表格样式 - 与对话页面markdown.css保持一致
    const tables = element.querySelectorAll('table')
    tables.forEach(table => {
      Object.assign((table as HTMLElement).style, {
        borderCollapse: 'separate',
        borderSpacing: '0',
        margin: '1.2em 0',
        overflow: 'hidden',
        width: '100%',
        borderRadius: '8px',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)',
        border: '1px solid #eaeaea',
        fontSize: '14px',
        lineHeight: '1.6'
      })

      const cells = table.querySelectorAll('th, td')
      cells.forEach((cell, index) => {
        const cellElement = cell as HTMLElement
        Object.assign(cellElement.style, {
          border: 'none',
          borderBottom: '1px solid #eaeaea',
          borderRight: '1px solid #eaeaea',
          padding: '12px 16px',
          textAlign: 'left',
          verticalAlign: 'middle'
        })
        
        // 最后一列不显示右边框
        const parentRow = cellElement.parentElement
        if (parentRow) {
          const cellsInRow = parentRow.querySelectorAll('th, td')
          if (index === cellsInRow.length - 1 || cellElement === cellsInRow[cellsInRow.length - 1]) {
            cellElement.style.borderRight = 'none'
          }
        }
      })

      const headers = table.querySelectorAll('th')
      headers.forEach((header, index) => {
        const headerElement = header as HTMLElement
        Object.assign(headerElement.style, {
          backgroundColor: '#f8f9fa',
          fontWeight: '600',
          color: '#444',
          borderBottom: '2px solid #ddd'
        })
        
        // 处理圆角
        const headerRow = headerElement.parentElement
        if (headerRow) {
          const headersInRow = headerRow.querySelectorAll('th')
          if (index === 0) {
            headerElement.style.borderTopLeftRadius = '8px'
          }
          if (index === headersInRow.length - 1) {
            headerElement.style.borderTopRightRadius = '8px'
          }
        }
      })
      
      // 处理最后一行的圆角
      const rows = table.querySelectorAll('tr')
      const lastRow = rows[rows.length - 1]
      if (lastRow) {
        const lastRowCells = lastRow.querySelectorAll('td')
        lastRowCells.forEach((cell, index) => {
          const cellElement = cell as HTMLElement
          cellElement.style.borderBottom = 'none'
          if (index === 0) {
            cellElement.style.borderBottomLeftRadius = '8px'
          }
          if (index === lastRowCells.length - 1) {
            cellElement.style.borderBottomRightRadius = '8px'
          }
        })
      }
      
      // 添加行的背景色交替效果
      const dataRows = table.querySelectorAll('tr')
      dataRows.forEach((row, index) => {
        const rowElement = row as HTMLElement
        if (index === 0) {
          // 表头行保持原样
          return
        }
        
        if (index % 2 === 0) {
          rowElement.style.backgroundColor = '#f8f9fa'
        } else {
          rowElement.style.backgroundColor = '#fff'
        }
        rowElement.style.transition = 'background-color 0.2s'
      })
    })
  }
}
