# GeneralAgent V2 · 身份认证与实例路由服务（GA-backend-v2）

从老项目 `ai-service-backend - GA` 迁移过来的**用户登录**能力，按 V2 架构（`apps/` 下一个可独立部署的服务）
用 **FastAPI + SQLAlchemy 2.0** 重建。

> 本仓库当前**只**包含用户登录相关能力，其它业务（AI 智能体、对话、知识库、用户组、权限、偏好等）一律未迁移。

## 迁移范围

| 能力 | 接口 | 状态 |
| --- | --- | --- |
| 图形验证码 | `GET /captcha` | 已迁移 |
| 本地账号登录（用户名/邮箱 + JWT） | `POST /aiUser/login` | 已迁移 |
| 修改密码（旧密码 + 强度 + 近5次历史密码） | `POST /aiUser/changePassword` | 已迁移 |
| 管理员解锁超期未登录账号 | `POST /aiUser/unlockAccount` | 已迁移 |
| 登录态校验（`LOCAL_NO_AUTHZ` 分支） | `Authorization: Bearer` 依赖 | 已迁移 |
| 默认管理员账号初始化 | 启动时幂等创建 | 已迁移（登录开箱可用所需） |
| CAS / SSO 远程令牌校验 | `validate_cas_login`、远程 SSO 分支 | **未迁移**（见下文） |
| 用户注册 `/aiUser/add`、用户组、权限、偏好等 | — | **未迁移** |
| 用户 → dsh 实例映射查询（给前置代理用） | `GET /internal/dsh/route` | 新增（**不是**老项目接口，见下文契约） |

### 为什么包含「默认管理员初始化」

登录功能要可用，库里必须存在账号。老项目在启动时用 `ensure_default_admin` 幂等创建 `admin`，
V2 保留了这一行为（`app/services/bootstrap.py`），但**没有**开放注册接口。

## 目录结构

```
GA-backend-v2/
├─ app/
│  ├─ main.py                     FastAPI 装配（create_app / lifespan / 异常处理器 / CORS）
│  ├─ config.py                   配置层：YAML + 环境变量（键名与老项目一致）
│  ├─ db.py                       Engine / Session 工厂 / get_session 依赖
│  ├─ api/
│  │  ├─ deps.py                  会话、验证码资源、Bearer 鉴权、admin 校验
│  │  └─ routes/
│  │     ├─ auth.py               四个登录接口（对应老项目 admin_server.py 的路由段）
│  │     └─ internal_dsh.py       内部接口：用户 → dsh 实例映射（供 proxy 调用，需共享密钥）
│  ├─ services/
│  │  ├─ auth_service.py          登录/改密/解锁业务逻辑（对应老项目 src/services/auth_service.py）
│  │  └─ bootstrap.py             默认管理员初始化
│  ├─ repositories/               数据访问（对应老项目 accessors；含 dsh 实例映射表）
│  ├─ models/                     ai_user / ai_password_history / ai_dsh_instance ORM 模型
│  └─ core/                       验证码、验证码缓存、密码策略、密码哈希与 JWT、异常契约
├─ config/config.yaml             服务配置
├─ sql/001_init_auth.sql          MySQL 建表 DDL（列定义取自老项目 dump）
├─ sql/002_drop_unrelated_tables.sql  清理与登录无关的 16 张表（破坏性，需先备份）
├─ sql/003_init_dsh_instance.sql  新建 ai_dsh_instance（用户 → dsh 实例映射，幂等可重复执行）
├─ tests/                         unittest 测试（144 个用例）
└─ tools/                         本地 SQLite 试跑 + 真实 HTTP 冒烟
```

## 快速开始

```bash
# 依赖（Python 3.11+）
pip install -r requirements.txt

# 1) 准备数据库（MySQL 8，utf8mb4）
mysql -uroot -p ai_service < sql/001_init_auth.sql

# 1b) 建立「用户 → dsh 实例」映射表（新建会话进 dsh 用；脚本幂等，可重复执行）
mysql -uroot -p ai_service < sql/003_init_dsh_instance.sql

# 2) 配置：复制 .env.example 为 .env 并按环境修改（至少填 DATABASE_URL 与 JWT_SECRET_KEY）
cp .env.example .env
#    要让前置代理能查映射，还需配一个共享密钥：DSH_INTERNAL_SECRET（不配则该接口整体 503）

# 3) 启动
python run.py                       # 监听 config/config.yaml 里的 host/port（默认 8038）
# 或
python -m uvicorn app.main:app --host 0.0.0.0 --port 8038
```

