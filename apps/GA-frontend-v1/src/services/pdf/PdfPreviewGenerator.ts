import type {PreviewConfig} from './types'
import type {ChatMessage} from '@/types'
import {EXPORT_CONTAINER_CONFIG, PAPER_SIZES} from './constants'
import PdfRenderer from './PdfRenderer'
import {useChatStore} from '@/stores/chat-store'
import {getCopyright} from '@/utils/RuntimeConfig'
import logoPng from '@/assets/ga-logo.svg'
import bgPoster from '@/assets/image/jpg/background.jpg'

/**
 * PDF预览生成器
 * 负责生成PDF预览内容
 */
export default class PdfPreviewGenerator {
    private static selectedMessages: ChatMessage[] | null = null

    /**
     * 设置选中的消息（用于选择模式预览）
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
     * 生成预览内容
     */
    static async generatePreview(config: PreviewConfig): Promise<string> {
        try {
            const messages = this.getMessages()
            if (messages.length === 0) {
                throw new Error('没有找到对话内容')
            }

            // 获取完整消息列表（用于查找工具调用结果）
            const chatStore = useChatStore()
            const allMessages = (chatStore.messages || []).map((msg, index) => ({
                ...msg,
                id: `msg-${index}-${Date.now()}`,
                timestamp: Date.now()
            }));

            // 创建导出容器
            const exportContainer = PdfRenderer.createExportContainer(
                messages,
                config.includeThinking,
                config.includeSystemMessages,
                this.selectedMessages ? allMessages : undefined,
                config.includeToolCalls !== false
            )

            // 在拷贝到预览页面前，先应用助手头像图标/首字母回退以保持一致
            const filteredMessages = messages.filter(m => m.role !== 'tool' && (config.includeSystemMessages ? true : m.role !== 'system'))
            this.applyAssistantAvatars(exportContainer, filteredMessages)

            // 临时添加到DOM以计算尺寸
            exportContainer.style.left = '-9999px'
            exportContainer.style.visibility = 'hidden'
            document.body.appendChild(exportContainer)

            // 等待DOM更新
            await new Promise(resolve => setTimeout(resolve, 150))
            await PdfRenderer.waitForImages(exportContainer)

            // 获取纸张配置
            const pagesContainer = this.createPagesContainerFromExportContainer(exportContainer, {
                paperSize: config.paperSize,
                scale: config.scale,
                copyrightPosition: config.copyrightPosition
            })

            // 清理临时容器
            document.body.removeChild(exportContainer)

            return pagesContainer.outerHTML

        } catch (error) {
            // 确保清理临时元素
            this.cleanupTempElements()
            throw error
        }
    }

    /**
     * 基于导出容器创建分页后的页面容器
     */
    static createPagesContainerFromExportContainer(
        exportContainer: HTMLElement,
        config: Pick<PreviewConfig, 'paperSize' | 'scale' | 'copyrightPosition'>,
        includePageNumbers: boolean = true
    ): HTMLElement {
        const paperConfig = PAPER_SIZES[config.paperSize]
        const containerWidth = EXPORT_CONTAINER_CONFIG.width
        const containerHeight = Math.round(containerWidth * paperConfig.aspectRatio)
        const copyrightPosition = config.copyrightPosition || 'page-bottom'
        // 仅在页面底部模式时为版权信息预留空间
        const bottomReserved = copyrightPosition === 'page-bottom' ? 40 : 0
        const contentHeight = containerHeight - bottomReserved
        const scale = config.scale / 100
        const totalContentHeight = exportContainer.scrollHeight
        const pagesCount = Math.max(1, Math.ceil(totalContentHeight / contentHeight))

        return this.createPagesContainer(
            exportContainer,
            containerWidth,
            containerHeight,
            contentHeight,
            scale,
            pagesCount,
            includePageNumbers,
            copyrightPosition
        )
    }

    /**
     * 创建页面容器
     */
    private static createPagesContainer(
        exportContainer: HTMLElement,
        containerWidth: number,
        containerHeight: number,
        contentHeight: number,
        scale: number,
        pagesCount: number,
        includePageNumbers: boolean,
        copyrightPosition: 'page-bottom' | 'last-page' = 'page-bottom'
    ): HTMLElement {
        const pagesContainer = document.createElement('div')
        pagesContainer.className = 'pdf-pages-container'

        for (let pageIndex = 0; pageIndex < pagesCount; pageIndex++) {
            const pageContainer = this.createPageContainer(
                exportContainer,
                containerWidth,
                containerHeight,
                contentHeight,
                scale,
                pageIndex,
                pagesCount,
                includePageNumbers,
                copyrightPosition
            )
            pagesContainer.appendChild(pageContainer)
        }

        // 仅在最后一页模式时添加版权尾页
        if (copyrightPosition === 'last-page') {
            const copyrightPage = this.createCopyrightPage(
                containerWidth,
                containerHeight,
                scale,
                pagesCount + 1,
                includePageNumbers
            )
            pagesContainer.appendChild(copyrightPage)
        }

        return pagesContainer
    }

