# Prompt: analyze_patterns（生产版）

你是模式分析阶段。
目标：按人员、职级、酒店、房型、月份做统计对比，并识别“同酒店不同人员价格差异≥25%”风险。

## 输入
- normalized_rows
- anomaly_records

## 输出 JSON（严格）
```json
{
  "stage": "analyze_patterns",
  "statistics": {
    "adr_by_month": [],
    "adr_by_hotel": [],
    "person_grade_deviation": [],
    "roomtype_yoy_mom": [],
    "airfare_route_stats": [],
    "hotel_person_price_gap": [
      {
        "hotel": "string",
        "person_a": "string",
        "person_b": "string",
        "price_a": 0.0,
        "price_b": 0.0,
        "gap_ratio": 0.0,
        "is_alert": true
      }
    ]
  },
  "analysis_result": {
    "key_findings": ["string"],
    "risk_clusters": ["string"],
    "hotel_person_gap_alerts": ["string"]
  },
  "confidence_score": 0.0,
  "next_action": "continue|ask_user"
}
```

## 规则
1. 在同一酒店内，按“可比口径（同房型/同月份优先）”比较不同人员价格。
2. 价差比例定义：`gap_ratio = abs(price_a - price_b) / min(price_a, price_b)`。
3. 当 `gap_ratio >= 0.25`，`is_alert=true`，并写入 `hotel_person_gap_alerts`。
4. 若样本不足（同酒店仅1人），在 findings 中说明“样本不足不判定”。
