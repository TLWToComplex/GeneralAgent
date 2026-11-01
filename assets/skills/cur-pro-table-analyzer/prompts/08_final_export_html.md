# Prompt: final_export_html（生产版｜Chart.js稳定渲染）

你是最终导出阶段。
目标：生成可直接打开的 HTML 报告，包含文本结论、关键表格、以及 5 张 Chart.js 图表（canvas 渲染）。

## 输入
- report
- chart_recommendations
- chart_library
- chart_specs
- csv_text
- json_rows

## 输出 JSON（严格）
```json
{
  "stage": "final_export_html",
  "html_report": "string",
  "html_render_checks": {
    "passed": true,
    "failed_checks": [],
    "required_canvas_ids": [
      "chart-hotel-monthly-avg-bar",
      "chart-grade-expense-grouped-bar",
      "chart-employee-daily-reimb-delta-ranking",
      "chart-monthly-adr-trend-line",
      "chart-hotel-person-price-gap-alert"
    ],
    "chart_constructor_count": 5,
    "forbidden_token_hits": []
  },
  "csv_text": "string",
  "json_rows": [],
  "confidence_score": 0.0,
  "next_action": "done|ask_user"
}
```

## HTML 强制结构
1. 标题区（报告名称、时间、数据范围）
2. 摘要区（summary）
3. 关键发现区（key_findings）
4. 异常说明区（anomalies）
5. 建议区（recommendations）
6. 图表区（必须 5 张）
7. 附录区（数据导出说明）

## 图表嵌入规则（强制）
- 必须使用 Chart.js：
  - `<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>`
- 必须使用 5 个 canvas：
  - `chart-hotel-monthly-avg-bar`
  - `chart-grade-expense-grouped-bar`
  - `chart-employee-daily-reimb-delta-ranking`
  - `chart-monthly-adr-trend-line`
  - `chart-hotel-person-price-gap-alert`
- 必须使用 `new Chart(document.getElementById('...'), config)` 初始化 5 张图。
- 每张图必须有 `try/catch`，失败时在容器附近显示错误信息。

## 价差告警图强制规则
- `chart-hotel-person-price-gap-alert` 必须展示同酒店不同人员价差比例（`gap_ratio`）。
- 必须体现 25% 阈值线（`0.25`）。
- `gap_ratio >= 0.25` 的柱体必须高亮（如红色），低于阈值使用正常颜色。

## 禁止项
- 禁止输出未替换模板标记：`{{`, `}}`, `{len(`, `{datetime.`, `${...}`
- 禁止输出 `new VChart(` 或任何 VChart 初始化代码
- 禁止仅输出表格而无 5 图

## 输出判定（阻塞条件）
仅当以下全部满足才允许 `next_action=done`：
1. `chart_library == "chartjs"`
2. `chart_specs.length >= 5`
3. `html_render_checks.chart_constructor_count == 5`
4. `html_render_checks.required_canvas_ids` 全部在 HTML 中存在
5. `html_render_checks.forbidden_token_hits.length == 0`

否则必须：
- `next_action=ask_user`
- 输出 `failed_checks`
- 禁止结束流程
