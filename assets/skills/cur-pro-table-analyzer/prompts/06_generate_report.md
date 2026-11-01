# Prompt: generate_report（生产版｜报销场景）

你是报告生成阶段。
目标：生成异常导向的报销分析报告，并产出 Chart.js 图表配置交接数据。

## 输入
- anomaly_records
- statistics
- analysis_result

## 输出 JSON（严格）
```json
{
  "stage": "generate_report",
  "report": {
    "summary": "string",
    "key_findings": ["string"],
    "anomalies": ["string"],
    "recommendations": ["string"]
  },
  "chart_recommendations": [
    {
      "chart_type":"bar|line",
      "purpose":"string",
      "x":"string",
      "y":"string",
      "why_this_chart":"string"
    }
  ],
  "chart_handoff": {
    "charts": [
      {
        "chart_id": "hotel_monthly_avg_bar|grade_expense_grouped_bar|employee_daily_reimb_delta_ranking|monthly_adr_trend_line|hotel_person_price_gap_alert",
        "chart_type": "bar|line",
        "title": "string",
        "description": "string",
        "x_field": "string",
        "y_field": "string",
        "group_field": "string",
        "canvas_id": "chart-hotel-monthly-avg-bar|chart-grade-expense-grouped-bar|chart-employee-daily-reimb-delta-ranking|chart-monthly-adr-trend-line|chart-hotel-person-price-gap-alert",
        "data_slice": [],
        "display_intent": "compare|trend|distribution|risk_density|alert"
      }
    ]
  },
  "final_export": {
    "csv_text": "string",
    "json_rows": []
  },
  "confidence_score": 0.0,
  "next_action": "continue"
}
```

## 强制图表覆盖（必须生成）
至少包含以下五类图：
1. 柱形图：各酒店月度均价对比（bar）
2. 分组条形图：职级 × 费用类型（月均/日均）对比（bar）
3. 排名柱状图：员工日均报销相对平均基线的正负偏差（bar，支持正负值）
4. 趋势图：月度 ADR 趋势（line）
5. 告警图：同酒店不同人员价格差异（gap_ratio）告警图（bar，阈值线=25%）

若任一图未生成，视为本阶段未完成。

## 规则
1. 先出文字结论，再出图表交接数据。
2. `chart_handoff.charts[].data_slice` 必须是可直接绘图的数据子集。
3. 本阶段不直接写 `chart_specs`，由下一阶段生成。
4. `canvas_id` 必须与 final HTML 中容器 id 完全一致（使用中划线命名）。
5. `hotel_person_price_gap_alert` 必须使用字段：`hotel`, `person_pair`, `gap_ratio`, `is_alert`。

## 失败降级策略
- Retry-1：先输出 report 与 chart_recommendations。
- Retry-2：仅输出五类强制图的 handoff 数据。
- 仍失败：输出最小可交付（summary + anomalies + recommendations）。
