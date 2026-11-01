/* ============================================================================
   路由表 —— 替代原型 console.js 1258–1307 行的 switchPage()。

   原型用 body[data-page] 作为「唯一权威」来控制子页互斥。Vue 里改由路由驱动：
   ConsoleView 是常驻外壳（侧栏 / 顶栏 / 指标条 / 抽屉 / 弹窗），
   七个页面作为它的子路由各自渲染到主区。

   `meta.page` 就是原来的页面 id，ConsoleView 会把它写回 body[data-page]，
   这样 console.css 里那 7 条 `body[data-page="X"] #X{display:flex}` 的规则
   继续生效，视觉零回归。
   ========================================================================== */

import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { isPageLocked } from '@/config/pages'
import type { PageId } from '@/config/pages'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    /** 对应原型的页面 id，用于写 body[data-page] 与装配指标条 */
    page?: PageId
    /** 顶栏标题（浏览器 document.title 用） */
    title?: string
    /** 该页面是否挂载 console.css（登录页不挂） */
    shell?: boolean
    /** 需要登录：未登录时重定向到 /login */
    requiresAuth?: boolean
    /** 仅未登录可进：已登录时重定向到控制台（避免登录后再手敲 /login） */
    guestOnly?: boolean
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: '登录 · GeneralAgent', guestOnly: true },
  },
  {
    path: '/console',
    component: () => import('@/views/ConsoleView.vue'),
    meta: { shell: true, requiresAuth: true },
    redirect: '/console/workbench',
    children: [
      {
        path: 'workbench',
        name: 'workbench',
        component: () => import('@/views/workbench/WorkbenchView.vue'),
        meta: { page: 'workbench', title: '工作台 · 会话调度', shell: true },
      },
      {
        path: 'registry',
        name: 'registry',
        component: () => import('@/views/registry/RegistryView.vue'),
        meta: { page: 'registry', title: '资产 · 镜像中心', shell: true },
      },
      {
        path: 'models',
        name: 'models',
        component: () => import('@/views/models/ModelsView.vue'),
        meta: { page: 'models', title: '资产 · 模型中心', shell: true },
      },
      {
        path: 'toolplatform',
        name: 'toolplatform',
        component: () => import('@/views/tools/ToolPlatformView.vue'),
        meta: { page: 'toolplatform', title: '资产 · 工具平台', shell: true },
      },
      {
        path: 'kb',
        name: 'kb',
        component: () => import('@/views/kb/KnowledgeBaseView.vue'),
        meta: { page: 'kb', title: '资产 · 知识库中心', shell: true },
      },
      {
        path: 'gateway',
        name: 'gateway',
        component: () => import('@/views/gateway/GatewayView.vue'),
        meta: { page: 'gateway', title: '运维 · 网关', shell: true },
      },
      {
        path: 'authz',
        name: 'authz',
        component: () => import('@/views/authz/AuthzView.vue'),
        meta: { page: 'authz', title: '运维 · 权限中心', shell: true },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/console/workbench',
  },
]

export const router = createRouter({
  // 原型是纯静态文件（双击即可打开），所以用 hash 路由，
  // 不需要服务端 rewrite 也能直接刷深链。
  history: createWebHashHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((to) => {
  const t = to.meta.title
  if (t) document.title = t
})

/* ============================================================================
   「开发中」页面的进入守卫

   侧栏把这几项渲染成了不可点的 <span>（见 AppSidebar.vue），
   但直接敲 URL、刷深链、或点顶栏面包屑仍然能走到路由 —— 所以这里再兜一道。

   拦的是**进入**，不是页面本身：路由与组件都保持完整，把
   config/pages.ts 里对应页的 locked 改成 false 就立刻能进（守卫自动放行）。

   为什么不做成"删掉路由"：那会让 deep link 掉到 404，而且开发时想进去调页面
   还得先把路由加回来。守卫保留了这个后门，同时对外表现为"进不去"。
   ========================================================================== */
const FIRST_ALLOWED = '/console/workbench'

/* ============================================================================
   登录守卫

   顺序是「先鉴权，再看页面是否锁定」：未登录时无论目标页是什么都先回登录页，
   否则会出现"被踢到工作台、工作台又因锁定把人送到别处"这类绕圈跳转。

   判定只读 auth store 的状态（令牌在 main.ts 里已提前 restore），不在这里发请求：
   令牌是否真的还有效由接口返回的 401 兜底（见 stores/auth.ts 的 handleUnauthorized）。
   ========================================================================== */
router.beforeEach((to) => {
  const auth = useAuthStore()
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth)
  const guestOnly = to.matched.some((record) => record.meta.guestOnly)

  if (requiresAuth && !auth.isAuthenticated) {
    return { path: '/login', replace: true }
  }
  if (guestOnly && auth.isAuthenticated) {
    return { path: FIRST_ALLOWED, replace: true }
  }

  const page = to.meta.page
  if (page && isPageLocked(page)) {
    return { path: FIRST_ALLOWED, replace: true }
  }
  return true
})