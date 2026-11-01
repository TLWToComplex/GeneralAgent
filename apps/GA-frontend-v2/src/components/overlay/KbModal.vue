<!--
  知识库中心：新建 / 编辑
  等价迁移自原型 console.html 第 886–954 行 + console.js 2917–2998
  （kbFormOpen / kbFormClose / kbFormSubmit）。

  回填与提交全部交给 store：formModel(overlay.modalEditingId) 给初始值
  （含按类型派生的切片长度 / 重叠默认值），submitForm(model) 负责校验名称、
  写库并返回是否成功。类型名用 kindOf(id)（新建时看当前 tab）。
-->
<script setup lang="ts">
import { computed, ref } from 'vue'
import IconSprite from '@/components/IconSprite.vue'
import { useKbStore } from '@/stores/kb'
import type { KbFormModel, KbState } from '@/stores/kb'
import { useOverlayStore } from '@/stores/overlay'
import { KBKIND } from '@/data/kb'

const overlay = useOverlayStore()
const kb = useKbStore()

/* 原型 console.html 905 / 916–925 的下拉选项 */
const LANGS = ['中文', '中英混合', '英文']
/*
 * 向量模型：原型给的是 bge-m3-1024 / text-embedding-3-large / qwen-embed-1024 /
 * m3e-base-768，迁移要求补上 bge-large-zh-v1.5。后两个原型值必须留着 ——
 * data/kb.ts 里确有 embed='qwen-embed-1024'、'm3e-base-768' 的记录，
 * 少一个选项编辑该库时下拉会回落到空值。
 */
const EMBEDS = [
  'bge-m3-1024',
  'bge-large-zh-v1.5',
  'text-embedding-3-large',
  'qwen-embed-1024',
  'm3e-base-768',
]
const STORES = ['milvus-corp', 'pgvector-ha', 'elasticsearch-knn']
/** 四态（原型 931–935 的 value / 中文） */
const STATES: { v: KbState; cn: string }[] = [
  { v: 'ready', cn: '就绪' },
  { v: 'indexing', cn: '索引中' },
  { v: 'paused', cn: '已暂停' },
  { v: 'failed', cn: '异常' },
]

/*
 * 初始值来自 store 的 formModel（kb.ts 333–348），它已按原型 kbFormOpen
 * （2930–2938）复现了所有默认值：语言中文、切片 512 字 / 一问一答 / 一条一口径、
 * 重叠 64 字、向量模型 bge-m3-1024、向量库 milvus-corp、状态 ready。
 */
const form = ref<KbFormModel>(kb.formModel(overlay.modalEditingId))

/** 编辑还是新建（决定标题与提交按钮文案） */
const isEdit = computed(() => overlay.modalEditingId !== null)
/** 当前类型：编辑看对象，新建看当前 tab（原型 2921 的 kind） */
const kind = computed(() => kb.kindOf(overlay.modalEditingId))

/** 标题：原型 2923 '(编辑|新建) + KBKIND[kind]' */
const title = computed(() => `${isEdit.value ? '编辑' : '新建'}${KBKIND[kind.value]}`)
/** 提交按钮：原型 2925 '保存修改' / '确认新建' */
const submitText = computed(() => (isEdit.value ? '保存修改' : '确认新建'))

/** 原型的 kbClose / kbCancel（kbFormClose） */
function onClose(): void {
  overlay.closeModal()
}

/** 原型 kbFormSubmit（2951–2998）：名称为空时 store 会提示「请先填写知识库名称」 */
function onSubmit(): void {
  if (kb.submitForm(form.value)) overlay.closeModal()
}
</script>

<template>
  <div
    class="modal is-on"
    id="kbModal"
    role="dialog"
    aria-modal="true"
    aria-labelledby="kbModalTitle"
    aria-hidden="false"
  >
    <form class="modal__card" id="kbForm" autocomplete="off" @submit.prevent="onSubmit">
      <header class="modal__head">
        <h3 id="kbModalTitle">{{ title }}</h3>
        <button class="iconbtn" type="button" id="kbClose" aria-label="关闭" @click="onClose">
          <IconSprite name="i-x" cls="ic" />
        </button>
      </header>

      <!-- 副标题：原型 894 的 #kbModalSub（内容取自 store 的 formSub） -->
      <p class="modal__sub" id="kbModalSub">{{ kb.formSub }}</p>

      <!-- 字段与顺序照抄原型 896–942 -->
      <div class="modal__grid">
        <label class="fld fld--wide">
          <i>知识库名称</i>
          <span class="fld__box">
            <input v-model="form.kbName" name="kbName" placeholder="如 财务共享问答" maxlength="32" />
          </span>
        </label>

        <label class="fld">
          <i>归属业务</i>
          <span class="fld__box">
            <input v-model="form.kbOwner" name="kbOwner" placeholder="财务管理部" maxlength="20" />
          </span>
        </label>

        <label class="fld">
          <i>内容语言</i>
          <span class="fld__box fld__box--sel">
            <select v-model="form.kbLang" name="kbLang">
              <option v-for="l in LANGS" :key="l" :value="l">{{ l }}</option>
            </select>
          </span>
        </label>

        <label class="fld">
          <i>切片长度</i>
          <span class="fld__box"><input v-model="form.kbChunk" name="kbChunk" maxlength="10" /></span>
        </label>

        <label class="fld">
          <i>切片重叠</i>
          <span class="fld__box"><input v-model="form.kbOverlap" name="kbOverlap" maxlength="10" /></span>
        </label>

        <label class="fld">
          <i>向量模型</i>
          <span class="fld__box fld__box--sel">
            <select v-model="form.kbEmbed" name="kbEmbed">
              <option v-for="e in EMBEDS" :key="e" :value="e">{{ e }}</option>
            </select>
          </span>
        </label>

        <label class="fld">
          <i>向量库</i>
          <span class="fld__box fld__box--sel">
            <select v-model="form.kbStore" name="kbStore">
              <option v-for="s in STORES" :key="s" :value="s">{{ s }}</option>
            </select>
          </span>
        </label>

        <label class="fld fld--wide">
          <i>状态</i>
          <span class="fld__box fld__box--sel">
            <select v-model="form.kbStatus" name="kbStatus">
              <option v-for="s in STATES" :key="s.v" :value="s.v">{{ s.cn }}</option>
            </select>
          </span>
        </label>

        <label class="fld fld--wide">
          <i>语料范围</i>
          <span class="fld__box">
            <input
              v-model="form.kbScope"
              name="kbScope"
              placeholder="如 12 类制度文件 + 3 套操作手册，按部门过滤"
              maxlength="48"
            />
          </span>
        </label>
      </div>

      <footer class="modal__foot">
        <p class="modal__hint" id="kbModalHint">{{ kb.formHint }}</p>
        <div class="modal__acts">
          <button class="btn btn--ghost" type="button" id="kbCancel" @click="onClose">取消</button>
          <button class="btn btn--main" type="submit"><span id="kbSubmit">{{ submitText }}</span></button>
        </div>
      </footer>
    </form>
  </div>
</template>