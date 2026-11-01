<!--
  权限中心：新建 / 编辑（角色 / 账号 / 资源策略 / 提权工单共用一套弹窗骨架）
  等价迁移自原型 console.html 第 1035–1133 行 + console.js 4511–4533（回填）与
  4611–4667（pzFormSubmit）。

  原型把四套字段组全量渲染成 `.tfields[data-kind="role|acct|pol|appr"]`，
  靠 hidden 切组；这里按 formTab 用 v-if 四选一。当前 tab 由 store 的
  formTab 给出（编辑时看对象、新建时看当前 tab），标题取 PZTABS[tab].item。
-->
<script setup lang="ts">
import { computed, ref } from 'vue'
import IconSprite from '@/components/IconSprite.vue'
import { PZTABS, useAuthzStore } from '@/stores/authz'
import type { PzFormModel, PzStatus } from '@/stores/authz'
import { useOverlayStore } from '@/stores/overlay'

const overlay = useOverlayStore()
const authz = useAuthzStore()

/* 原型 console.html 1053 / 1074–1076 / 1091 / 1119 的下拉选项 */
const ROLE_KINDS = ['内置角色', '自定义角色', '服务账号角色']
/*
 * 数据范围：原型 role 组只给了 4 个（本部门 / 全公司 / 仅本人 / 指定项目），
 * 这里补上 data/authz.ts 里出现过的 生产环境 / 外部协作 / 研发中心，
 * 否则编辑这些范围的记录时下拉会回落到空值。
 */
const SCOPES = ['全公司', '本部门', '仅本人', '指定项目', '生产环境', '外部协作', '研发中心']
const ROLE_BINDS = [
  '平台管理员',
  '模型运营',
  '值班运维',
  '审计员（只读）',
  '数据分析师',
  '服务账号',
  '外部只读',
]
const EFFECTS = ['允许', '拒绝', '需要审批']
const STATES: { v: PzStatus; cn: string }[] = [
  { v: 'ok', cn: '正常' },
  { v: 'warn', cn: '告警' },
  { v: 'off', cn: '停用' },
]

/*
 * 初始值：store 的 formModel（authz.ts 300–323）已按原型 opsFormOpen 的
 * 权限分支（4512–4532）复现了四组字段的回填与默认值。
 */
const form = ref<PzFormModel>(authz.formModel(overlay.modalEditingId))

/** 编辑还是新增 */
const isEdit = computed(() => overlay.modalEditingId !== null)
/** 当前字段组（原型 4462 的 Pz.formTab） */
const tab = computed(() => authz.formTab)

/*
 * 原型 1104 的申请时限是文本框（默认「2 小时」），迁移要求给出候选值，
 * 所以改成下拉；但 data/authz.ts 里存在「1 小时」这类候选外的值，
 * 一律把回填值并进选项，避免编辑时选中项丢失。
 */
const LIFE_OPTIONS = ['2 小时', '30 分钟', '8 小时', '至 12-31', '长期有效']
const lifeOptions = computed<string[]>(() => {
  const cur = form.value.pzLife
  return cur && LIFE_OPTIONS.indexOf(cur) < 0 ? [cur, ...LIFE_OPTIONS] : LIFE_OPTIONS
})

/** 标题：原型 4506 '(编辑|新建) + PZTABS[tab].item' */
const title = computed(() => `${isEdit.value ? '编辑' : '新建'}${PZTABS[tab.value].item}`)
/** 提交按钮：原型 4508 '保存修改' / '确认保存' */
const submitText = computed(() => (isEdit.value ? '保存修改' : '确认保存'))

/** 原型的 pzClose / pzCancel（opsFormClose('pz')） */
function onClose(): void {
  overlay.closeModal()
}

/** 原型 pzFormSubmit（4611–4667）：名称为空时 store 会提示「请先填写名称」 */
function onSubmit(): void {
  if (authz.submitForm(form.value)) overlay.closeModal()
}
</script>

