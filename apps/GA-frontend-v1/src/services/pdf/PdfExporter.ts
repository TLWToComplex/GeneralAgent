import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'
import type {ExportProgress, MarkdownExportOptions, PdfExportOptions, TextExportOptions} from './types'
import type {ChatMessage} from '@/types'
import type {Message} from '@/types/mcp'
import {EXPORT_STAGES, PAPER_SIZES, QUALITY_CONFIG} from './constants'
import PdfRenderer from './PdfRenderer'
import PdfPreviewGenerator from './PdfPreviewGenerator'
import {useChatStore} from '@/stores/chat-store'
import {getImagePreviewUrl, isImageFile} from '@/utils/conversationImages'
import logoPng from '@/assets/ga-logo.svg'

type ExportableChatMessage = ChatMessage & Pick<Partial<Message>, 'display_content' | 'files'>

/**
 * PDF导出核心服务类
 * 负责处理各种格式的导出功能
 */
export default class PdfExporter {
    private static progressCallback?: (progress: ExportProgress) => void
    private static selectedMessages: ChatMessage[] | null = null

    /**
     * 设置进度回调函数
     */
    static setProgressCallback(callback: (progress: ExportProgress) => void) {
        this.progressCallback = callback
    }

    /**
     * 设置选中的消息（用于选择模式导出）
     */
    static setSelectedMessages(messages: ChatMessage[]) {
        this.selectedMessages = messages
    }

    /**
     * 清除选中的消息
     */
    static clearSelectedMessages() {
        this.selectedMessages = null
    }

    /**
     * 更新导出进度
     */
    private static updateProgress(stage: string, percent: number) {
        if (this.progressCallback) {
            this.progressCallback({stage, percent})
        }
    }

    /**
     * 导出PDF格式
     */
    static async exportPdf(options: PdfExportOptions, filename: string): Promise<void> {
        let exportContainer: HTMLElement | null = null
        let pagesContainer: HTMLElement | null = null

        try {
            this.updateProgress(EXPORT_STAGES.PREPARING, 5)

            const messages = this.getMessages()
            if (messages.length === 0) {
                throw new Error('没有找到对话内容')
            }

            this.updateProgress('解析对话内容...', 15)

            // 获取完整消息列表（用于查找工具调用结果）
            const chatStore = useChatStore()
            const allMessages = (chatStore.messages || []).map((msg, index) => ({
                ...msg,
                id: `msg-${index}-${Date.now()}`,
                timestamp: Date.now()
            }));

            // 创建导出容器
            this.updateProgress(EXPORT_STAGES.GENERATING_CONTENT, 25)
            exportContainer = PdfRenderer.createExportContainer(
                messages,
                options.includeThinking,
                options.includeSystemMessages,
                this.selectedMessages ? allMessages : undefined,
                options.includeToolCalls !== false
            )
            
            // 同步助手头像到导出容器（图标优先，首字母回退）
            const filteredMessages = messages.filter(m => m.role !== 'tool' && (options.includeSystemMessages ? true : m.role !== 'system'))
            applyAssistantAvatars(exportContainer, filteredMessages)
            await this.inlineAgentAvatarImages(exportContainer)
            this.updateProgress('构建页面结构...', 40)
            // 添加到DOM并等待渲染
            document.body.appendChild(exportContainer)
            await this.waitForFrame()
            await PdfRenderer.waitForImages(exportContainer)
            await this.waitForFonts()

            this.updateProgress(EXPORT_STAGES.RENDERING_PAGE, 55)
            pagesContainer = PdfPreviewGenerator.createPagesContainerFromExportContainer(
                exportContainer,
                {
                    paperSize: options.paperSize,
                    scale: options.scale,
                    copyrightPosition: options.copyrightPosition || 'page-bottom'
                },
                false
            )
            Object.assign(pagesContainer.style, {
                position: 'absolute',
                left: '-9999px',
                top: '0',
                width: 'fit-content',
                pointerEvents: 'none'
            })
            document.body.appendChild(pagesContainer)
            await this.waitForFrame()

            // 生成PDF
            this.updateProgress('计算页面布局...', 65)

            this.updateProgress('生成PDF文档...', 75)
            const pageElements = Array.from(pagesContainer.children)
                .filter((element): element is HTMLElement => element instanceof HTMLElement)

            if (pageElements.length === 0) {
                throw new Error('未生成可导出的PDF页面')
            }

            await this.generatePdf(pageElements, options, filename)

            this.updateProgress('保存文件...', 95)

            this.updateProgress(EXPORT_STAGES.COMPLETED, 100)

        } catch (error) {
            this.updateProgress(EXPORT_STAGES.FAILED, 100)
            throw error
        } finally {
            if (pagesContainer?.parentNode) {
                pagesContainer.parentNode.removeChild(pagesContainer)
            }
            if (exportContainer?.parentNode) {
                exportContainer.parentNode.removeChild(exportContainer)
            }
        }
    }

