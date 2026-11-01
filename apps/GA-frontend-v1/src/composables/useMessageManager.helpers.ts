export type SessionFileContext = {
  filename: string;
  content: string;
};

export type KnowledgeSearchResult = {
  ragSystemPromptAddon: string;
  retrievedDocs?: any[];
};

export function buildKnowledgePromptAddon(docs: any[]): string {
  let addon = "你是一个专业的知识库问答助手。请根据以下从知识库中检索到的相关信息，回答用户的问题。\n\n<知识库信息>\n";

  docs.forEach((doc, index) => {
    const source = doc.metadata?.source ? ` (来源: ${doc.metadata.source})` : '';
    addon += `[片段 ${index + 1}]${source}\n${doc.page_content}\n\n`;
  });

  addon += "</知识库信息>\n\n";
  addon += "回答要求：\n";
  addon += "1. 请主要基于上述提供的知识库信息进行回答。\n";
  addon += "2. 如果知识库信息不足以回答问题，请如实说明，不要编造信息。\n";
  addon += "3. 在回答中可以适当引用信息来源。\n";
  return addon;
}

export function buildAgentMessageContent(content: string, ragSystemPromptAddon: string): string {
  return ragSystemPromptAddon ? `${ragSystemPromptAddon}\n用户问题：\n${content}` : content;
}

export type ParsedKbCitation = {
  page_content: string;
  metadata: { source: string };
};

/**
 * 从历史会话的 system 提示词中还原知识库引用片段，与 buildKnowledgePromptAddon 的输出格式互逆：
 * <知识库信息>
 * [片段 1] (来源: xxx.docx)
 * 片段内容...
 * </知识库信息>
 * 用于 /aiChatRecord/list 恢复历史时，接口未返回 kb_citations（空数组）时作为兜底，
 * 保证历史会话与实时知识库问答的“知识引用”面板展示一致。
 */
export function parseKbCitationsFromKnowledgePrompt(systemPrompt: string): ParsedKbCitation[] {
  if (!systemPrompt) return [];

  const blockMatch = systemPrompt.match(/<知识库信息>([\s\S]*?)<\/知识库信息>/);
  if (!blockMatch) return [];
  const block = blockMatch[1];

  const headerRe = /\[片段\s*\d+\]\s*(?:\(来源[:：]\s*([^)\n]*)\))?/g;
  const headers: Array<{ start: number; end: number; source: string }> = [];
  let match: RegExpExecArray | null;
  while ((match = headerRe.exec(block)) !== null) {
    headers.push({
      start: match.index,
      end: match.index + match[0].length,
      source: (match[1] || '').trim()
    });
  }
  if (headers.length === 0) return [];

  const citations: ParsedKbCitation[] = [];
  headers.forEach((header, i) => {
    const next = headers[i + 1];
    const pageContent = block
      .slice(header.end, next ? next.start : block.length)
      .replace(/^\n+|\n+$/g, '')
      .trim();
    if (!pageContent) return;
    citations.push({
      page_content: pageContent,
      metadata: { source: header.source }
    });
  });

  return citations;
}

export function extractSessionFileContexts(files?: any[]): SessionFileContext[] {
  if (!files || files.length === 0) return [];

  return files
    .filter((file) => file.parseResult && file.parseResult.document_chunks)
    .map((file) => {
      const chunks = file.parseResult.document_chunks;
      const fileContent = chunks.map((chunk: any) => chunk.content).join('\n\n');
      return {
        filename: file.name || 'unknown',
        content: fileContent
      };
    });
}

export function mergeSessionFileContexts(
  existingContexts: SessionFileContext[],
  newContexts: SessionFileContext[]
): SessionFileContext[] {
  const mergedContexts = [...existingContexts];

  newContexts.forEach((newFile) => {
    const exists = mergedContexts.some((existing) => existing.filename === newFile.filename);
    if (!exists) {
      mergedContexts.push(newFile);
    }
  });

  return mergedContexts;
}

export function buildDocumentsBlock(sessionFileContexts: SessionFileContext[]): string {
  return sessionFileContexts.map((doc, index) => (
    `【文档 ${index + 1}】文件名: ${doc.filename}\n${doc.content}`
  )).join('\n\n');
}

export function buildFinalSystemPrompt(params: {
  baseSystemPrompt: string;
  sessionFileContexts: SessionFileContext[];
  systemPromptAddons: string[];
  hasActiveAgent: boolean;
}): string {
  const {
    baseSystemPrompt,
    sessionFileContexts,
    systemPromptAddons,
    hasActiveAgent
  } = params;

  let finalSystemPrompt = baseSystemPrompt;

  if (sessionFileContexts.length > 0) {
    const docsBlock = buildDocumentsBlock(sessionFileContexts);

    if (hasActiveAgent) {
      finalSystemPrompt = `${finalSystemPrompt}\n\n以下是用户上传的文档内容，请基于此进行回答：\n\n<documents>\n${docsBlock}\n</documents>\n\n请结合上述文档内容完成任务。在回答涉及文档内容时，请遵循以下准则：\n1. **基于文档**：优先依据文档内容回答。\n2. **来源标注**：引用特定内容时请标注内容来源。\n3. **无知声明**：如果文档中没有相关信息，请如实说明。`;
    } else {
      finalSystemPrompt = `你是一位专业的文档分析助手。你的核心任务是基于用户上传的文档内容进行精准回答。

以下是用户当前会话中累积上传的文档内容：

<documents>
${docsBlock}
</documents>

请严格遵循以下回复准则：
1. **基于文档**：所有回答必须优先依据上述文档内容，严禁在文档未提及的情况下随意编造。
2. **来源标注**：如果回答引用了特定文档的内容，请在适当位置标注内容来源。
3. **多文档综合**：如果问题涉及多个文档，请综合相关信息进行对比或总结。
4. **无知声明**：如果文档中找不到问题的答案，请明确告知“文档中未包含相关信息”。`;
    }
  }

  systemPromptAddons.filter(Boolean).forEach((addon) => {
    finalSystemPrompt += `\n\n${addon}`;
  });

  return finalSystemPrompt;
}
