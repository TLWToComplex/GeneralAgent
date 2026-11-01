/* ============================================================================
   AI 工具（内部下发）—— 工具平台 AI 工具标签页的数据与「完整安装使用流程」

   与 data/tools.ts（MCP 服务 / Skill 工具）的区别：
     · MCP / Skill 是**平台内部注册的可调用能力**，关注端点、配额、调用量；
     · AI 工具是**下发给人的客户端软件**（dsh 桌面版 exe / dsh 终端版 / Zed），
       关注在哪下载、怎么装、怎么接内网大模型、装完怎么验证。
   所以两者共用工具平台的卡片骨架（.regcard.toolrow），但 AI 工具卡片点进去
   是一条**分步装机流程**（AiStep），而不是详情抽屉。

   流程内容的来源是《Coding Agent 内网配置手册》（0921 版）：
   内网 vLLM 模型、dsh 三形态接入、Zed 的 settings.json 与 API Key 设置。
   手册里的命令、路径、字段名一律照抄，不「顺手改写」，避免与手册口径不一致。

   步骤内容用一套小「块 DSL」描述（AiBlock），由 components/AiBlocks.vue 渲染：
   段落 / 命令块 / 键值表 / 提示条 / 清单 / 表格 / 下载条目。
   这样做的好处：内容全部留在 data 层（与项目其它数据文件同一风格），
   视图层只负责把块画出来，改动文案不需要碰组件。
   ========================================================================== */

/* ---------------------------------------------------------------- 内网大模型 */

/** 手册里的内网大模型参数 —— 三个 AI 工具全部接同一个端点 */
export const INTERNAL_LLM = {
  /**
   * 内部网络接入方式。手册上写的是「必须连 robot WiFi」；
   * 桌面版流程**完全不提网络前提**（默认能看到这个页面的人网络环境就是通的），
   * 这个常量现在只给 Zed 流程与参数速查页使用。
   */
  network: 'robot WiFi',
  host: '172.16.234.96',
  baseURL: 'http://172.16.234.96:8666/v1',
  chatURL: 'http://172.16.234.96:8666/v1/chat/completions',
  apiKey: 'sk-master-1234',
  /** 密钥的环境变量名（dsh 与 Zed 都用它） */
  apiKeyEnv: 'INTERNAL_LLM_API_KEY',
  model: 'qwen3.8-27b',
  protocol: 'openai-completions',
  /** Langfuse 观测平台 */
  langfuse: 'http://172.16.234.96:3000',
  /** dsh 侧的 Provider ID（小写、永久） */
  dshProvider: 'internal',
  /** Zed 侧的 provider ID（环境变量名由它派生） */
  zedProvider: 'internal-llm',
} as const

/* ---------------------------------------------------------------- 类型 */

/** 工具形态：桌面端 / 终端 / IDE（也是 AI 标签页的筛选维度） */
export type AiToolKind = 'desktop' | 'cli' | 'ide'
/** 分发渠道：官方开源 / 第三方 */
export type AiToolChannel = 'official' | 'thirdparty'
/** 状态：已上架 / 预览版 */
export type AiState = 'ready' | 'preview'

export const AIKIND: Record<AiToolKind, { cn: string; cls: string; icon: string }> = {
  desktop: { cn: '桌面端', cls: 'is-llm', icon: 'i-cards' },
  cli: { cn: '终端', cls: 'is-sys', icon: 'i-term' },
  ide: { cn: 'IDE', cls: 'is-embed', icon: 'i-model' },
}

export const AICHANNEL: Record<AiToolChannel, string> = {
  official: '官方开源',
  thirdparty: '第三方',
}

/** 状态基色（写进卡片的 --st）与中文名 */
export const AIST: Record<AiState, { cn: string; v: string }> = {
  ready: { cn: '已上架', v: 'var(--teal)' },
  preview: { cn: '预览版', v: 'var(--gold)' },
}

/** 下载条目（安装包） */
export interface AiFile {
  name: string
  size: string
  /**
   * 安装包地址。**相对地址 = 平台内置的安装包**（文件放在 public/ai-tools/ 下，
   * 构建后随 dist 一起发出去，点「领取安装包」直接下载，不需要外网）；
   * 绝对 http(s) 地址 = 外链，会开新标签页（当前三个工具都没有这种条目）。
   */
  url: string
  /** 最新版标记 */
  latest?: boolean
  note?: string
}

/** 提示条的语义（info 蓝 / warn 琥珀 / ok 绿） */
export type AiNoteKind = 'info' | 'warn' | 'ok'

/**
 * 步骤里的一块内容。
 * 用判别联合（t 字段）而不是「一个万能对象 + 一堆可选字段」，
 * 渲染端 v-if 分支写起来干净，也保证数据里不会出现「既没正文也没命令」的空块。
 */
export type AiBlock =
  | { t: 'p'; v: string }
  | { t: 'code'; v: string; title?: string; lang?: string }
  | { t: 'kv'; rows: [string, string][]; title?: string }
  | { t: 'note'; v: string; kind: AiNoteKind; title?: string }
  | { t: 'list'; v: string[]; title?: string }
  | { t: 'table'; head: string[]; rows: string[][]; title?: string }
  | { t: 'files'; v: AiFile[]; title?: string }
  /** 可选块：整块降级展示（虚线 + 「可选」角标），里面可嵌套上面任意块 */
  | { t: 'optional'; v: AiBlock[]; title?: string }

/** 装机流程里的一步 */
export interface AiStep {
  id: string
  title: string
  /** 一句话目标（步骤头部右侧） */
  goal: string
  /** 该步预估耗时 */
  eta: string
  blocks: AiBlock[]
}

export interface AiTool {
  id: AiToolId
  name: string
  /** 卡片副标题：形态 · 提供方 */
  sub: string
  kind: AiToolKind
  channel: AiToolChannel
  state: AiState
  /** 一句话定位 */
  desc: string
  /** 卡片①栏的标签（[标签名, 值]） */
  tags: [string, string][]
  /** 卡片②栏的六项配置（[键, 值]） */
  cfg: [string, string][]
  /** 本页累计下发次数（心跳里会涨） */
  downloads: number
  /** 装机流程总耗时预期 */
  eta: string
  /** 平台侧可直接领取的文件；空数组表示走命令行安装 */
  files: AiFile[]
  /**
   * 卡片上「复制安装命令」给出的一行命令。
   * 只对「没有安装包、靠命令行装起来」的工具有意义（如 dsh 终端版）。
   */
  quickCmd?: string
  steps: AiStep[]
}

