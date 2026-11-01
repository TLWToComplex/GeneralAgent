---
name: daily-report-query
description: When the user wants to query daily reports (e.g. "查日报", "我的日报", "本周日报", "查张三的日报", "搜索附件中关于XX的内容"), this skill supports two modes: (1) direct API query by time range and person, (2) semantic search in knowledge base for uploaded attachments, then parse filenames to find corresponding daily reports.
# ⚠️ 配置须知：部署前需在智能体环境变量中设置以下三个变量（详见 scripts/config.py）：
#   REPORTS_API_BASE  — 日报后端 API 地址（默认 http://172.22.16.1:8000）
#   KB_API_BASE       — 知识库 API 地址（默认 http://192.168.0.104:7861）
#   MAIN_SYSTEM_BASE  — 主系统地址（默认 http://172.22.16.1:8038）
#   此注释为 YAML 注释，不会影响 skill 行为。
---

# Daily Report Query

## Overview

Two query modes:

1. **Mode 1 — Direct API query**: Query daily reports by time range and person via the reports API.
2. **Mode 2 — Semantic search**: Search uploaded attachments in the knowledge base, parse filenames to find corresponding daily reports.

## Scripts

| File | Purpose |
|------|---------|
| `scripts/config.py` | Service URLs and constants |
| `scripts/utils.py` | Shared utilities (token extraction, filename parsing, author name resolution, formatting) |
| `scripts/query_reports.py` | Mode 1: Query reports API by time/person |
| `scripts/search_kb.py` | Mode 2: Search knowledge base, parse filenames, fetch linked reports |

## Trigger Conditions

Trigger when the user message contains any of:

- **Mode 1** (time/person query): "查日报", "我的日报", "今天日报", "昨天日报", "本周日报", "上周日报", "最近日报", "查张三的日报", "查张三和李四的日报"
- **Mode 2** (semantic search): "搜索附件", "查附件", "查文档", "搜一下XX", "有没有XX的文档", "查一下关于XX的附件"

## Workflow

### Step 1: Extract Token

Extract the token from the environment variable:

```python
import os
token = os.environ.get("USER_TOKEN")
```

If the token cannot be found, respond: "无法获取认证信息，请重新登录后重试。"

### Step 2: Determine Mode

Analyze the user's intent:

- **Mode 1** — User asks about reports by time, person, or both. Keywords: "日报" + time/person patterns.
- **Mode 2** — User asks about file/attachment content. Keywords: "附件", "文档", "文件", "搜索" + content description.

If the user's intent is unclear (e.g., just "查日报" with no time or person specified), respond with the basic link `{{url}}?token=<token>` and ask what conditions they want to query.

### Step 3: Execute and Return Link

After executing the API call, always return a frontend link in `{{url}}` format that includes the actual query parameters used. The link allows the user to view results in the page.

---

## Mode 1: Direct API Query

### Step M1.1: Determine Date Range

Parse the user's intent:

| Intent Pattern | Date Range |
|---------------|------------|
| "今天日报", "查今天的" | today |
| "昨天日报", "昨天的" | yesterday |
| "本周日报", "这周" | Monday of this week ~ today |
| "上周日报", "上周" | Monday of last week ~ Sunday of last week |
| "最近N天" | today - N days ~ today |
| 具体日期 "查6月20号的" | specified date |
| No date specified | omit date filter |

Use Python to calculate:

```python
from datetime import date, timedelta
today = date.today()
# today
start = today; end = today
# yesterday
start = today - timedelta(days=1); end = today - timedelta(days=1)
# this week
start = today - timedelta(days=today.weekday()); end = today
# last week
last_monday = today - timedelta(days=today.weekday() + 7)
start = last_monday; end = last_monday + timedelta(days=6)
```

### Step M1.2: Extract Staff Names

| Pattern | staff_names |
|---------|-------------|
| "查{name}的日报" | "name" |
| "查{name1}和{name2}的日报" | "name1,name2" |
| "我的日报", "查日报" (no name) | omit |

### Step M1.3: Execute Script

Run `scripts/query_reports.py` from the skill directory:

```bash
cd .codebuddy/skills/daily-report-query && \
python scripts/query_reports.py \
  --start "<YYYY-MM-DD>" \
  --end "<YYYY-MM-DD>" \
  --staff "<names>" \
  --frontend-url "{{url}}"
```

