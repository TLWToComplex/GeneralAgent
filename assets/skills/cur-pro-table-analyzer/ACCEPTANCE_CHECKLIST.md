# 验收清单（对齐原始需求：酒店报销分析场景）

> 目标：确保“原始需求为唯一目标”且聚焦酒店报销分析。

## A. 图片→文字识别 + 布局分析

- [ ] 支持用户上传表格图片
- [ ] 输出 OCR 文本 token（含置信度）
- [ ] 输出布局分析结果（单元格物理坐标）
- [ ] 支持合并单元格（rowspan/colspan）
- [ ] 低置信触发人工确认

## B. 文本→结构化表格 + 校验纠错

- [ ] 按结构重建二维表
- [ ] 支持输出 Markdown/CSV/JSON
- [ ] 在分析前提供人工修正入口
- [ ] 支持 LLM 逻辑清洗
- [ ] 所有修正具备 before/after/reason

## C. 酒店报销核心分析（必须全部覆盖）

- [ ] 房价异常识别
- [ ] 平均房价 ADR（总体/按月/按酒店/按人员/按职级）
- [ ] 同房型同比 / 环比波动超过 ±20% 预警
- [ ] 月度新增酒店 + 发生额 > 10000 元预警
- [ ] 高频异常消费识别
- [ ] 按人员 + 职级差异分析

## D. 报表与可视化建议

- [ ] 输出总结（summary）
- [ ] 输出关键发现（key findings）
- [ ] 输出异常说明（anomalies）
- [ ] 输出行动建议（recommendations）
- [ ] 输出图表建议（类型+用途+x/y+原因）

## E. 约束与工程化

- [ ] 全流程不依赖外部 API
- [ ] 仅使用平台多模态/LLM能力
- [ ] 每阶段输出标准 JSON（含 confidence_score/next_action）
- [ ] 支持多表格/跨页
- [ ] 失败有重试和降级策略

## F. 交付完整性

- [ ] `.cursor/skills/table-image-analysis-report/SKILL.md` 已定义流程与规则
- [ ] `prompts/` 已提供生产版模板
- [ ] `schemas/pipeline.schema.json` 与 prompts 对齐
- [ ] `examples/full-run-sample.json` 可作为回归样例
- [ ] `playbook.md` 可直接执行
