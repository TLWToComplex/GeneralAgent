<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    v-bind="$attrs"
  >
    <!-- 文档外框 -->
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <!-- 文档折角 -->
    <polyline points="14,2 14,8 20,8"/>
    <!-- Markdown符号 -->
    <path d="M8 13h1l2-3 2 3h1"/>
    <path d="M16 16v-3"/>
  </svg>
</template>