export type AiToolId = 'dsh-desktop' | 'dsh-cli' | 'zed'

/* ---------------------------------------------------------------- 块构造助手 */

const p = (v: string): AiBlock => ({ t: 'p', v })
const code = (v: string, title?: string, lang?: string): AiBlock => ({ t: 'code', v, title, lang })
const kv = (rows: [string, string][], title?: string): AiBlock => ({ t: 'kv', rows, title })
const note = (v: string, kind: AiNoteKind = 'info', title?: string): AiBlock => ({
  t: 'note',
  v,
  kind,
  title,
})
const list = (v: string[], title?: string): AiBlock => ({ t: 'list', v, title })
const table = (head: string[], rows: string[][], title?: string): AiBlock => ({
  t: 'table',
  head,
  rows,
  title,
})
const files = (v: AiFile[], title?: string): AiBlock => ({ t: 'files', v, title })
/**
 * 可选块：把「不是必经」的内容整块包起来。桌面版把 settings.yaml 与两个
 * 兼容开关从独立一步降级成配置步里的可选块 —— 它不再占用步骤导航的一格，
 * 视觉上也明显比必经步骤轻一档。
 */
const optional = (v: AiBlock[], title?: string): AiBlock => ({ t: 'optional', v, title })

/* ------------------------------------------------- 平台内置的安装包（内网下载） */

/**
 * 安装包在站点里的相对目录 —— 文件真身在 `public/ai-tools/`，
 * 构建时 Vite 会把 public/ 原样拷进 dist/，所以开发与生产都能直接下。
 *
 * 这里刻意存**相对地址**：部署到子路径（如 /ai/）时也不会失效。
 * 点击时由 `stores/tools.ts` 的 claimFile() 用 new URL(url, document.baseURI)
 * 拼成绝对地址再触发下载，并且带上 download 属性强制下载而不是在浏览器里打开。
 */
export const AI_FILE_DIR = 'ai-tools/'

/** dsh 桌面版安装包：官方正式桌面版（Windows x64，275.91 MB） */
export const DSH_DESKTOP_EXE = 'dsh-latest-windows-x64.exe'
/** Zed 安装包（Windows x64，81.66 MB） */
export const ZED_EXE = 'Zed-x86_64.exe'

/* --------------------------------------------------- 三处共用的内网模型片段 */

/** 内网模型参数表（dsh 桌面 / dsh 终端 / Zed 的表单字段完全一致） */
function llmRows(): [string, string][] {
  return [
    ['Provider ID', INTERNAL_LLM.dshProvider],
    ['显示名称', '内网大模型'],
    ['API 地址', INTERNAL_LLM.baseURL],
    ['API 协议', INTERNAL_LLM.protocol],
    ['API 密钥', INTERNAL_LLM.apiKey],
    ['模型 ID', INTERNAL_LLM.model],
  ]
}

/** $DSH_HOME/settings.yaml 的官方写法（含两个关键 compat 开关） */
const DSH_SETTINGS_YAML = `llm-pi-ai:
  providers:
    internal:
      apiKeyEnv: INTERNAL_LLM_API_KEY
      api: openai-completions
      baseURL: http://172.16.234.96:8666/v1
      compat:
        supportsDeveloperRole: false
        maxTokensField: max_tokens
      models:
        - id: qwen3.8-27b
          reasoningEfforts:      # 可选：为模型声明推理等级
            low: low
            medium: medium
            xhigh: xhigh`

/** 连通性验证：一条 curl 就能判断「内网模型是否可达」 */
const LLM_CURL = String.raw`curl -X POST "http://172.16.234.96:8666/v1/chat/completions" ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer sk-master-1234" ^
  -d "{\"model\":\"qwen3.8-27b\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":10}"`

const LLM_NO_PROXY = String.raw`set NO_PROXY=172.16.234.96
set HTTP_PROXY=
set HTTPS_PROXY=`

/**
 * 三个工具共用的排错表（手册第四节 + dsh 官方排错优先级）。
 * `withNetwork = false` 给桌面版用：那一版默认访问者的网络环境是通的，
 * 因此不出现「连接超时 / 请求被代理转发」这类网络前提。
 */
function llmTroubleshoot(withNetwork = true): string[][] {
  const rows: string[][] = [
    ['MISSING_CREDENTIAL', '密钥未配置', '在表单里填 apiKey，或让 apiKeyEnv 指向已设置的环境变量'],
    ['网关拒绝每个请求', 'HTTP 400 / 422', '设 compat.supportsDeveloperRole:false 与 compat.maxTokensField:max_tokens'],
    ['只有推理模型失败', '普通模型正常', '同上 —— 原因是 developer 角色被网关拒绝'],
    ['证书错误', 'TLS 校验失败', String.raw`启动前设 set NODE_EXTRA_CA_CERTS=C:\path\to\corp-ca.pem`],
  ]
  if (withNetwork) {
    rows.push(['连接超时', '请求被代理转发', `把内网地址加进 NO_PROXY（只认主机名 / 后缀 / IP，不支持 CIDR 网段）`])
  }
  return rows
}

/* ============================================================================
   ① dsh 桌面版（exe）
   ========================================================================== */

export const DSH_DESKTOP_FILES: AiFile[] = [
  {
    name: DSH_DESKTOP_EXE,
    size: '275.9 MB',
    url: AI_FILE_DIR + DSH_DESKTOP_EXE,
    latest: true,
    note: 'DeepSeek Harness 0.2.0-rc.2 官方正式桌面版（exe 属性里的 ProductName = DeepSeek Harness），平台内置，点「领取安装包」直接下载；双击即装，安装包内置 dsh 运行时，无需另装 Node.js',
  },
]

/* ------------------------------------------------- 内网 mirror hub（包源） */