启动后：`/docs` 为 Swagger UI，`/health` 健康检查，根路径返回服务与接口清单。
首次启动会自动创建默认管理员 `admin / Aa123456`（见 `default_admin` 配置）。

> `sql/003` 只建表、不动存量数据。脚本里带有可执行的巡检 SELECT，以及登记/停用映射的
> INSERT / UPDATE 模板（把 `demo` 换成实际用户名即可）；建议先在测试库跑一遍。

### 免 MySQL 本地试跑

```bash
# 终端 1：SQLite 建库 + 预置联调验证码/演示账号/一条 dsh 映射，监听 8038
python tools/dev_sqlite_server.py --seed

# 终端 2：真实 HTTP 冒烟（50 项断言）
python tools/smoke_login.py --base-url http://127.0.0.1:8038
```

`--seed` 会预置固定答案的验证码（否则随机验证码无法被外部脚本得知）、演示账号
`demo / Kp!3RzT7Vm`，以及一条 `demo → http://127.0.0.1:8083/` 的 dsh 映射（容器名
`dsh-web-demo`、代理账号 `demo`），**仅用于本地联调**。
该脚本在未配置内部接口密钥时会自动使用联调密钥 `dev-internal-secret` 并打印 curl 示例。
冒烟脚本可重复执行；想回到初始状态就删掉 `data/` 目录后重启。

## 接口契约

字段名、响应体结构、状态码与老项目保持一致，前端无需改动解析逻辑。

### `GET /captcha`（无需认证）

```json
{"code": 200, "message": "success",
 "data": {"captchaId": "<uuid>", "captchaImage": "data:image/png;base64,..."}}
```

验证码写入进程内存缓存，默认有效期 300 秒；**一次性使用**，无论校验通过与否都立即作废。

### `POST /aiUser/login`（无需认证）

请求：

```json
{"username": "用户名或邮箱", "password": "明文密码", "captchaId": "<uuid>", "captchaCode": "ABCD"}
```

成功 `200`：

```json
{"status": "success", "message": "登录成功",
 "user": {"id": 1, "uuid": "...", "username": "admin", "email": "...", "realname": "管理员",
          "platform_sort": [], "preferences": {}, "create_time": "...", "is_del": 0,
          "last_login_time": "...", "last_password_change": "...", "needUpdateMsg": false},
 "token": "<JWT>", "passwordExpiredWarning": false}
```

`user` 里不含 `password`，`additional_info` 被平铺到顶层（与老项目一致）。

失败响应统一为 `{"error": "<提示语>"}`：

| 状态码 | 提示语 | 触发条件 |
| --- | --- | --- |
| 400 | `请求体必须为JSON格式` | 请求体缺失或不是 JSON 对象 |
| 400 | `{字段名}为必填字段` | `username` / `password` / `captchaId` / `captchaCode` 缺失 |
| 401 | `验证码已过期，请重新获取` | captchaId 不存在、已作废或超过 300 秒 |
| 401 | `验证码错误` | 验证码答案不匹配 |
| 401 | `用户名或邮箱无效` | 用户不存在或已被软删除 |
| 401 | `密码错误，还剩N次机会` | 密码错误且未达锁定阈值 |
| 401 | `连续5次密码错误，账号已锁定5分钟` | 第 5 次密码错误，同时写入锁定标记 |
| 403 | `账号已锁定，请N分钟后重试` | 处于密码错误锁定期 |
| 403 | `账号已超过30天未登录，已被自动锁定，请联系管理员解锁` | 超过 N 天未登录（首次判定，同时落库标记） |
| 403 | `账号因超过30天未登录已被锁定，请联系管理员解锁` | 已带 `inactive_locked` 标记 |
| 500 | `系统错误，请稍后重试` | 写库失败 |

登录判定顺序（与老项目一致）：
**验证码 → 查用户 → 密码错误锁定 → 30天未登录锁定 → 校验密码 → 成功则清零失败计数、清除不活跃标记、刷新 `last_login_time`、签发 JWT（默认 1 小时）。**

### `POST /aiUser/changePassword`（需登录）

请求 `{"uuid": "...", "old_password": "...", "new_password": "..."}`

