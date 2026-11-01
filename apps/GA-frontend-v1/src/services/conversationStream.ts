import StorageService from "@/utils/StorageService";
import { getApiBaseUrl } from "@/utils/RuntimeConfig";
import type { Message } from "@/types/mcp";

export interface PendingConversation {
  sessionThreadId: string;
  chatType: string;
  agentId: string;
  turnId: string;
  user?: Message;
}
const key = () => {
  try {
    const profile = JSON.parse(localStorage.getItem("user-profile") || "{}");
    return (
      "pending-conversations:" +
      (profile.uuid || profile.username || "anonymous")
    );
  } catch {
    return "pending-conversations:anonymous";
  }
};
const memory = new Map<string, Record<string, PendingConversation>>();
export function pendingConversations(): Record<string, PendingConversation> {
  const accountKey = key();
  if (memory.has(accountKey)) return memory.get(accountKey)!;
  try {
    const entries = JSON.parse(sessionStorage.getItem(accountKey) || "{}");
    memory.set(accountKey, entries);
    return entries;
  } catch {
    return {};
  }
}
export function savePendingConversation(value: PendingConversation) {
  const entries = { ...pendingConversations(), [value.sessionThreadId]: value };
  memory.set(key(), entries);
  try {
    sessionStorage.setItem(key(), JSON.stringify(entries));
  } catch {
    // Keep session/turn metadata even when image data exceeds the tab's storage quota.
    const compact = Object.fromEntries(
      Object.entries(entries).map(([id, item]) => [
        id,
        {
          ...item,
          user: item.user
            ? { role: "user", content: item.user.content, turn_id: item.turnId }
            : undefined,
        },
      ]),
    );
    try {
      sessionStorage.setItem(key(), JSON.stringify(compact));
    } catch {}
  }
}
export function forgetPendingConversation(id: string) {
  const entries = { ...pendingConversations() };
  delete entries[id];
  memory.set(key(), entries);
  try {
    sessionStorage.setItem(key(), JSON.stringify(entries));
  } catch {}
}
export function streamUrl(
  type: string,
  action: "status" | "resume",
  id: string,
) {
  const prefix =
    type === "agent" || type === "deepagent"
      ? "/skill/api/chat/stream"
      : type === "travel_planner"
        ? "/travel/api/chat/stream"
        : "/aiChat/stream";
  return (
    getApiBaseUrl().replace(/\/+$/, "") +
    prefix +
    "/" +
    action +
    "?session_thread_id=" +
    encodeURIComponent(id)
  );
}
export function streamHeaders(): Record<string, string> {
  const token = StorageService.getAccessToken();
  return token ? { Authorization: "Bearer " + token } : {};
}
export async function getStreamStatus(type: string, id: string) {
  const response = await fetch(streamUrl(type, "status", id), {
    headers: streamHeaders(),
  });
  if (!response.ok) throw new Error("无法查询对话运行状态: " + response.status);
  const result = await response.json();
  if (!result.data || typeof result.data.exists !== "boolean")
    throw new Error("对话状态响应无效");
  return result.data as {
    exists: boolean;
    status?: string;
    turn_id?: string;
    created_at?: number;
  };
}