/**
 * 内网 mirror hub —— dsh 的 agent 装包时用的私有包源（默认按 Nexus3 的仓库形态拼地址）。
 *
 * 为什么单开一步：agent 会自己执行 `pip install` / `npm install`，默认走的是公网镜像
 * （pypi 阿里源、npm 腾讯源）；内网环境出不去外网，装包就会卡在超时。
 * 第 4 步的一键脚本把包源地址换到这里，pip / npm / pnpm / uv 一起换。
 *
 * ⚠️ 换 hub 时只改这一处：基地址 + 两个路径，第 4 步的命令与键值表都由它拼出来
 * （脚本自己的默认值也放在顶部：setup-internal-mirror.ps1 的 -HubBase / -PipPath / -NpmPath）。
 */
export const MIRROR_HUB = {
  /** mirror hub 基地址（Nexus3 默认 8081） */
  base: 'http://172.16.234.96:8081',
  /** pip 的 simple 索引路径 */
  pipPath: '/repository/pypi-proxy/simple',
  /** npm registry 路径 */
  npmPath: '/repository/npm-proxy/',
} as const

/** 第 4 步下发的镜像源脚本（两个文件必须放同一目录 —— .cmd 用 %~dp0 找 .ps1） */
export const DSH_MIRROR_FILES: AiFile[] = [
  {
    name: 'setup-internal-mirror.cmd',
    size: '1.2 KB',
    url: AI_FILE_DIR + 'setup-internal-mirror.cmd',
    note: '双击入口：调同目录的 .ps1',
  },
  {
    name: 'setup-internal-mirror.ps1',
    size: '23.2 KB',
    url: AI_FILE_DIR + 'setup-internal-mirror.ps1',
    note: '主脚本：换 pip / npm / pnpm / uv 包源，改前备份、可一键回滚',
  },
]

/** 第 4 步的执行命令（CMD）：先预演看计划，再正式替换 */
const MIRROR_RUN_CMD = String.raw`cd /d "%USERPROFILE%\Downloads"

:: ① 先预演：只打印要改哪些文件，不写盘
setup-internal-mirror.cmd -HubBase ${MIRROR_HUB.base} -DryRun

:: ② 正式替换：改 pip / npm 的用户配置 + 写 dsh 环境变量
setup-internal-mirror.cmd -HubBase ${MIRROR_HUB.base}`

/** 第 4 步的验证命令（CMD）：换没换过来，一条条看 */
const MIRROR_VERIFY_CMD = String.raw`python -m pip config list
npm config get registry
type "%USERPROFILE%\.dsh\.env"`

/** 第 4 步的常见问题 */
const MIRROR_TROUBLESHOOT: string[][] = [
  ['预检报「两个源都不可达」', '退出码 2，未改动任何文件', '先确认已连内网，再核对 -HubBase 与 hub 路径是否写对'],
  ['pip 还是去公网', 'pip config list 里仍是阿里源', '脚本写的是用户级 pip.ini；确认没有旧的 PIP_INDEX_URL 环境变量把它顶掉'],
  ['dsh 里装包仍超时', 'CMD 里 pip 正常、agent 里不正常', '~/.dsh/.env 要**重启 dsh** 才加载，重启后再试'],
  ['npm 报 401 / 要登录', 'registry 可达但拒绝匿名', '给脚本加 -NpmAuthToken <token>，写进 .npmrc'],
]