- `200`：`{"status": "success", "message": "密码更新成功"}`
- `400`：密码强度/历史密码不合规（如 `密码长度不能少于10位`、`密码必须包含至少一个特殊符号（如 !@# 等）`、`密码不能与近5次历史密码相同`）
- `401`：`{"error": "旧密码不正确"}`
- `404`：`{"error": "用户不存在"}`

成功后写入一条密码历史（只保留最近 5 条）并刷新 `additional_info.last_password_change`。

### `POST /aiUser/unlockAccount`（需 admin）

请求 `{"uuid": "..."}`

- `200`：`{"status": "success", "message": "账号已解锁，用户可以正常登录"}`
- `200`：`{"status": "success", "message": "该账号未被锁定，无需解锁"}`
- `403`：`{"code": 403, "message": "权限不足，仅管理员可访问"}`（非 admin，沿用老项目 `admin_required` 的响应体）
- `404`：`{"error": "用户不存在"}`

只解除「超过 N 天未登录」的自动锁定，不会清除密码错误锁定。

### `GET /internal/dsh/route`（内部接口，需共享密钥）

给前置代理（`proxy/`）用的：按用户名或 UUID 查出该用户应该被反代到哪个 dsh 实例。
**不面向浏览器**，也不接受 JWT —— 它下发的是容器回环地址与启动令牌文件名，属于凭据级信息。

请求（`username` 与 `uuid` 必须且只能提供一个）：

```http
GET /internal/dsh/route?username=demo      HTTP/1.1
X-Internal-Token: <dsh.internal_secret>
```

成功 `200`：

```json
{"code": 200, "message": "success",
 "data": {"username": "demo", "uuid": "...", "containerName": "dsh-web-demo",
          "proxyUser": "demo", "host": "127.0.0.1", "port": 8083,
          "target": "http://127.0.0.1:8083/", "tokenFile": null, "status": 1}}
```

- `target` 可直接当作反代目标；`tokenFile` 为 `null` 表示由代理按自己的
  `TOKENS_DIR` / `proxyUser` 推导令牌文件（后端不假设代理的部署目录）。
- `status`：`1` 启用 / `0` 停用（只有 `1` 会被返回，见下表 403）。

失败响应统一为 `{"code": <状态码>, "message": "<提示语>"}`：

| 状态码 | 提示语 | 触发条件 |
| --- | --- | --- |
| 503 | `内部接口未启用：请在 config/config.yaml 的 dsh.internal_secret 或环境变量 DSH_INTERNAL_SECRET 配置共享密钥` | 未配置密钥（默认状态），接口整体不启用 |
| 401 | `内部接口令牌缺失` | 未带 `X-Internal-Token` |
| 401 | `内部接口令牌无效` | 密钥不匹配（常量时间比较） |
| 400 | `username与uuid必须且只能提供一个` | 两个都给或都不给 |
| 404 | `用户不存在或已删除` | 用户名/UUID 查不到，或用户已软删除（与登录口径一致） |
| 404 | `该用户未登记 dsh 实例` | 用户存在但映射表里没有该用户的记录 |
| 403 | `该用户的 dsh 实例已停用` | 映射存在但 `status = 0` |

校验顺序是「密钥 → 用户有效性 → 映射存在 → 映射启用」，任何一步失败都只给粗粒度提示，
不泄漏「某用户名是否存在且登记了实例」这类组合信息。每次查询都会记一条带调用方 IP 的日志
（反代场景取 `X-Forwarded-For` 首段）。

代理侧调用示例：

```bash
curl -H 'X-Internal-Token: dev-internal-secret' \
     'http://127.0.0.1:8038/internal/dsh/route?username=demo'
```

### 鉴权约定

受保护接口读 `Authorization: Bearer <token>`：

- 缺失：`401 {"message": "Bearer令牌缺失", "code": 401}`
- 非法/过期：`401 {"message": "Bearer令牌无效", "code": 401}`

JWT 载荷：顶层 `username` + `identity{username,user_id,timestamp}` + `iat/exp/jti`，
签名算法 HS256，有效期 `jwt.access_token_expires_seconds`（默认 3600，与老项目一致）。
（不使用 `sub` 承载字典：PyJWT 2.10 起要求 `sub` 必须是字符串。）

## 配置

优先级：环境变量 / `.env` **高于** `config/config.yaml`。常用项：

