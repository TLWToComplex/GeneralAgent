---
name: GA-platform-assistant
description: "Use this skill whenever the user asks about: (1) the user-feedback / improvement-tracking table for the platform (e.g. '反馈', '需求', '改进进度', '已上线', '当前进度', or wants to 新增/编辑/删除 a feedback record); (2) how to use the GeneralAgent (GA) platform itself (e.g. '怎么用', '使用手册', '功能说明', 'how do I'); or (3) usage metrics / tracking data of the platform (e.g. '多少人用过', '谁用得最多', '最近使用情况', '活跃用户'). The skill exposes four CLI scripts that hit the backend:\n  - scripts/query_feedback.py — searches the ai_user_feedback table\n  - scripts/manage_feedback.py — renders an HTML form to 新增/编辑/删除 a feedback record (form POSTs to /aiUserFeedback/{add,update,delete})\n  - scripts/query_kb.py — calls the kb_chat knowledge-base proxy for the GeneralAgent user manual\n  - scripts/query_metrics.py — aggregates Langfuse usage tracking data\nDo NOT use this skill for unrelated tasks like document generation, code editing, or general web browsing."
---

# GeneralAgent平台助手 (GA-platform-assistant)

本技能用于回答**GeneralAgent平台**的三类问题。每一类都对应一个 CLI 脚本，agent 应在沙盒里运行脚本拿到 JSON 返回，再用自然语言回答用户。将用户问的问题都认为是**GeneralAgent平台**相关的。

## 工作流总览

| 用户问题类型                               | 调用脚本 | 数据来源 |
|--------------------------------------| --- | --- |
| 用户反馈 / 改进追溯 / 某反馈进度 / 查看工单           | `scripts/query_feedback.py` | 后台 MySQL 表 `ai_user_feedback`（通过 `/aiUserFeedback/query` 暴露） |
| 新增 / 编辑 / 删除 用户反馈 / 提交 / 编辑 工单 / 我要反馈 | `scripts/manage_feedback.py` | 渲染一份 HTML 表单，用户点提交后由表单 JS POST 到 `/aiUserFeedback/{add,update,delete}` |
| 怎么使用GeneralAgent / 平台功能 / 操作手册               | `scripts/query_kb.py` | 知识库 `kb_chat` 中的《GeneralAgent-用户手册》等文档 |
| 谁用过 / 用了多少次 / 活跃情况                   | `scripts/query_metrics.py` | Langfuse 追踪数据（`/aiUsageMetrics/*` 聚合） |

**关键原则（两条同时遵守，缺一不可）**：

1. **只调用必需的脚本**，不要"以防万一"把所有脚本都跑一遍。
   - 用户问"谁用得最多" → 只跑 `query_metrics.py top-users`，不要再跑 feedback / kb。
   - 用户问"Canvas 怎么用" → 只跑 `query_kb.py`。
   - 用户问"已上线的需求有哪些" → 只跑 `query_feedback.py`。
   - 用户说"我要新增/修改/编辑用户反馈" → 只跑 `manage_feedback.py`，不要再跑 `query_feedback.py` 凑数。
   - 只有当用户明确把多个类别串在一起问时（例："已上线的反馈里，哪个最常被使用？"）才组合调用。
2. **每个被实际调用的脚本都必须带 `--html`**，输出可视化报告给前端；没调用的脚本就不要生成 HTML。`manage_feedback.py` 本身就只输出 HTML（无需 `--html` 开关，已默认渲染表单）。详见下文的"HTML 报告"章节。

## 环境变量

所有脚本使用以下环境变量定位后台。沙盒已经默认通过后台地址访问宿主机；在常规部署下**无需修改**。