const DSH_DESKTOP_STEPS: AiStep[] = [
  {
    id: 'prepare',
    title: '准备工作',
    goal: '确认系统与磁盘满足要求',
    eta: '2 分钟',
    blocks: [
      p('dsh 桌面版是 DeepSeek Harness 的**官方正式桌面版**。'),
      kv([
        ['适用系统', 'Windows 10 / 11 64 位'],
        ['磁盘占用', '安装 + 缓存约 1 GB'],
        ['运行时依赖', '无（安装包内置 Electron 与 dsh 运行时，不需要 Node.js）'],
        ['模型', `${INTERNAL_LLM.model}（内网 vLLM 部署）`],
      ], '环境要求'),
      list(['确认磁盘剩余空间 ≥ 1 GB']),
    ],
  },
  {
    id: 'download',
    title: '下载安装包',
    goal: '从本页直接领取官方正式桌面版安装包',
    eta: '1–3 分钟（内网直连）',
    blocks: [
      p('安装包已内置在本平台（`public/ai-tools/`，DeepSeek Harness 0.2.0-rc.2 官方正式桌面版），点下面的「领取」按钮**直接下载**。'),
      files(DSH_DESKTOP_FILES, '可下载的安装包'),
      kv([
        ['版本', 'v0.2.0-rc.2（官方正式桌面版）'],
        ['文件名', 'dsh-latest-windows-x64.exe'],
        ['体积', '275.9 MB'],
        ['来源', '平台内置'],
      ], '安装包信息'),
      p('下载后建议核对一下文件完整性（可选，两个命令都在本机执行）：'),
      code(
        String.raw`certutil -hashfile "%USERPROFILE%\Downloads\dsh-latest-windows-x64.exe" SHA256`,
        '校验 SHA256（CMD）',
        'cmd',
      ),
      note('SHA256 前 16 位应为 D61CD8882F8B8A12。对不上就别装，重新从本页下载。', 'info', '校验值'),
      note('若浏览器把下载拦了，右键「领取」按钮选「链接另存为」即可。', 'ok', '小提示'),
    ],
  },
  {
    id: 'install',
    title: '安装与首次启动',
    goal: '装好并打开客户端',
    eta: '3 分钟',
    blocks: [
      list([
        '双击 dsh-latest-windows-x64.exe',
        'UAC 弹窗点「是」，选择安装目录（默认即可）',
        '等安装完成，从开始菜单启动 DeepSeek Harness',
      ]),
      p('首次启动会在用户目录下创建配置目录 $DSH_HOME（默认 ~/.dsh/），模型配置之后写在这里的 settings.yaml 中。'),
      code(String.raw`dir "%USERPROFILE%\.dsh"`, '确认配置目录已生成（CMD）', 'cmd'),
      note('启动成功能进主界面就算这一步过了。此时还没接内网模型，模型列表里是空的 —— 正常。', 'ok', '完成标志'),
    ],
  },
  {
    id: 'mirror',
    title: '换内网镜像源',
    goal: '让 agent 装包走内网，不再出外网',
    eta: '1 分钟',
    blocks: [
      p('装完客户端、接模型之前，先把包源换掉：dsh 的 agent 会自己执行 `pip install` / `npm install` 这类命令，默认走的是公网镜像（pypi 阿里源、npm 腾讯源）；内网环境出不去外网，装包会卡住或超时。'),
      p('平台提供了一个一键脚本，把 **pip / npm / pnpm / uv** 的包源地址换成内网 mirror hub。改之前自动备份，改错了可以一键还原。'),
      files(DSH_MIRROR_FILES, '可下载的脚本（两个文件必须放同一个目录）'),
      list([
        '把上面两个文件下到**同一个目录**（例如 `%USERPROFILE%\\Downloads`）',
        '打开 CMD 执行下面的命令（**不需要管理员权限**：只改当前用户的配置）',
        '看到预检「可达」与最后的 `[done] exit code 0` 就算成功',
      ], '三步跑完'),
      code(MIRROR_RUN_CMD, '执行（CMD）', 'cmd'),
      kv([
        ['内网包源基地址', MIRROR_HUB.base],
        ['pip 索引', MIRROR_HUB.base + MIRROR_HUB.pipPath],
        ['npm registry', MIRROR_HUB.base + MIRROR_HUB.npmPath],
        ['会改哪些文件', '`%APPDATA%\\pip\\pip.ini`、`%USERPROFILE%\\.npmrc`、`%USERPROFILE%\\.dsh\\.env`'],
        ['生效时机', 'pip / npm **立即生效**；dsh 桌面版**重启一次**后 `.env` 才进 agent 子进程'],
      ], '脚本会改什么'),
      note('脚本默认按 Nexus3 的仓库路径拼地址。如果 hub 是其它形态（Artifactory / devpi / Verdaccio），在命令末尾加 `-PipPath` 与 `-NpmPath` 指定路径。', 'info', 'hub 路径'),
      note('改之前会把原文件备份成 `<文件名>.bak-<时间戳>`。想还原成脚本执行前的样子，跑 `setup-internal-mirror.cmd -Revert`。', 'info', '可回滚'),
      note('Windows 弹出「已保护你的电脑」时，点「更多信息 → 仍要运行」；或先在 CMD 里执行 `powershell -Command "Unblock-File .\\setup-internal-mirror.cmd"` 解除下载标记。', 'warn', '下载受阻'),
      p('换没换过来，执行这三条看一下：'),
      code(MIRROR_VERIFY_CMD, '验证（CMD）', 'cmd'),
      table(['问题', '现象', '处理'], MIRROR_TROUBLESHOOT, '常见问题'),
      list([
        '`-CheckOnly` —— 只打印当前实际生效的源与连通性，不写盘',
        '`-PersistUserEnv` —— 同时写用户级环境变量，让终端里散装的 uv 等工具也走内网',
        '`-SmokeTest` —— 真的下载一个小包，做端到端验证',
        '`-CondaChannel <url>` —— 顺便把 conda 的 channel 也换成内网',
      ], '脚本的可选参数（按需加在命令末尾）'),
    ],
  },
  {
    id: 'config-form',
    title: '配置内网模型',
    goal: '把内网 vLLM 端点接进客户端',
    eta: '2 分钟',
    blocks: [
      p('打开 **设置（Settings）→ 模型（Models）**，页面上有两个入口：'),
      list([
        '❌ 「添加提供方」—— dsh 自带的官方厂商（DeepSeek、anthropic、openai 等），不是我们要的',
        '✅ 「添加自定义提供方」—— 选这个',
      ]),
      kv(llmRows(), '按下表填写'),
      note('表单里的「探测模型 / 获取可用模型」按钮会调 GET /models 自动列出端点提供的模型供勾选。内网 vLLM 支持该端点；探测失败就手动填模型 ID，效果一样。', 'info'),
      note('保存后**立即生效，无需重启**。到这一步模型就已经接好了 —— 下面的可选设置**不是必经步骤**。', 'ok'),
      // settings.yaml 与两个兼容开关：原来各占一步，现降级成「可选块」——
      // 只有网关拒绝请求时才需要，所以不再占用左侧导航的一格。
      optional(
        [
          p('配置写入 $DSH_HOME/settings.yaml（默认 ~/.dsh/settings.yaml）。官方格式如下，可直接整段粘贴：'),
          code(DSH_SETTINGS_YAML, 'settings.yaml', 'yaml'),
          note(
            '两个 compat 开关对内网网关很关键（官方排错一节的原话）：\n· supportsDeveloperRole: false —— dsh 默认把系统提示词以 role:"developer" 发送，很多网关（含 vLLM）会直接拒绝；\n· maxTokensField: max_tokens —— dsh 默认写 max_completion_tokens，只认 max_tokens 的服务端会拒绝。',
            'warn',
            '别漏了 compat',
          ),
          p('密钥可以用 apiKeyEnv 引用环境变量，也可以直接把 apiKey 写进 yaml。推荐前者：'),
          code('setx INTERNAL_LLM_API_KEY "sk-master-1234"', '设置密钥环境变量（CMD，执行后重启终端）', 'cmd'),
          note('setx 是 CMD 命令，**不能在 PowerShell 里执行**。PowerShell 里请用 [System.Environment]::SetEnvironmentVariable(\'INTERNAL_LLM_API_KEY\', \'sk-master-1234\', \'User\')。', 'info'),
        ],
        '遇到网关拒绝请求时再看：settings.yaml 与两个兼容性开关',
      ),
    ],
  },
  {
    id: 'use',
    title: '选择工作区并开始使用',
    goal: '跑通第一个编码任务',
    eta: '5 分钟',
    blocks: [
      p('与 Web 版一致：先在对话框处**选择工作区（Choose workspace）**，添加并选中你要处理的项目目录 —— 未选中前输入框是禁用的。'),
      list([
        '选择工作区 → 添加项目根目录并选中',
        '在对话框的模型选择器里选 qwen3.8-27b',
        '输入任务，例如：「把这个仓库的结构梳理成一份 README」',
        'Agent 会读写工作区文件、执行命令、维护计划；**需要审批的操作会先询问**',
      ], '首次使用四步'),
      note('桌面端把你在 UI 里选中的目录作为工作区根；终端版（headless）没有这步交互，工作区就是执行命令时所在的目录。', 'info'),
    ],
  },
  {
    id: 'verify',
    title: '验证与排错',
    goal: '确认模型真的通了',
    eta: '5 分钟',
    blocks: [
      list([
        '模型选择器里能看到 qwen3.8-27b',
        '发一句「你好」，能正常收到回复',
        '设置 → 模型里的 API 地址 / 协议与参数表完全一致',
      ], '验收清单'),
      p('也可以用一条 curl 单独验证内网模型是否可达（与客户端无关，排除法用）：'),
      code(LLM_CURL, '连通性自检（CMD）', 'cmd'),
      note('预期返回包含 "choices" 的 JSON。若这条不通，先核对密钥与端点地址是否和参数表一致，别在客户端里绕。', 'ok'),
      table(['问题', '现象', '处理'], llmTroubleshoot(false), '常见问题'),
      note(`模型调用失败的排查顺序（官方排错）：① MISSING_CREDENTIAL → 密钥未配置；② 网关拒绝每个请求 → 打开两个 compat 开关；③ 只有推理模型失败 → 同上（developer 角色被拒）。观测平台：${INTERNAL_LLM.langfuse}（Langfuse）。`, 'info'),
    ],
  },
]

