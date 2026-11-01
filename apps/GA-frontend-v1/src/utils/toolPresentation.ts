import type { ToolCall } from '@/types/mcp';

export type ToolKind = 'read' | 'write' | 'search' | 'command' | 'browser' | 'mcp' | 'tool';
const clean = (value: unknown): string => typeof value === 'string' && !/^(unknown|unknow|null|undefined)$/i.test(value.trim()) ? value.trim() : '';

/** Resolve only known metadata; never invent a provider for an unqualified tool. */
export function resolveToolServer(tool: ToolCall, servers: Record<string, any> = {}): string {
  const id = clean(tool.server_id);
  const explicit = clean((tool as ToolCall & { server_name?: string }).server_name);
  if (explicit) return explicit;
  for (const [key, server] of Object.entries(servers)) {
    if (!server || typeof server !== 'object') continue;
    if ((tool.server_url && server.url === tool.server_url) || (id && [key, server.id, server.server_id].includes(id))) {
      return clean(server.name) || clean(server.server_name) || clean(key);
    }
  }
  if (id) return id;
  const match = tool.function?.name?.match(/^mcp__(.+?)__/);
  if (match) return match[1];
  const matches = Object.entries(servers).filter(([, server]) =>
    Array.isArray(server?.tools) && server.tools.some((entry: any) =>
      (typeof entry === 'string' ? entry : entry?.name || entry?.function?.name) === tool.function?.name));
  if (matches.length === 1) {
    const [key, server] = matches[0];
    return clean(server.name) || clean(server.server_name) || clean(key);
  }
  return '';
}

export function getToolPresentation(tool: ToolCall, server = '') {
  const name = clean(tool.function?.name) || '工具';
  let args: Record<string, any> = {};
  try { const value = JSON.parse(tool.function?.arguments || '{}'); if (value && typeof value === 'object') args = value; } catch { /* partial streaming JSON */ }
  let kind: ToolKind = 'tool';
  if (server || /^mcp[_-]/i.test(name)) kind = 'mcp';
  else if (/^(read_file|read|cat|ls|list_directory|glob)$/i.test(name)) kind = 'read';
  else if (/^(write_file|edit_file|create_file|apply_patch|str_replace)$/i.test(name)) kind = 'write';
  else if (/(search|browse_web|fetch_url)/i.test(name)) kind = 'search';
  else if (/(exec|shell|terminal|run_command)/i.test(name)) kind = 'command';
  else if (/(browser|playwright)/i.test(name)) kind = 'browser';
  const actions: Record<ToolKind, [string, string, string]> = {
    read: ['读取', '已读取', '个文件'], write: ['更新', '已更新', '个文件'],
    search: ['搜索', '已搜索', '次'], command: ['执行', '已执行', '条命令'],
    browser: ['操作浏览器', '已操作浏览器', '次浏览器操作'],
    mcp: ['调用', '已调用', '次 MCP'], tool: ['调用', '已调用', '个工具'],
  };
  const file = clean(args.file_path) || clean(args.path) || clean(args.filename);
  const detail = kind === 'read' || kind === 'write' ? file.split(/[\\/]/).pop()
    : kind === 'search' ? clean(args.query) || clean(args.q) || clean(args.keywords)
    : kind === 'command' ? clean(args.command) || clean(args.cmd) : '';
  const shortName = name.replace(/^mcp__.+?__/, '');
  return { kind, action: actions[kind][0], completed: actions[kind][1], unit: actions[kind][2], subject: server ? `${server} / ${shortName}` : detail || shortName, name };
}
