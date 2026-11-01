<!--
  网关：新建 / 编辑（用户路由与告警规则共用一套弹窗骨架）
  等价迁移自原型 console.html 第 955–1034 行 + console.js 4452–4609
  （opsFormOpen 的网关分支 / opsFormClose / gwFormSubmit）。

  原型用 `.tfields[data-kind="gwroute|gwalert"]` 全量渲染、靠 hidden 切组；
  这里按 isAlert 用 v-if 二选一。字段与默认值来自 store 的
  formModel(overlay.modalEditingId)，副标题来自 formSub(mode)。
-->
<script setup lang="ts">
import { computed, ref } from 'vue'
import IconSprite from '@/components/IconSprite.vue'
import { useGatewayStore } from '@/stores/gateway'
import type { GwFormModel } from '@/stores/gateway'
import type { GwStatus } from '@/data/gateway'
import { useOverlayStore } from '@/stores/overlay'

const overlay = useOverlayStore()
const gateway = useGatewayStore()

/* 原型 console.html 982 / 1000 / 1018 的下拉选项 */
const CACHES = ['sessions.json 已落盘', '未落盘']
const SEVS = ['P1 严重', 'P2 警告', 'P3 提示']
const STATES: { v: GwStatus; cn: string }[] = [
  { v: 'ok', cn: '正常' },
  { v: 'warn', cn: '告警' },
  { v: 'off', cn: '停用' },
]

/*
 * 初始值：store 的 formModel（gateway.ts 287–315）已经按原型 opsFormOpen
 * 复现了回填规则 —— 含从 target 里正则取端口的写法、cache 的「已落盘」判定、
 * gwLimit / gwFuse / gwStatus 的默认值。
 */
const form = ref<GwFormModel>(gateway.formModel(overlay.modalEditingId))

/** 编辑还是新增 */
const isEdit = computed(() => overlay.modalEditingId !== null)
/** 告警规则表单 or 用户路由表单（原型 4473 的 isAlert） */
const isAlert = computed(() => form.value.isAlert)

/*
 * 原型 4503：新建时通知渠道的默认值是「值班群 + 短信」（告警规则回落成「值班群」）。
 * store 的 formModel 对新记录统一给 '值班群'，这里把用户路由的默认值补齐。
 */
if (!isEdit.value && !isAlert.value) form.value.gwNotice = '值班群 + 短信'

/** 标题：原型 4474 '(编辑|新建) + (告警规则|用户路由)' */
const title = computed(
  () => `${isEdit.value ? '编辑' : '新建'}${isAlert.value ? '告警规则' : '用户路由'}`,
)
/** 提交按钮：原型 4482 '保存修改' / '确认保存' */
const submitText = computed(() => (isEdit.value ? '保存修改' : '确认保存'))
/** 副标题：store 的 formSub（原型 4475–4481 的三段文案，含容器/日志页兜底） */
const sub = computed(() => gateway.formSub(isEdit.value ? 'edit' : 'add'))

/** 原型的 gwClose / gwCancel（opsFormClose('gw')） */
function onClose(): void {
  overlay.closeModal()
}

/**
 * 端口只收数字：原型 4568 在提交时剥非数字字符，这里顺手在输入时剥掉，
 * 让输入框内容与最终写进 ROUTES 的 http://127.0.0.1:<端口>/ 一致。
 * 不用 v-model：做不到「先改 DOM 值再同步」，而 :value + @input 可以。
 */
function onPort(e: Event): void {
  const el = e.target as HTMLInputElement
  const digits = el.value.replace(/[^\d]/g, '')
  el.value = digits
  form.value.gwPort = digits
}

/** 原型 gwFormSubmit（4549–4609）：名称为空时 store 会提示「请先填写…」 */
function onSubmit(): void {
  if (gateway.submitForm(form.value)) overlay.closeModal()
}
</script>