    /**
     * 导出纯文本格式
     */
    static async exportText(options: TextExportOptions, filename: string): Promise<void> {
        try {
            this.updateProgress(EXPORT_STAGES.PREPARING, 10)

            const messages = this.getMessages()
            if (messages.length === 0) {
                throw new Error('没有找到对话内容')
            }

            this.updateProgress('解析对话内容...', 25)

            this.updateProgress(EXPORT_STAGES.PROCESSING_CONTENT, 40)

            // 获取完整消息列表（当存在选中消息时）
            let allMessages: ChatMessage[] | undefined
            if (this.selectedMessages && this.selectedMessages.length > 0) {
                const {useChatStore} = await import('../../stores/chat-store')
                const chatStore = useChatStore()
                allMessages = chatStore.messages.map(msg => ({
                    ...msg,
                    id: (msg as any).id || `${(msg as any).timestamp || Date.now()}-${Math.random()}`,
                    timestamp: (msg as any).timestamp || Date.now()
                } as ChatMessage))
            }

            const content = this.buildTextContent(messages, options, allMessages)

            this.updateProgress('格式化文本内容...', 65)

            this.updateProgress('生成文本文件...', 80)

            const blob = new Blob([content], {type: 'text/plain;charset=utf-8'})

            this.updateProgress('保存文件...', 95)

            this.downloadFile(blob, filename)

            this.updateProgress(EXPORT_STAGES.COMPLETED, 100)

        } catch (error) {
            this.updateProgress(EXPORT_STAGES.FAILED, 100)
            throw error
        }
    }

    /**
     * 导出Markdown格式
     */
    static async exportMarkdown(options: MarkdownExportOptions, filename: string): Promise<void> {
        try {
            this.updateProgress(EXPORT_STAGES.PREPARING, 10)

            const messages = this.getMessages()
            if (messages.length === 0) {
                throw new Error('没有找到对话内容')
            }

            this.updateProgress('解析对话内容...', 25)

            this.updateProgress(EXPORT_STAGES.PROCESSING_CONTENT, 40)

            // 获取完整消息列表（当存在选中消息时）
            let allMessages: ChatMessage[] | undefined
            if (this.selectedMessages && this.selectedMessages.length > 0) {
                const {useChatStore} = await import('../../stores/chat-store')
                const chatStore = useChatStore()
                allMessages = chatStore.messages.map(msg => ({
                    ...msg,
                    id: (msg as any).id || `${(msg as any).timestamp || Date.now()}-${Math.random()}`,
                    timestamp: (msg as any).timestamp || Date.now()
                } as ChatMessage))
            }

            const content = this.buildMarkdownContent(messages, options, allMessages)

            this.updateProgress('格式化Markdown内容...', 65)

            this.updateProgress('生成Markdown文件...', 80)

            const blob = new Blob([content], {type: 'text/markdown;charset=utf-8'})

            this.updateProgress('保存文件...', 95)

            this.downloadFile(blob, filename)

            this.updateProgress(EXPORT_STAGES.COMPLETED, 100)

        } catch (error) {
            this.updateProgress(EXPORT_STAGES.FAILED, 100)
            throw error
        }
    }

