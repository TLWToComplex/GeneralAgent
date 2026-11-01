---
name: 表格分析
description: 面向报销单（住宿、机票等）的 Excel/Table/图表数据分析 Skill，聚焦异常数据检查、对比分析和报告生成，不涉及图片识别。
disable-model-invocation: false
---

# Reimbursement Table Analyzer Skill

## Scope

仅围绕“结构化数据分析”执行，不做识图：
1. 读取并理解用户提供的 Excel / Table / 图表数据
2. 数据结构识别与字段语义映射（人员、职级、费用类型、酒店、航线、日期、金额）
3. 数据校验与清洗（缺失、重复、格式、币种、口径统一）
4. 异常检测与规则分析（住宿、机票等）
5. 统计分析与对比分析（人员、职级、月份、酒店、房型）
6. 生成异常报告与行动建议
7. 图表报告阶段调用图表子能力生成可渲染图表配置（优先 Chart.js，保障HTML本地可稳定显示）

约束：
- 不使用外部 API
- 仅使用平台文本模型能力
- 不执行 OCR / 布局分析
- 必须执行并完成全部 9 个阶段，禁止为追求速度提前结束。

## Execution Workflow (must run in order)

1. `collect_input`
2. `ingest_structured_data`
3. `validate_and_normalize`
4. `detect_anomalies`
5. `analyze_patterns`
6. `generate_report`（生成 `chart_recommendations`）
7. `build_chart_specs`（生成 `chart_library=chartjs` 与 `chart_specs`）
8. `final_export_html`
9. `export_long_image`

Do not skip steps.

Mandatory completion policy (strict):
- 必须执行并完成全部 9 个阶段，禁止为追求速度提前结束。
- 仅当 `export_long_image.next_action=done` 时，任务才视为完成。
- 任一阶段失败必须返回阻塞原因并重试/请求用户，不得跳过后续必需阶段。

Hard gate:
- `final_export_html` 前必须满足：
  - `chart_library == "chartjs"`
  - `chart_specs.length >= 5`
  - `render_summary.generated_chart_count == 5`
  - `render_summary.missing_charts.length == 0`
  - 所有图 `validation.is_renderable == true`
- 任一条件不满足，必须返回 `next_action=ask_user`，禁止仅输出表格。

## Mandatory Analysis Angles (must all be covered)

1. 房价异常（单笔过高、离群值、异常波动）
2. 平均房价 ADR（按月/酒店/人员/职级）
3. 同房型同比 / 环比波动超过 ±20%
4. 月度新增酒店且发生额较大（>10000 元）预警
5. 高频异常消费（短周期反复高额/高频）
6. 按人员与对应职级进行差异与偏离分析
7. 机票异常（同航线/同时间窗口价格异常、舱位不合理、临近出发高价）

## Confidence Gate

- `confidence_score >= 0.85`: continue automatically
- `0.65 <= confidence_score < 0.85`: request quick user confirmation for key mappings/thresholds
- `confidence_score < 0.65`: stop and request detailed user confirmation

## Retry Policy

Each stage: max 2 retries.
- Retry-1: fix schema/format/mapping errors only
- Retry-2: degrade to core fields only (人员、职级、费用类型、日期、金额)
- If still failing: return blocked status and request user action

## Mandatory Output Requirements

Final output must include:
- `normalized_rows`
- `cleaning_log`
- `anomaly_records`
- `analysis_result`
- `report`
- `chart_recommendations`
- `chart_library`
- `chart_specs`
- `html_report`
- `html_render_checks`
- `long_image_export`
- `csv_text`
- `json_rows`

## Stage Prompt Assets

Load and follow these files:
- `prompts/01_collect_input.md`
- `prompts/02_ingest_structured_data.md`
- `prompts/03_validate_and_normalize.md`
- `prompts/04_detect_anomalies.md`
- `prompts/05_analyze_patterns.md`
- `prompts/06_generate_report.md`
- `prompts/07_build_chart_specs.md`
- `prompts/08_final_export_html.md`
- `prompts/09_export_long_image.md`

## Blocked Response Template

```json
{
  "stage": "string",
  "status": "blocked",
  "reason": "string",
  "what_is_missing": ["string"],
  "user_can_do": ["string"],
  "next_action": "ask_user"
}
```

## References

- Detailed runbook: `playbook.md`
- Full schema: `schemas/pipeline.schema.json`
- Full sample: `examples/full-run-sample.json`
- Acceptance checklist: `ACCEPTANCE_CHECKLIST.md`