    /**
     * 创建单个页面容器
     */
    private static createPageContainer(
        exportContainer: HTMLElement,
        containerWidth: number,
        containerHeight: number,
        contentHeight: number,
        scale: number,
        pageIndex: number,
        totalPages: number,
        includePageNumbers: boolean,
        copyrightPosition: 'page-bottom' | 'last-page' = 'page-bottom'
    ): HTMLElement {
        const pageContainer = document.createElement('div')
        pageContainer.className = 'pdf-main-container'

        Object.assign(pageContainer.style, {
            position: 'relative',
            width: `${containerWidth * scale}px`,
            height: `${containerHeight * scale}px`,
            backgroundColor: '#f5f7fa',
            overflow: 'hidden'
        })

        // 创建内容容器
        const contentContainer = document.createElement('div')
        contentContainer.className = 'pdf-content-container'

        // 计算当前页应该显示的内容
        const startPos = pageIndex * contentHeight

        Object.assign(contentContainer.style, {
            transform: `scale(${scale})`,
            transformOrigin: 'top left',
            width: `${containerWidth}px`,
            height: `${contentHeight}px`,
            padding: `${EXPORT_CONTAINER_CONFIG.padding}px`,
            boxSizing: 'border-box',
            position: 'absolute',
            top: '0',
            overflow: 'hidden'
        })

        // 创建一个临时容器来复制内容
        const tempContainer = document.createElement('div')
        tempContainer.innerHTML = exportContainer.innerHTML
        tempContainer.style.position = 'relative'
        tempContainer.style.top = `${-startPos}px`

        // 复制导出容器的内容
        contentContainer.appendChild(tempContainer)

        pageContainer.appendChild(contentContainer)
        if (includePageNumbers) {
            const pageNumber = this.createPageNumber(pageIndex + 1, totalPages, scale)
            pageContainer.appendChild(pageNumber)
        }
        
        // 仅在页面底部模式时添加每页底部版权信息
        if (copyrightPosition === 'page-bottom') {
            const copyright = this.createCopyright(scale, contentHeight)
            pageContainer.appendChild(copyright)
        }

        return pageContainer
    }

    /**
     * 创建页码元素
     */
    private static createPageNumber(current: number, total: number, scale: number): HTMLElement {
        const pageNumber = document.createElement('div')
        pageNumber.className = 'page-number-preview'
        pageNumber.textContent = `${current} / ${total}`

        Object.assign(pageNumber.style, {
            position: 'absolute',
            bottom: '10px',
            right: '7px',
            fontSize: `${12 * scale}px`,
            color: '#666',
            backgroundColor: 'rgba(255, 255, 255, 0.8)',
            padding: `${3 * scale}px ${8 * scale}px`,
            borderRadius: `${8 * scale}px`,
            fontFamily: 'Arial, sans-serif',
            zIndex: '10',
            pointerEvents: 'none',
            fontWeight: '500',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
            letterSpacing: '0.5px'
        })

        return pageNumber
    }

    /**
     * 创建版权信息元素
     */
    private static createCopyright(scale: number, containerHeight: number): HTMLElement {
        const copyrightText = getCopyright()
        const copyrightContainer = document.createElement('div')
        copyrightContainer.className = 'pdf-copyright'

        Object.assign(copyrightContainer.style, {
            position: 'absolute',
            top: `${containerHeight - 0}px`,
            left: `${12}px`,
            right: `${12}px`,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            zIndex: '10',
            pointerEvents: 'none'
        })

        // logo 和GeneralAgent水平排列在同一行
        const titleRow = document.createElement('div')
        Object.assign(titleRow.style, {
            display: 'flex',
            alignItems: 'center',
            gap: `${6 * scale}px`
        })

        const logoImg = document.createElement('img')
        logoImg.src = logoPng
        logoImg.crossOrigin = 'anonymous'
        Object.assign(logoImg.style, {
            height: `${20 * scale}px`,
            width: 'auto',
            display: 'block'
        })

        const systemName = document.createElement('div')
        systemName.textContent = 'GeneralAgent'
        Object.assign(systemName.style, {
            fontSize: `${16 * scale}px`,
            color: '#1a1a1a',
            fontFamily: "'SmileySansOblique', sans-serif",
            fontWeight: '500',
            letterSpacing: '0'
        })

        titleRow.appendChild(logoImg)
        titleRow.appendChild(systemName)

        const companyName = document.createElement('div')
        companyName.textContent = copyrightText
        Object.assign(companyName.style, {
            fontSize: `${8 * scale}px`,
            color: '#999',
            fontFamily: 'Arial, sans-serif',
            fontWeight: '400',
            letterSpacing: '0.2px',
            textAlign: 'center',
            marginTop: '2px'
        })

        copyrightContainer.appendChild(titleRow)
        copyrightContainer.appendChild(companyName)

        return copyrightContainer
    }

