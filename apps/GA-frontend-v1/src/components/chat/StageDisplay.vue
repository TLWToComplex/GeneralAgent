<template>
  <div v-if="stage" class="stage-display">
    <div class="stage-badge">
      <span class="stage-label">当前阶段</span>
      <span class="stage-value">{{ stage }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  stage?: string
}>();
</script>

<style scoped>
.stage-display {
  margin-bottom: 12px;
}

.stage-badge {
  display: inline-flex;
  align-items: center;
  background-color: #f0f5ff;
  border: 1px solid #adc6ff;
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 12px;
  color: #2f54eb;
}

.stage-label {
  font-weight: 600;
  margin-right: 6px;
  opacity: 0.8;
}

.stage-value {
  font-weight: 500;
}
</style>