| 变量名             | 默认值                     | 说明                                      |
|-----------------|-------------------------|-----------------------------------------|
| `BACKEND_URL`   | os.getenv("BACKEND_URL")  | admin_server 的访问地址                      |
| `USER_NAME` | `admin`                 | 本地 `LOCAL_NO_AUTHZ` 模式下随便给一个非空 token 即可 |
| `KB_NAME`       | `GeneralAgent用户手册`              | GeneralAgent用户手册知识库名称                           |

如果脚本报 `连接失败` / `404`，先把 `BACKEND_URL` 切到实际可达的地址再重试，不要尝试改这些 Python 脚本本身。

## HTML 报告（重要 — 必须遵守）

**只要本技能被触发并实际产出了数据，就必须生成且只生成一份 HTML 报告**，对应"被实际调用的那一个脚本"。规则非常机械化，按下表执行：

| 这次实际调用了哪些脚本 | 应该生成几份 HTML | 在哪个脚本上加 `--html` |
| --- | --- | --- |
| 只调了 `query_feedback.py` | 1 份 | 给 `query_feedback.py` 加 `--html` |
| 只调了 `manage_feedback.py <动作>` | 1 份（表单 HTML） | 不需要 `--html` 参数，脚本默认就写 HTML |
| 只调了 `query_kb.py` | 1 份 | 给 `query_kb.py` 加 `--html` |
| 只调了 `query_metrics.py <子命令>` | 1 份 | 给该 `query_metrics.py` 调用加 `--html` |
| 用户的问题确实横跨多个类别，本回合调了多个脚本 | 每个被调用的脚本各加 1 次 `--html`（每个脚本最多一次） | 给每个被调用的脚本都加 `--html` |
| 这次根本没调用本技能的脚本（无关问题） | 0 份 | 什么都不要做 |

**严禁**为了"凑齐三类报告"去调用本回合用不到的脚本。判定标准非常严格：**没拿来当数据源就不要给它生成 HTML**。

### 反面例子（不要这样做）

- ❌ 用户问"谁使用最多" → 同时跑 `query_feedback.py --html`、`query_kb.py --html`、`query_metrics.py top-users --html`，前端会出现 3 个 Web Preview，其中 2 个是空报告。
- ❌ 用户问"Canvas 怎么用" → 只需要跑 `query_kb.py --html`，不要再额外跑 feedback / metrics 凑数。

### 正面例子

- ✅ "谁用得最多" → 只 `python scripts/query_metrics.py top-users --limit 20 --html`。
- ✅ "Canvas 怎么用" → 只 `python scripts/query_kb.py "Canvas 怎么用" --html`。
- ✅ "已上线的需求里，最常被使用的是哪个" → 同时跑 `query_feedback.py --status 已上线 --html` 和 `query_metrics.py top-users --html`，**两份都要 `--html`**；其它脚本不动。

HTML 写到 workspace 目录下后，admin_server 会自动给前端注入下载链接，不要再手工拼 URL。模板位置 `assets/report_template.html`，三类报告共用，按 `reportType` 自动切换布局。

生成的文件名会自动带上时间戳（如 `feedback_report_20260618_143022.html`），确保每次生成的报告文件都是唯一的，不会覆盖之前的报告。

## 1. 查询用户反馈

```bash
python scripts/query_feedback.py --keyword "知识库" --status 已上线 --limit 500 --html
```

关键参数（全部可选；不传时返回全部未删除记录）：
- `--keyword` 关键词，会同时匹配反馈内容/改进措施/验证结果/备注
- `--priority` 高 / 中 / 低
- `--status` 例如 "需求确认" / "开发中" / "已上线"
- `--source` 需求来源，模糊匹配
- `--limit` 返回条数，默认 500
- `--html` 生成 HTML 报告（默认 `workspace 目录下 feedback_report_<时间戳>.html`）— 按上方"HTML 报告"规则带上

输出是 JSON：`{"total": N, "items": [{...feedback row...}, ...]}`。回答用户时挑出 `feedback_content`、`status`、`progress`、`improvement_plan` 等字段说明即可。

