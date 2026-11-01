/* ============================================================================
   权限中心数据 —— 等价迁移自原型 console.js 第 4162–4311 行。

   四张表共用一套骨架：
     · 角色（role）  · 账号（acct）  · 资源策略（pol）  · 提权工单（appr）
   因为原型的 renderOpsGrid / pzBands / 表单都按 `tab` 分支取字段，
   所以这里用一个宽松的联合结构承载，固定字段显式声明、tab 专有字段可选。
   ========================================================================== */

export type PzStatus = 'ok' | 'warn' | 'off'
export type PzTab = 'role' | 'acct' | 'pol' | 'appr'

/** 四类对象的公共字段 */
export interface PermBase {
  id: string
  name: string
  status: PzStatus
  /** 分类：内置角色 / 自定义角色 / 部门 / 允许 / 拒绝 / 需要审批 … */
  cat: string
  /** 数据范围 */
  scope: string
  desc: string
  /** 允许动作 */
  acts: string
  owner: string
  lastReview: string
}

/** 角色 */
export interface PermRole extends PermBase {
  tab: 'role'
  /** 权限域，矩阵按它给满档 */
  domains: string
  members: string
  life: string
  mfa: string
  approver: string
  risk: string
}

/** 账号 */
export interface PermAcct extends PermBase {
  tab: 'acct'
  role: string
  dept: string
  mfa: string
  login: string
  res: string
  expire: string
  risk: string
}

/** 资源策略 */
export interface PermPol extends PermBase {
  tab: 'pol'
  res: string
  effect: string
  cond: string
  prio: string
  applied: string
  hit: string
  expire: string
}

/** 提权工单 */
export interface PermAppr extends PermBase {
  tab: 'appr'
  who: string
  res: string
  life: string
  approver: string
  at: string
  due: string
  stage: string
  risk: string
}

export type PermRecord = PermRole | PermAcct | PermPol | PermAppr
export type PzRow = PermRecord


export const PERMROLES: PermRole[] = [
  { id: 'pz-01', tab: 'role', name: '平台管理员', status: 'ok', cat: '内置角色',
    scope: '全公司', desc: '平台最高权限：可管理模型、镜像、知识库、工具与网关配置',
    acts: '全部动作', domains: '模型 / 镜像 / 知识库 / 工具 / 网关', members: '3 个账号',
    life: '长期有效', mfa: '强制双因子 + 操作二次确认', approver: '信息安全部',
    lastReview: '2024-11-02 复核通过', risk: '高风险 · 需季度复核', owner: '信息安全部' },
  { id: 'pz-02', tab: 'role', name: '模型运营', status: 'ok', cat: '自定义角色',
    scope: '全公司', desc: '负责模型上线与配额调整，不允许删除生产模型',
    acts: '查看 · 上线 · 调整配额', domains: '模型中心 / 网关路由', members: '8 个账号',
    life: '长期有效', mfa: '强制双因子', approver: '平台负责人',
    lastReview: '2024-11-02 复核通过', risk: '中风险 · 需半年复核', owner: '平台负责人' },
  { id: 'pz-03', tab: 'role', name: '值班运维', status: 'ok', cat: '内置角色',
    scope: '指定项目', desc: '值班期间可重启、下线与摘除流量，不可改配额与权限',
    acts: '重启 · 下线 · 摘除流量', domains: '工作台 / 网关路由 / 上下游', members: '12 个账号',
    life: '值班窗口内有效', mfa: '强制双因子 + 值班打卡', approver: '值班主管',
    lastReview: '2024-10-28 复核通过', risk: '中风险 · 工期到点自动回收', owner: '值班主管' },
  { id: 'pz-04', tab: 'role', name: '审计员（只读）', status: 'ok', cat: '内置角色',
    scope: '全公司', desc: '只读访问全部审计流水与配置快照，不能执行任何写操作',
    acts: '查看 · 导出审计', domains: '全部模块（只读）', members: '4 个账号',
    life: '长期有效', mfa: '强制双因子', approver: '合规负责人',
    lastReview: '2024-11-02 复核通过', risk: '低风险 · 需年度复核', owner: '合规负责人' },
  { id: 'pz-05', tab: 'role', name: '数据分析师', status: 'warn', cat: '自定义角色',
    scope: '本部门', desc: '可查询指标与知识库，导出敏感数据需要逐次审批',
    acts: '查看 · 检索 · 申请导出', domains: '知识库 / 指标平台', members: '26 个账号',
    life: '长期有效', mfa: '未强制（待整改）', approver: '数据归属部门',
    lastReview: '2024-09-15 复核通过', risk: '中风险 · 待补双因子', owner: '数据归属部门' },
  { id: 'pz-06', tab: 'role', name: '外部只读', status: 'off', cat: '服务账号角色',
    scope: '指定项目', desc: '给外部协作方的最小权限，项目结束后停用',
    acts: '查看', domains: '指定知识库 / 指定模型', members: '0 个账号',
    life: '已停用', mfa: '不适用', approver: '信息安全部',
    lastReview: '2024-08-30 复核通过', risk: '低风险 · 已停用', owner: '信息安全部' },
]

