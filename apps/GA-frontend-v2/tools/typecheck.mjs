/* ============================================================================
   spawn-free 类型检查

   沙箱禁止程序通过管道创建子进程（Node 的 child_process 默认 stdio:'pipe'
   会 EPERM），所以 `npx tsc` / `vue-tsc` 这类 CLI 在这里跑不起来。
   TypeScript 是纯 JS，可以直接 require 它的 API 在进程内做类型检查 ——
   这条路不 spawn 任何东西。

   用法：
     node tools/typecheck.mjs                 # 检查全部（含 .vue 的 <script> 段）
     node tools/typecheck.mjs src/data        # 只检查某个子目录

   注意：本脚本只做 .ts 类型检查。.vue 单文件组件由 tools/sfc-typecheck.mjs
   把 <script setup lang="ts"> 抽出来后再交给这里检查。
   ========================================================================== */

import ts from 'typescript'
import { readdirSync, statSync, existsSync } from 'node:fs'
import { join, relative, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('..', import.meta.url))
const filterArg = process.argv[2]

const configPath = join(root, 'tsconfig.json')
if (!existsSync(configPath)) {
  console.error('找不到 tsconfig.json')
  process.exit(2)
}

const { config, error } = ts.readConfigFile(configPath, ts.sys.readFile)
if (error) {
  console.error(ts.flattenDiagnosticMessageText(error.messageText, '\n'))
  process.exit(2)
}

/* 只检查 .ts/.d.ts —— .vue 走另一条路（见 sfc-typecheck.mjs） */
const parsed = ts.parseJsonConfigFileContent(config, ts.sys, root, undefined, configPath)
let fileNames = parsed.fileNames.filter((f) => f.endsWith('.ts') && !f.endsWith('.d.ts') || f.endsWith('.d.ts'))

if (filterArg) {
  const abs = join(root, filterArg)
  fileNames = fileNames.filter((f) => f.startsWith(abs + sep) || f === abs)
}

const program = ts.createProgram(fileNames, parsed.options)
const diagnostics = [
  ...program.getSyntacticDiagnostics(),
  ...program.getSemanticDiagnostics(),
]

const formatHost = {
  getCanonicalFileName: (f) => f,
  getCurrentDirectory: () => root,
  getNewLine: () => '\n',
}

if (diagnostics.length === 0) {
  console.log(`类型检查通过：${fileNames.length} 个 .ts 文件，0 个错误`)
  process.exit(0)
}

for (const d of diagnostics) {
  const msg = ts.flattenDiagnosticMessageText(d.messageText, '\n  ')
  if (d.file && d.start !== undefined) {
    const { line, character } = d.file.getLineAndCharacterOfPosition(d.start)
    const rel = relative(root, d.file.fileName).split(sep).join('/')
    console.log(`${rel}:${line + 1}:${character + 1}  TS${d.code}  ${msg}`)
  } else {
    console.log(`TS${d.code}  ${msg}`)
  }
}

console.log(`\n共 ${diagnostics.length} 个类型错误（检查 ${fileNames.length} 个文件）`)
process.exit(1)