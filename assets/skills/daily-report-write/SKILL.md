---
name: daily-report-skill
description: When the user expresses intent to write a daily report (e.g. "写日报", "我要写日报", "提交日报", "日报"), this skill parses the user's message into structured report fields, generates a link that opens the report form pre-filled, and the user confirms and saves manually.
# ⚠️ 配置须知：部署前需在 skill 配置中设置 `url` 参数，指向日报前端页面地址。
#    格式示例：{{url}} → http://your-domain/report-hub
#    此注释为 YAML 注释，不会影响 skill 行为。
---

# Daily Report

## Overview

When the user wants to write a daily report, parse the natural language input into four fields (date, today's work, tomorrow's plan, issues), and generate a link that opens the daily report system with the form pre-filled. The user then reviews and clicks save manually.

## Trigger Conditions

Trigger when the user message contains any of the following intents:

- "写日报", "我要写日报", "提交日报", "日报"
- "今日工作", "今天完成了", "今日工作总结", "今天做了"
- "daily report", "write report"
- Any other clear intent to write or submit a daily report

## Workflow

### Step 1: Extract Token

Extract the token from the environment variable:

```python
import os
token = os.environ.get("USER_TOKEN")
```

If the token cannot be found, respond: "无法获取认证信息，请重新登录后重试。"

### Step 2: Return Link and Ask for Auto-fill

Always start by returning the basic link in inline code format:

`{{url}}?token=<token>`

Then ask the user if they want auto-fill: "已为您生成日报链接，可在弹出界面中手动填写。如果您需要我帮您自动填充，请按以下格式描述您的工作内容，我会帮您填好：\n\n今天完成了：<内容>\n明天计划：<内容>\n遇到的问题：<内容>"

**If the user's message already includes work content** (e.g., "今天完成了XX", "今天做了XX，明天计划XX"), skip the question and proceed directly to Step 3 to parse content.

**If the user replies with work content** → proceed to Step 3.

**If the user ignores the auto-fill offer** → they already have the basic link, done.

### Step 3: Parse Content (auto-fill mode only)

Parse the user's message into four fields:

| Field | URL Param | Description |
|-------|-----------|-------------|
| 日期 | `write` | Report date in `YYYY-MM-DD` format. Default to today's date unless the user specifies otherwise. |
| 今日工作 | `today` | What the user accomplished or worked on today. |
| 明日计划 | `plan` | What the user plans to do tomorrow. |
| 问题风险 | `issue` | Any issues, blockers, or risks the user encountered. |

Parsing rules:

- **今日工作**: Look for keywords like "今天完成了", "今日完成", "今天做了", "今天", "今日工作". If the user's message is a single paragraph without explicit labels, treat the entire content as `today`.
- **明日计划**: Look for keywords like "明天计划", "明日计划", "明天做", "明天", "明日工作". If not mentioned, leave empty.
- **问题风险**: Look for keywords like "问题", "风险", "困难", "阻塞", "遇到问题". If not mentioned, leave empty.
- **日期**: Default to today. If the user says "补昨天的日报" or "补前天的", calculate accordingly using `date.today()`.

### Step 4: Generate Link

Construct the URL with the four fields as query parameters. All parameter values must be URL-encoded.

```
{{url}}?token=<token>&write=<date>&today=<url_encoded>&plan=<url_encoded>&issue=<url_encoded>
```

Use Python's `urllib.parse.quote` to URL-encode the content values. Execute the following Python script to construct and output the link:

```python
import urllib.parse
from datetime import date, timedelta

token = "<extracted_token>"
write_date = "<YYYY-MM-DD>"  # default: date.today().isoformat()
today_content = "<parsed_content>"
plan_content = "<parsed_content>"
issue_content = "<parsed_content>"

params = {
    "token": token,
    "write": write_date,
    "today": today_content,
    "plan": plan_content,
    "issue": issue_content,
}
query_string = "&".join(f"{k}={urllib.parse.quote(v, safe='')}" for k, v in params.items())
link = f"{{url}}?{query_string}"
print(link)
```

**Important**: Replace all `<...>` placeholders with actual values. Escape double quotes and newlines in the content strings properly.

### Step 5: Return Result

Present the link to the user in Markdown inline code format, along with a summary of what was parsed:

```
日报已自动填充，请点击链接确认并保存：
`<generated_link>`

预填内容预览：
- 日期：{date}
- 今日工作：{today}
- 明日计划：{plan}
- 问题风险：{issue}
```

## URL Format Reference

The daily report frontend at `{{url}}` accepts these query parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `token` | Yes | Authentication token for auto-login |
| `write` | Yes | Report date in `YYYY-MM-DD` format |
| `today` | No | Pre-fill "今日工作内容" field |
| `plan` | No | Pre-fill "明日计划" field |
| `issue` | No | Pre-fill "问题与风险" field |

When the page loads with `?write=<date>`, it will automatically open the report edit modal with the form fields pre-filled from `today`, `plan`, and `issue`.

## Examples

### Example 1: Just intent, no content — return basic link

**User**: "写日报"

**Response**: Return `{{url}}?token=xxx`，并提示："已为您生成日报链接，点击即可手动填写。如果您需要我帮您自动填充，请按以下格式描述您的工作内容，我会帮您填好：\n\n今天完成了：<内容>\n明天计划：<内容>\n遇到的问题：<内容>"

**User replies with content** → Proceed to auto-fill (see Example 2).

### Example 2: Auto-fill — content already provided

**User**: "今天完成了登录模块开发，修复了3个bug；明天计划做权限管理；遇到问题：数据库连接池偶尔超时"

**Parsed**:
- write: "2026-06-18" (today)
- today: "完成了登录模块开发，修复了3个bug"
- plan: "做权限管理"
- issue: "数据库连接池偶尔超时"

**Link**: `{{url}}?token=xxx&write=2026-06-18&today=%E5%AE%8C%E6%88%90%E4%BA%86...`

### Example 3: Auto-fill — simple content

**User**: "今天主要做了前端页面重构和接口联调"

**Parsed**:
- write: "2026-06-18" (today)
- today: "主要做了前端页面重构和接口联调"
- plan: ""
- issue: ""

### Example 4: Auto-fill — supplementing yesterday's report

**User**: "补昨天的日报，做了代码审查和文档更新"

**Parsed**:
- write: "2026-06-17" (yesterday)
- today: "做了代码审查和文档更新"
- plan: ""
- issue: ""