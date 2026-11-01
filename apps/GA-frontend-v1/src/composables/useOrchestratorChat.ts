import { streamUrl, streamHeaders } from '@/services/conversationStream'
import { ref } from 'vue'
import { finishTaskTiming } from '@/utils/taskTiming'
import StorageService from '@/utils/StorageService'
import type { Message, ToolCall } from '@/types/mcp'
import NotificationService from '@/utils/NotificationService'
import { ensureAuthenticatedRequestAllowed, http, registerSilentAbortSignal } from '@/utils/http'
import { v4 as uuidv4 } from 'uuid'
import { getApiBaseUrl } from '@/utils/RuntimeConfig'
import { eventBus, MCP_EVENTS } from '@/utils/EventBus'
import { useSandboxFilesStore } from '@/stores/sandboxFilesStore'

export function useOrchestratorChat() {
  const orchestratorUrl = ref<string>('')
  const messages = ref<Message[]>([])
  const isProcessing = ref<boolean>(false)
  const createSessionThreadId = () => uuidv4()
  const initialSessionThreadId = StorageService.getWorkspaceSessionThreadId() || createSessionThreadId()
  const sessionThreadId = ref<string>(initialSessionThreadId)
  let sessionGeneration = 0
  const logConversationSession = (reason: string, value: string) => {
    console.log(`[conversation] ${reason} session_thread_id:`, value)
  }
  // 初始化时即持久化，确保普通对话（非智能体）也能拥有稳定的会话线程 ID，
  // 供后续对话历史功能使用（刷新后仍能恢复同一会话）
  StorageService.setWorkspaceSessionThreadId(initialSessionThreadId)
  logConversationSession('current', initialSessionThreadId)
  const createUiKey = () => uuidv4()
  let activeRequestController: AbortController | null = null
  let activeAssistantMessage: Message | null = null
  let activeRequestAgentType: 'orchestrator' | 'assistant' | 'deepagent' | null = null
  let interruptRequested = false

  const normalizeTodos = (todos: any): Message['todos'] => {
    if (!Array.isArray(todos)) return undefined
    const normalized = todos
      .map((todo: any) => {
        const content = typeof todo?.content === 'string' ? todo.content : ''
        const rawStatus = typeof todo?.status === 'string' ? todo.status : 'pending'
        // DeepAgent 可能返回 in-progress / in progress，需要统一为前端状态
        const status = rawStatus.replace('-', '_').replace(/\s+/g, '_') as 'pending' | 'in_progress' | 'completed'
        if (!content) return null
        return {
          ...todo,
          content,
          status: (status === 'in_progress' || status === 'completed') ? status : 'pending'
        }
      })
      .filter(Boolean)
    return normalized.length > 0 ? normalized : undefined
  }

  const ensureBlocks = (assistantMessage: Message) => {
    if (!assistantMessage.orchestratorBlocks) {
      assistantMessage.orchestratorBlocks = []
    }
    return assistantMessage.orchestratorBlocks
  }

  const appendContentBlock = (assistantMessage: Message, text: string) => {
    if (!text) return
    const blocks = ensureBlocks(assistantMessage)
    const last = blocks[blocks.length - 1]
    if (last && last.type === 'content') {
      last.content += text
      return
    }
    blocks.push({ type: 'content', content: text })
  }

  const appendReasoningBlock = (assistantMessage: Message, text: string) => {
    if (!text) return
    const blocks = ensureBlocks(assistantMessage)
    const last = blocks[blocks.length - 1]
    if (last && last.type === 'reasoning') {
      last.content += text
      return
    }
    blocks.push({ type: 'reasoning', content: text })
  }

  const appendToolBlock = (assistantMessage: Message, toolCallId: string) => {
    if (!toolCallId) return
    const blocks = ensureBlocks(assistantMessage)
    const last = blocks[blocks.length - 1]
    if (last && last.type === 'tools') {
      if (!last.toolCallIds.includes(toolCallId)) {
        last.toolCallIds.push(toolCallId)
      }
      return
    }
    blocks.push({ type: 'tools', toolCallIds: [toolCallId] })
  }

  /**
   * 去掉 assistant 内容中重复的 map 代码块。
   * 当 DeepAgent 的 execute 工具注入了 map block，同时 DeepAgent 自己的回复也包含 map block 时，
   * 会出现两个 canvas-map。此函数只保留第一个。
   */
  const deduplicateMapBlocks = (msg: Message) => {
    if (!msg?.content) return

    // 匹配第一个完整的 ```map...``` 代码块
    const firstBlockRegex = /```map\n[\s\S]*?\n```\n?/
    const match = msg.content.match(firstBlockRegex)
    if (!match || match.index === undefined) return

    const firstEnd = match.index + match[0].length
    const after = msg.content.substring(firstEnd)

    // 检查第一个 map block 之后是否还有第二个
    if (!after.includes('```map')) return

    console.log('[Orchestrator] 检测到重复 map block，正在去重')

    // 删除后续所有 map block（含 fence），保留第一个和中间的非 map 文本
    const cleanedAfter = after.replace(/```map[\s\S]*?```\n?/g, '')
    msg.content = msg.content.substring(0, firstEnd) + cleanedAfter

    // 同步更新 orchestratorBlocks：渲染按块独立解析 map artifact，
    // 而重复的 map 块分布在多个 content 块中（tools 块会将 content 流切段），
    // 因此将所有 content 块合并为去重后的第一个块，删除其余 content 块
    if (msg.orchestratorBlocks) {
      const firstContent = msg.orchestratorBlocks.find(b => b.type === 'content')
      if (firstContent) {
        firstContent.content = msg.content
        msg.orchestratorBlocks = msg.orchestratorBlocks.filter(
          b => b.type !== 'content' || b === firstContent
        )
      }
    }
  }

  const markAssistantMessageStopped = (assistantMessage?: Message | null) => {
    const target = assistantMessage || activeAssistantMessage
    if (!target || target.role !== 'assistant') return
    finishTaskTiming(target)
    target.isStreaming = false
    ;(target as any).isStopped = true
    messages.value = [...messages.value]
    eventBus.emit(MCP_EVENTS.CONVERSATION_STOPPED)
  }

  type StreamTarget = 'content' | 'reasoning'

  type ProcessContext = {
    multiLineTarget: StreamTarget | null
  }

  const appendStreamText = (assistantMessage: Message, target: StreamTarget, text: string) => {
    if (!text) return
    if (target === 'reasoning') {
      assistantMessage.reasoning_content = (assistantMessage.reasoning_content || '') + text
      appendReasoningBlock(assistantMessage, text)
      return
    }
    assistantMessage.content += text
    appendContentBlock(assistantMessage, text)
  }

  const processResponse = (chunk: string, assistantMessage: Message, context: ProcessContext) => {
    const lines = chunk.split(/\r?\n/)
    
    for (const rawLine of lines) {
      // Don't trim yet for multi-line preservation, but trim for protocol check
      let line = rawLine.trim()
      
      // Remove optional "data:" prefix commonly found in SSE streams
      if (line.startsWith('data:')) {
        line = line.substring(5).trim()
      }
      
      if (!line && !context.multiLineTarget) continue;
      if (line === '[DONE]') continue;
      if (line.startsWith('{')) {
        try {
          const chunk = JSON.parse(line)
          if (Array.isArray(chunk.choices)) {
            const delta = chunk.choices[0]?.delta || {}
            if (delta.reasoning_content || delta.reasoning) appendStreamText(assistantMessage, 'reasoning', delta.reasoning_content || delta.reasoning)
            if (delta.content) appendStreamText(assistantMessage, 'content', delta.content)
            continue
          }
        } catch { /* Other protocols are parsed below. */ }
      }

      // 1. Handle Multi-line string continuation
      if (context.multiLineTarget) {
          let contentPart = rawLine; // Use raw line to preserve indentation
          
          // Check for closing quote
          // We assume the server sends the closing quote at the end of the line
          if (contentPart.trim().endsWith('"')) {
               // Check if it's an escaped quote
               const trimmed = contentPart.trim();
               let backslashCount = 0;
               // Check backslashes before the last quote
               // trimmed.length - 1 is the quote. Start checking from -2.
               for (let i = trimmed.length - 2; i >= 0; i--) {
                   if (trimmed[i] === '\\') backslashCount++;
                   else break;
               }
               
               // If even number of backslashes (0, 2, 4...), it is NOT escaped -> It IS the closing quote.
               if (backslashCount % 2 === 0) {
                   // Find the last quote in the *original* contentPart to strip it correctly
                   const lastQuoteIndex = contentPart.lastIndexOf('"');
                   if (lastQuoteIndex !== -1) {
                       contentPart = contentPart.substring(0, lastQuoteIndex);
                   }
                   const target = context.multiLineTarget;
                   context.multiLineTarget = null;
                   appendStreamText(assistantMessage, target, '\n' + contentPart);
                   continue;
               }
          }
          
          // Append with newline (restore the newline we split on)
          const text = '\n' + contentPart;
          appendStreamText(assistantMessage, context.multiLineTarget, text);
          continue;
      }

      // 2. Protocol Handling
      
      const protocolTargets: Array<{ prefix: '0' | '1'; target: StreamTarget }> = [
        { prefix: '0', target: 'content' },
        { prefix: '1', target: 'reasoning' }
      ]

      let handledProtocolText = false
      for (const { prefix, target } of protocolTargets) {
        // 2a/2b. Text Stream (0: content, 1: reasoning)
        const quotedMatch = line.match(new RegExp(`^${prefix}:\\s*"(.*)"\\s*$`))
        if (quotedMatch) {
          try {
            const text = JSON.parse(`"${quotedMatch[1]}"`)
            appendStreamText(assistantMessage, target, text)
          } catch (e) {
            console.error('[Orchestrator] JSON parse error:', e)
            appendStreamText(assistantMessage, target, quotedMatch[1])
          }
          handledProtocolText = true
          break
        }

        const rawMatch = line.match(new RegExp(`^${prefix}:\\s*(.*)$`))
        if (!rawMatch) continue

        let contentPart = rawMatch[1]

        if (contentPart.startsWith('"')) {
          if (contentPart.endsWith('"') && contentPart.length >= 2) {
            try {
              const text = JSON.parse(contentPart)
              appendStreamText(assistantMessage, target, text)
              handledProtocolText = true
              break
            } catch (e) {
              // Failed to parse, strip quotes and treat as raw
              contentPart = contentPart.substring(1, contentPart.length - 1)
            }
          } else {
            // Starts with " but NO end " - Enter MultiLine Mode
            contentPart = contentPart.substring(1)
            context.multiLineTarget = target
            appendStreamText(assistantMessage, target, contentPart)
            handledProtocolText = true
            break
          }
        }

        const text = contentPart.replace(/\\n/g, '\n')
        appendStreamText(assistantMessage, target, text)
        handledProtocolText = true
        break
      }
      if (handledProtocolText) continue

      // 2c. Tool Events (2:)
      if (line.startsWith('2:')) {
        try {
          const jsonStr = line.substring(2).trim()
          const events = JSON.parse(jsonStr)
          
          if (Array.isArray(events)) {
            for (const event of events) {
              handleToolEvent(event, assistantMessage)
            }
          } else if (typeof events === 'object' && events !== null) {
            handleToolEvent(events, assistantMessage)
          }
        } catch (e) {
          console.error('Failed to parse tool event:', e)
        }
        continue;
      }
      
      // 2d. JSON Format (e.g. DeepAgent)
      if (line.startsWith('{') && line.endsWith('}')) {
        try {
          const jsonObj = JSON.parse(line);
          if (typeof jsonObj.current_stage === 'string' && jsonObj.current_stage.trim()) {
            assistantMessage.stage = jsonObj.current_stage.trim()
          } else if (typeof jsonObj.stage === 'string' && jsonObj.stage.trim()) {
            assistantMessage.stage = jsonObj.stage.trim()
          }

          const todos = normalizeTodos(jsonObj.todo_list ?? jsonObj.todos)
          if (todos) {
            assistantMessage.todos = todos
          }

          if (typeof jsonObj.content === 'string') {
            assistantMessage.content += jsonObj.content;
            appendContentBlock(assistantMessage, jsonObj.content);
            continue;
          }
        } catch (e) {
          // Ignore and fall through to fallback
        }
      }

      // 3. Fallback (Raw text line)
      // For raw text fallback, we should restore newline if it's not the first line
      const textToAppend = (assistantMessage.content ? '\n' : '') + rawLine;
      assistantMessage.content += textToAppend;
      appendContentBlock(assistantMessage, textToAppend);
    }
  }

  const handleToolEvent = (event: any, assistantMessage: Message) => {
    if (!assistantMessage.tool_calls) {
      assistantMessage.tool_calls = []
    }

    if (event.type === 'tool_start') {
      // Check if already exists (deduplication)
      const exists = assistantMessage.tool_calls.some(t => t.id === event.run_id)
      if (exists) return

      const toolCall: ToolCall = {
        id: event.run_id || `call-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        type: 'function',
        function: {
          name: event.tool || 'unknown',
          arguments: JSON.stringify(event.input || {})
        },
        status: 'executing'
      }
      assistantMessage.tool_calls.push(toolCall)
      appendToolBlock(assistantMessage, toolCall.id)
    } else if (event.type === 'tool_end') {
      const toolCall = assistantMessage.tool_calls.find(t => t.id === event.run_id)

      console.log('[Orchestrator][tool_end] event.run_id:', event.run_id, 'toolCall found:', !!toolCall, 'tool:', event.tool)

      if (toolCall) {
        toolCall.status = 'completed'
        appendToolBlock(assistantMessage, toolCall.id)

        // Extract content
        let outputContent = event.output || ''

        // 诊断：execute 工具的原始输出（在字符串化之前）
        if (event.tool === 'execute') {
          const outputType = typeof outputContent
          const isObj = outputType === 'object' && outputContent !== null
          console.log('[Orchestrator][tool_end] execute raw output type:', outputType,
            'isObj:', isObj,
            'keys:', isObj ? Object.keys(outputContent) : 'N/A',
            'preview:', isObj ? JSON.stringify(outputContent).substring(0, 300) : String(outputContent).substring(0, 300)
          )
        }

        // 如果 event.output 是对象而不是字符串，尝试直接提取 markdown 字段
        if (typeof outputContent === 'object' && outputContent !== null) {
          const obj = outputContent as any
          // 直接检查 markdown 字段（含嵌套）
          if (obj.markdown && typeof obj.markdown === 'string') {
            outputContent = obj.markdown
          } else if (event.tool === 'execute') {
            // 搜索嵌套的 markdown 字段
            const nestedMd = obj.result?.markdown || obj.output?.markdown || obj.data?.markdown
            if (nestedMd && typeof nestedMd === 'string') {
              outputContent = nestedMd
            } else {
              outputContent = JSON.stringify(outputContent)
            }
          } else {
            outputContent = JSON.stringify(outputContent)
          }
        }

        const rawLength = outputContent.length
        const rawHasMap = outputContent.includes('```map')

        // 先尝试 JSON 解析（优先，避免 content='...' 匹配到错误的工具输出）
        let jsonExtracted = false
        try {
          const parsed = JSON.parse(outputContent)
          if (parsed && typeof parsed === 'object') {
            if (parsed.markdown) {
              // 直接包含 markdown 字段
              outputContent = parsed.markdown
              jsonExtracted = true
            } else if (event.tool === 'execute') {
              // execute 工具可能将 skill 结果包装在嵌套对象中
              // 递归搜索包含 ```map 的 markdown 字段（最多 3 层深度）
              const foundMarkdown = (function findMarkdown(obj: any, depth: number): string | null {
                if (depth > 3 || !obj || typeof obj !== 'object') return null
                for (const key of Object.keys(obj)) {
                  if (key === 'markdown' && typeof obj[key] === 'string') return obj[key]
                  if (typeof obj[key] === 'object' && obj[key] !== null) {
                    const result = findMarkdown(obj[key], depth + 1)
                    if (result) return result
                  }
                }
                return null
              })(parsed, 0)
              if (foundMarkdown) {
                outputContent = foundMarkdown
                jsonExtracted = true
                console.log('[Orchestrator][tool_end] execute: extracted markdown from nested JSON')
              } else {
                console.log('[Orchestrator][tool_end] execute: JSON keys:', Object.keys(parsed), 'no markdown field found')
              }
            }
          }
        } catch (_) {
          // 不是 JSON，保持原样
        }

        // 如果 JSON 提取失败，尝试 content='...' 提取
        if (!jsonExtracted) {
          const contentMatch = outputContent.match(/content='([\s\S]*?)'(\s+name=|$)/)
          if (contentMatch) {
            outputContent = contentMatch[1]
          }
        }

        // ===== 关键修复：处理字面量 \n 转义 =====
        // 某些 orchestrator 后端将换行符作为字面量 \n（两个字符 \ + n）发送，
        // 而非真正的换行符（一个字符）。这导致 artifactParser 的正则无法匹配 ```map 代码块。
        const hasLiteralBackslashN = outputContent.includes('\\n')
        const hasRealNewline = outputContent.includes('\n')
        if (hasLiteralBackslashN && !hasRealNewline) {
          console.log('[Orchestrator][tool_end] 检测到字面量 \\n，正在转换为真正的换行符')
          outputContent = outputContent
            .replace(/\\n/g, '\n')
            .replace(/\\t/g, '\t')
            .replace(/\\\\/g, '\\')
            .replace(/\\"/g, '"')  // 修复 execute 工具输出的双重转义（\" → "）
        } else if (hasRealNewline && outputContent.includes('\\"')) {
          // execute 工具输出混合了 console.log（真实换行）和 JSON 结果（双重转义 \"、\\）
          // 需要 unescape 才能让 map block 的 JSON.parse 成功
          console.log('[Orchestrator][tool_end] 检测到双重转义内容（真实换行 + \\"），正在 unescape')
          outputContent = outputContent
            .replace(/\\"/g, '"')
            .replace(/\\\\/g, '\\')
        }

        console.log('[Orchestrator][tool_end] tool:', event.tool, 'rawLen:', rawLength, 'rawHasMap:', rawHasMap, 'jsonExtracted:', jsonExtracted, 'finalLen:', outputContent.length, 'hasMap:', outputContent.includes('```map'), 'hasRealNewline:', outputContent.includes('\n'))

        // 诊断日志：输出 execute 工具的实际内容，帮助定位 map 数据缺失问题
        if (event.tool === 'execute') {
          console.log('[Orchestrator][tool_end] execute output (first 500):', outputContent.substring(0, 500))
          console.log('[Orchestrator][tool_end] execute output (last 300):', outputContent.substring(outputContent.length - 300))
        }

        // 检测 map 代码块：处理所有工具的输出
        // 通过严格的 JSON 验证来区分真实的地图配置数据和源代码中的模板字面量
        // - 真实地图数据：JSON 有效，含 type:'map'/queryParams/center 字段
        // - 源代码片段：JSON 无效（含 JS 语法、变量引用等），被过滤掉
        const mapBlockMatch = outputContent.match(/```map\n([\s\S]*?)```/);

        if (mapBlockMatch && assistantMessage) {
          let mapJson = mapBlockMatch[1].trim();
          // 修复 skill 模板字面量闭合 fence 前的反斜杠
          if (mapJson.endsWith('\\')) mapJson = mapJson.slice(0, -1).trim();
          // 严格 JSON 验证：确保是有效的地图配置，而非源代码片段
          let isValidMapConfig = false;
          try {
            const parsed = JSON.parse(mapJson);
            isValidMapConfig = parsed && (parsed.type === 'map' || parsed.queryParams || parsed.center);
          } catch (_) {
            // 不是有效 JSON，跳过
          }
          if (isValidMapConfig) {
            const mapBlock = `\n\n\`\`\`map\n${mapJson}\n\`\`\`\n`;
            if (!assistantMessage.content.includes(mapJson)) {
              assistantMessage.content += mapBlock;
              appendContentBlock(assistantMessage, mapBlock);
              console.log('[Orchestrator][tool_end] ✅ map block injected into assistant message, jsonLen:', mapJson.length)
            }
          } else {
            console.log('[Orchestrator][tool_end] ⚠️ standard regex matched but content is not valid map JSON, skipping')
          }
        } else if (outputContent.includes('```map')) {
          // 回退：标准正则失败，尝试更宽松的匹配
          // 使用 matchAll 取最后一个匹配（跳过源代码中的模板字面量，取实际查询结果）
          console.log('[Orchestrator][tool_end] 标准正则未匹配，尝试回退正则')
          const fallbackRegex = /```map[\s\\n]*([\s\S]*?)(?:```|$)/g;
          const allMatches = [...outputContent.matchAll(fallbackRegex)];
          const fallbackMatch = allMatches.length > 0 ? allMatches[allMatches.length - 1] : null;
          if (fallbackMatch) {
            let jsonContent = fallbackMatch[1].replace(/\\n/g, '\n').replace(/\\t/g, '\t').replace(/\\\\/g, '\\').trim();
            // 修复 skill 模板字面量 \`\`\`map 产生的前导/尾随反斜杠
            // skill 代码: `\n\`\`\`map\n{JSON}\n\`\`\`\n` 渲染后闭合 fence 前有 \
            if (jsonContent.endsWith('\\')) {
              jsonContent = jsonContent.slice(0, -1).trim();
            }
            // 验证提取的内容是有效的 JSON 地图配置（不是源代码片段）
            let isValidMapConfig = false;
            try {
              const parsed = JSON.parse(jsonContent);
              isValidMapConfig = parsed && (parsed.type === 'map' || parsed.queryParams || parsed.center);
            } catch (_) {
              // 不是有效 JSON，跳过注入
            }
            if (isValidMapConfig) {
              const mapBlock = `\n\n\`\`\`map\n${jsonContent}\n\`\`\`\n`;
              if (!assistantMessage.content.includes('```map')) {
                assistantMessage.content += mapBlock;
                appendContentBlock(assistantMessage, mapBlock);
                console.log('[Orchestrator][tool_end] ✅ map block injected via fallback regex (validated JSON)')
              }
            } else {
              console.log('[Orchestrator][tool_end] ⚠️ fallback regex matched but content is not valid map JSON, skipping injection')
              console.log('[Orchestrator][tool_end] fallback extracted (first 300):', jsonContent.substring(0, 300))
              // 二次尝试：从提取的内容中查找完整的 JSON 对象
              const jsonObjMatch = jsonContent.match(/\{[\s\S]*"type"\s*:\s*"map"[\s\S]*\}/);
              if (jsonObjMatch) {
                try {
                  const parsed2 = JSON.parse(jsonObjMatch[0]);
                  if (parsed2 && parsed2.type === 'map') {
                    const cleanJson = JSON.stringify(parsed2, null, 2);
                    const mapBlock = `\n\n\`\`\`map\n${cleanJson}\n\`\`\`\n`;
                    if (!assistantMessage.content.includes('```map')) {
                      assistantMessage.content += mapBlock;
                      appendContentBlock(assistantMessage, mapBlock);
                      console.log('[Orchestrator][tool_end] ✅ map block injected via JSON object extraction (second chance)')
                    }
                  }
                } catch (e2: any) {
                  console.log('[Orchestrator][tool_end] second chance JSON parse also failed:', e2?.message)
                }
              }
            }
          }
        }

        // 最终兜底：如果以上都未注入 map block，直接在输出中搜索包含 "type":"map" 的 JSON 对象
        if (!assistantMessage.content.includes('```map') && outputContent.includes('"type"')) {
          const directJsonMatch = outputContent.match(/\{[\s\S]*?"type"\s*:\s*"map"[\s\S]*?\}\s*(?=\n*\\n*`|$)/);
          if (directJsonMatch) {
            try {
              const parsed3 = JSON.parse(directJsonMatch[0].trim());
              if (parsed3 && parsed3.type === 'map' && (parsed3.queryParams || parsed3.center)) {
                const cleanJson = JSON.stringify(parsed3, null, 2);
                const mapBlock = `\n\n\`\`\`map\n${cleanJson}\n\`\`\`\n`;
                assistantMessage.content += mapBlock;
                appendContentBlock(assistantMessage, mapBlock);
                console.log('[Orchestrator][tool_end] ✅ map block injected via direct JSON search (final fallback)')
              }
            } catch (e3: any) {
              console.log('[Orchestrator][tool_end] direct JSON search failed:', e3?.message)
            }
          }
        }

        // Check if tool result message already exists
        const resultExists = messages.value.some(
          m => m.role === 'tool' && m.tool_call_id === toolCall.id
        )

        if (!resultExists) {
          const toolMessage: Message = {
            role: 'tool',
            content: outputContent,
            tool_call_id: toolCall.id,
            uiKey: createUiKey()
          }
          messages.value.push(toolMessage)
        }
      }
    } else if (event.type === 'todos') {
      const todos = normalizeTodos(event.todos ?? event.todo_list)
      if (todos) {
        assistantMessage.todos = todos
      }
    } else if (event.type === 'stage') {
      if (event.stage) {
        assistantMessage.stage = event.stage
      } else if (event.current_stage) {
        assistantMessage.stage = event.current_stage
      }
    } else if (event.type === 'progress' || event.type === 'update') {
      const todos = normalizeTodos(event.todos ?? event.todo_list)
      if (todos) {
        assistantMessage.todos = todos
      }
      const stage = event.current_stage || event.stage
      if (typeof stage === 'string' && stage.trim()) {
        assistantMessage.stage = stage.trim()
      }
    } else if (event.type === 'interrupt') {
      if (event.message && event.message !== 'false') {
        assistantMessage.interrupt = {
          type: 'interrupt',
          message: event.message,
          run_id: event.run_id,
          thread_id: event.thread_id
        }
      }
    }
  }

  const resolveUrl = () => {
    try {
      const cfg = StorageService.getActiveAgent()
      const url = (cfg?.orchestrator?.serviceUrl) || (cfg?.config?.orchestrator?.serviceUrl)
      return (typeof url === 'string' ? url.replace(/`/g, '').trim() : '')
    } catch {
      return ''
    }
  }

  const updateUrl = () => {
    orchestratorUrl.value = resolveUrl()
  }

  // Initialize URL and listeners
  updateUrl()
  window.addEventListener('active-agent-updated', updateUrl)
  window.addEventListener('agent-selection-changed', updateUrl)

  async function _performRequest(
    url: string,
    body: any,
    assistantMessage: Message,
    additionalHeaders?: Record<string, string>,
    requestMeta?: { agentType?: 'orchestrator' | 'assistant' | 'deepagent'; resume?: boolean }
  ): Promise<boolean> {
    const generation = sessionGeneration
    const isCurrent = () => generation === sessionGeneration
    assistantMessage.taskStartedAt ||= Date.now()
    assistantMessage.taskFinishedAt = undefined
    const requestController = new AbortController()
    activeRequestController = requestController
    activeAssistantMessage = assistantMessage
    activeRequestAgentType = requestMeta?.agentType || null
    interruptRequested = false

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...additionalHeaders
      }
      const response = await fetch(url, {
        method: requestMeta?.resume ? 'GET' : 'POST',
        headers,
        body: requestMeta?.resume ? undefined : JSON.stringify(body),
        signal: requestController.signal
      })

      if (!isCurrent()) return false
      if (requestMeta?.resume && response.status === 404) {
        assistantMessage.isStreaming = false
        return true
      }
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      
      const context: ProcessContext = { multiLineTarget: null }
      
      if (reader) {
        for (;;) {
          const { done, value } = await reader.read()
          if (!isCurrent()) return false
          if (done) break
          const chunkText = decoder.decode(value, { stream: true })
          buffer += chunkText
          const parts = buffer.split(/\r?\n/)
          buffer = parts.pop() || ''
          for (const part of parts) {
            if (!part) continue
            processResponse(part, assistantMessage, context)
          }
          messages.value = [...messages.value]
        }
        if (buffer.trim()) {
          processResponse(buffer, assistantMessage, context)
        }
      } else {
        const raw = await response.text()
        if (!isCurrent()) return false
        processResponse(raw, assistantMessage, context)
      }
      if (interruptRequested) {
        markAssistantMessageStopped(assistantMessage)
      } else {
        finishTaskTiming(assistantMessage)
        assistantMessage.isStreaming = false
      }
      // 工具注入 + AI 回复可能各带一个 map block，去重只保留第一个
      deduplicateMapBlocks(assistantMessage)
      messages.value = [...messages.value]
      return true
    } catch (e: any) {
      if (!isCurrent()) return false
      if (interruptRequested || e?.name === 'AbortError') {
        markAssistantMessageStopped(assistantMessage)
        return true
      }
      NotificationService.error(`请求失败: ${e}`)
      finishTaskTiming(assistantMessage)
      assistantMessage.isStreaming = false
      assistantMessage.content += '\n[请求出错]'
      messages.value = [...messages.value]
      return false
    } finally {
      if (activeRequestController === requestController) {
        activeRequestController = null
        activeAssistantMessage = null
        activeRequestAgentType = null
      }
      if (isCurrent()) isProcessing.value = false
    }
  }

  async function send(content: string, displayContent?: string, kbCitations?: any[], skipPush: boolean = false, turnId?: string): Promise<boolean> {
    if (!orchestratorUrl.value) {
      NotificationService.error('未配置编排式智能体服务 URL')
      return false
    }

    try {
      ensureAuthenticatedRequestAllowed(orchestratorUrl.value)
    } catch {
      return false
    }

    if (!content.trim()) return false

    isProcessing.value = true

    if (!skipPush) {
      messages.value.push({ role: 'user', content, display_content: displayContent || content, uiKey: createUiKey() })
      // 先推入消息，然后获取响应式对象
      messages.value.push({ role: 'assistant', content: '', isStreaming: true, uiKey: createUiKey(), orchestratorBlocks: [], kb_citations: kbCitations })
    } else if (kbCitations && messages.value.length > 0) {
      // 如果 skipPush 为 true，但传入了 kbCitations，则更新最后一个消息的 kb_citations
      const lastMessage = messages.value[messages.value.length - 1];
      if (lastMessage && lastMessage.role === 'assistant') {
        lastMessage.kb_citations = kbCitations;
      }
    }
    const assistantMessage = messages.value[messages.value.length - 1]

    const apiMessages = messages.value.slice(0, -1).map(m => ({
      role: m.role,
      content: m.content
    }))

    return _performRequest(orchestratorUrl.value, {
      messages: apiMessages,
      session_thread_id: sessionThreadId.value,
      turn_id: turnId
    }, assistantMessage, undefined, { agentType: 'orchestrator' })
  }

  async function retry(): Promise<boolean> {
    if (!orchestratorUrl.value) {
      NotificationService.error('未配置编排式智能体服务 URL')
      return false
    }
    try {
      ensureAuthenticatedRequestAllowed(orchestratorUrl.value)
    } catch {
      return false
    }
    if (isProcessing.value) return false
    isProcessing.value = true
    // 仅推入新的智能体流式消息，不添加用户消息
    messages.value.push({ role: 'assistant', content: '', isStreaming: true, uiKey: createUiKey() })
    const assistantMessage = messages.value[messages.value.length - 1]
    
    const apiMessages = messages.value.slice(0, -1).map(m => ({
      role: m.role,
      content: m.content
    }))
    
    return _performRequest(orchestratorUrl.value, {
      messages: apiMessages,
      session_thread_id: sessionThreadId.value
    }, assistantMessage, undefined, { agentType: 'orchestrator' })
  }

  async function sendToAgent(content: string, agentId: string, displayContent?: string, kbCitations?: any[], skipPush: boolean = false, turnId?: string): Promise<boolean> {
    const baseUrl = getApiBaseUrl()
    if (!baseUrl) {
      NotificationService.error('未配置 API 基础 URL')
      return false
    }
    const url = `${baseUrl.replace(/\/+$/, '')}/skill/api/agent/chat`

    try {
      ensureAuthenticatedRequestAllowed(url)
    } catch {
      return false
    }

    if (!content.trim()) return false
    if (!agentId) {
      NotificationService.error('未找到智能体 ID')
      return false
    }

    isProcessing.value = true

    if (!skipPush) {
      // 常规智能体的消息历史也需要维护
      messages.value.push({ role: 'user', content, turn_id: turnId, display_content: displayContent || content, uiKey: createUiKey() })
      messages.value.push({ role: 'assistant', content: '', turn_id: turnId, isStreaming: true, uiKey: createUiKey(), orchestratorBlocks: [], kb_citations: kbCitations })
    } else if (kbCitations && messages.value.length > 0) {
      const lastMessage = messages.value[messages.value.length - 1];
      if (lastMessage && lastMessage.role === 'assistant') {
        lastMessage.kb_citations = kbCitations;
      }
    }
    const assistantMessage = messages.value[messages.value.length - 1]

    // 构造 payload
    const apiMessages = [{
      role: 'user',
      content: content
    }]

    const token = StorageService.getAccessToken()
    const additionalHeaders: Record<string, string> = {}
    if (token) {
      additionalHeaders['Authorization'] = `Bearer ${token}`
    }

    const raw = localStorage.getItem('user-profile')
    const userId = raw ? (JSON.parse(raw).uuid || '') : ''

    return _performRequest(url, {
      uuid: agentId,
      user_id: userId,
      messages: apiMessages,
      session_id: sessionThreadId.value,
      session_thread_id: sessionThreadId.value,
      turn_id: turnId
    }, assistantMessage, additionalHeaders, { agentType: 'assistant' })
  }

  async function sendToDeepAgent(content: string, agentId: string, filePaths: string[], displayContent?: string, kbCitations?: any[], skipPush: boolean = false, turnId?: string): Promise<boolean> {
    const baseUrl = getApiBaseUrl()
    if (!baseUrl) {
      NotificationService.error('未配置 API 基础 URL')
      return false
    }
    const url = `${baseUrl.replace(/\/+$/, '')}/skill/api/deepagent/chat`

    try {
      ensureAuthenticatedRequestAllowed(url)
    } catch {
      return false
    }

    if (!content.trim() && (!filePaths || filePaths.length === 0)) return false
    if (!agentId) {
      NotificationService.error('未找到智能体ID')
      return false
    }

    // 对话开始前记录沙箱文件基线，结束后用于 diff 出新增交付文件
    useSandboxFilesStore().beginTurn(sessionThreadId.value)

    isProcessing.value = true

    if (!skipPush) {
      messages.value.push({ role: 'user', content, turn_id: turnId, display_content: displayContent || content, uiKey: createUiKey() })
      messages.value.push({ role: 'assistant', content: '', turn_id: turnId, isStreaming: true, uiKey: createUiKey(), orchestratorBlocks: [], kb_citations: kbCitations })
    } else if (kbCitations && messages.value.length > 0) {
      const lastMessage = messages.value[messages.value.length - 1];
      if (lastMessage && lastMessage.role === 'assistant') {
        lastMessage.kb_citations = kbCitations;
      }
    }
    const assistantMessage = messages.value[messages.value.length - 1]

    const apiMessages = [{
      role: 'user',
      content: content || '分析文件' // 给一个默认的内容，防止为空时后端报错
    }]

    const token = StorageService.getAccessToken()
    const additionalHeaders: Record<string, string> = {}
    if (token) {
      additionalHeaders['Authorization'] = `Bearer ${token}`
    }

    const raw = localStorage.getItem('user-profile')
    const userId = raw ? (JSON.parse(raw).uuid || '') : ''

    const sendingSessionId = sessionThreadId.value
    const ok = await _performRequest(url, {
      session_thread_id: sessionThreadId.value,
      uuid: agentId,
      user_id: userId,
      messages: apiMessages,
      file_paths: filePaths,
      turn_id: turnId
    }, assistantMessage, additionalHeaders, { agentType: 'deepagent' })

    // 对话结束后刷新沙箱文件清单，并通知画布“交付中心”
    if (ok && sessionThreadId.value === sendingSessionId) {
      const sandboxFilesStore = useSandboxFilesStore()
      await sandboxFilesStore.fetchFiles(sendingSessionId)
      if (sessionThreadId.value !== sendingSessionId) return ok
      eventBus.emit(MCP_EVENTS.SANDBOX_FILES_UPDATED, {
        added: sandboxFilesStore.lastAdded,
        files: sandboxFilesStore.files
      })
    }
    return ok
  }

  function detachCurrentRequest() {
    sessionGeneration++
    activeRequestController?.abort()
    activeRequestController = null
    activeAssistantMessage = null
    activeRequestAgentType = null
    isProcessing.value = false
    useSandboxFilesStore().clear()
  }

  async function resumeStream(type: string, turnId: string, createdAt?: number) {
    const assistant: Message = { role: 'assistant', content: '', turn_id: turnId, isStreaming: true, uiKey: createUiKey(), orchestratorBlocks: [], taskStartedAt: createdAt ? createdAt * 1000 : Date.now() }
    messages.value.push(assistant)
    isProcessing.value = true
    const target = messages.value[messages.value.length - 1]
    return _performRequest(streamUrl(type, 'resume', sessionThreadId.value), undefined, target, streamHeaders(), { resume: true, agentType: type === 'deepagent' ? 'deepagent' : type === 'agent' ? 'assistant' : 'orchestrator' })
  }

  async function stopCurrentRequest(): Promise<boolean> {
    const controller = activeRequestController
    const generation = sessionGeneration
    if (!isProcessing.value || !activeRequestController) {
      return false
    }

    const currentSessionThreadId = (sessionThreadId.value || '').trim()
    if (!currentSessionThreadId) {
      throw new Error('未找到当前会话 ID')
    }

    await http.post('/skill/api/chat/interrupt', {
      session_thread_id: currentSessionThreadId
    })

    if (generation !== sessionGeneration || controller !== activeRequestController) return true
    interruptRequested = true
    markAssistantMessageStopped()
    controller?.abort()
    return true
  }

  function regenerateSessionThreadId(): string {
    sessionGeneration++
    sessionThreadId.value = createSessionThreadId()
    StorageService.setWorkspaceSessionThreadId(sessionThreadId.value)
    logConversationSession('enter new conversation', sessionThreadId.value)
    return sessionThreadId.value
  }

  function setSessionThreadId(value?: string | null): string {
    sessionGeneration++
    const normalized = typeof value === 'string' ? value.trim() : ''
    sessionThreadId.value = normalized || createSessionThreadId()
    StorageService.setWorkspaceSessionThreadId(sessionThreadId.value)
    logConversationSession(normalized ? 'enter history conversation' : 'enter new conversation', sessionThreadId.value)
    return sessionThreadId.value
  }

  function replaceMessages(nextMessages: Message[]): void {
    const list = Array.isArray(nextMessages) ? nextMessages : []
    messages.value = list.map((message) => ({
      ...message,
      tool_calls: Array.isArray(message?.tool_calls)
        ? message.tool_calls.map((toolCall) => ({
            ...toolCall,
            function: toolCall?.function ? { ...toolCall.function } : toolCall?.function
          }))
        : message?.tool_calls,
      orchestratorBlocks: Array.isArray(message?.orchestratorBlocks)
        ? message.orchestratorBlocks.map((block) => (
            block?.type === 'tools'
              ? { ...block, toolCallIds: Array.isArray(block.toolCallIds) ? [...block.toolCallIds] : [] }
              : { ...block }
          ))
        : message?.orchestratorBlocks,
      files: Array.isArray(message?.files) ? message.files.map((file) => ({ ...file })) : message?.files,
      kb_citations: Array.isArray(message?.kb_citations)
        ? message.kb_citations.map((citation) => ({ ...citation }))
        : message?.kb_citations,
      todos: Array.isArray(message?.todos) ? message.todos.map((todo) => ({ ...todo })) : message?.todos
    }))
  }

  /**
   * 启动（或复用）指定会话 ID 的沙盒容器。
   * 容器与会话 ID 绑定且内容一致，可被任意智能体共用，因此支持预热备用容器。
   * 本函数只负责发起后端初始化请求，不改动当前会话状态。
   */
  async function startSandboxContainer(
    sessionThreadIdForContainer: string,
    agentUuid: string,
    options: { signal?: AbortSignal; silent?: boolean } = {}
  ): Promise<string> {
    const normalizedAgentUuid = String(agentUuid || '').trim()
    const normalizedSessionId = String(sessionThreadIdForContainer || '').trim()
    if (!normalizedSessionId) {
      throw new Error('沙盒会话 ID 不能为空')
    }
    if (!normalizedAgentUuid) {
      if (!options.silent) {
        NotificationService.error('未找到智能体 UUID')
      }
      throw new Error('智能体 UUID 不能为空')
    }

    const baseUrl = getApiBaseUrl()
    if (!baseUrl) {
      if (!options.silent) {
        NotificationService.error('未配置 API 基础 URL')
      }
      throw new Error('API base URL is required')
    }

    const externalSignal = options.signal
    if (externalSignal) {
      // 注册为静默取消信号：被抢占取消时不弹“网络异常”提示
      registerSilentAbortSignal(externalSignal)
    }

    await http.post('/aiChat/initialize', {
      sessionThreadId: normalizedSessionId,
      agentUuid: normalizedAgentUuid
    }, {
      timeout: 60000,
      signal: externalSignal,
      silentAbort: externalSignal ? externalSignal : !!options.silent,
      silentError: !!options.silent
    })

    return normalizedSessionId
  }

  /** 已发起释放的会话 ID，避免同一容器被重复释放 */
  const releasingSessionIds = new Set<string>()

  /**
   * 后台静默释放沙盒容器：同步返回，不阻塞调用方、不弹错误提示、不占用全局 loading。
   * 释放只用于回收资源，失败不影响前端后续流程，因此 fire-and-forget 即可。
   */
  function releaseSandboxContainer(sessionThreadIdForRelease: string): Promise<void> {
    const normalizedSessionId = String(sessionThreadIdForRelease || '').trim()
    if (!normalizedSessionId || releasingSessionIds.has(normalizedSessionId)) return Promise.resolve()

    releasingSessionIds.add(normalizedSessionId)
    return http.post('/skill/api/deepagent/release', {
      session_thread_id: normalizedSessionId
    }, {
      timeout: 15000,
      silentAbort: true,
      silentError: true
    })
      .then(() => {})
      .catch((error: unknown) => {
        console.warn('后台释放沙盒容器失败（已忽略）:', normalizedSessionId, error)
      })
      .finally(() => {
        releasingSessionIds.delete(normalizedSessionId)
      })
  }

  /**
   * 初始化智能体会话
   * @param agentUuid 智能体 UUID
   * @param existingSessionThreadId 复用已有会话 ID（打开历史记录/预热容器时使用），不传则新建
   * @param options signal 可抢占取消；silent 时失败不弹全局提示
   */
  async function initializeAgentSession(
    agentUuid: string,
    existingSessionThreadId?: string,
    options: { signal?: AbortSignal; silent?: boolean } = {}
  ): Promise<string> {
    // 会话 ID 在请求前同步落地：新对话复用现有 ID，切换智能体无需等待容器启动完成。
    const nextSessionThreadId = String(existingSessionThreadId || '').trim() || createSessionThreadId()
    sessionGeneration++
    sessionThreadId.value = nextSessionThreadId
    StorageService.setWorkspaceSessionThreadId(nextSessionThreadId)
    logConversationSession(existingSessionThreadId ? 'enter conversation' : 'enter new conversation', nextSessionThreadId)

    await startSandboxContainer(nextSessionThreadId, agentUuid, options)
    return nextSessionThreadId
  }

  return {
    orchestratorUrl,
    messages,
    isProcessing,
    sessionThreadId,
    send,
    retry,
    sendToAgent,
    sendToDeepAgent,
    stopCurrentRequest,
    detachCurrentRequest,
    resumeStream,
    initializeAgentSession,
    startSandboxContainer,
    releaseSandboxContainer,
    regenerateSessionThreadId,
    setSessionThreadId,
    replaceMessages,
    clear: (options?: { regenerateSessionThreadId?: boolean }) => {
      sessionGeneration++
      const shouldRegenerateSessionThreadId = options?.regenerateSessionThreadId !== false
      messages.value = []
      isProcessing.value = false
      useSandboxFilesStore().clear()
      if (shouldRegenerateSessionThreadId) {
        regenerateSessionThreadId()
      } else {
        StorageService.setWorkspaceSessionThreadId(sessionThreadId.value)
      }
    }
  }
}