/* ============================================================================
   ② dsh 终端版（CLI / headless）
   ========================================================================== */

const DSH_CLI_STEPS: AiStep[] = [
  {
    id: 'node',
    title: '装 Node.js（前提）',
    goal: '让 npx 可用',
    eta: '3 分钟',
    blocks: [
      p('dsh 是 Node 程序，先装运行时。官方推荐 LTS：'),
      code('winget install OpenJS.NodeJS.LTS', '安装 Node.js LTS（CMD / PowerShell）', 'cmd'),
      note('装完**必须重启终端**，PATH 才会生效（新开的窗口才认识 node / npm / npx）。', 'warn'),
      code('node -v\nnpm -v', '确认版本（重启终端后执行）', 'cmd'),
    ],
  },
  {
    id: 'registry',
    title: '换 npm 国内镜像源',
    goal: '把首次下载从十几分钟压到一两分钟',
    eta: '1 分钟',
    blocks: [
      code('npm config set registry https://registry.npmmirror.com', '切到国内镜像（CMD）', 'cmd'),
      note(
        '本机实测：外网 npm 源只有 ~2–4 KB/s。dsh 主包很小（约 200 KB），但依赖树（Cordis 生态 + 前端资源）首次要拉几 MB～几十 MB，**首次下载几分钟到十几分钟都属正常**。超过 5 分钟进度完全不动就 Ctrl+C 重试（npx 有缓存）。',
        'warn',
        '下载时长预期',
      ),
      note('下载只发生一次，缓存在 %LOCALAPPDATA%\\npm-cache，之后启动都是秒开。公司若有 npm 私服（Nexus / Verdaccio），把 registry 指向私服会快一个数量级。', 'info'),
    ],
  },
  {
    id: 'launch',
    title: '启动：Web UI 或 headless',
    goal: '把 dsh 跑起来',
    eta: '5 分钟',
    blocks: [
      p('**网页版**：一条命令起服务，浏览器访问 http://127.0.0.1:3080。'),
      code('npx @deepseek-ai/dsh web', '启动 Web UI', 'cmd'),
      p('第一次会询问是否安装包，输入 y：'),
      code('Need to install the following packages:\n  @deepseek-ai/dsh@0.1.5-rc.2\nOk to proceed? (y) y', '首次启动的确认提示', 'text'),
      note('启动后终端会打印 DeepSeek Harness Web UI: http://127.0.0.1:3080。**这个终端窗口要保持开着**，关闭即停止服务。', 'warn'),
      p('**无头模式（headless）**：单次任务，打印最终答案后退出。工作区规则很明确 —— 没有「选择工作区」这一步，`dsh` 把**运行命令时所在的目录**作为工作区根目录：'),
      code(String.raw`cd /d C:\my-project
npx @deepseek-ai/dsh --profile headless "帮我把 README 翻译成中文"`, '在项目目录里跑一次任务（CMD）', 'cmd'),
      note('与网页版的区别：网页版是先启动服务、再在 UI 里选工作区；headless 是「人在哪个目录，工作区就是哪个目录」，启动即干活。', 'info'),
    ],
  },
  {
    id: 'profiles',
    title: '自定义 profile 与其它形态',
    goal: '按需扩展终端用法',
    eta: '3 分钟',
    blocks: [
      code(String.raw`:: 从官方模板派生一个自己的 profile（第一次）
npx @deepseek-ai/dsh --profile myagent --from-default-profile headless

:: 之后用自定义 profile 跑任务（同样在项目目录中执行）
dsh --profile myagent "任务"`, '自定义 profile', 'cmd'),
      list([
        '--profile headless —— 单次任务，打印结果后退出（默认下发的形态）',
        '--profile tui —— 终端界面（需安装对应 profile 插件）',
        '--profile acp —— Agent Client Protocol，供 Claude Code 等工具把 dsh 作为后端接入',
      ], '可用的 profile'),
      note('profile 是 dsh 的「一切皆插件」架构落地方式：同一套模型配置，不同前端形态共用。', 'info'),
    ],
  },
  {
    id: 'config',
    title: '配置内网模型',
    goal: '让终端版指向内网 vLLM',
    eta: '3 分钟',
    blocks: [
      p('与桌面版**共用同一份配置**：$DSH_HOME/settings.yaml（默认 ~/.dsh/settings.yaml）。'),
      code(DSH_SETTINGS_YAML, 'settings.yaml', 'yaml'),
      code('setx INTERNAL_LLM_API_KEY "sk-master-1234"', '密钥走环境变量（CMD，执行后重启终端）', 'cmd'),
      note('网页版也可以不用 yaml：在 Web UI 里走 设置 → 模型 → 添加自定义提供方 表单填一遍即可，两者写的是同一份配置。', 'info'),
      kv(llmRows(), '表单字段速查'),
    ],
  },
  {
    id: 'verify',
    title: '验证与排错',
    goal: '确认命令行链路可用',
    eta: '5 分钟',
    blocks: [
      list([
        '启动命令打印出 Web UI 地址，浏览器能打开 127.0.0.1:3080',
        'Web UI / 无头任务的模型列表里能看到 qwen3.8-27b',
        '无头模式跑一句「总结当前仓库」，能打印最终答案后退出',
      ], '验收清单'),
      code(LLM_CURL, '连通性自检（CMD）', 'cmd'),
      table(['问题', '现象', '处理'], [
        ...llmTroubleshoot(),
        ['npx 卡住 / 进度不动', '首次拉依赖很慢', 'Ctrl+C 后重试（npx 有缓存，不会从头下）'],
        ['命令找不到 dsh', '重启终端后仍报错', '用完整写法 npx @deepseek-ai/dsh；确认 Node.js 已装且在 PATH'],
      ], '常见问题'),
      note(String.raw`dsh 出站请求走 HTTP_PROXY / HTTPS_PROXY。若机器挂了代理，内网地址必须直连：set NO_PROXY=172.16.234.96（NO_PROXY 只认主机名 / 后缀 / IP，不支持 CIDR 网段）。`, 'warn', '代理环境'),
    ],
  },
]

