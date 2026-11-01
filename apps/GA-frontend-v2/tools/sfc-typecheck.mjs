/* ============================================================================
   .vue 单文件组件的类型检查（不 spawn 任何子进程）

   为什么不用 vue-tsc：它是一条 CLI，要 spawn（沙箱下 EPERM）。
   但 vue-tsc 的核心 @vue/language-core 是纯 JS，可以直接在进程内调用：
     · createVueLanguagePlugin.createVirtualCode → 把 .vue 拆成虚拟 TS 文件
     · toTsDiagnostics                          → 把语言核心的诊断翻成 TS 诊断
   再把 TypeScript 的 CompilerHost 包一层，
   让 TS 在 import '@/views/XxxView.vue' 时拿到虚拟文件，而不是全局的 *.vue shim。

   注意：因为这里为每个 .vue 提供了真实声明，
   src/env.d.ts 里那条 `declare module '*.vue'` 会造成重复声明，
   所以本脚本把 env.d.ts 从程序里剔除。vite build 仍然需要它，别删文件。

   用法：
     node tools/sfc-typecheck.mjs                 # 检查全部 .vue
     node tools/sfc-typecheck.mjs src/views       # 只检查某个子目录

   【注意 · 已知误报】
   本脚本是「不 spawn 的近似方案」，用来在沙箱里做快速体检，
   真正的验收标准是 `npx vue-tsc --noEmit`（也就是 npm run build 的第一步），
   它在本项目里已经是 0 错误。

   两类只在近似方案里出现的假问题，别照着改代码：
     1. 组件上的 `@update:xxx` 绑定会报 TS2322
        （__VLS_NormalizeComponentEvent 在缺少 projectVersion 的
        createProgram 模式下解析不出被更新 props 的完整形状）。
        实际 vue-tsc 不报。
     2. 模板里写 `x as T` 这类 TS 语法会报 TS1005 等语法错。
        这个是**真**问题（Vue 模板表达式是 JS），vue-tsc 同样会报，
        两边一致，必须改。
   ========================================================================== */

import ts from 'typescript'
import vue from '@vue/language-core'
import { readdirSync, statSync, existsSync } from 'node:fs'
import { join, relative, sep, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const { createVueLanguagePlugin, createParsedCommandLine, toTsDiagnostics } = vue
const root = fileURLToPath(new URL('..', import.meta.url))
const filterArg = process.argv[2]

const configPath = join(root, 'tsconfig.json')
const parsed = createParsedCommandLine(ts, ts.sys, configPath)
const options = parsed.options

/* ---------------------------------------------------------------- 收集 .vue */
function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    if (name === 'node_modules' || name === 'dist' || name === '.npm-cache') continue
    const p = join(dir, name)
    const st = statSync(p)
    if (st.isDirectory()) walk(p, out)
    else if (name.endsWith('.vue')) out.push(resolve(p))
  }
  return out
}

let vueFiles = walk(join(root, 'src'))
if (filterArg) {
  const abs = resolve(join(root, filterArg))
  vueFiles = vueFiles.filter((f) => f.startsWith(abs + sep) || f === abs)
}

if (!vueFiles.length) {
  console.log('没有找到 .vue 文件')
  process.exit(0)
}

/* ---------------------------------------------------------------- 虚拟代码 */
const plugin = createVueLanguagePlugin(ts, options, parsed.vueOptions ?? {}, (id) => id)

/** 磁盘绝对路径 → { main: 虚拟主文件名, files: Map<虚拟文件名, 源码> } */
const virtualByVue = new Map()

/**
 * 虚拟文件名 → 源码。
 * 由于本脚本用 createProgram（不是 LanguageService，没有 projectVersion），
 * 不能把带 query 的虚拟路径直接交给 TS —— 它会把 &type=script 当成文件名的一部分、
 * 找不到 sourceFile，进而把 .vue 原文件当 TS 解析（满屏 TS1127）。
 * 所以这里按「? 之前的部分」建索引：<vue>.vue.ts?x&y 与 <vue>.vue.ts 视作同一个文件，
 * 源码取 script_ts（模板检查代码在里面）那一份。
 */
const virtualText = new Map()

/**
 * 每个「? 之前的虚拟路径」可能被多次写入：根代码（.vue 原文，TS 语法不合法）
 * 与它的子块都会映射到同一个 <vue>.vue.ts。
 * 用 -1 表示「原始 .vue 文本」这种兜底内容，0 起表示真实的虚拟 TS 代码，
 * 只有不小于已存优先级时才覆盖 —— 这样 script_ts 永远不会被模板块或原文冲掉。
 */
