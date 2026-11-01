import type { Message } from '@/types/mcp';

const CACHE_KEY = 'mcp-task-timings-v1';
type Timing = { taskStartedAt: number; taskFinishedAt: number };
const valid = (value: any): value is Timing => Number.isFinite(value?.taskStartedAt)
  && Number.isFinite(value?.taskFinishedAt) && value.taskFinishedAt >= value.taskStartedAt;

export function readTaskTiming(message: Message): Timing | undefined {
  if (valid(message)) return message;
  const key = message.tool_calls?.[0]?.id || message.turn_id;
  if (!key) return;
  try {
    const cached = JSON.parse(localStorage.getItem(CACHE_KEY) || '{}')[key];
    if (valid(cached)) return cached;
  } catch { /* Missing or unavailable local cache. */ }
}

export function finishTaskTiming(message: Message, now = Date.now()) {
  if (!Number.isFinite(message.taskStartedAt)) return;
  message.taskFinishedAt = Math.max(message.taskStartedAt!, now);
  const key = message.tool_calls?.[0]?.id || message.turn_id;
  if (!key) return;
  try {
    const raw = JSON.parse(localStorage.getItem(CACHE_KEY) || '{}');
    const entries = Object.entries(raw).filter(([id, timing]) => id !== key && valid(timing)).slice(-299);
    entries.push([key, { taskStartedAt: message.taskStartedAt, taskFinishedAt: message.taskFinishedAt }]);
    localStorage.setItem(CACHE_KEY, JSON.stringify(Object.fromEntries(entries)));
  } catch { /* Timing on the message remains available if storage is blocked. */ }
}

export function formatTaskDuration(start: number, end: number): string {
  const seconds = Math.max(0, Math.floor((end - start) / 1000));
  return seconds >= 60 ? `${Math.floor(seconds / 60)}m ${seconds % 60}s` : `${seconds}s`;
}