<template>
  <div
    class="modal is-on"
    id="gwModal"
    role="dialog"
    aria-modal="true"
    aria-labelledby="gwModalTitle"
    aria-hidden="false"
  >
    <form class="modal__card" id="gwForm" autocomplete="off" @submit.prevent="onSubmit">
      <header class="modal__head">
        <h3 id="gwModalTitle">{{ title }}</h3>
        <button class="iconbtn" type="button" id="gwClose" aria-label="关闭" @click="onClose">
          <IconSprite name="i-x" cls="ic" />
        </button>
      </header>

      <!-- 副标题：原型 963 的 #gwModalSub -->
      <p class="modal__sub" id="gwModalSub">{{ sub }}</p>

      <div class="modal__grid">
        <!-- 用户路由字段组：原型 967–985（登录用户 / 容器名 / 目标端口 / token / 会话缓存）
             + 原型 1006–1014 的入口源、同源校验、通知渠道 -->
        <div v-if="!isAlert" class="tfields" data-kind="gwroute">
          <label class="fld fld--wide">
            <i>登录用户</i>
            <span class="fld__box">
              <input
                v-model="form.gwName"
                name="gwName"
                placeholder="如 a（代理侧 ROUTES 的键）"
                maxlength="32"
              />
            </span>
          </label>
          <label class="fld">
            <i>目标容器</i>
            <span class="fld__box">
              <input v-model="form.gwContainer" name="gwContainer" placeholder="dsh-web-a" maxlength="32" />
            </span>
          </label>
          <label class="fld">
            <i>端口</i>
            <span class="fld__box">
              <input
                :value="form.gwPort"
                name="gwPort"
                placeholder="8083"
                maxlength="40"
                inputmode="numeric"
                @input="onPort"
              />
            </span>
          </label>
          <label class="fld">
            <i>启动令牌</i>
            <span class="fld__box">
              <input v-model="form.gwToken" name="gwToken" placeholder="tok-a-8f3c1d" maxlength="32" />
            </span>
          </label>
          <label class="fld">
            <i>会话缓存</i>
            <span class="fld__box fld__box--sel">
              <select v-model="form.gwCache" name="gwCache">
                <option v-for="c in CACHES" :key="c" :value="c">{{ c }}</option>
              </select>
            </span>
          </label>

          <label class="fld fld--wide">
            <i>入口源（ENTRY_ORIGIN）</i>
            <span class="fld__box">
              <input v-model="form.gwLimit" name="gwLimit" maxlength="32" />
            </span>
          </label>
          <label class="fld fld--wide">
            <i>防护（同源校验 / 白名单）</i>
            <span class="fld__box">
              <input v-model="form.gwFuse" name="gwFuse" maxlength="36" />
            </span>
          </label>
          <label class="fld fld--wide">
            <i>通知渠道</i>
            <span class="fld__box">
              <input v-model="form.gwNotice" name="gwNotice" maxlength="32" />
            </span>
          </label>
        </div>

        <!-- 告警规则字段组：原型 988–1003（规则名称 / 监控对象 / 触发条件 / 严重程度）
             + 该组的通知渠道默认「值班群」（store formModel 已给） -->
        <div v-else class="tfields" data-kind="gwalert">
          <label class="fld fld--wide">
            <i>规则名称</i>
            <span class="fld__box">
              <input
                v-model="form.gwAlertName"
                name="gwAlertName"
                placeholder="如 容器实例不可达"
                maxlength="32"
              />
            </span>
          </label>
          <label class="fld">
            <i>监控对象</i>
            <span class="fld__box">
              <input
                v-model="form.gwTarget"
                name="gwTarget"
                placeholder="全部 dsh-web-* / proxy"
                maxlength="40"
              />
            </span>
          </label>
          <label class="fld">
            <i>触发条件</i>
            <span class="fld__box">
              <input
                v-model="form.gwCond"
                name="gwCond"
                placeholder="连接失败 / 连续 3 次超时"
                maxlength="40"
              />
            </span>
          </label>
          <label class="fld">
            <i>严重程度</i>
            <span class="fld__box fld__box--sel">
              <select v-model="form.gwSev" name="gwSev">
                <option v-for="s in SEVS" :key="s" :value="s">{{ s }}</option>
              </select>
            </span>
          </label>
          <label class="fld fld--wide">
            <i>通知渠道</i>
            <span class="fld__box">
              <input v-model="form.gwNotice" name="gwNotice" maxlength="32" />
            </span>
          </label>
        </div>

        <!-- 公共字段：原型 1015–1021（状态 ok / warn / off） -->
        <label class="fld fld--wide">
          <i>状态</i>
          <span class="fld__box fld__box--sel">
            <select v-model="form.gwStatus" name="gwStatus">
              <option v-for="s in STATES" :key="s.v" :value="s.v">{{ s.cn }}</option>
            </select>
          </span>
        </label>
      </div>

      <footer class="modal__foot">
        <p class="modal__hint" id="gwModalHint">{{ gateway.formHint }}</p>
        <div class="modal__acts">
          <button class="btn btn--ghost" type="button" id="gwCancel" @click="onClose">取消</button>
          <button class="btn btn--main" type="submit"><span id="gwSubmit">{{ submitText }}</span></button>
        </div>
      </footer>
    </form>
  </div>
</template>