    /**
     * 生成PDF文档
     */
    private static async generatePdf(
        pageElements: HTMLElement[],
        options: PdfExportOptions,
        filename: string
    ): Promise<void> {
        const paperConfig = PAPER_SIZES[options.paperSize]
        const qualityConfig = QUALITY_CONFIG[options.quality]

        const pageWidth = paperConfig.width
        const pageHeight = paperConfig.height

        // 创建PDF
        const pdf = new jsPDF({
            orientation: 'portrait',
            unit: 'mm',
            format: options.paperSize,
            putOnlyUsedFonts: true,
            compress: true,
            floatPrecision: 4
        })

        const totalPages = pageElements.length
        for (let index = 0; index < totalPages; index++) {
            const pageElement = pageElements[index]
            const targetCanvasWidth = this.mmToPx(pageWidth, qualityConfig.targetDpi)
            const targetCanvasHeight = this.mmToPx(pageHeight, qualityConfig.targetDpi)
            const requiredScale = Math.max(
                targetCanvasWidth / Math.max(pageElement.offsetWidth, 1),
                targetCanvasHeight / Math.max(pageElement.offsetHeight, 1)
            )
            // 以 scale 为上限，满足 DPI 需求即可，避免过度渲染
            const renderScale = Math.min(qualityConfig.scale, requiredScale)
            const canvas = await html2canvas(pageElement, {
                scale: renderScale,
                useCORS: true,
                logging: false,
                allowTaint: true,
                backgroundColor: '#f5f7fa',
                width: pageElement.offsetWidth,
                height: pageElement.offsetHeight,
                imageTimeout: 0,
                onclone: (clonedDoc) => {
                    const style = clonedDoc.createElement('style')
                    style.innerHTML = `* { print-color-adjust: exact; -webkit-print-color-adjust: exact; }`
                    clonedDoc.head.appendChild(style)
                }
            })

            if (index > 0) {
                pdf.addPage()
            }
            pdf.setFillColor(245, 247, 250)
            pdf.rect(0, 0, pageWidth, pageHeight, 'F')

            const imageDataUrl = this.getCanvasDataUrl(canvas, qualityConfig.format, qualityConfig.quality)
            pdf.addImage(
                imageDataUrl,
                qualityConfig.format,
                0, 0,
                pageWidth, pageHeight,
                undefined,
                qualityConfig.imageCompression
            )
            this.addPageCopyableTexts(pdf, pageElement, pageWidth, pageHeight)

            const currentPage = index + 1
            const pageProgress = 75 + Math.round((currentPage / totalPages) * 20)
            this.updateProgress(`生成PDF文档... (${currentPage}/${totalPages})`, Math.min(pageProgress, 95))
        }

        // 保存PDF
        pdf.save(filename)
    }

    private static mmToPx(mm: number, dpi: number): number {
        return Math.round((mm / 25.4) * dpi)
    }

    private static getCanvasDataUrl(canvas: HTMLCanvasElement, format: 'JPEG' | 'PNG', quality: number): string {
        if (format === 'PNG') {
            return canvas.toDataURL('image/png')
        }
        return canvas.toDataURL(`image/${format.toLowerCase()}`, quality)
    }