| 配置键 | 环境变量 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `database.url` | `DATABASE_URL` | `mysql+pymysql://root:123456@localhost:3306/ai_service?charset=utf8mb4` | 数据库连接 |
| `jwt.secret_key` | `JWT_SECRET_KEY` | 空 | **生产必须显式配置**；为空时生成一次性随机密钥并在启动日志告警（重启后旧 token 失效） |
| `jwt.access_token_expires_seconds` | `JWT_ACCESS_TOKEN_EXPIRES_SECONDS` | 3600 | token 有效期 |
| `sso.url` | `SSO_URL` | `LOCAL_NO_AUTHZ` | 本地登录模式；配成其它值受保护接口直接返回 501 |
| `auth.max_login_failures` / `lock_minutes` | `AUTH_*` | 5 / 5 | 密码错误锁定策略 |
| `auth.inactive_lock_days` | `AUTH_INACTIVE_LOCK_DAYS` | 30 | 超过该天数未登录自动锁定（admin 豁免） |
| `auth.password_expire_days` / `admin_password_expire_days` | `AUTH_*` | 90 / 60 | 密码超期提醒阈值 |
| `auth.password_history_keep` | `AUTH_PASSWORD_HISTORY_KEEP` | 5 | 禁止复用的历史密码条数 |
| `captcha.*` | `CAPTCHA_*` | 300s / 1000 / 4位 | 验证码有效期、缓存容量、字符数 |
| `default_admin.*` | `DEFAULT_ADMIN_ENABLED` 等 | `admin / Aa123456` | 首次启动自动创建的管理员 |
| `dsh.internal_secret` | `DSH_INTERNAL_SECRET` | 空 | 内部映射接口 `GET /internal/dsh/route` 的共享密钥；**为空时该接口返回 503（不启用）**，需与代理侧配置一致 |

数据库兼容性：密码哈希沿用 Werkzeug（`generate_password_hash`），
因此 **V2 可以直接复用既有 `ai_user` 数据**，无需重置密码。

## 测试与验证

```bash
# 单元 + 接口测试（144 个用例，内存 SQLite）
python -m unittest discover -s tests -v

# 真实 HTTP 冒烟（50 项断言，需先起 tools/dev_sqlite_server.py --seed）
python tools/smoke_login.py --base-url http://127.0.0.1:8038
```

覆盖点：验证码生成/缓存/TTL/容量淘汰、登录全部成功与失败分支、失败计数与 5 次锁定、
30 天未登录锁定与 admin 豁免、密码超期提醒（90/60 天）、改密的强度与历史密码规则、
历史记录保留 5 条、管理员解锁、鉴权失败与越权、默认管理员初始化幂等、
内部映射接口（密钥缺失/错误、参数互斥、按用户名与 uuid 两种查法、用户不存在、
未登记映射、映射停用、端口不泄漏）、DDL 与 ORM 的表/列/类型一致性。

> 本机验证环境说明：仓库根 conda 环境里装着 `fastapi 0.124.0 + starlette 1.6.0`，
> 这一组合不兼容（`FastAPI()` 构造即报错），因此上面的命令是用
> `D:\zrq\software\miniconda3\envs\ai-service-backend\python.exe`（fastapi 0.124.4 + starlette 0.50.0）跑的。
> `requirements.txt` 已显式约束 `starlette>=0.40,<0.51`，干净环境安装即可。

已知测试盲区：测试跑在 SQLite 上，而 SQLite 不支持 `SELECT ... FOR UPDATE`
（`UserRepository._supports_row_lock()` 会自动降级），因此**行锁并发保护只能在 MySQL 上验证**；
另外远程 SSO 分支未迁移，只验证了「配置非 LOCAL_NO_AUTHZ 时返回 501」。

> SQLite 与 MySQL 还有一处差异：`ai_user.username` 在 MySQL 下是 `utf8mb4_0900_ai_ci`
> （不区分大小写），`username = 'ZhangSan'` 能匹配 `zhangsan`；SQLite 区分大小写。
> 因此 `tests/test_login.py` 里"用户名严格匹配"的断言只在 SQLite 上成立，
> 生产行为以 MySQL 的排序规则为准（与老项目一致，老项目 DDL 同样是 `utf8mb4_0900_ai_ci`）。

## 与老项目的差异

### 有意的调整（不改变接口契约）

