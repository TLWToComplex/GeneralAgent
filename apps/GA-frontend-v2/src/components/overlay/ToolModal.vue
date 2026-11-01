<!--
  工具平台：新增 / 编辑 MCP 服务与 Skill 工具
  等价迁移自原型 console.html 第 804–885 行 + console.js 2330–2445（toolFormOpen /
  toolFormClose / toolFormSubmit）。

  原型靠 `.tfields[data-kind]` + hidden 属性切换两套字段组，这里改用 v-model 与
  v-if（CSS 的 .tfields{display:contents} 只负责让 .fld 落进 .modal__grid，
  去掉整组元素在视觉上完全等价）。字段名统一走 store 的 ToolFormModel。
-->
<script setup lang="ts">
import { computed, ref } from 'vue'
import IconSprite from '@/components/IconSprite.vue'
import { useToolsStore } from '@/stores/tools'
import type { ToolFormModel, ToolState } from '@/stores/tools'
import { useOverlayStore } from '@/stores/overlay'

const overlay = useOverlayStore()
const tools = useToolsStore()

/** MCP 接入方式（原型 822 + data/tools.ts 的 McpTransport 值域） */
const MCP_TRANSPORTS = ['stdio', 'SSE', 'streamable-http']
/** Skill 运行时（原型 2362 写死 Python 3.12；data/tools.ts 增加 Node 22） */
const SKILL_RUNTIMES = ['Python 3.12', 'Node 22']
/** Skill 适用智能体（原型 849–851 的 option 顺序） */
const SKILL_OWNERS = [
  'Ops-Agent',
  'Report-Agent',
  'Code-Agent',
  'Review-Agent',
  'Ingest-Agent',
  'Search-Agent',
]
/** 状态三态（原型 866–869 的 value / 中文） */
const STATES: { v: ToolState; cn: string }[] = [
  { v: 'online', cn: '在线' },
  { v: 'degraded', cn: '异常' },
  { v: 'offline', cn: '已下线' },
]

/*
 * 初始值由 store 的 formModel(overlay.modalEditingId) 灌入 —— 它内部按
 * 「编辑对象的 kind 或当前 tab」还原工具类型（tools.ts 185–202）。
 * ConsoleView 用 v-if 挂载本组件，setup 阶段即等价于原型 toolFormOpen 的回填。
 */
const form = ref<ToolFormModel>(tools.formModel(overlay.modalEditingId))

/** 编辑还是新增（决定标题与提交按钮文案） */
const isEdit = computed(() => overlay.modalEditingId !== null)
/** 是否 MCP 表单（原型 2337 的 isMcp，来自 store） */
const isMcp = computed(() => tools.formIsMcp)

/*
 * 新建 Skill 时原型给「版本 1.0.0 / 运行时长上限 120s」两个 HTML 默认值
 * （console.html 845 / 856）；store 的 formModel 对无记录返回空串，这里按原型补上，
 * 不填也不会丢 —— store 提交时仍有 '120s' / '0.1.0' 的兜底。
 */
if (!isEdit.value && !isMcp.value) {
  if (!form.value.toolTimeout) form.value.toolTimeout = '120s'
  if (!form.value.toolVersion) form.value.toolVersion = '1.0.0'
}

/** 标题：原型 2346 '(编辑|新增) + (MCP 服务|Skill 工具)' */
const title = computed(
  () => `${isEdit.value ? '编辑' : '新增'}${isMcp.value ? ' MCP 服务' : ' Skill 工具'}`,
)
/** 提交按钮：原型 2350 '保存修改' / '确认新增' */
const submitText = computed(() => (isEdit.value ? '保存修改' : '确认新增'))

/** 原型的 toolClose / toolCancel：opsFormClose 的等价物 */
function onClose(): void {
  overlay.closeModal()
}

/** 原型 toolFormSubmit（2383–2444）：store 负责校验名称并写注册表 */
function onSubmit(): void {
  if (tools.submitForm(form.value)) overlay.closeModal()
}
</script>

