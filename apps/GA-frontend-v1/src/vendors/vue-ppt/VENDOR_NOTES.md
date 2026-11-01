# vue-ppt Embedded Vendor

该目录是 `aisix_v2` 内部 vendored 的 `vue-ppt` 源码。

用途：

- 为 Canvas 的 PPT 模式提供原生 `vue-ppt` UI
- 通过 workspace 参与根目录统一依赖安装
- 通过根脚本构建出 `src/vendors/vue-ppt/dist`

常用命令：

```powershell
cd d:\Study\MCP\ppt\aisix_v2
npm install
```

```powershell
cd d:\Study\MCP\ppt\aisix_v2
npm run dev
```

```powershell
cd d:\Study\MCP\ppt\aisix_v2
npm run build
```

说明：

- 根目录 `npm install` 会同时安装主工程和该 vendored 包依赖
- 根目录 `npm install` 会在安装完成后自动构建一次 vendored `vue-ppt`，产物保留在当前目录下的 `dist`
- `npm run dev` 直接启动主工程 `vite`，不会在每次启动前重复构建 `vue-ppt`
- `npm run build` 会在主工程正式打包前通过 npm workspace 自动刷新 vendored `vue-ppt`
- 主工程 dev 会直接从这份 `dist` 提供 `/vendors/vue-ppt/*`
- 主工程 build 会把这份 `dist` 复制到最终输出目录中的 `dist/vendors/vue-ppt`
- vendored 包内部的 `prepare` 已改成无副作用脚本，不会影响主仓安装流程
