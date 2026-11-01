# Playbook（Trae Solo 执行手册）

本手册用于严格执行 `table-image-to-analysis-report` Skill。唯一目标：完成“表格图片→表格→分析→报告”。

## 0. 执行总则

1. 禁止调用外部 API。
2. 必须按阶段顺序执行，不可跳步。
3. 每阶段必须输出 JSON：`stage/confidence_score/next_action`。
4. 当 `next_action=ask_user` 时，必须停止自动推进。
5. 所有纠错必须可追溯（before/after/reason）。

## 1. 阶段流水线

1) collect_input
2) ocr_extract
3) layout_parse
4) table_reconstruct
5) validate_and_correct
6) analyze_data
7) generate_report
8) final_export

## 2. 置信度网关

- `>=0.85`：自动继续
- `[0.65,0.85)`：快速人工确认（仅关键字段）
- `<0.65`：详细人工确认 + 建议补图

## 3. 标准重试策略

每阶段最多 2 次重试：

- Retry-1：仅修复结构与格式（不改业务语义）
- Retry-2：降级为“高置信核心字段”策略
- 仍失败：输出失败报告并等待用户

## 4. 人工确认节点（必须停）

- OCR 歧义过多
- 布局冲突（无法确定行列边界）
- 高风险纠错（金额/人名/日期被改写）
- 跨页合并后列名冲突

## 5. 多表格/跨页执行规则

### 多表格（单图）
- 对每个表格分配 `table_id`
- 默认主表：面积最大且标题完整
- 次表写入 `additional_tables`

### 跨页（多图）
- 每页独立提取并附 `page_index`
- 合并时执行列名映射并记录 `merge_rules`
- 冲突写入 `merge_warnings`

## 6. 分析与报告最低要求

分析最少输出：
- 总体均值
- 个体与均值差异（正负）
- 异常数据与判定依据（z-score 或 IQR）

报告最少输出：
- 摘要
- 关键发现
- 异常说明
- 行动建议
- 图表建议（类型+用途+x/y）

## 7. 失败时返回格式

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

## 8. 交付内容检查清单

- [ ] 阶段输出 JSON 完整
- [ ] `confidence_score` 合理
- [ ] 纠错日志完整
- [ ] 分析结果可复核
- [ ] 报告具备可执行建议
- [ ] 最终导出含 Markdown/CSV/JSON