- Omit `--start` / `--end` if no date filter
- Omit `--staff` if no person specified
- The script outputs formatted report list + frontend link

### Step M1.4: Present Results

Present the API results to the user. **关键：末尾必须附带前端链接，单独一行，用 Markdown 行内代码格式 `` `url` `` 包裹，不加任何前缀文字**（否则系统无法识别并渲染网页卡片）：

```
`{{url}}?token=<token>&all=true&start_date=<date>&end_date=<date>&staff_names=<names>`
```

如果未找到结果，回复"未找到符合条件的日报记录。"

---

## Mode 2: Semantic Knowledge Base Search

### Step M2.1: Execute Script

Run `scripts/search_kb.py` from the skill directory:

```bash
cd .codebuddy/skills/daily-report-query && \
python scripts/search_kb.py "<search_query>" --frontend-url "{{url}}"
```

- `<search_query>` is the user's search intent (e.g., "登录模块", "数据迁移方案")

### Step M2.2: Present Results

Present the knowledge base search results and linked daily reports. **关键：末尾必须附带一个前端链接，单独一行，将所有日报 ID 通过 `ids` 参数传递，用 Markdown 行内代码格式 `` `url` `` 包裹，不加任何前缀文字**：

`{{url}}?token=<token>&ids=<id1>,<id2>,<id3>`

ID 通过 `compute_report_id(author_id, date)` 计算。

如果搜索无结果，回复"知识库中未找到相关的内容。"

---

## Link Format

**每次查询结果末尾必须附带一个前端链接，单独一行，用 Markdown 行内代码格式 `` `url` `` 包裹，不加任何前缀文字。** 参照 `daily-report-skill` 的链接格式，系统会识别 `{{url}}` 模板并自动渲染网页卡片。

**Mode 1**（按时间/人员查询）：
`{{url}}?token=<token>&all=true&start_date=<date>&end_date=<date>&staff_names=<names>`
参数与 `list_reports` 接口实际传入的参数一致。

**Mode 2**（语义搜索）：
`{{url}}?token=<token>&ids=<id1>,<id2>,<id3>`

ID 通过 `compute_report_id(author_id, date)` 计算，前端调用 `list_reports?ids=...` 直接定位到对应日报。

---

## Filename Format Reference

Knowledge base files are stored with the naming convention:

```
{author_id}_{date}_{original_filename}
```

- `author_id`: UUID (36 chars, e.g. `abc12345-def6-7890-abcd-ef1234567890`)
- `date`: `YYYY-MM-DD`
- `original_filename`: the original uploaded filename

This is parsed by `scripts/utils.py` → `parse_filename()` to link knowledge base results back to daily reports.

## ID Format

日报 ID = `md5(author_id + "_" + date)`

由 `scripts/utils.py` → `compute_report_id()` 计算。从知识库文件名解析出 `author_id` 和 `date` 后，可直接计算日报 ID，通过 `GET /api/reports?ids=id1,id2` 批量精确查询，无需日期范围扫描。

## Examples

### Example 1: Mode 1 — Today's reports

**User**: "查今天的日报"

**Action**: `python scripts/query_reports.py --start "2026-07-01" --end "2026-07-01" --frontend-url "{{url}}"`

### Example 2: Mode 1 — Specific person

**User**: "查张三的日报"

**Action**: `python scripts/query_reports.py --staff "张三" --frontend-url "{{url}}"`

### Example 3: Mode 1 — Person + date range

**User**: "查张三和李四本周的日报"

**Action**: `python scripts/query_reports.py --start "2026-06-29" --end "2026-07-01" --staff "张三,李四" --frontend-url "{{url}}"`

### Example 4: Mode 2 — Semantic search

**User**: "搜索附件中关于登录模块的文档"

**Action**: `python scripts/search_kb.py "登录模块" --frontend-url "{{url}}"`

### Example 5: Mode 2 — No results

**User**: "查一下有没有关于数据迁移的附件"

**Action**: `python scripts/search_kb.py "数据迁移" --frontend-url "{{url}}"`

**Response**: "知识库中未找到与"数据迁移"相关的内容。"