| 项 | 老项目 | V2 | 原因 |
| --- | --- | --- | --- |
| 技术栈 | Flask + flask-sqlalchemy + flask-jwt-extended + `async_route` | FastAPI + SQLAlchemy 2.0 | V2 架构选型 |
| Service 返回 | `(success, result)` 元组，由 Controller 转 HTTP | 抛 `ApiError`（带原状态码与文案） | 响应组装集中一处 |
| 本地令牌校验 | `LOCAL_NO_AUTHZ` 分支**不校验签名**，任意 Bearer 值都能得到用户名 | 校验签名与有效期 | 安全收敛 |
| 改密写库失败 | 把数据库异常原文以 400 返回前端 | 500 `服务器内部错误`（细节只进日志） | 不向客户端泄漏内部错误 |
| 请求体不是 JSON 对象 | JSON 数组会报 `username为必填字段` | 统一 400 `请求体必须为JSON格式` | 提示语更贴切 |
| 字段存在但类型错/为 `null` | 只查「键是否存在」，`password: null` 会走到服务层 → 401 `密码错误，还剩N次机会` | pydantic 校验 → 400 `password格式不正确` | 缺字段与非法字段应区分，避免把畸形请求算作一次密码失败 |
| 安全检查 | `LOCAL_NO_AUTHZ` 分支不校验签名，任意 `Bearer xxx` 都能拿到用户名 | 校验签名与有效期 | 安全收敛（已在上方单列运维影响） |
| 远程 SSO 配置 | 走远程校验 | 配了非 `LOCAL_NO_AUTHZ` 时受保护接口返回 501 | 避免误配置造成鉴权降级 |
| CORS | `allow_origins=["*"]` + `allow_credentials=True`（浏览器会拒绝） | 通配源 + `allow_credentials=False`，可配置 | 组合合法 |
| 脏数据时间戳 | `additional_info.locked_until` 非法时抛异常，登录直接 500 | 忽略该字段并清除锁定标记后继续 | 单条脏数据不应阻断全部登录 |
| 未预期异常 | 登录流程无兜底（Flask 默认 500） | 统一异常处理器返回 500 `服务器内部错误` | 响应契约统一 |
| 数据库不可用时启动 | 导入期执行 `ensure_default_data()`，连不上库则服务直接起不来 | 初始化失败只记错误日志，服务照常启动并可访问 `/health` | 避免数据库抖动导致实例无法就绪 |
| 安全阈值 | 硬编码在代码里 | 移到 `auth.*` 配置，**默认值相同** | 可运维 |

### 刻意保留的老项目行为

迁移遵循「行为一致优先」，下面这些看似奇怪的点是**刻意保留**的，改动前请先确认业务口径：

1. **锁定提示语少一分钟**：剩余时间用 `int(total_seconds/60)` 截断，锁 5 分钟时会提示「请4分钟后重试」。
2. **密码黑名单分支实际不可达**：密码策略先查复杂度（大写/小写/数字/特殊符号）再查黑名单，
   而黑名单里没有任何一条能满足复杂度；且黑名单按「密码转小写」比对，集合中带大写字母的条目（如 `Aa123456`）永不命中。
3. **创建用户不写密码历史**：`add_user` 只写 `last_password_change`，因此初始密码可以再改回来一次。
4. **默认管理员初始密码不满足策略**：`Aa123456` 只有 8 位，无法通过 `changePassword` 改回该值（可用管理手段重置）。
5. **验证码一次性使用**：校验失败也作废，必须重新获取。
6. **admin 豁免 30 天未登录锁定**；`unlockAccount` 只解不活跃锁定，不影响密码错误锁定。
7. **软删除用户无法登录**（`is_del=1` 视为用户不存在）。
8. `additional_info` 平铺进登录响应顶层；`needUpdateMsg = not realname`。
9. 超期密码**只提醒不阻断**登录。
10. **登录只写 `additional_info`，不刷新 `ai_user.update_time` / `update_by`**：老项目登录走
    `update_user_additional_info_in_transaction`（只赋值 JSON 字段 + commit），`update_time` 仅由
    `update_user`（注册/管理/解锁/改密路径）刷新。不要"顺手修成"登录时刷新更新时间，那是行为偏离。
11. `Authorization: Bearer` 是本地模式下唯一的令牌来源（老项目本地分支同样不读 `X-ACCESS-TOKEN`，该头部只用于未迁移的 SSO 分支）。

### 未迁移部分

