import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useArtifactStore = defineStore('artifact', () => {
  const errors = ref<Record<string, string>>({});
  const fixRequests = ref<Record<string, boolean>>({});

  function setError(id: string, error: string) {
    if (!id) return;
    errors.value[id] = error;
  }

  function clearError(id: string) {
    if (!id) return;
    if (errors.value[id]) {
      delete errors.value[id];
    }
  }

  function getError(id: string) {
    if (!id) return null;
    return errors.value[id];
  }

  function setFixRequested(id: string, requested: boolean = true) {
    if (!id) return;
    fixRequests.value[id] = requested;
  }

  function getFixRequested(id: string) {
    if (!id) return false;
    return !!fixRequests.value[id];
  }

  return {
    errors,
    fixRequests,
    setError,
    clearError,
    getError,
    setFixRequested,
    getFixRequested
  };
});