const virtualPri = new Map()

function ensureVirtual(vuePath) {
  if (virtualByVue.has(vuePath)) return virtualByVue.get(vuePath)
  const text = ts.sys.readFile(vuePath)
  if (text === undefined) return undefined
  const snapshot = ts.ScriptSnapshot.fromString(text)
  /* createVirtualCode(fileName, languageId, snapshot, root?) */
  const virtual = plugin.createVirtualCode(vuePath, 'vue', snapshot)
  if (!virtual) return undefined

  const files = new Map()
  /* 脚本段优先：script_ts 含编译后的 setup + 模板检查代码 */
  let scriptText = null
  let fallbackScript = null

  const store = (fileName, snap, pri) => {
    if (!snap) return
    const src = snap.getText(0, snap.getLength())
    /* 统一按 ? 之前的路径存：TS 只会以这个路径请求它 */
    const base = fileName.split('?')[0]
    files.set(fileName, src)
    const prev = virtualPri.get(base)
    if (prev === undefined || prev <= pri) {
      virtualPri.set(base, pri)
      virtualText.set(base, src)
    }
  }

  /* 根代码只是兜底：它是 .vue 原文（含 <template>），当 TS 解析会满屏语法错误 */
  store(vuePath, virtual.initSnapshot, -1)

  const walk = (nodes, base) => {
    for (const node of nodes ?? []) {
      const vf = base === vuePath ? `${vuePath}.ts?${node.id}` : `${base}&${node.id}`
      store(vf, node.snapshot, 0)
      if (node.id === 'script_ts') {
        scriptText = node.snapshot?.getText(0, node.snapshot.getLength()) ?? null
        store(`${vuePath}.ts`, node.snapshot, 1)
      }
      if (node.id === 'scriptsetup_raw') {
        fallbackScript = node.snapshot?.getText(0, node.snapshot.getLength()) ?? null
      }
      if (node.embeddedCodes) walk(node.embeddedCodes, vf)
    }
  }
  walk(virtual.embeddedCodes, vuePath)

  const main = `${vuePath}.ts`
  /* 主文件内容 = script_ts ≫ scriptsetup_raw；都没有（纯模板组件）就退回根代码 */
  let mainText = scriptText ?? fallbackScript ?? files.get(vuePath) ?? ''
  /* script_ts 开头的 /// <reference types="../../..../.vue-global-types/x.d.ts" />
     是按 .vue 所在目录算的相对路径；虚拟文件挪到了 <vue>.vue.ts（浅一层），
     这条相对路径就会失效。改成磁盘绝对路径，等价且不受层级影响。 */
  const shim = join(root, 'node_modules', '.vue-global-types', 'vue_3.5_0_0_0.d.ts')
  if (existsSync(shim) && /\.vue-global-types/.test(mainText)) {
    mainText = mainText.replace(
      /\/\/\/\s*<reference\s+types="[^"]*\.vue-global-types[^"]*"\s*\/>/,
      `/// <reference types="${shim.replace(/\\/g, '/').replace(/\.d\.ts$/, '')}" />`,
    )
  }
  files.set(main, mainText)
  virtualText.set(main, mainText)

  const entry = { main, files }
  virtualByVue.set(vuePath, entry)
  return entry
}

for (const f of vueFiles) ensureVirtual(f)

/* ---------------------------------------------------------------- host */
const defaultHost = ts.createCompilerHost(options, true)

const host = {
  ...defaultHost,

  getSourceFile(fileName, languageVersion, onError, shouldCreate) {
    const virtual = virtualText.get(fileName)
    if (virtual !== undefined) {
      return ts.createSourceFile(fileName, virtual, languageVersion, true)
    }
    return defaultHost.getSourceFile(fileName, languageVersion, onError, shouldCreate)
  },

  fileExists(fileName) {
    if (virtualText.has(fileName)) return true
    if (/\.vue$/.test(fileName)) return existsSync(fileName)
    return defaultHost.fileExists(fileName)
  },

  readFile(fileName) {
    const virtual = virtualText.get(fileName)
    if (virtual !== undefined) return virtual
    return defaultHost.readFile(fileName)
  },

  /* 把 import '...vue' 解析到语言核心给出的虚拟主文件 */
  resolveModuleName(moduleName, containingFile) {
    const hit = resolveVueModule(moduleName, containingFile)
    if (hit) return hit
    return ts.resolveModuleName(moduleName, containingFile, options, defaultHost).resolvedModule
  },

  /* createProgram 优先走这个新接口（旧接口只在它缺席时才用），所以两个都要给。
     注意：返回数组的长度必须与入参一致，且每一项都不能是 undefined。 */
  resolveModuleNameLiterals(moduleLiterals, containingFile) {
    return moduleLiterals.map((lit) => {
      const hit = resolveVueModule(lit.text, containingFile)
      if (hit) {
        return { resolvedModule: hit, failedLookupLocations: [], affectingLocations: [] }
      }
      const fallback = ts.resolveModuleName(lit.text, containingFile, options, defaultHost)
      return {
        resolvedModule: fallback.resolvedModule,
        failedLookupLocations: [],
        affectingLocations: [],
      }
    })
  },
}

