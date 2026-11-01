import { effectScope, ref, watch, type Ref } from 'vue';
import StorageService, { WORKSPACE_STORAGE_CLEARED_EVENT } from '@/utils/StorageService';

type WorkspaceStorageEntry<T> = {
  state: Ref<T>;
  defaultValue: T;
};

const workspaceStorageRefs = new Map<string, WorkspaceStorageEntry<any>>();
let suppressWorkspacePersistence = false;
let resetListenerBound = false;

// 缓存的 ref 与应用同生命周期，落盘监听必须脱离调用方组件的 effect scope：
// 组件卸载会停掉自己作用域内的 watch，之后复用缓存 ref 的实例就再也写不进 sessionStorage。
const persistenceScope = effectScope(true);

function cloneDefaultValue<T>(value: T): T {
  if (typeof (globalThis as any)?.structuredClone === 'function') {
    try {
      return (globalThis as any).structuredClone(value) as T;
    } catch {}
  }

  if (Array.isArray(value) || (value !== null && typeof value === 'object')) {
    try {
      return JSON.parse(JSON.stringify(value)) as T;
    } catch {}
  }

  return value;
}

function bindWorkspaceResetListener() {
  if (resetListenerBound || typeof window === 'undefined') {
    return;
  }

  resetListenerBound = true;
  window.addEventListener(WORKSPACE_STORAGE_CLEARED_EVENT, () => {
    suppressWorkspacePersistence = true;
    workspaceStorageRefs.forEach((entry) => {
      entry.state.value = cloneDefaultValue(entry.defaultValue);
    });
    queueMicrotask(() => {
      suppressWorkspacePersistence = false;
    });
  });
}

export function useWorkspaceStorage<T>(key: string, defaultValue: T): Ref<T> {
  bindWorkspaceResetListener();

  const cached = workspaceStorageRefs.get(key) as WorkspaceStorageEntry<T> | undefined;
  if (cached) {
    return cached.state;
  }

  const state = ref(StorageService.getWorkspaceValue<T>(key, defaultValue) as T) as Ref<T>;

  persistenceScope.run(() => {
    watch(
      state,
      (newValue) => {
        if (suppressWorkspacePersistence) {
          return;
        }
        if (newValue === undefined || newValue === null) {
          StorageService.removeWorkspaceValue(key);
          return;
        }
        StorageService.setWorkspaceValue(key, newValue);
      },
      { deep: true }
    );
  });

  workspaceStorageRefs.set(key, {
    state,
    defaultValue: cloneDefaultValue(defaultValue)
  });
  return state;
}

export default useWorkspaceStorage;
