/* ============================================================================
   权限中心明细表的列定义 —— 等价迁移自原型 console.js pzCols（3795–3877）

   四个 tab：角色 / 账号 / 资源策略 / 提权工单。
   与 gwCols 一样，各 tab 字段差异大，用一个「所有字段都可选」的宽类型承接。
   ========================================================================== */

import type { OpsCol } from '@/lib/util'
import { actsHtml, chipOf, esc, fam } from '@/lib/util'
import type { PermAcct, PermAppr, PermPol, PermRole, PzStatus } from '@/data/authz'

/** 表格行：四张表的字段并集（同 gwcols，逐接口 Partial 再交叉） */
export type PzTableRow = Partial<PermRole> &
  Partial<PermAcct> &
  Partial<PermPol> &
  Partial<PermAppr> & {
    id: string
    name: string
    status: PzStatus
  }

const code = (s: unknown): string => `<code>${esc(s)}</code>`
const sub = (s: unknown): string => `<span class="cell__sub">${esc(s)}</span>`

/** 行尾操作列（原型 3805） */
const tail: OpsCol<PzTableRow> = {
  k: 'acts',
  t: '',
  cls: 'gtable__act',
  w: '138px',
  v: (g) => actsHtml(g.status, 'pact'),
}

export function pzCols(tab: string): OpsCol<PzTableRow>[] {
  if (tab === 'role') {
    return [
      {
        k: 'name',
        t: '角色 / 说明',
        cls: 'gtable__lead',
        w: '2.4fr',
        v: (g) => `<span class="cell__main">${esc(g.name)}</span>${sub(g.desc)}`,
      },
      { k: 'st', t: '状态', w: '92px', v: (g) => chipOf(g.status) },
      { k: 'cat', t: '类型', w: '112px', v: (g) => fam(g.cat ?? '') },
      { k: 'scope', t: '数据范围', w: '104px', v: (g) => esc(g.scope) },
      {
        k: 'acts',
        t: '允许动作',
        w: '180px',
        v: (g) => `<span class="cell__sub is-ink">${esc(g.acts)}</span>`,
      },
      { k: 'members', t: '成员', w: '86px', num: true, v: (g) => esc(g.members) },
      {
        k: 'mfa',
        t: '强约束',
        w: '150px',
        v: (g) => {
          const ok = /强制双因子/.test(g.mfa ?? '')
          return (
            `<span class="cell__main2${ok ? '' : ' is-warn'}">${
              ok ? '双因子已强制' : '未强制'
            }</span>` + sub(g.approver)
          )
        },
      },
      tail,
    ]
  }

  if (tab === 'acct') {
    return [
      {
        k: 'name',
        t: '账号 / 部门',
        cls: 'gtable__lead',
        w: '2.3fr',
        v: (g) =>
          `<span class="cell__main">${esc(g.name)}</span>` +
          sub(`${g.dept ?? ''} · ${g.login ?? ''}`),
      },
      { k: 'st', t: '状态', w: '92px', v: (g) => chipOf(g.status) },
      { k: 'role', t: '绑定角色', w: '132px', v: (g) => esc(g.role) },
      { k: 'scope', t: '数据范围', w: '100px', v: (g) => esc(g.scope) },
      {
        k: 'mfa',
        t: '双因子',
        w: '140px',
        v: (g) => {
          const off = /未开启|已关闭|不适用/.test(g.mfa ?? '')
          return `<span class="cell__main2${off ? ' is-warn' : ''}">${esc(g.mfa)}</span>`
        },
      },
      {
        k: 'res',
        t: '可访问资源',
        w: '180px',
        v: (g) => `<span class="cell__sub is-ink">${esc(g.res)}</span>`,
      },
      { k: 'expire', t: '有效期', w: '130px', v: (g) => esc(g.expire) },
      tail,
    ]
  }

  if (tab === 'pol') {
    return [
      {
        k: 'name',
        t: '策略 / 资源匹配',
        cls: 'gtable__lead',
        w: '2.5fr',
        v: (g) => `<span class="cell__main">${esc(g.name)}</span>${sub(code(g.res))}`,
      },
      { k: 'st', t: '状态', w: '92px', v: (g) => chipOf(g.status) },
      { k: 'effect', t: '效果', w: '112px', v: (g) => fam(g.effect ?? '') },
      { k: 'prio', t: '优先级', w: '104px', num: true, v: (g) => esc(g.prio) },
      { k: 'scope', t: '生效范围', w: '120px', v: (g) => esc(g.scope) },
      { k: 'cond', t: '命中条件', w: '210px', v: (g) => sub(g.cond) },
      {
        k: 'hit',
        t: '最近命中',
        w: '160px',
        v: (g) => sub(g.applied) + sub(g.hit),
      },
      tail,
    ]
  }

  /* 提权工单（原型 3861–3876） */
  return [
    {
      k: 'name',
      t: '工单 / 说明',
      cls: 'gtable__lead',
      w: '2.5fr',
      v: (g) => `<span class="cell__main">${esc(g.name)}</span>${sub(g.desc)}`,
    },
    { k: 'st', t: '状态', w: '92px', v: (g) => chipOf(g.status) },
    { k: 'who', t: '申请人', w: '160px', v: (g) => code(g.who) },
    { k: 'res', t: '申请资源', w: '200px', v: (g) => code(g.res) },
    { k: 'acts', t: '申请动作', w: '130px', v: (g) => esc(g.acts) },
    { k: 'life', t: '时限', w: '96px', num: true, v: (g) => esc(g.life) },
    {
      k: 'stage',
      t: '审批环节',
      w: '190px',
      v: (g) => `<span class="cell__main2">${esc(g.stage)}</span>` + sub(g.due),
    },
    tail,
  ]
}