/* ============================================================================
   ③ Zed（IDE 编码助手）
   ========================================================================== */

const ZED_SETTINGS_JSON = `{
  "language_models": {
    "openai_compatible": {
      "internal-llm": {
        "api_url": "http://172.16.234.96:8666/v1",
        "available_models": [
          {
            "name": "qwen3.8-27b",
            "display_name": "Qwen3.8-27B 内网",
            "max_tokens": 32000,
            "capabilities": {
              "tools": true,
              "images": false,
              "parallel_tool_calls": false,
              "prompt_cache_key": false,
              "chat_completions": true,
              "interleaved_reasoning": false,
              "max_tokens_parameter": false
            }
          }
        ]
      }
    }
  }
}`

/** Zed 安装包：同样是平台内置，点「领取安装包」直接下载 */
export const ZED_FILES: AiFile[] = [
  {
    name: ZED_EXE,
    size: '81.7 MB',
    url: AI_FILE_DIR + ZED_EXE,
    latest: true,
    note: 'Zed 1.20.2 的 Windows x64 安装程序（文件属性里的 ProductName = Zed / CompanyName = Zed Industries），平台内置，点「领取安装包」直接下载（不连外网）；双击安装，无需账号',
  },
]

const ZED_STEPS: AiStep[] = [
  {
    id: 'prepare',
    title: '准备工作',
    goal: '确认系统与账号前提',
    eta: '1 分钟',
    blocks: [
      p('Zed 是用 **Rust 从头编写**的高性能 IDE，原生支持 AI 编码代理（Zed Agent）、内联代码转换、编辑预测；启动快、GPU 加速渲染，支持 Vim / VS Code 键位。'),
      kv([
        ['适用系统', 'Windows / macOS / Linux'],
        ['网络要求', `连接 ${INTERNAL_LLM.network}（内网地址 ${INTERNAL_LLM.host} 必须直连）`],
        ['账号', '不需要 —— 用自定义 openai_compatible 接口无需注册 / 登录'],
        ['硬件', 'GPU 加速渲染，集成显卡可用'],
        ['模型', `${INTERNAL_LLM.model}（内网 vLLM 部署）`],
      ], '环境要求'),
      note('Zed 的可选登录（Sign In）只用于团队协作、同步设置等高级功能。纯内网 AI 编码场景**完全跳过登录**。', 'ok'),
    ],
  },
  {
    id: 'install',
    title: '安装 Zed',
    goal: '装好并启动 IDE',
    eta: '3 分钟',
    blocks: [
      p('安装包已内置在本平台（`public/ai-tools/`，Zed 1.20.2），点顶部「领取安装包」**直接下载**，全程走内网：'),
      files(ZED_FILES, '可下载的安装包'),
      list([
        '双击下载得到的 Zed-x86_64.exe',
        '跟随安装向导完成安装（默认选项即可）',
        '从开始菜单启动 Zed',
      ], '安装三步'),
      p('下载后建议核对一下文件完整性（可选，本机执行）：'),
      code(
        String.raw`certutil -hashfile "%USERPROFILE%\Downloads\Zed-x86_64.exe" SHA256`,
        '校验 SHA256（CMD）',
        'cmd',
      ),
      note('SHA256 前 16 位应为 82C2F6E682A73E3F。对不上就别装，重新从本页下载。', 'info', '校验值'),
      note('安装后如果要**在命令行里调用 zed**，需要关掉当前终端重新打开（PATH 才会刷新）。只用图形界面的话可以忽略。', 'warn', '命令行调用'),
    ],
  },
  {
    id: 'settings',
    title: '配置内网模型（settings.json）',
    goal: '让 Zed 认识内网端点',
    eta: '4 分钟',
    blocks: [
      list([
        '菜单：File → Settings → Open Settings',
        '快捷键：Ctrl + ,',
        '命令面板：Ctrl + Shift + P → 输入 zed: open settings',
      ], '打开 settings.json 的三种方式'),
      p('把下面这段整段粘进 settings.json（没有 language_models 就新增，有就合并内部字段）：'),
      code(ZED_SETTINGS_JSON, 'settings.json', 'json'),
      note('Zed 的 settings.json 使用**标准 JSON**，不支持 // 注释。语法错误会让模型列表直接不显示。', 'warn', '不要写注释'),
      table(['字段', '作用'], [
        ['api_url', '内网 OpenAI 兼容端点（带 /v1）'],
        ['available_models[].name', '模型 ID，必须与端点一致：qwen3.8-27b'],
        ['available_models[].display_name', '模型选择器里显示的名字'],
        ['max_tokens', '上下文 / 输出上限，手册给的是 32000'],
        ['capabilities.tools', '允许 Agent 调用工具（读写文件、跑命令）'],
        ['capabilities.chat_completions', '走 Chat Completions 协议（内网 vLLM 用这个）'],
        ['capabilities.max_tokens_parameter', '内网网关只认 max_tokens 时保持 false'],
      ], '字段说明'),
    ],
  },
  {
    id: 'apikey',
    title: '设置 API Key',
    goal: '把密钥交给 Zed（四种方式任选）',
    eta: '3 分钟',
    blocks: [
      list([
        `① 运行批处理：双击「设置Zed环境变量.bat」，然后重启 Zed`,
        `② CMD：setx ${INTERNAL_LLM.apiKeyEnv} "${INTERNAL_LLM.apiKey}"`,
        `③ PowerShell：[System.Environment]::SetEnvironmentVariable('${INTERNAL_LLM.apiKeyEnv}', '${INTERNAL_LLM.apiKey}', 'User')`,
        '④ Zed UI：Ctrl + Shift + P → agent: open settings → Settings → AI → LLM Providers 里填 Key（存进系统密钥链）',
      ], '四种设置方式'),
      code(String.raw`:: 方式二（CMD，注意 setx 不能在 PowerShell 里执行）
setx INTERNAL_LLM_API_KEY "sk-master-1234"`, '命令行设置（CMD）', 'cmd'),
      code(`[System.Environment]::SetEnvironmentVariable('INTERNAL_LLM_API_KEY', 'sk-master-1234', 'User')`, 'PowerShell 设置', 'powershell'),
      note(`命名规则：provider ID 转 UPPER_SNAKE_CASE + _API_KEY。本例 ${INTERNAL_LLM.zedProvider} → ${INTERNAL_LLM.apiKeyEnv}。`, 'info', '变量名怎么来的'),
      note('setx 是 CMD 命令，**不能在 PowerShell 中执行**。无论用哪种方式，改完都要**重启 Zed** 才生效。', 'warn'),
    ],
  },
  {
    id: 'agent',
    title: '使用 Zed Agent 与内联助手',
    goal: '把 AI 用进日常编码',
    eta: '5 分钟',
    blocks: [
      table(['操作', '入口'], [
        ['打开 Agent 面板', 'Ctrl + Shift + A（或命令面板 agent: toggle panel，或侧边栏 Agent 图标）'],
        ['内联助手', '选中代码 → Ctrl + Shift + I'],
        ['打开设置', 'Ctrl + ,'],
        ['命令面板', 'Ctrl + Shift + P'],
      ], '快捷键'),
      list([
        '用 Zed 打开你的项目',
        'Ctrl + Shift + A 打开 Agent 面板',
        '输入任务，例如：「在 src 目录下创建一个模块，实现一个简单的 HTTP 服务」',
        'Agent 搜索项目结构 → 创建 / 修改文件 → 在 Review 面板展示 diff',
        '逐条审核确认 / 拒绝，通过后改动应用到项目；Agent 执行终端命令需授权',
      ], 'Agent 工作流示例'),
      note('内联助手适合小改动：选中一段代码 → Ctrl + Shift + I → 输入「添加错误处理」「改成 async/await」，AI 直接替换选中内容。', 'info'),
    ],
  },
  {
    id: 'verify',
    title: '验证与常见问题',
    goal: '确认模型在 IDE 里可用',
    eta: '4 分钟',
    blocks: [
      list([
        `① Agent 面板的模型下拉里出现「Qwen3.8-27B 内网」`,
        '② Ctrl + , 打开 settings.json，确认 language_models 配置在',
        '③ 打开任意文件选中一行代码，Ctrl + Shift + I 输入「解释这段代码」，看是否正常响应',
      ], '验收清单'),
      code(LLM_CURL, '连通性自检（CMD）', 'cmd'),
      table(['问题', '处理'], [
        ['Agent 面板没有模型', '检查 settings.json 里的 language_models 配置是否完整'],
        ['API 调用失败', `确认环境变量 ${INTERNAL_LLM.apiKeyEnv} 已设置，且设置后重启过 Zed`],
        ['模型列表不显示', '重启 Zed；检查 settings.json 的 JSON 语法（不支持注释、不能有多余逗号）'],
        ['连接超时', `确认已连 ${INTERNAL_LLM.network}，且能 ping 通 ${INTERNAL_LLM.host}`],
        ...llmTroubleshoot().map((r) => [r[0], r[2]]),
      ], '常见问题'),
      note(String.raw`Zed 同样走系统代理设置：若机器挂了代理，把内网地址加进 NO_PROXY 直连（set NO_PROXY=172.16.234.96）。`, 'warn', '代理环境'),
    ],
  },
]

