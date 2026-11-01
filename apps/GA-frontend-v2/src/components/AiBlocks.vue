<!--
  安装流程的内容块渲染器 —— 把 data/aitools.ts 里的 AiBlock 判别联合画出来。

  为什么单独抽一个组件：
    「某个工具的安装流程」（AiToolGuide）与「内网模型参数速查」（AiModelRef）
    用的是同一套块，只是外层容器不同。块渲染只有这一份，改文案/样式不会两边跑偏。

  块类型（见 data/aitools.ts 的 AiBlock）：
    p      段落
    code   命令 / 配置片段（带标题、语言角标与复制按钮）
    kv     键值表（表单字段、环境要求这类「照着填」的信息）
    note   提示条（info 蓝 / warn 琥珀 / ok 绿）
    list   清单（勾选式的操作步骤）
    table  表格（快捷键、字段说明、常见问题）
    files     下载条目（安装包 / 发布页，点「领取」由父组件记账）
    optional  可选块（整块降级：虚线边 + 「可选」角标，里面可嵌套上面任意块）

  行内最小 Markdown（md()）：
    内容里用 **粗体** 与 `代码` 表达强调 —— 直接写 HTML 会把转义责任推给数据层，
    所以这里做一次「先 esc、再替换」的最小解析。顺序不能反：先替换就等于放开了
    XSS 的口子（虽然内容全部来自仓库内的静态数据，也没有必要冒这个险）。

  复制与领取不在这里决定行为，一律 emit 给父组件 —— 记账、提示、开新标签页的
  逻辑集中在 store 与视图层，块渲染保持无副作用。
-->
<script setup lang="ts">
import IconSprite from '@/components/IconSprite.vue'
import { esc } from '@/lib/util'
import type { AiBlock, AiFile, AiNoteKind } from '@/data/aitools'

defineProps<{ blocks: readonly AiBlock[] }>()

const emit = defineEmits<{
  (e: 'copy', text: string, label: string): void
  (e: 'file', file: AiFile): void
}>()

/** 提示条的默认标题（数据里没写 title 时用） */
const NOTE_CN: Record<AiNoteKind, string> = {
  info: '说明',
  warn: '注意',
  ok: '要点',
}

/** 可选块里会嵌套一层 AiBlocks，把子块的 copy / file 原样透传给父组件 */
function onCopy(text: string, label: string): void {
  emit('copy', text, label)
}
function onFile(file: AiFile): void {
  emit('file', file)
}

/** 行内最小 Markdown：**粗体**、`代码`、换行 → <br>。先 esc 再替换，顺序不能反 */
function md(s: string): string {
  return esc(s)
    .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
}
</script>

<template>
  <div class="aiblocks">
    <template v-for="(b, i) in blocks" :key="i">
      <!-- 段落 -->
      <p v-if="b.t === 'p'" class="aip" v-html="md(b.v)" />

      <!-- 命令 / 配置片段 -->
      <figure v-else-if="b.t === 'code'" class="aicode">
        <figcaption>
          <span class="aicode__title">{{ b.title || '命令 / 配置' }}</span>
          <span v-if="b.lang" class="aicode__lang">{{ b.lang }}</span>
          <button
            class="aicode__copy"
            type="button"
            :aria-label="`复制${b.title || '这段内容'}`"
            @click="emit('copy', b.v, b.title || '代码块')"
          >
            <!-- 复制图标：图标精灵里没有这一个，按 AppTopbar「退出」的写法内联（.ic 是描边式） -->
            <svg class="ic" aria-hidden="true" viewBox="0 0 24 24">
              <rect x="9" y="9" width="11" height="11" rx="2.4" />
              <path d="M6.4 14.8A2.4 2.4 0 0 1 4 12.4V6.4A2.4 2.4 0 0 1 6.4 4h6a2.4 2.4 0 0 1 2.4 2.4" />
            </svg>
            复制
          </button>
        </figcaption>
        <pre><code>{{ b.v }}</code></pre>
      </figure>

      <!-- 提示条 -->
      <div v-else-if="b.t === 'note'" class="ainote" :class="`is-${b.kind}`">
        <b class="ainote__title">{{ b.title || NOTE_CN[b.kind] }}</b>
        <p v-html="md(b.v)" />
      </div>

      <!-- 键值表 -->
      <div v-else-if="b.t === 'kv'" class="aikv">
        <h5 v-if="b.title">{{ b.title }}</h5>
        <dl>
          <template v-for="(row, j) in b.rows" :key="j">
            <dt v-html="md(row[0])" />
            <dd v-html="md(row[1])" />
          </template>
        </dl>
      </div>

      <!-- 清单 -->
      <div v-else-if="b.t === 'list'" class="ailist">
        <h5 v-if="b.title">{{ b.title }}</h5>
        <ul>
          <li v-for="(it, j) in b.v" :key="j" v-html="md(it)" />
        </ul>
      </div>

      <!-- 表格 -->
      <div v-else-if="b.t === 'table'" class="aitable">
        <h5 v-if="b.title">{{ b.title }}</h5>
        <div class="aitable__wrap">
          <table>
            <thead>
              <tr>
                <th v-for="(h, j) in b.head" :key="j">{{ h }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, j) in b.rows" :key="j">
                <td v-for="(c, k) in row" :key="k" v-html="md(c)" />
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 下载条目 -->
      <div v-else-if="b.t === 'files'" class="aifiles">
        <h5 v-if="b.title">{{ b.title }}</h5>
        <div v-for="(f, j) in b.v" :key="j" class="aifile">
          <span class="aifile__ico"><IconSprite name="i-download" cls="ic" /></span>
          <span class="aifile__id">
            <b>{{ f.name }}</b>
            <i>{{ f.size }}<template v-if="f.note"> · {{ f.note }}</template></i>
          </span>
          <span v-if="f.latest" class="tagchip">最新</span>
          <button class="btn btn--main" type="button" @click="emit('file', f)">
            <span>领取</span>
          </button>
        </div>
      </div>

      <!-- 可选块：整块降级（虚线边 + 「可选」角标），里面可继续嵌套任意块 -->
      <section v-else-if="b.t === 'optional'" class="aiopt">
        <header class="aiopt__head">
          <span class="aiopt__badge">可选</span>
          <b class="aiopt__title">{{ b.title || '进阶设置' }}</b>
        </header>
        <AiBlocks :blocks="b.v" @copy="onCopy" @file="onFile" />
      </section>
    </template>
  </div>
</template>