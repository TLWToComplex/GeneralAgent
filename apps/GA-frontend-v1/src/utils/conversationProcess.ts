import type { OrchestratorBlock, ToolCall } from '@/types/mcp';
import { getToolPresentation, resolveToolServer } from './toolPresentation';

type ProcessEntry = { block: OrchestratorBlock; index: number };
export type ProcessSection =
  | { type: 'content'; key: string; content: string }
  | { type: 'process'; key: string; entries: ProcessEntry[]; toolCallIds: string[] };

export function groupProcessBlocks(blocks: OrchestratorBlock[]): ProcessSection[] {
  const sections: ProcessSection[] = [];
  blocks.forEach((block, index) => {
    if (block.type === 'content') {
      sections.push({ type: 'content', key: `content-${index}`, content: block.content });
      return;
    }
    let section = sections[sections.length - 1];
    if (!section || section.type !== 'process') {
      section = { type: 'process', key: `process-${index}`, entries: [], toolCallIds: [] };
      sections.push(section);
    }
    section.entries.push({ block, index });
    if (block.type === 'tools') {
      for (const id of block.toolCallIds) {
        if (!section.toolCallIds.includes(id)) section.toolCallIds.push(id);
      }
    }
  });
  return sections;
}

export function summarizeProcessTools(tools: ToolCall[], streaming: boolean): string {
  const counts = new Map<string, number>();
  for (const tool of tools) {
    const info = getToolPresentation(tool, resolveToolServer(tool));
    const prefix = tool.status === 'completed' ? '已'
      : tool.status === 'failed' ? '未能'
      : streaming ? (tool.status === 'executing' ? '正在' : '待') : '未完成';
    const key = `${prefix}${info.action}|${info.unit}`;
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  return [...counts].map(([key, count]) => {
    const [action, unit] = key.split('|');
    return `${action} ${count} ${unit}`;
  }).join('，');
}