/* ============================================================================
   三个工具的汇总
   ========================================================================== */

export const AI_TOOLS: readonly AiTool[] = [
  {
    id: 'dsh-desktop',
    name: 'DSH 桌面版',
    sub: '官方正式桌面版 · 内网下发',
    kind: 'desktop',
    channel: 'official',
    state: 'preview',
    desc: 'DeepSeek Harness 的官方正式 Windows 桌面版，安装包由平台内置下发，双击装完即可用内网 vLLM 跑编码任务，含文件读写、命令执行与计划维护。',
    tags: [
      ['版本', 'v0.2.0-rc.2'],
      ['体积', '275.9 MB'],
      ['流程', '7 步'],
    ],
    cfg: [
      ['安装方式', '图形安装包 (.exe)'],
      ['领取渠道', '平台内置（点击即下载）'],
      ['适用系统', 'Windows 10/11 x64'],
      ['配置方式', '设置表单 / settings.yaml'],
      ['内网接入', `${INTERNAL_LLM.model}`],
      ['安装包大小', '275.9 MB'],
    ],
    downloads: 1284,
    eta: '约 20 分钟',
    files: DSH_DESKTOP_FILES,
    steps: DSH_DESKTOP_STEPS,
  },
  {
    id: 'dsh-cli',
    name: 'DSH 终端版',
    sub: 'headless / CLI · 官方（@deepseek-ai/dsh）',
    kind: 'cli',
    channel: 'official',
    state: 'preview',
    desc: 'DeepSeek Harness 的命令行形态：npx 一条命令起 Web UI 或无头任务，工作区就是执行命令时所在的目录。',
    tags: [
      ['包名', '@deepseek-ai/dsh'],
      ['主包', '约 200 KB'],
      ['流程', '6 步'],
    ],
    cfg: [
      ['安装方式', 'winget (Node.js) + npx'],
      ['领取渠道', 'npm / npmmirror'],
      ['适用系统', 'Windows · macOS · Linux'],
      ['配置方式', 'settings.yaml + 环境变量'],
      ['内网接入', `${INTERNAL_LLM.model}`],
      ['官方来源', 'deepseek-ai/deepseek-harness'],
    ],
    downloads: 3620,
    eta: '约 20 分钟（首次下载可能更久）',
    files: [],
    quickCmd: 'npx @deepseek-ai/dsh web',
    steps: DSH_CLI_STEPS,
  },
  {
    id: 'zed',
    name: 'Zed',
    sub: 'Rust 高性能 IDE · 内网下发',
    kind: 'ide',
    channel: 'official',
    state: 'ready',
    desc: 'Rust 编写的高性能 IDE，原生 AI 编码代理（Zed Agent）+ 内联代码转换，安装包由平台内置下发，用 settings.json 接内网 openai_compatible 端点，无需注册登录。',
    tags: [
      ['版本', 'v1.20.2'],
      ['安装', '.exe 安装包（内网下载）'],
      ['流程', '6 步'],
    ],
    cfg: [
      ['安装方式', '图形安装包 (.exe)'],
      ['领取渠道', '平台内置（点击即下载）'],
      ['适用系统', 'Windows 10/11 x64'],
      ['配置方式', 'settings.json + 环境变量'],
      ['内网接入', `${INTERNAL_LLM.model}`],
      ['安装包大小', '81.7 MB'],
    ],
    downloads: 2415,
    eta: '约 20 分钟',
    files: ZED_FILES,
    steps: ZED_STEPS,
  },
]