    private static addPageCopyableTexts(
        pdf: jsPDF,
        pageElement: HTMLElement,
        pageWidth: number,
        pageHeight: number
    ): void {
        const pageRect = pageElement.getBoundingClientRect()
        if (pageRect.width <= 0 || pageRect.height <= 0) {
            return
        }

        const textElements = Array.from(pageElement.querySelectorAll('[data-pdf-copy-text]'))
            .filter((element): element is HTMLElement => element instanceof HTMLElement)

        textElements.forEach((element) => {
            const text = element.getAttribute('data-pdf-copy-text')?.trim() || ''
            if (!text) {
                return
            }

            const rect = element.getBoundingClientRect()
            const clippedLeft = Math.max(rect.left, pageRect.left)
            const clippedTop = Math.max(rect.top, pageRect.top)
            const clippedRight = Math.min(rect.right, pageRect.right)
            const clippedBottom = Math.min(rect.bottom, pageRect.bottom)
            const clippedWidth = clippedRight - clippedLeft
            const clippedHeight = clippedBottom - clippedTop

            if (clippedWidth <= 0 || clippedHeight <= 0) {
                return
            }

            const computedStyle = window.getComputedStyle(element)
            const fontSizePx = Number.parseFloat(computedStyle.fontSize || '11') || 11
            const lineHeightPx = Number.parseFloat(computedStyle.lineHeight || '') || fontSizePx * 1.5
            const fontSizeMm = (fontSizePx / pageRect.width) * pageWidth
            const lineHeightMm = (lineHeightPx / pageRect.height) * pageHeight
            const x = ((clippedLeft - pageRect.left) / pageRect.width) * pageWidth
            const y = ((clippedTop - pageRect.top) / pageRect.height) * pageHeight
            const maxWidth = (clippedWidth / pageRect.width) * pageWidth
            const textLines = pdf.splitTextToSize(text, Math.max(maxWidth, fontSizeMm))

            pdf.setFont('helvetica', 'normal')
            pdf.setFontSize(fontSizeMm)
            pdf.setTextColor(37, 99, 235)

            textLines.forEach((line: string, lineIndex: number) => {
                pdf.text(line, x, y + fontSizeMm + lineIndex * lineHeightMm, {
                    baseline: 'bottom'
                })
            })
        })
    }

    /**
     * 等待下一帧渲染完成（比 setTimeout 更快）
     */
    private static async waitForFrame(): Promise<void> {
        await new Promise<void>(resolve => requestAnimationFrame(() => resolve()))
    }

    private static async waitForFonts(): Promise<void> {
        const fontSet = (document as Document & { fonts?: FontFaceSet }).fonts
        if (!fontSet?.ready) {
            return
        }

        try {
            await fontSet.ready
        } catch {
            // 忽略字体等待失败，继续导出
        }
    }

    private static async inlineAgentAvatarImages(container: HTMLElement): Promise<void> {
        const avatarImages = Array.from(
            container.querySelectorAll('img[data-pdf-agent-avatar="true"]')
        ) as HTMLImageElement[]

        if (avatarImages.length === 0) {
            return
        }

        await Promise.all(
            avatarImages.map(async (img) => {
                const src = img.getAttribute('src') || ''
                if (!src || src.startsWith('data:')) {
                    return
                }

                try {
                    const response = await fetch(src)
                    if (!response.ok) {
                        return
                    }

                    const blob = await response.blob()
                    const dataUrl = await new Promise<string>((resolve, reject) => {
                        const reader = new FileReader()
                        reader.onload = () => resolve(String(reader.result || ''))
                        reader.onerror = () => reject(reader.error)
                        reader.readAsDataURL(blob)
                    })

                    if (dataUrl) {
                        img.src = dataUrl
                    }
                } catch {
                    // 忽略内联失败，保留原始图片地址继续导出
                }
            })
        )
    }

    /**
     * 构建纯文本内容
     */
    private static buildTextContent(messages: ExportableChatMessage[], options: TextExportOptions, allMessages?: ExportableChatMessage[]): string {
        let content = 'MCP对话记录\n\n'

        messages.forEach((message, index) => {
            if (index > 0) {
                content += '\n' + '-'.repeat(80) + '\n\n'
            }

            // 添加角色标签
            if (options.includeRoleLabels) {
                const roleLabels = {
                    user: '用户',
                    assistant: '助手',
                    system: '系统',
                    tool: '工具'
                }
                content += `【${roleLabels[message.role] || message.role}】\n`
            }

            // 添加思考过程
            if (options.includeThinking && message.role === 'assistant' && message.reasoning_content) {
                content += '\n【思考过程】\n'
                content += this.processTextContent(message.reasoning_content, options.simplifyContent) + '\n'
                content += '【回答】'
            }

            const imageText = this.buildTextImageSection(message)
            if (imageText) {
                content += imageText
            }

            // 添加消息内容
            if (message.content) {
                content += this.processTextContent(message.content, options.simplifyContent) + '\n'
            }

            // 添加工具调用
            if (options.includeToolCalls !== false && message.tool_calls?.length) {
                content += '\n【工具调用】\n'
                message.tool_calls.forEach(toolCall => {
                    content += `【工具】\n${toolCall.function.name}\n`
                    content += `【参数】\n${toolCall.function.arguments}\n`

                    // 查找工具调用结果
                    const searchMessages = allMessages || messages
                    const toolResult = this.findToolCallResult(toolCall.id, searchMessages)
                    if (toolResult) {
                        content += `【结果】\n${this.processTextContent(toolResult.content, options.simplifyContent)}\n`
                    }
                })
            }
        })

        return content
    }