    /**
     * 创建版权尾页（居中展示版权信息）
     */
    private static createCopyrightPage(
        containerWidth: number,
        containerHeight: number,
        scale: number,
        pageNumber: number,
        includePageNumbers: boolean
    ): HTMLElement {
        const copyrightText = getCopyright()
        const pageContainer = document.createElement('div')
        pageContainer.className = 'pdf-main-container'

        Object.assign(pageContainer.style, {
            position: 'relative',
            width: `${containerWidth * scale}px`,
            height: `${containerHeight * scale}px`,
            backgroundImage: `url(${bgPoster})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            overflow: 'hidden'
        })

        // 居中容器
        const centerContainer = document.createElement('div')
        Object.assign(centerContainer.style, {
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: `${5 * scale}px`
        })

        // Logo 和系统名称水平排列
        const titleRow = document.createElement('div')
        Object.assign(titleRow.style, {
            display: 'flex',
            alignItems: 'center',
            gap: `${10 * scale}px`
        })

        // Logo
        const logoImg = document.createElement('img')
        logoImg.src = logoPng
        logoImg.crossOrigin = 'anonymous'
        Object.assign(logoImg.style, {
            height: `${34 * scale}px`,
            width: 'auto',
            display: 'block'
        })

        // 系统名称
        const systemName = document.createElement('div')
        systemName.textContent = 'GeneralAgent'
        Object.assign(systemName.style, {
            fontSize: `${28 * scale}px`,
            color: '#1a1a1a',
            fontFamily: "'SmileySansOblique', sans-serif",
            fontWeight: '500',
            letterSpacing: '0'
        })

        titleRow.appendChild(logoImg)
        titleRow.appendChild(systemName)
        centerContainer.appendChild(titleRow)

        // 副标题
        const subtitle = document.createElement('div')
        subtitle.textContent = '企业级智能体平台'
        Object.assign(subtitle.style, {
            fontSize: `${13 * scale}px`,
            color: '#666',
            fontFamily: 'Arial, sans-serif',
            fontWeight: '400',
            letterSpacing: '7px',
            textAlign: 'center',
            marginLeft: `${8 * scale}px`
        })

        // 分隔线
        const divider = document.createElement('div')
        Object.assign(divider.style, {
            width: `${270 * scale}px`,
            height: '1px',
            backgroundColor: 'transparent',
            margin: `${6 * scale}px 0`,
            marginTop: `${20 * scale}px`,
            marginBottom: `-${3 * scale}px`
        })

        // 公司名称
        const companyName = document.createElement('div')
        companyName.textContent = copyrightText
        Object.assign(companyName.style, {
            fontSize: `${11 * scale}px`,
            color: '#999',
            fontFamily: 'Arial, sans-serif',
            fontWeight: '400',
            letterSpacing: '0.5px',
            textAlign: 'center'
        })

        centerContainer.appendChild(subtitle)
        pageContainer.appendChild(centerContainer)

        // 底部容器 - 分隔线和公司名称
        const bottomContainer = document.createElement('div')
        Object.assign(bottomContainer.style, {
            position: 'absolute',
            bottom: `${20 * scale}px`,
            left: '50%',
            transform: 'translateX(-50%)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: `${10 * scale}px`
        })

        bottomContainer.appendChild(divider)
        bottomContainer.appendChild(companyName)
        pageContainer.appendChild(bottomContainer)

        if (includePageNumbers) {
            const pageNum = this.createPageNumber(pageNumber, pageNumber, scale)
            pageContainer.appendChild(pageNum)
        }

        return pageContainer
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
        const chatStore = useChatStore()
        return (chatStore.messages || []).map((msg, index) => ({
            ...msg,
            id: `msg-${index}-${Date.now()}`,
            timestamp: Date.now()
        }))
    }

    /**
     * 清理临时元素
     */
    private static cleanupTempElements(): void {
        const tempContainer = document.querySelector('.pdf-export-container')
        if (tempContainer && tempContainer.parentNode) {
            tempContainer.parentNode.removeChild(tempContainer)
        }

        const tempDiv = document.querySelector('div[style*="-9999px"]')
        if (tempDiv && tempDiv.parentNode) {
            tempDiv.parentNode.removeChild(tempDiv)
        }
    }

    private static applyAssistantAvatars(container: HTMLElement, messages: ChatMessage[]): void {
        const messageEls = Array.from(container.children) as HTMLElement[]
        const len = Math.min(messageEls.length, messages.length)

        for (let i = 0; i < len; i++) {
            const msg = messages[i]
            if (msg.role !== 'assistant') continue

            const messageContainer = messageEls[i]
            const avatarContainer = messageContainer.firstElementChild as HTMLElement | null
            if (!avatarContainer) continue

            while (avatarContainer.firstChild) avatarContainer.removeChild(avatarContainer.firstChild)

            // 创建头像容器：径向渐变背景，中心淡紫色向外弥散至#f5f7fa
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
            Object.assign(img.style, {
                width: '33px',
                height: '20px'
            })

            imgWrapper.appendChild(img)
            avatarContainer.appendChild(imgWrapper)
        }
    }
}