/** 「内网模型参数」参考面板的内容（三个工具都要用到同一组参数） */
export interface AiRefSection {
  id: string
  title: string
  goal: string
  blocks: AiBlock[]
}

/**
 * 卡片上「复制配置」按钮给出的文本 —— 一段可直接粘贴的接入配置。
 *
 * dsh 侧给 settings.yaml（含两个 compat 开关，这是最容易被漏掉的坑），
 * Zed 侧给 settings.json。末尾都带上密钥的环境变量命令。
 */
export function quickConfigText(id: AiToolId): string {
  const envLine = `setx ${INTERNAL_LLM.apiKeyEnv} "${INTERNAL_LLM.apiKey}"`
  if (id === 'zed') {
    return (
      `# Zed 设置（Ctrl + , 打开 settings.json，标准 JSON，不支持注释）\n` +
      `${ZED_SETTINGS_JSON}\n\n` +
      `# API Key 环境变量（CMD，设置后重启 Zed）\n${envLine}`
    )
  }
  return (
    `# dsh 设置（$DSH_HOME/settings.yaml，默认 ~/.dsh/settings.yaml）\n` +
    `${DSH_SETTINGS_YAML}\n\n` +
    `# 密钥环境变量（CMD，设置后重启终端）\n${envLine}`
  )
}

export const AI_REF_SECTIONS: readonly AiRefSection[] = [
  {
    id: 'endpoint',
    title: '内网大模型端点',
    goal: '所有 AI 工具共用同一个端点与密钥',
    blocks: [
      kv([
        ['网络', `${INTERNAL_LLM.network}（内网 IP，必须先连上）`],
        ['API 地址', INTERNAL_LLM.baseURL],
        ['Chat 端点', INTERNAL_LLM.chatURL],
        ['API Key', INTERNAL_LLM.apiKey],
        ['模型 ID', `${INTERNAL_LLM.model}（vLLM 部署）`],
        ['协议', `${INTERNAL_LLM.protocol}（OpenAI 兼容 Chat Completions）`],
        ['观测平台', `${INTERNAL_LLM.langfuse}（Langfuse）`],
      ], '参数速查'),
      code(LLM_CURL, '连通性自检（CMD）', 'cmd'),
      note('预期返回包含 "choices" 的 JSON。这条不通就别在客户端里绕 —— 先解决网络与密钥。', 'ok'),
    ],
  },
  {
    id: 'dsh',
    title: 'dsh 配置（settings.yaml）',
    goal: '桌面版与终端版共用同一份配置',
    blocks: [
      p('路径：$DSH_HOME/settings.yaml（默认 ~/.dsh/settings.yaml）。'),
      code(DSH_SETTINGS_YAML, 'settings.yaml', 'yaml'),
      kv(llmRows(), 'Web / 桌面版表单字段'),
      note(
        '· supportsDeveloperRole: false —— dsh 默认把系统提示词以 role:"developer" 发送，很多网关会拒绝；\n· maxTokensField: max_tokens —— dsh 默认写 max_completion_tokens，只认 max_tokens 的服务端会拒绝。',
        'warn',
        '两个关键 compat 开关',
      ),
      code('setx INTERNAL_LLM_API_KEY "sk-master-1234"', '密钥环境变量（CMD）', 'cmd'),
    ],
  },
  {
    id: 'zed',
    title: 'Zed 配置（settings.json）',
    goal: 'IDE 侧接内网端点',
    blocks: [
      code(ZED_SETTINGS_JSON, 'settings.json', 'json'),
      note(`provider ID ${INTERNAL_LLM.zedProvider} 对应的环境变量名是 ${INTERNAL_LLM.apiKeyEnv}（UPPER_SNAKE_CASE + _API_KEY）。Zed 不需要注册 / 登录。`, 'info'),
      note('settings.json 是标准 JSON，不支持 // 注释。', 'warn'),
    ],
  },
  {
    id: 'network',
    title: '网络与代理',
    goal: '内网直连、外网走代理的机器怎么配',
    blocks: [
      code(LLM_NO_PROXY, '把内网地址排除出代理（CMD）', 'cmd'),
      list([
        'NO_PROXY 只认主机名 / 后缀 / IP，**不支持 CIDR 网段**（如 10.0.0.0/8 无效）',
        String.raw`企业 TLS 拦截代理报证书错误时：set NODE_EXTRA_CA_CERTS=C:\path\to\corp-ca.pem（启动前设置）`,
        `API 地址 ${INTERNAL_LLM.host} 是内网 IP，必须连接 ${INTERNAL_LLM.network}`,
      ]),
      table(['问题', '现象', '处理'], llmTroubleshoot(), '模型调用失败排查顺序'),
    ],
  },
]