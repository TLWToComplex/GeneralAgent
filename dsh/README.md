# dsh

`dsh/` 下的目录中只做构建，从官方仓库拉取代码进行构建镜像，不 fork 源码。

| 路径 | 放什么 | 什么时候动 |
| --- | --- | --- |
| `image/` | Dockerfile、entrypoint.sh、dsh-home/ | 基础镜像版本、启动流程、容器内默认配置 |
| `pins.yaml` | 锁定的官方 dsh 版本 | 升级官方底座 |
| `docs/` | 镜像使用与升级手册 | 构建流程或升级步骤有变 |
| `dsh-plugins/` | GeneralAgent自研插件源码 | 增改插件能力 |
| `dsh-agent-presets/` | Agent 预设模式 | 新增工作模式 |

`image/` 里的文件：Dockerfile 决定基础镜像与依赖，entrypoint.sh 决定容器起来之后做什么，dsh-home/ 是 DSH_HOME 的模板，容器启动时铺到数据目录，profile patch 与默认设置都放这里。

`pins.yaml` 定义当前跑的是哪个官方版本。

`dsh-plugins/` 是插件源码和聚合 bundle 包，它只声明各依赖的版本并带一份 `cordis.patch.yml`，装这一个包，GeneralAgent的一套能力就位。

`dsh-agent-presets/` 每个预设一个目录，`daily-report/` 是写日报模式，`GA-ppt-preset/` 是做电科模版 PPT 模式。预设决定所有人的默认工作方式，影响面比单个插件大，所以和插件一起放在 `dsh/` 下，跟着底座一起分发。