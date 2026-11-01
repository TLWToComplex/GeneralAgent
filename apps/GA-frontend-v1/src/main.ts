// src/main.ts
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import Antd from 'ant-design-vue';
import 'ant-design-vue/dist/reset.css';
// 过程块统一设计 token：思考 / 工具调用 / 任务清单 / 审批共用
import '@/assets/styles/process-block.css';
import App from './App.vue';
import router from './router';
import { initTheme } from '@/config';
import StorageService, { STORAGE_KEYS } from '@/utils/StorageService';
import { loadRuntimeConfig } from '@/utils/RuntimeConfig';
import { initTabScope } from '@/utils/TabScopeService';

// 启动函数：先加载运行时配置，再初始化应用
async function bootstrap() {
  // 无依赖的初始化先行：主题与本地状态读取
  initTheme();
  StorageService.get(STORAGE_KEYS.USER_PREFERENCES);

  // 并行加载运行时配置与初始化 Tab 作用域，避免串行等待叠加阻塞首屏
  await Promise.all([loadRuntimeConfig(), initTabScope()]);

  // 创建Vue应用实例
  const app = createApp(App);

  // 创建并使用Pinia状态管理
  const pinia = createPinia();
  app.use(pinia);

  // 使用路由
  app.use(router);

  // 使用Ant Design Vue组件库
  app.use(Antd);

  // 挂载应用
  app.mount('#app');
}

bootstrap();