<template>
  <div
    class="modal is-on"
    id="toolModal"
    role="dialog"
    aria-modal="true"
    aria-labelledby="toolModalTitle"
    aria-hidden="false"
  >
    <form class="modal__card" id="toolForm" autocomplete="off" @submit.prevent="onSubmit">
      <header class="modal__head">
        <h3 id="toolModalTitle">{{ title }}</h3>
        <button class="iconbtn" type="button" id="toolClose" aria-label="关闭" @click="onClose">
          <IconSprite name="i-x" cls="ic" />
        </button>
      </header>

      <!-- 副标题：原型 812 的 #toolModalSub（内容取自 store 的 formSub） -->
      <p class="modal__sub" id="toolModalSub">{{ tools.formSub }}</p>

      <div class="modal__grid">
        <!-- MCP 字段组：原型 816–834（服务名称 / 接入方式 / 端点 / 提供方 / 暴露工具数） -->
        <div v-if="isMcp" class="tfields" data-kind="mcp">
          <label class="fld fld--wide">
            <i>服务名称</i>
            <span class="fld__box">
              <input v-model="form.toolName" name="toolName" placeholder="如 sheet-mcp" maxlength="32" />
            </span>
          </label>
          <label class="fld">
            <i>分类</i>
            <span class="fld__box">
              <input v-model="form.toolCat" name="toolCat" placeholder="如 数据服务" maxlength="16" />
            </span>
          </label>
          <label class="fld">
            <i>接入方式</i>
            <span class="fld__box fld__box--sel">
              <select v-model="form.toolTransport" name="toolTransport">
                <option v-for="t in MCP_TRANSPORTS" :key="t" :value="t">{{ t }}</option>
              </select>
            </span>
          </label>
          <label class="fld">
            <i>端点</i>
            <span class="fld__box">
              <input
                v-model="form.toolEndpoint"
                name="toolEndpoint"
                placeholder="wss://mcp.internal/sheet"
                maxlength="64"
              />
            </span>
          </label>
          <label class="fld">
            <i>提供方</i>
            <span class="fld__box">
              <input v-model="form.toolVendor" name="toolVendor" placeholder="数据平台组" maxlength="24" />
            </span>
          </label>
          <label class="fld">
            <i>暴露能力</i>
            <span class="fld__box">
              <input v-model="form.toolExposes" name="toolExposes" maxlength="4" />
            </span>
          </label>
        </div>

        <!-- Skill 字段组：原型 837–858，把「接入方式」换成运行时、「提供方」换成适用智能体 -->
        <div v-else class="tfields" data-kind="skill">
          <label class="fld fld--wide">
            <i>技能名称</i>
            <span class="fld__box">
              <input v-model="form.toolName" name="toolName" placeholder="如 table-diff" maxlength="32" />
            </span>
          </label>
          <label class="fld">
            <i>分类</i>
            <span class="fld__box">
              <input v-model="form.toolCat" name="toolCat" placeholder="数据处理" maxlength="16" />
            </span>
          </label>
          <label class="fld">
            <i>运行时</i>
            <span class="fld__box fld__box--sel">
              <select v-model="form.toolTransport" name="toolTransport">
                <option v-for="r in SKILL_RUNTIMES" :key="r" :value="r">{{ r }}</option>
              </select>
            </span>
          </label>
          <label class="fld">
            <i>端点</i>
            <span class="fld__box">
              <input
                v-model="form.toolEndpoint"
                name="toolEndpoint"
                placeholder="skills/table_diff.py"
                maxlength="64"
              />
            </span>
          </label>
          <label class="fld">
            <i>适用智能体</i>
            <span class="fld__box fld__box--sel">
              <select v-model="form.toolOwner" name="toolOwner">
                <option v-for="o in SKILL_OWNERS" :key="o" :value="o">{{ o }}</option>
              </select>
            </span>
          </label>
          <label class="fld">
            <i>暴露能力</i>
            <span class="fld__box">
              <input v-model="form.toolExposes" name="toolExposes" maxlength="4" />
            </span>
          </label>
          <label class="fld">
            <i>版本</i>
            <span class="fld__box">
              <input v-model="form.toolVersion" name="toolVersion" placeholder="如 2.3.1" maxlength="12" />
            </span>
          </label>
          <label class="fld">
            <i>时长上限</i>
            <span class="fld__box">
              <input v-model="form.toolTimeout" name="toolTimeout" placeholder="如 120s" maxlength="8" />
            </span>
          </label>
        </div>

        <!-- 公共字段：原型 861–872（描述 + 状态） -->
        <label class="fld fld--wide">
          <i>描述</i>
          <span class="fld__box">
            <input
              v-model="form.toolDesc"
              name="toolDesc"
              placeholder="一句话说明这个工具做什么"
              maxlength="48"
            />
          </span>
        </label>
        <label class="fld fld--wide">
          <i>状态</i>
          <span class="fld__box fld__box--sel">
            <select v-model="form.toolStatus" name="toolStatus">
              <option v-for="s in STATES" :key="s.v" :value="s.v">{{ s.cn }}</option>
            </select>
          </span>
        </label>
      </div>

      <footer class="modal__foot">
        <p class="modal__hint" id="toolModalHint">{{ tools.formHint }}</p>
        <div class="modal__acts">
          <button class="btn btn--ghost" type="button" id="toolCancel" @click="onClose">取消</button>
          <button class="btn btn--main" type="submit"><span id="toolSubmit">{{ submitText }}</span></button>
        </div>
      </footer>
    </form>
  </div>
</template>