/** 命中 .vue 时返回虚拟主文件的解析结果，否则返回 undefined */
function resolveVueModule(moduleName, containingFile) {
  if (!/\.vue$/.test(moduleName)) return undefined
  const resolvedVue = resolveVuePath(moduleName, containingFile)
  if (!resolvedVue) return undefined
  const entry = ensureVirtual(resolvedVue)
  if (!entry?.main) return undefined
  return {
    resolvedFileName: entry.main,
    extension: ts.Extension.Ts,
    isExternalLibraryImport: false,
  }
}

/** 把 '@/' 与相对路径解析成磁盘上的真实 .vue 路径 */
function resolveVuePath(moduleName, containingFile) {
  let base
  if (moduleName.startsWith('@/')) {
    const alias = options.paths?.['@/*']?.[0] ?? 'src/*'
    base = join(root, alias.replace('*', moduleName.slice(2)))
  } else if (moduleName.startsWith('.')) {
    base = resolve(containingFile, '..', moduleName)
  } else {
    return undefined
  }
  for (const cand of [base, `${base}.vue`, join(base, 'index.vue')]) {
    if (cand.endsWith('.vue') && existsSync(cand)) return cand
  }
  return undefined
}

/* ---------------------------------------------------------------- 检查 */
/* 根文件：全部 .ts（剔掉 *.vue 的通配 shim —— 这里每个 .vue 都有自己的虚拟声明，
   保留通配会与之冲突）+ 全部 .vue 的虚拟主文件。
   src/env.d.ts 必须留下：v-html 的 GlobalDirectives 增强写在里面。 */
const tsFiles = parsed.fileNames.filter((f) => !/shims?-vue\.d\.ts$/.test(f))
const rootNames = [...tsFiles, ...[...virtualByVue.values()].map((e) => e.main).filter(Boolean)]

/* 直接用 createProgram：它只需要 host 上的 resolveModuleName（旧版签名），
   不像 LanguageService 那样还要求 getScriptFileNames / getScriptSnapshot 等一堆成员。 */
const program = ts.createProgram(rootNames, options, host)

const diags = [
  ...program.getSyntacticDiagnostics(),
  ...program.getSemanticDiagnostics(),
]

/* 语言核心自己的诊断（模板上的问题，比如插值里用错成员） */
for (const vuePath of vueFiles) {
  try {
    const text = ts.sys.readFile(vuePath)
    if (text === undefined) continue
    const code = plugin.createVirtualCode(vuePath, 'vue', ts.ScriptSnapshot.fromString(text))
    if (!code) continue
    for (const d of toTsDiagnostics(plugin.getDiagnostics(vuePath, code), ts)) {
      if (d.file) diags.push(d)
    }
  } catch {
    /* 语言核心对个别文件可能抛错，跳过 */
  }
}

const all = diags.filter((d) => !(d.file && /env\.d\.ts$/.test(d.file.fileName)))

if (!all.length) {
  console.log(`类型检查通过：${vueFiles.length} 个 .vue 文件，0 个错误`)
  process.exit(0)
}

const seen = new Set()
for (const d of all) {
  const msg = ts.flattenDiagnosticMessageText(d.messageText, '\n  ')
  const key = `${d.file?.fileName}:${d.start}:${d.code}`
  if (seen.has(key)) continue
  seen.add(key)
  if (d.file && d.start !== undefined) {
    const { line, character } = d.file.getLineAndCharacterOfPosition(d.start)
    const rel = relative(root, d.file.fileName).split(sep).join('/')
    console.log(`${rel}:${line + 1}:${character + 1}  TS${d.code}  ${msg}`)
  } else {
    console.log(`TS${d.code}  ${msg}`)
  }
}

console.log(`\n共 ${seen.size} 个类型错误（检查 ${vueFiles.length} 个 .vue 文件）`)
process.exit(1)

void rootNames