export const PERMACCTS: PermAcct[] = [
  { id: 'pz-a8', tab: 'acct', name: 'intern.sun@corp', status: 'ok', cat: '研发中心',
    scope: '仅本人', desc: '实习生账号，只能看自己的任务与配额，到期自动失效',
    role: '数据分析师', dept: '研发中心', mfa: '已开启 · 短信', login: '今天 09:05 · 10.24.6.31',
    acts: '查看', res: '本人的任务 / 配额', expire: '实训期结束（12-15）',
    lastReview: '近 30 天 12 次查看，0 次越权', risk: '低风险 · 到期自动回收', owner: '研发中心' },
  { id: 'pz-a1', tab: 'acct', name: 'ops.zhang@corp', status: 'ok', cat: '云原生组',
    scope: '全公司', desc: '平台负责人，工作日 9:00–21:00 可执行高风险操作',
    role: '平台管理员', dept: '云原生组', mfa: '已开启 · 硬件密钥', login: '今天 09:12 · 10.24.8.6',
    acts: '全部动作', res: '全部资源', expire: '长期有效',
    lastReview: '近 30 天 42 次操作，0 次拒绝', risk: '高风险账号 · 已开双因子', owner: '云原生组' },
  { id: 'pz-a2', tab: 'acct', name: 'ops.lin@corp', status: 'ok', cat: '云原生组',
    scope: '指定项目', desc: '值班运维，仅在值班窗口内可重启与下线',
    role: '值班运维', dept: '云原生组', mfa: '已开启 · 短信', login: '今天 08:40 · 10.24.8.19',
    acts: '重启 · 下线 · 摘除流量', res: '工作台 / 网关路由', expire: '值班窗口内',
    lastReview: '近 30 天 18 次操作，1 次超范围被拒', risk: '中风险账号', owner: '云原生组' },
  { id: 'pz-a3', tab: 'acct', name: 'report.zhou@corp', status: 'warn', cat: '财务管理部',
    scope: '本部门', desc: '报表口径核对，正在申请敏感数据导出的临时提权',
    role: '数据分析师', dept: '财务管理部', mfa: '已开启 · 短信', login: '今天 10:02 · 10.24.12.4',
    acts: '查看 · 检索 · 申请导出', res: '知识库 / 指标平台', expire: '长期有效',
    lastReview: '近 30 天 96 次检索，2 次申请待批', risk: '中风险 · 待补硬件密钥', owner: '财务管理部' },
  { id: 'pz-a4', tab: 'acct', name: 'audit.chen@corp', status: 'ok', cat: '信息安全部',
    scope: '全公司', desc: '审计员，只读访问审计流水与配置快照',
    role: '审计员（只读）', dept: '信息安全部', mfa: '已开启 · 硬件密钥', login: '昨天 17:20 · 10.24.5.8',
    acts: '查看 · 导出审计', res: '全部模块（只读）', expire: '长期有效',
    lastReview: '近 30 天 12 次导出，全部留痕', risk: '低风险账号', owner: '信息安全部' },
  { id: 'pz-a5', tab: 'acct', name: 'svc:gateway@corp', status: 'ok', cat: '核心平台',
    scope: '指定项目', desc: '网关服务账号，仅调用鉴权与配额接口',
    role: '服务账号', dept: '核心平台', mfa: '不适用 · 证书双向认证', login: '持续在线 · 集群内',
    acts: '鉴权校验 · 配额读取', res: '权限中心内部接口', expire: '证书到期前有效',
    lastReview: '每日 240 万次调用，0 次越权', risk: '低风险 · 证书 30 天后到期', owner: '核心平台' },
  { id: 'pz-a6', tab: 'acct', name: 'extern.li@partner', status: 'ok', cat: '外部协作',
    scope: '指定项目', desc: '外部协作方，只能读取指定知识库的指定目录',
    role: '外部只读', dept: '外部协作', mfa: '已开启 · 短信', login: '今天 09:50 · 公网入口',
    acts: '查看', res: '指定知识库（3 个目录）', expire: '项目结束（12-31）',
    lastReview: '近 30 天 64 次检索，0 次越权', risk: '中风险 · 到期需回收', owner: '外部协作' },
  { id: 'pz-a7', tab: 'acct', name: 'intern.wu@corp', status: 'off', cat: '研发中心',
    scope: '仅本人', desc: '实习生账号，实训结束后已停用',
    role: '数据分析师', dept: '研发中心', mfa: '已关闭', login: '30 天前 · 已停用',
    acts: '查看', res: '无', expire: '已停用',
    lastReview: '已回收全部权限', risk: '已停用', owner: '研发中心' },
]

