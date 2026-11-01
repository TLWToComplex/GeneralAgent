# apps

`apps/` 按一个可独立部署的单元一个目录排，目录名即服务名。

| 目录 | 职责 |
| --- | --- |
| `GA-frontend-v1/` | 平台前端 |
| `GA-backend-v1/` | 平台后端 |
| `GA-frontend-v2/` | 平台前端 |
| `GA-backend-v2/` | 平台后端 |
| `proxy/` | 统一代理 |
| `permission/` | 权限中心 |
| `gateway/` | 统一网关 |
| `mirror-hub/` | 镜像中心 |

前四个是平台自身的界面与业务逻辑，后面四个是平台要建的中心能力。它们都是可独立部署的服务。