/**
 * 过程块统一状态机
 *
 * 思考（reasoning）、工具调用（tool call）、任务清单（todo）、审批（interrupt）
 * 本质上都是"过程性元信息"，共用同一套状态与视觉指示，避免各组件各写一套。
 */

/** 统一后的过程状态 */
export type ProcessStatus =
  | 'streaming'          // 参数 / 思考文本正在增量到达
  | 'pending'            // 已排队，尚未开始
  | 'running'            // 执行中（含思考中）
  | 'awaiting-approval'  // 等待用户确认（HITL）
  | 'completed'
  | 'error'
  | 'denied';

/** 指示器图形种类 */
export type IndicatorKind =
  | 'spinner'  // 细环旋转：进行中（光球只保留给思考块，避免多球同屏）
  | 'dot'      // 空心圆点：排队中
  | 'check'    // 对勾：完成
  | 'cross'    // 叉：失败
  | 'shield'   // 盾牌：待审批
  | 'ban';     // 禁止：已拒绝 / 已取消

export interface ProcessStatusMeta {
  /** 左侧指示器图形 */
  indicator: IndicatorKind;
  /** 标题文字是否带扫光（shimmer） */
  shimmer: boolean;
  /** 是否属于"进行中"，用于决定是否显示旋转指示与动效 */
  active: boolean;
  /** 默认是否展开：运行中 / 失败 / 待审批需要用户关注，故展开；完成后折叠降噪 */
  autoExpand: boolean;
  /** 中文状态文案 */
  label: string;
}

export const PROCESS_STATUS_META: Record<ProcessStatus, ProcessStatusMeta> = {
  'streaming': {
    indicator: 'spinner', shimmer: true, active: true, autoExpand: true, label: '生成中',
  },
  'pending': {
    indicator: 'dot', shimmer: false, active: false, autoExpand: false, label: '排队中',
  },
  'running': {
    indicator: 'spinner', shimmer: true, active: true, autoExpand: true, label: '执行中',
  },
  'awaiting-approval': {
    indicator: 'shield', shimmer: false, active: true, autoExpand: true, label: '等待确认',
  },
  'completed': {
    indicator: 'check', shimmer: false, active: false, autoExpand: false, label: '已完成',
  },
  'error': {
    indicator: 'cross', shimmer: false, active: false, autoExpand: true, label: '失败',
  },
  'denied': {
    indicator: 'ban', shimmer: false, active: false, autoExpand: false, label: '已拒绝',
  },
};

/** 后端历史字段（executing / failed / success）到统一状态的归一化 */
const LEGACY_STATUS_MAP: Record<string, ProcessStatus> = {
  executing: 'running',
  failed: 'error',
  success: 'completed',
  cancelled: 'denied',
  approved: 'completed',
  in_progress: 'running',
};

const VALID_STATUS: ProcessStatus[] = [
  'streaming', 'pending', 'running', 'awaiting-approval', 'completed', 'error', 'denied',
];

/**
 * 把任意来源的状态字符串归一化为 ProcessStatus
 * 兼容：后端旧字段、todo 的 in_progress、undefined
 */
export function normalizeProcessStatus(raw?: string | null): ProcessStatus {
  if (!raw) return 'pending';
  const lower = raw.trim().toLowerCase();
  if (LEGACY_STATUS_MAP[lower]) return LEGACY_STATUS_MAP[lower];
  if ((VALID_STATUS as string[]).includes(lower)) return lower as ProcessStatus;
  return 'pending';
}

/** 取状态元信息 */
export function getStatusMeta(status: ProcessStatus): ProcessStatusMeta {
  return PROCESS_STATUS_META[status];
}

/** 是否处于进行中（决定旋转指示、shimmer、高亮） */
export function isActiveStatus(status: ProcessStatus): boolean {
  return PROCESS_STATUS_META[status].active;
}

/**
 * 工具调用的展开策略
 *
 * 替代原先散落在各组件里的 hasContentAfterLastTool / autoCollapse* 等一系列 watch：
 * - 进行中（streaming / running / awaiting-approval）→ 展开，用户正在等它
 * - 失败 → 强制展开，用户需要看错误
 * - 完成 / 拒绝 → 折叠，降低消息流噪音
 * 用户手动操作过后（userToggled=true）不再被自动策略覆盖。
 */
export function shouldAutoExpand(status: ProcessStatus, userToggled = false): boolean {
  if (userToggled) return false;
  return PROCESS_STATUS_META[status].autoExpand;
}

/** 任务清单条目状态 → 统一状态 */
export function normalizeTodoStatus(raw?: string | null): ProcessStatus {
  const lower = (raw || '').trim().toLowerCase();
  if (lower === 'completed' || lower === 'done') return 'completed';
  if (lower === 'in_progress' || lower === 'running') return 'running';
  return 'pending';
}

/**
 * 毫秒耗时格式化：<1s 显示 ms，<1min 显示 s，其余显示 m s
 * 各工具组件原先各写了一份，统一到这里。
 */
export function formatDuration(duration?: number): string {
  if (duration === undefined || duration === null || Number.isNaN(duration)) return '';
  if (duration < 1000) return `${Math.round(duration)}ms`;
  if (duration < 60000) return `${(duration / 1000).toFixed(1)}s`;
  const minutes = Math.floor(duration / 60000);
  const seconds = Math.floor((duration % 60000) / 1000);
  return `${minutes}m ${seconds}s`;
}

/**
 * 工具参数格式化
 *
 * 流式传输过程中 JSON 是不完整的，JSON.parse 必然失败，
 * 此时直接原样返回，交给打字光标渲染，绝不能抛错。
 */
export function formatToolArguments(args?: string): string {
  if (!args) return '';
  const trimmed = args.trim();
  try {
    return JSON.stringify(JSON.parse(trimmed), null, 2);
  } catch {
    return trimmed;
  }
}

/** 参数是否仍在流式生成（JSON 不完整即为流式中） */
export function isArgumentsStreaming(args?: string, messageStreaming = true): boolean {
  if (!messageStreaming) return false;
  if (!args) return true;
  try {
    JSON.parse(args);
    return false;
  } catch {
    return true;
  }
}
