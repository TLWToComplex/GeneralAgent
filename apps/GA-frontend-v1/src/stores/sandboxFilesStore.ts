import { defineStore } from 'pinia';
import { ref } from 'vue';
import { getApiBaseUrl } from '@/utils/RuntimeConfig';
import StorageService from '@/utils/StorageService';

export interface SandboxFile {
  filename: string;
  path: string;
  size: number;
  modified: string;
  download_url: string;
}

/**
 * 沙箱交付文件 store
 * 通过 /skill/api/files/list 查询当前会话沙箱 /workspace 下的生成文件，
 * 作为“交付中心”的数据源，兜底正则匹配遗漏的下载链接。
 */
export const useSandboxFilesStore = defineStore('sandboxFiles', () => {
  const files = ref<SandboxFile[]>([]);
  const loading = ref(false);
  // 最近一次对话轮次新增的文件（用于自动打开画布等场景）
  const lastAdded = ref<SandboxFile[]>([]);
  const loadedSessionId = ref('');
  // 本轮对话开始前的文件路径基线，用于 diff 出新增文件
  let turnBaseline: string[] | null = null;
  let requestGeneration = 0;

  const normalizeFiles = (raw: unknown, sessionThreadId: string): SandboxFile[] => {
    const list = Array.isArray(raw) ? raw : [];
    const baseUrl = (getApiBaseUrl() || '').replace(/\/+$/, '');
    const result: SandboxFile[] = [];
    for (const item of list) {
      if (!item || typeof item !== 'object') continue;
      const rec = item as Record<string, unknown>;
      const filename = String(rec.filename || rec.path || '').trim();
      const path = String(rec.path || rec.filename || '').trim() || filename;
      if (!filename) continue;
      // 后端返回的 download_url host 是后端自身视角（如 localhost），
      // 统一用前端 baseUrl 重新拼接，避免跨域/不可达
      let downloadUrl = String(rec.download_url || '').trim();
      if (baseUrl && path) {
        const encodedPath = path.split('/').map(encodeURIComponent).join('/');
        downloadUrl = `${baseUrl}/skill/api/files/${encodedPath}?session_thread_id=${encodeURIComponent(sessionThreadId)}`;
      }
      result.push({
        filename,
        path,
        size: typeof rec.size === 'number' ? rec.size : 0,
        modified: String(rec.modified || ''),
        download_url: downloadUrl
      });
    }
    return result;
  };

  async function fetchFiles(sessionThreadId: string, options?: { asBaseline?: boolean }): Promise<SandboxFile[]> {
    const sid = (sessionThreadId || '').trim();
    const baseUrl = (getApiBaseUrl() || '').replace(/\/+$/, '');
    if (!sid || !baseUrl) return [];

    const generation = ++requestGeneration;
    loading.value = true;
    try {
      const url = `${baseUrl}/skill/api/files/list?session_thread_id=${encodeURIComponent(sid)}`;
      const token = StorageService.getAccessToken();
      const response = await fetch(url, {
        method: 'GET',
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      const json = await response.json();
      console.log('[DeepAgent] /skill/api/files/list 返回:', json);
      const list = normalizeFiles(json?.data?.files, sid);
      if (generation !== requestGeneration || StorageService.getWorkspaceSessionThreadId() !== sid) return list;

      if (options?.asBaseline) {
        turnBaseline = list.map(f => f.path);
      } else {
        const baseline = turnBaseline ?? (loadedSessionId.value === sid ? files.value.map(f => f.path) : null);
        lastAdded.value = baseline ? list.filter(f => !baseline.includes(f.path)) : list;
        turnBaseline = null;
      }

      files.value = list;
      loadedSessionId.value = sid;
      return list;
    } catch (e) {
      console.warn('[DeepAgent] 查询沙箱文件清单失败:', e);
      return [];
    } finally {
      if (generation === requestGeneration) loading.value = false;
    }
  }

  /**
   * 在一轮 DeepAgent 对话开始前调用，记录基线，
   * 以便对话结束后 diff 出本轮新增文件。
   */
  function beginTurn(sessionThreadId: string) {
    const sid = (sessionThreadId || '').trim();
    if (!sid) return;
    if (loadedSessionId.value === sid) {
      turnBaseline = files.value.map(f => f.path);
    } else {
      turnBaseline = null;
      void fetchFiles(sid, { asBaseline: true });
    }
  }

  function clear() {
    requestGeneration++;
    loading.value = false;
    files.value = [];
    lastAdded.value = [];
    loadedSessionId.value = '';
    turnBaseline = null;
  }

  return {
    files,
    loading,
    lastAdded,
    loadedSessionId,
    fetchFiles,
    beginTurn,
    clear
  };
});
