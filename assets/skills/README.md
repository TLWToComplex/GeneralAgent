# Skills

AI Agent Skills 集合，包含以下项目：

## 项目列表

### 1. cur-pro-table-analyzer
智能表格图片识别与分析工具。支持从图片中提取表格数据，进行布局分析、数据校验、统计分析和可视化报告生成。

**核心功能：**
- 表格图片识别与数据提取
- 布局分析与数据校验
- 异常检测与统计分析
- 可视化报告生成
- 支持多种图表类型（26种）

**主要文件：**
- `SKILL.md` - 技能描述与使用说明
- `prompts/` - 分析流程提示词模板
- `references/` - 参考文档与 API 说明
- `schemas/` - 数据结构定义
- `examples/` - 示例文件

---

### 2. doc-审阅修订
Word 文档审阅与修订工具。支持文档格式校验、自动修订、差异对比和 AI 辅助审查。

**核心功能：**
- 文档格式自动校验
- 修订跟踪与记录
- 格式差异对比
- AI 辅助审查
- 自动修复格式问题
- HTML 报告生成

**主要文件：**
- `SKILL.md` - 技能描述与使用说明
- `scripts/` - Python 脚本（校验、修复、对比等）
- `templates/` - 配置模板
- `references/` - 规范文档
- `test/` - 测试用例

---

### 3. rules-extract
制度文件摘要工具。从制度/规章/办法类文件中提取结构化摘要（七个维度：制度名称、核心目标、责任主体、关键执行步骤、关键阈值、禁止事项、关键词），输出为长度稳定、样式规范的 Markdown 表格或 Word 文档。

**核心功能：**
- 七维度结构化摘要提取（缺一不可）
- 输入支持本地文件（txt/md/pdf/docx）、网页 URL 与直接文本
- 摘要长度三档可控（short/medium/long），条数与字数有硬性配额
- 输出 Markdown 表格，可导出规范 Word 文档（深蓝标题、专业表头、隔行着色）
- 未配置大模型时自动回退本地规则提取，开箱可用

**主要文件：**
- `SKILL.md` - 技能描述与使用说明
- `scripts/extract_rules.py` - 提取脚本（大模型 + 本地规则回退）
- `templates/` - Word 输出模板
- `test_rule.md` - 测试样例

---

### 4. pdf_ocr_to_excel
PDF OCR 表格提取工具。将 PDF（含扫描件）通过 OCR 解析提取表格数据并导出为 Excel，支持跨页表格合并、合并单元格保留与样式化输出。

**核心功能：**
- PDF 页面渲染与 OCR 识别（minerU API）
- HTML `<table>` 与 Markdown 表格双向解析
- 表格结构校验与修复（行列对齐、空单元格填充）
- 一个表格一个 sheet，保留标题、合并单元格与表头样式

**主要文件：**
- `SKILL.md` - 技能描述与使用说明
- `scripts/pdf_ocr_to_excel.py` - OCR 提取主脚本
- `scripts/excel_utils.py` - 表格校验与 Excel 写入
- `scripts/html_table_parser.py` - HTML 表格解析

---

### 5. analyze-travel-expenses
差旅消费数据统计与报表工具。对导出的 Excel/CSV/TSV 差旅消费明细做合并、去重、校验、汇总、统计、对比、排名与可视化，一键生成 Excel 与 HTML 财务分析报告。

**核心功能：**
- 多文件合并、去重与数据校验（validation.json）
- 酒店数量/等级/排名、部门费用、每月出差曲线、住宿顶格报销等内置分析模块
- 协议酒店、价格偏离、退订重订、前二十大城市、机票/火车票、退票退款分析
- 扩展分析模块可配置启停，输出 HTML 报告与 Excel 报表

**主要文件：**
- `SKILL.md` - 技能描述与使用说明
- `scripts/pipeline.py` - 一键执行管道
- `scripts/analysis_modules/` - 各分析模块
- `config/config.json` - 模块开关与中文配置
- `templates/` - HTML 报告模板
- `references/` - 业务规则与输出结构说明

---

### 6. 合同审核
合同审阅与风险评估工具（V2-1）。支持对合同、协议、条款类文件执行结构化条款提取、双轨制合规检查、法律/财务风险评分，并生成 DOCX 报告、Word 批注版与 Markdown 报告。

**核心功能：**
- 条款结构化提取（LLM，输出 extracted_clauses.json）
- 双轨制合规检查（必查法规 + 选查行业法规，输出 compliance_report.json）
- 风险分析（规则引擎 + LLM 双引擎，输出 risk_register.json）
- 修改建议与条款级版本差异对比（输出 suggestions.json）
- DOCX 结构化报告生成（推荐）
- Word 批注/修订追踪（原始合同 + 批注标记）
- Markdown 报告生成（兜底查阅）

**主要文件：**
- `SKILL.md` - 技能描述与使用说明
- `scripts/extract_clauses.py` - 条款提取
- `scripts/compliance_check.py` - 合规检查（双轨制）
- `scripts/analyze_risks.py` - 风险分析
- `scripts/generate_docx_report.py` - DOCX 报告生成
- `scripts/generate_report.py` - Markdown 报告生成
- `scripts/content_tracker.py` - Word 批注/修订追踪
- `config/industry_regulations.json` - 行业法规配置
- `laws/` - 法规原文

---

### 7. supermap-camera-query
SuperMap 相机查询技能（占位，待补充）。

---

### 8. GA-ppt
PPT 生成与编辑工具。基于 PptxGenJS + Python 的混合工作流：先由 `build_structure.py` 生成封面/章节页/结尾页，再用 PptxGenJS 生成内容页，最后由 `merge_content.py` 合并为成品 PPTX。

**核心功能：**
- 源文件（PDF/Word/图片）驱动生成，标题、章节与内容必须取自源文件，禁止通用示例内容
- 混合工作流：结构生成 → 内容页生成 → 合并、清理、打包，产出唯一 `output.pptx`
- PPTX 读取与分析（markitdown）、幻灯片缩略图预览
- 幻灯片编辑与修改

**主要文件：**
- `SKILL.md` - 技能描述与使用说明
- `editing.md` / `pptxgenjs.md` - 编辑规范与 API 参考
- `scripts/build_structure.py`、`scripts/merge_content.py`、`scripts/thumbnail.py` 等脚本
- `templates/reference.pptx` - 结构模板

---

### 9. file-completeness-check-v8-all-files-uniquely-associated
文件齐套性核查工具（LLM 匹配版）。上传"文件齐套性要求 DOCX + 项目资料 ZIP"，自动提取要求条目与文件清单，由大模型将 ZIP 内每个真实文件唯一关联到最匹配的要求条目，仅交付一份 Word 格式《文件齐套性核查记录》。

**核心功能：**
- 要求条目与 ZIP 文件清单自动提取（`check_completeness.py` extract 模式，含 DOCX 标题/首段摘录预览）
- LLM 逐文件匹配，遵循"一文件一项"唯一关联原则
- 五种判定状态：已匹配 / 部分满足 / 疑似匹配 / 未找到 / 待确认适用性
- 严格区分相近文件类型（如报告≠大纲、策划书≠设计方案），不能直接核销的标记待人工确认
- 唯一交付物：`文件齐套性核查记录.docx`（核查结果、文件对应明细、需补齐文件、需人工确认文件）

**主要文件：**
- `SKILL.md` - 技能描述与使用说明
- `scripts/check_completeness.py` - 数据提取与 Word 报告生成脚本
- `manifest.txt`、`README.md` - 内容清单与说明

---

## 使用说明

各技能的使用方法请参考对应文件夹中的 `SKILL.md` 文件。