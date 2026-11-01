<template>
  <div class="switch-component" :class="{ 'is-checked': modelValue }" @click="toggleSwitch">
    <div class="switch-inner"></div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
}>();

const toggleSwitch = () => {
  emit('update:modelValue', !props.modelValue);
};

// 导出组件
defineExpose({});
</script>

<style scoped>
.switch-component {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 22px;
  background-color: #d9d9d9;
  border-radius: 22px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.switch-component.is-checked {
  background-color: #1677ff;
}

.switch-inner {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  background-color: #fff;
  border-radius: 50%;
  transition: left 0.2s;
}

.switch-component.is-checked .switch-inner {
  left: 24px;
}
</style> 