    /**
     * 构建Markdown内容
     */
    private static buildMarkdownContent(messages: ExportableChatMessage[], options: MarkdownExportOptions, allMessages?: ExportableChatMessage[]): string {
        let content = ''

        // 添加元数据头
        if (options.includeMetadata) {
            const now = new Date()
            content += `---\n`
            content += `title: MCP对话记录\n`
            content += `date: ${now.toISOString()}\n`
            content += `---\n\n`
        }

        content += `# MCP对话记录\n\n`

        messages.forEach((message, index) => {
            if (message.role === 'system' && !options.includeSystemMessages) {
                return
            }

            if (index > 0) {
                content += '\n---\n\n'
            }

            // 角色标签和图标
            const roleConfig = {
                user: {label: '用户', icon: '👤'},
                assistant: {label: '助手', icon: '🤖'},
                system: {label: '系统', icon: '⚙️'},
                tool: {label: '工具', icon: '🔧'}
            }

            const config = roleConfig[message.role] || {label: message.role, icon: '❓'}
            content += `### ${config.icon} ${config.label}\n\n`

            // 思考过程
            if (options.includeThinking && message.role === 'assistant' && message.reasoning_content) {
                content += `#### 思考过程\n\n`
                content += this.processMarkdownContent(message.reasoning_content, options.includeCodeblockSyntax) + '\n'
                content += `#### 回答\n`
            }

            const imageMarkdown = this.buildMarkdownImageSection(message)
            if (imageMarkdown) {
                content += imageMarkdown
            }

            // 消息内容
            if (message.content) {
                content += this.processMarkdownContent(message.content, options.includeCodeblockSyntax) + '\n\n'
            }

            // 工具调用
            if (options.includeToolCalls !== false && message.tool_calls?.length) {
                content += `#### 工具调用\n\n`
                message.tool_calls.forEach(toolCall => {
                    content += `**工具**: ${toolCall.function.name}\n\n`
                    content += '**参数**:\n\n```json\n'
                    try {
                        const args = JSON.parse(toolCall.function.arguments)
                        content += JSON.stringify(args, null, 2)
                    } catch (e) {
                        content += toolCall.function.arguments
                    }
                    content += '\n```\n\n'

                    // 查找工具调用结果
                    const searchMessages = allMessages || messages
                    const toolResult = this.findToolCallResult(toolCall.id, searchMessages)
                    if (toolResult) {
                        content += `**结果**:\n\n\`\`\`\n`
                        content += toolResult.content + '\n\`\`\`\n\n'
                    }
                })
            }
        })

        return content
    }

    private static getMessageImages(message: ExportableChatMessage): Array<{name: string; url: string}> {
        const files = Array.isArray(message.files) ? message.files : []
        return files
            .filter(file => isImageFile(file))
            .map(file => ({
                name: String(file?.name || '图片').trim() || '图片',
                url: getImagePreviewUrl(file)
            }))
            .filter(item => !!item.url)
    }

    private static buildTextImageSection(message: ExportableChatMessage): string {
        const images = this.getMessageImages(message)
        if (images.length === 0) {
            return ''
        }

        let content = '\n【图片】\n'
        images.forEach((image, index) => {
            const label = images.length > 1 ? `图片${index + 1}` : '图片'
            content += `${label}: ${image.name}\n`
        })
        return content
    }

