/* ============================================================================
   页面注册表 —— 等价迁移自原型 console.js 1212–1256 行的 PAGES 表。

   它是「面包屑 / 顶栏搜索语义 / 指标条装配」的唯一来源。
   原型的 switchPage() 会据此同步 body[data-page]、侧栏高亮与各页搜索框；
   Vue 里这些改由路由 + store 派生，这张表只保留页面的静态元信息。
   ========================================================================== */

export type PageId =
  | 'workbench'
  | 'registry'
  | 'models'
  | 'toolplatform'
  | 'kb'
  | 'gateway'
  | 'authz'

/** 顶层指标条的装配类型 */
export type KpiStrip = 'workbench' | 'registry' | 'models' | 'tools' | 'kb' | 'gw' | 'perm'
/** 顶栏搜索框的作用域 */
export type SearchScope = 'sessions' | 'registry' | 'models' | 'tools' | 'kb' | 'gw' | 'perm'

export interface PageMeta {
  /** 侧栏 data-nav 标识（注意 registry 页的导航标识是 mirror） */
  nav: string
  /** 面包屑首段 */
  head: string
  /** 面包屑末段 */
  tail: string
  /** 顶栏搜索框占位文案 */
  ph: string
  strip: KpiStrip
  search: SearchScope
  /**
   * 该页「开发中」：侧栏菜单项置灰且不可点击进入。
   *
   * 语义（三处联动，真源只有这一个字段）：
   *   ① AppSidebar 把这一项渲染成不可点的 <span class="side__link is-locked">，
   *      并挂一个「开发中」小标；
   *   ② router 的 beforeEach 拦下直接敲 URL / 深链进入的导航，重定向到工作台；
   *   ③ console.css 里 .side__link.is-locked 负责置灰外观。
   *
   * 页面本身**不做任何降级** —— 路由与组件都保持完整。这样开发时
   * 把 locked 改成 false（或临时注释掉守卫）就能立刻进去调页面。
   *
   * 想解锁某一页：把这里的 locked 改成 false 即可，三处会一起生效。
   */
  locked?: boolean
}

export const PAGES: Record<PageId, PageMeta> = {
  workbench: {
    nav: 'workbench',
    head: '工作台',
    tail: '会话调度',
    ph: '搜索会话 / 智能体 / workspace 路径',
    strip: 'workbench',
    search: 'sessions',
  },
  registry: {
    nav: 'mirror',
    head: '资产',
    tail: '镜像中心',
    ph: '搜索镜像 / 标签 / digest',
    strip: 'registry',
    search: 'registry',
    locked: true,
  },
  models: {
    nav: 'model',
    head: '资产',
    tail: '模型中心',
    ph: '搜索模型 / 家族 / 版本',
    strip: 'models',
    search: 'models',
    locked: true,
  },
  toolplatform: {
    nav: 'toolplatform',
    head: '资产',
    tail: '工具平台',
    ph: '搜索 MCP 服务 / Skill 工具 / AI 工具',
    strip: 'tools',
    search: 'tools',
  },
  kb: {
    nav: 'kb',
    head: '资产',
    tail: '知识库中心',
    ph: '搜索知识库 / 语料 / 向量库',
    strip: 'kb',
    search: 'kb',
    locked: true,
  },
  gateway: {
    nav: 'gateway',
    head: '运维',
    tail: '网关',
    ph: '搜索登录用户 / 容器名 / 端口 / 请求号',
    strip: 'gw',
    search: 'gw',
  },
  authz: {
    nav: 'authz',
    head: '运维',
    tail: '权限中心',
    ph: '搜索角色 / 账号 / 资源 / 工单',
    strip: 'perm',
    search: 'perm',
    locked: true,
  },
}

/** 侧栏结构：分组 + 入口（原型 console.html 的第 62–90 行） */
export interface NavItem {
  nav: string
  label: string
  page: PageId
  icon: string
  /** 右侧小徽标（只有工作台有，原型里写死 12） */
  badge?: string
}

/** 这一页是不是「开发中」（侧栏置灰 + 不可进入）。AppSidebar 与 router 守卫共用。 */
export function isPageLocked(page: PageId): boolean {
  return PAGES[page].locked === true
}

export interface NavGroup {
  label: string | null
  items: NavItem[]
}

export const NAV: NavGroup[] = [
  {
    // 「运行」组省略组标题、只留工作台：会话 Workspace 与智能体已并入工作台的工位视图
    label: null,
    items: [{ nav: 'workbench', label: '工作台', page: 'workbench', icon: 'i-grid', badge: '12' }],
  },
  {
    label: '资产',
    items: [
      // Skill 中心 / MCP 中心 / AI 工具中心 / 学习资料 已合并为「工具平台」一项
      { nav: 'model', label: '模型中心', page: 'models', icon: 'i-model' },
      { nav: 'mirror', label: '镜像中心', page: 'registry', icon: 'i-mirror' },
      { nav: 'kb', label: '知识库中心', page: 'kb', icon: 'i-book' },
      { nav: 'toolplatform', label: '工具平台', page: 'toolplatform', icon: 'i-tool' },
    ],
  },
  {
    label: '运维',
    items: [
      { nav: 'gateway', label: '网关', page: 'gateway', icon: 'i-pulse' },
      { nav: 'authz', label: '权限中心', page: 'authz', icon: 'i-shield' },
    ],
  },
]

/** 路由 path ↔ 页面 id（/console 是主控台外壳，子页挂在它下面） */
export const PAGE_PATHS: Record<PageId, string> = {
  workbench: '/console/workbench',
  registry: '/console/registry',
  models: '/console/models',
  toolplatform: '/console/toolplatform',
  kb: '/console/kb',
  gateway: '/console/gateway',
  authz: '/console/authz',
}

/** body 上的局部类名（原型 switchPage 会维护，便于局部样式挂钩与调试） */
export const PAGE_BODY_CLASS: Partial<Record<PageId, string>> = {
  registry: 'on-registry',
  models: 'on-models',
  toolplatform: 'on-tools',
  kb: 'on-kb',
  gateway: 'on-gw',
  authz: 'on-perm',
}