<template>
  <div
    class="modal is-on"
    id="pzModal"
    role="dialog"
    aria-modal="true"
    aria-labelledby="pzModalTitle"
    aria-hidden="false"
  >
    <form class="modal__card" id="pzForm" autocomplete="off" @submit.prevent="onSubmit">
      <header class="modal__head">
        <h3 id="pzModalTitle">{{ title }}</h3>
        <button class="iconbtn" type="button" id="pzClose" aria-label="关闭" @click="onClose">
          <IconSprite name="i-x" cls="ic" />
        </button>
      </header>

      <!-- 副标题：原型 1043 的 #pzModalSub（内容取自 store 的 formSub） -->
      <p class="modal__sub" id="pzModalSub">{{ authz.formSub }}</p>

      <div class="modal__grid">
        <!-- 角色字段组：原型 1047–1061（角色名称 / 角色类型 / 数据范围） -->
        <div v-if="tab === 'role'" class="tfields" data-kind="role">
          <label class="fld fld--wide">
            <i>角色名称</i>
            <span class="fld__box">
              <input
                v-model="form.pzName"
                name="pzName"
                placeholder="如 模型运营（只读）"
                maxlength="32"
              />
            </span>
          </label>
          <label class="fld">
            <i>角色类型</i>
            <span class="fld__box fld__box--sel">
              <select v-model="form.pzKind" name="pzKind">
                <option v-for="k in ROLE_KINDS" :key="k" :value="k">{{ k }}</option>
              </select>
            </span>
          </label>
          <label class="fld">
            <i>数据范围</i>
            <span class="fld__box fld__box--sel">
              <select v-model="form.pzScope" name="pzScope">
                <option v-for="s in SCOPES" :key="s" :value="s">{{ s }}</option>
              </select>
            </span>
          </label>
        </div>

        <!-- 账号字段组：原型 1064–1079（账号标识 / 所属部门 / 绑定角色） -->
        <div v-else-if="tab === 'acct'" class="tfields" data-kind="acct">
          <label class="fld fld--wide">
            <i>账号</i>
            <span class="fld__box">
              <input v-model="form.pzAcct" name="pzAcct" placeholder="如 ops.lin@corp" maxlength="40" />
            </span>
          </label>
          <label class="fld">
            <i>部门</i>
            <span class="fld__box">
              <input v-model="form.pzDept" name="pzDept" placeholder="云原生组" maxlength="20" />
            </span>
          </label>
          <label class="fld">
            <i>绑定角色</i>
            <span class="fld__box fld__box--sel">
              <select v-model="form.pzRoleBind" name="pzRoleBind">
                <option v-for="r in ROLE_BINDS" :key="r" :value="r">{{ r }}</option>
              </select>
            </span>
          </label>
        </div>

        <!-- 资源策略字段组：原型 1082–1094（策略名称 / 资源匹配 / 效果） -->
        <div v-else-if="tab === 'pol'" class="tfields" data-kind="pol">
          <label class="fld fld--wide">
            <i>策略名称</i>
            <span class="fld__box">
              <input
                v-model="form.pzPolName"
                name="pzPolName"
                placeholder="如 生产镜像只读"
                maxlength="32"
              />
            </span>
          </label>
          <label class="fld">
            <i>资源匹配</i>
            <span class="fld__box">
              <input
                v-model="form.pzRes"
                name="pzRes"
                placeholder="image:registry.internal/prod/*"
                maxlength="48"
              />
            </span>
          </label>
          <label class="fld">
            <i>效果</i>
            <span class="fld__box fld__box--sel">
              <select v-model="form.pzEffect" name="pzEffect">
                <option v-for="e in EFFECTS" :key="e" :value="e">{{ e }}</option>
              </select>
            </span>
          </label>
        </div>

        <!-- 工单字段组：原型 1097–1107（工单主题 / 申请人 / 申请时限） -->
        <div v-else class="tfields" data-kind="appr">
          <label class="fld fld--wide">
            <i>工单名称</i>
            <span class="fld__box">
              <input
                v-model="form.pzApprName"
                name="pzApprName"
                placeholder="如 申请临时导出权限"
                maxlength="40"
              />
            </span>
          </label>
          <label class="fld">
            <i>申请人</i>
            <span class="fld__box">
              <input v-model="form.pzWho" name="pzWho" placeholder="report.zhou@corp" maxlength="40" />
            </span>
          </label>
          <label class="fld">
            <i>时限</i>
            <span class="fld__box fld__box--sel">
              <select v-model="form.pzLife" name="pzLife">
                <option v-for="l in lifeOptions" :key="l" :value="l">{{ l }}</option>
              </select>
            </span>
          </label>
        </div>

        <!-- 公共字段：原型 1110–1122（动作 / 补充说明 / 状态） -->
        <label class="fld fld--wide">
          <i>允许动作</i>
          <span class="fld__box">
            <input
              v-model="form.pzActs"
              name="pzActs"
              placeholder="如 查看 · 部署"
              maxlength="40"
            />
          </span>
        </label>
        <label class="fld fld--wide">
          <i>说明</i>
          <span class="fld__box">
            <input
              v-model="form.pzDesc"
              name="pzDesc"
              placeholder="一句话说明这个授权用来做什么"
              maxlength="48"
            />
          </span>
        </label>
        <label class="fld fld--wide">
          <i>状态</i>
          <span class="fld__box fld__box--sel">
            <select v-model="form.pzStatus" name="pzStatus">
              <option v-for="s in STATES" :key="s.v" :value="s.v">{{ s.cn }}</option>
            </select>
          </span>
        </label>
      </div>

      <footer class="modal__foot">
        <p class="modal__hint" id="pzModalHint">{{ authz.formHint }}</p>
        <div class="modal__acts">
          <button class="btn btn--ghost" type="button" id="pzCancel" @click="onClose">取消</button>
          <button class="btn btn--main" type="submit"><span id="pzSubmit">{{ submitText }}</span></button>
        </div>
      </footer>
    </form>
  </div>
</template>