- **CAS / SSO 远程令牌校验**：老项目 `validate_cas_login` 与 `jwt_required` 的远程分支依赖外部 SSO 地址，
  本地无法端到端验证，按本次范围排除；`app/api/deps.py` 预留了接入位置（配置非 `LOCAL_NO_AUTHZ` 时显式 501）。
- 用户注册 `/aiUser/add`（含软删除用户重建逻辑）、用户组、权限、偏好、AI 智能体/对话/知识库等全部接口。
- 老项目在 `/aiUserPreferences/get` 里顺带刷新 `last_login_time` 的逻辑——宿主接口不在本次范围内。

> ⚠️ **上线前必须确认：30 天未登录自动锁定现在没有"活跃保活"了。**
> 老项目前端每次调用 `GET /aiUserPreferences/get` 都会刷新 `additional_info.last_login_time`
> （`admin_server.py` → `AuthController.update_last_login_time()`，其注释写明目的就是"防止因超过30天未登录而被自动锁定"）。
> V2 只迁移了 4 个接口，其中只有**登录**会刷新这个时间戳，因此：
> **只要用户连续 30 天没有登录（哪怕天天在用系统），就会被自动锁定，必须管理员解锁。**
> 处理方式二选一：
> 1) 按需迁移保活逻辑：把偏好/心跳类接口迁移过来（或在 `require_current_user` 里刷新 `last_login_time`，
>    代价是每个受保护请求多一次写库）；
> 2) 先调整阈值：`AUTH_INACTIVE_LOCK_DAYS`（如 90/180）或临时关闭该规则，等保活接口就位后再收紧。

## 部署注意事项：会话有效期

V2 的本地令牌**真的会过期**（老项目 `LOCAL_NO_AUTHZ` 分支只解码不验签、也不检查 `exp`，会话几乎不会失效）：

1. **必须显式配置 `JWT_SECRET_KEY`**（环境变量或 `config/config.yaml` 的 `jwt.secret_key`）。
   未配置时服务会生成一次性随机密钥并在启动日志告警——**每次重启都会让已签发的 token 全部失效**。
2. 前端需要处理**会话中途 401**（token 到期或被重启作废）：老项目行为下不会出现这种情况，建议在
   401 时清空本地登录态并跳回登录页，而不是当成"接口报错"。
3. 需要更长会话就调大 `jwt.access_token_expires_seconds`（默认 3600，与老项目硬编码值一致）。

## 部署

```bash
docker build -t GA-backend-v2 .
docker run -d --name GA-backend-v2 -p 8038:8038 \
  -e DATABASE_URL='mysql+pymysql://user:pass@mysql:3306/ai_service?charset=utf8mb4' \
  -e JWT_SECRET_KEY='<强随机密钥>' \
  -e DSH_INTERNAL_SECRET='<与代理侧一致的共享密钥>' \
  GA-backend-v2
```

`DSH_INTERNAL_SECRET` 只影响 `GET /internal/dsh/route`：不配则该接口整体 503（登录不受影响）。
`/internal/*` 应只在内网 / 同机可达，**不要**通过公网入口暴露（它下发容器回环地址与令牌文件名）。

服务无状态（验证码缓存在进程内存，多副本部署时验证码请求需落在同一副本，或后续换成 Redis/网关会话保持）。

## （可选）清理与登录无关的表

V2 只读写 `ai_user`、`ai_password_history`（以及 `sql/003` 新建的 `ai_dsh_instance`），
其余 16 张表（`ai_agent`、`ai_chat_record`、`ai_user_group` 等）在代码里没有任何引用，可以按需清理：

```bash
mysql -h127.0.0.1 -uroot -p ai_service < sql/002_drop_unrelated_tables.sql
```

`sql/002_drop_unrelated_tables.sql` 分三步：先只读核对（列出待删表、行数、保留表），
再执行 `DROP TABLE IF EXISTS`，最后后置校验（只剩两张表 + 结构抽查 + 待删表残留检查）。

> ⚠️ **执行前必须确认没有别的服务还在用这些库表**（老项目后台、前端其它模块、定时任务），
> 并先 `mysqldump` 备份——MySQL 的 DDL 隐式提交，删掉就回滚不了，只能从备份恢复。
> 库里那两个存储过程（`sp_cleanup_etl_logs`、`sp_generate_monthly_attendance`）操作的是
> `etl_job_log`/`attendance_summary` 等本库并不存在的表，脚本不动它们。