export const PERMPOLS: PermPol[] = [
  { id: 'pz-p1', tab: 'pol', name: '生产镜像只读', status: 'ok', cat: '允许',
    scope: '生产环境', desc: '允许拉取生产仓库镜像，禁止推送与删除标签',
    res: 'image:registry.internal/prod/*', acts: '拉取 · 查看标签', effect: '允许',
    cond: '来源 = 集群内网 · 账号开启双因子', prio: '优先级 100',
    applied: '命中 6 个角色 / 42 个账号', hit: '近 7 天命中 18420 次',
    expire: '长期有效', owner: '信息安全部', lastReview: '2024-11-01 复核通过' },
  { id: 'pz-p2', tab: 'pol', name: '敏感数据导出', status: 'warn', cat: '需要审批',
    scope: '全公司', desc: '导出含个人信息的数据需要逐次审批，审批通过后 2 小时有效',
    res: 'dataset:finance/* / kb:客服问答库', acts: '导出',
    effect: '需要审批', cond: '审批人 = 数据归属部门 + 信息安全部', prio: '优先级 300',
    applied: '命中 2 个角色 / 26 个账号', hit: '近 7 天命中 6 次 · 2 次待批',
    expire: '长期有效', owner: '数据归属部门', lastReview: '2024-10-20 复核通过' },
  { id: 'pz-p3', tab: 'pol', name: '禁止删除生产模型', status: 'ok', cat: '拒绝',
    scope: '生产环境', desc: '任何账号都不得直接删除生产模型，必须先下线并走变更流程',
    res: 'model:prod/*', acts: '删除', effect: '拒绝', cond: '无条件 · 优先级最高',
    prio: '优先级 900', applied: '命中全部角色', hit: '近 7 天拦截 3 次',
    expire: '长期有效', owner: '平台负责人', lastReview: '2024-11-02 复核通过' },
  { id: 'pz-p4', tab: 'pol', name: '工具平台自助注册', status: 'ok', cat: '允许',
    scope: '研发中心', desc: '研发同学可自助注册 MCP 与 Skill，上线前需要连通性探测通过',
    res: 'tool:*/register', acts: '注册 · 编辑 · 下线', effect: '允许',
    cond: '归属部门 = 研发中心 · 探测通过', prio: '优先级 200',
    applied: '命中 3 个角色 / 58 个账号', hit: '近 7 天命中 214 次',
    expire: '长期有效', owner: '平台运营', lastReview: '2024-10-30 复核通过' },
  { id: 'pz-p5', tab: 'pol', name: '网关配置变更', status: 'ok', cat: '需要审批',
    scope: '生产环境', desc: '生产网关的路由、限流与熔断变更需要平台负责人审批',
    res: 'gateway:prod/routes/*', acts: '新增 · 修改 · 删除', effect: '需要审批',
    cond: '审批人 = 平台负责人 · 变更窗口 10:00–18:00', prio: '优先级 400',
    applied: '命中 2 个角色 / 11 个账号', hit: '近 7 天命中 9 次 · 全部通过',
    expire: '长期有效', owner: '平台负责人', lastReview: '2024-11-02 复核通过' },
  { id: 'pz-p6', tab: 'pol', name: '外部账号访问限制', status: 'off', cat: '拒绝',
    scope: '外部协作', desc: '外部账号禁止访问审计流水与权限配置，策略暂由入口白名单替代',
    res: 'audit:* / authz:*', acts: '全部动作', effect: '拒绝',
    cond: '账号类型 = 外部', prio: '优先级 800',
    applied: '命中 1 个角色 / 6 个账号', hit: '近 7 天拦截 0 次',
    expire: '已停用', owner: '信息安全部', lastReview: '2024-09-12 复核通过' },
]