    private static buildMarkdownImageSection(message: ExportableChatMessage): string {
        const images = this.getMessageImages(message)
        if (images.length === 0) {
            return ''
        }

        let content = '#### 图片\n\n'
        images.forEach((image) => {
            if (/^https?:\/\//i.test(image.url) || /^data:image\//i.test(image.url)) {
                content += `![${image.name}](${image.url})\n\n`
            } else {
                content += `- 图片: ${image.name}\n`
            }
        })

        if (!content.endsWith('\n\n')) {
            content += '\n'
        }

        return content
    }

    /**
     * 查找工具调用结果
     */
    private static findToolCallResult(toolCallId: string, messages: ExportableChatMessage[]): ExportableChatMessage | null {
        return messages.find(msg => msg.role === 'tool' && msg.tool_call_id === toolCallId) || null
    }

    /**
     * 处理文本内容
     */
    private static processTextContent(content: string, simplify: boolean): string {
        if (!simplify) return content

        return content
            .replace(/#{1,6}\s+/g, '')
            .replace(/\*\*(.*?)\*\*/g, '$1')
            .replace(/\*(.*?)\*/g, '$1')
            .replace(/`{3}[\s\S]*?`{3}/g, (match) => {
                return match.replace(/^```[\s\S]*?\n/, '').replace(/```$/, '')
            })
            .replace(/`(.*?)`/g, '$1')
            .replace(/!\[(.*?)]\((.*?)\)/g, '图片: $1')
            .replace(/\[(.*?)]\((.*?)\)/g, '$1 (链接: $2)')
    }

    /**
     * 处理Markdown内容
     */
    private static processMarkdownContent(content: string, includeCodeblockSyntax: boolean): string {
        if (includeCodeblockSyntax) return content
        return content.replace(/```(\w+)/g, '```')
    }

    /**
     * 获取消息列表
     */
    private static getMessages(): ChatMessage[] {
        // 如果有选中的消息，返回选中的消息
        if (this.selectedMessages && this.selectedMessages.length > 0) {
            return this.selectedMessages
        }

        // 否则返回全部消息
        const chatStore = useChatStore();

        return (chatStore.messages || []).map((msg, index) => ({
            ...msg,
            id: `msg-${index}-${Date.now()}`,
            timestamp: Date.now()
        }))
    }

    /**
     * 下载文件
     */
    private static downloadFile(blob: Blob, filename: string): void {
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = filename
        link.click()

        setTimeout(() => {
            URL.revokeObjectURL(url)
        }, 100)
    }
}

function applyAssistantAvatars(container: HTMLElement, messages: ChatMessage[]): void {
  const messageEls = Array.from(container.children) as HTMLElement[]
  const len = Math.min(messageEls.length, messages.length)

  for (let i = 0; i < len; i++) {
    const msg = messages[i]
    if (msg.role !== 'assistant') continue

    const messageContainer = messageEls[i]
    const avatarContainer = messageContainer.firstElementChild as HTMLElement | null
    if (!avatarContainer) continue

    while (avatarContainer.firstChild) avatarContainer.removeChild(avatarContainer.firstChild)

    // ����ͷ�����������򽥱䱳�������ĵ���ɫ������ɢ��#f5f7fa
    const imgWrapper = document.createElement('div')
    Object.assign(imgWrapper.style, {
      width: '36px',
      height: '36px',
      borderRadius: '50%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'radial-gradient(circle at center, rgba(114, 120, 220, 0.18) 0%, rgba(114, 120, 220, 0.10) 55%, rgba(245, 247, 250, 0.98) 75%, rgba(245, 247, 250, 0.5) 88%, rgba(245, 247, 250, 0) 100%)',
      boxShadow: '0 0 15px 5px rgba(245, 247, 250, 0.6), 0 0 30px 8px rgba(245, 247, 250, 0.3)'
    })

    const img = document.createElement('img')
    img.src = logoPng
    img.crossOrigin = 'anonymous'
    img.setAttribute('data-pdf-agent-avatar', 'true')
    Object.assign(img.style, {
      width: '33px',
      height: '20px'
    })

    imgWrapper.appendChild(img)
    avatarContainer.appendChild(imgWrapper)
  }
}