## 2. 增 / 改 / 删 用户反馈（统一操作面板）

当用户明确说要**新增**、**修改**、**编辑**、**更新**或**删除**用户反馈时，**只调一次** `scripts/manage_feedback.py`，不带任何动作参数、也不需要 uuid。脚本会渲染一份**统一的 HTML 操作面板**：

- 页面打开后会自动加载现有反馈列表（服务端预拉取，已嵌入 HTML）；
- 顶部有"＋ 新增反馈"按钮（→ 表单 POST 到 `/aiUserFeedback/add`）；
- 每行右侧有"编辑 / 删除"按钮：编辑会弹出预填表单（→ POST `/aiUserFeedback/update`），删除会弹出确认对话框（→ POST `/aiUserFeedback/delete`）；
- 工具栏支持按 关键字 / 状态 / 优先级 前端过滤；
- 所有写操作都在浏览器里完成，脚本本身**不写数据库**。

```bash
python scripts/manage_feedback.py                  # 默认写到 workspace/feedback_form_<时间戳>.html
```

参数：
- 仅一个可选 `--html`，自定义输出文件名；默认 `workspace/feedback_form_<时间戳>.html`。
- **不接受** `add` / `edit` / `delete` 等动作参数，也**不需要** `--uuid` —— 这些都由用户在 HTML 页面里选择。

行为细节：
- 生成的 HTML 中已嵌入 `BACKEND_URL` 与 `USER_NAME`，所以无论用户在哪个浏览器打开都能直接命中后端。
- 涉及的后端接口（均在 `admin_server.py` 中注册）：`/aiUserFeedback/list`、`/aiUserFeedback/add`、`/aiUserFeedback/update`、`/aiUserFeedback/delete`。
- 删除是硬删除，数据会被永久移除。
- 用户不需要事先知道 uuid —— 直接在列表里点编辑/删除即可。

## 3. 查询GeneralAgent使用方法（kb_chat）

```bash
python scripts/query_kb.py "如何创建知识库" --html
```

参数：
- 第一个位置参数：用户问题
- `--html` 生成 HTML 报告（默认 `workspace 目录下 kb_report_<时间戳>.html`）— 按上方"HTML 报告"规则带上

输出是 JSON，含 `docs`/`source_documents` 等字段。回答时**必须基于检索到的文档**，未命中要明确告知。

## 4. 查询使用追踪数据

```bash
# 整体概览（默认查询当前的所有数据）
python scripts/query_metrics.py summary --html

# 自定义时间窗口
python scripts/query_metrics.py summary --from 2026-05-01 --to 2026-06-15 --html

# 使用次数排行榜
python scripts/query_metrics.py top-users --limit 20 --html

# 单个用户活动详情
python scripts/query_metrics.py user-activity --user-name alice --sample 5 --html
```

返回 JSON：
- `summary`：`totalTraces`（总会话/调用数）、`uniqueUsers`、`activeDays`
- `top-users`：`ranking` 列表，按 `traceCount` 倒序
- `user-activity`：用户的 `traceCount`、`firstSeen`、`lastSeen`、最近 `sample` 条 trace 摘要

每个子命令都支持 `--html`，默认输出到 `workspace 目录下 metrics_<子命令>_<时间戳>.html`。

## 回答规范

- **先判类 → 只调对应脚本（一个或多个）→ 给每个被调用的脚本都加 `--html`**。
- **不要为了"补齐"再去调用其它脚本**，不属于本次问题类别的脚本绝不调用，也绝不生成它们的 HTML。
- 直接把脚本输出当作权威信息源，不要凭空编数字。
- 反馈表里的 `progress` 是 0~1 的小数（如 `0.5` 表示 50%）。
- 说明使用追踪数据时，注明时间窗口或当前时间。
- 生成了 HTML 才在回答末尾提一句"已生成可视化报告"；没生成时**不要**虚假提示。
- 全程使用中文回答。