export const PERMAPPRS: PermAppr[] = [
  { id: 'pz-r1', tab: 'appr', name: '申请敏感数据导出权限', status: 'warn', cat: '需要审批',
    scope: '本部门', desc: '为季度口径核对申请临时导出权限，仅限指定报表范围',
    who: 'report.zhou@corp', res: 'dataset:finance/月度报表', acts: '导出',
    life: '2 小时', approver: '财务管理部 + 信息安全部', at: '今天 10:20 提交',
    due: '剩 1 小时 40 分', stage: '一级已通过 · 待信息安全部', risk: '涉及个人信息 3 类字段',
    owner: '财务管理部', lastReview: '审批中' },
  { id: 'pz-r2', tab: 'appr', name: '申请生产网关变更窗口', status: 'warn', cat: '需要审批',
    scope: '生产环境', desc: '发布新版本前需要调整限流阈值，申请 30 分钟变更窗口',
    who: 'ops.lin@corp', res: 'gateway:prod/routes/v1-chat', acts: '修改限流',
    life: '30 分钟', approver: '平台负责人', at: '今天 09:40 提交',
    due: '剩 20 分钟', stage: '待平台负责人', risk: '影响对话入口限流',
    owner: '平台负责人', lastReview: '审批中' },
  { id: 'pz-r3', tab: 'appr', name: '申请临时值班权限', status: 'ok', cat: '允许',
    scope: '指定项目', desc: '替班期间申请值班运维权限，到点自动回收',
    who: 'ops.wang@corp', res: '工作台 / 网关路由', acts: '重启 · 下线',
    life: '8 小时', approver: '值班主管', at: '今天 08:05 提交',
    due: '已通过 · 22:05 自动回收', stage: '已通过', risk: '自动回收已开启',
    owner: '值班主管', lastReview: '2024-11-02 通过' },
  { id: 'pz-r4', tab: 'appr', name: '申请知识库语料范围扩容', status: 'ok', cat: '允许',
    scope: '本部门', desc: '客服问答库需要新增两个业务线的标准问答对',
    who: 'cs.song@corp', res: 'kb:客服问答库', acts: '新增语料 / 重建索引',
    life: '长期有效', approver: '客户服务中心', at: '昨天 16:30 提交',
    due: '已通过', stage: '已通过', risk: '语料已脱敏',
    owner: '客户服务中心', lastReview: '2024-11-01 通过' },
  { id: 'pz-r5', tab: 'appr', name: '申请外部协作只读权限', status: 'warn', cat: '需要审批',
    scope: '外部协作', desc: '合作方需要读取指定知识库目录，项目结束后回收',
    who: 'extern.li@partner', res: 'kb:产品说明书库/公开目录', acts: '查看',
    life: '至 12-31', approver: '产品部 + 信息安全部', at: '昨天 11:12 提交',
    due: '剩 5 天', stage: '待产品部', risk: '外部账号 · 需限制目录',
    owner: '产品部', lastReview: '审批中' },
  { id: 'pz-r6', tab: 'appr', name: '申请模型压测配额', status: 'off', cat: '拒绝',
    scope: '生产环境', desc: '压测会占用大量 GPU，当前窗口不批，建议改用离线副本',
    who: 'code.liu@corp', res: 'model:prod/DeepSeek-V3-Chat', acts: '压测',
    life: '1 小时', approver: '平台负责人', at: '3 天前提交',
    due: '已驳回', stage: '已驳回', risk: '压测影响在线流量',
    owner: '平台负责人', lastReview: '2024-10-30 驳回' },
]