---
name: doc-审阅修订
description: >
  docx 文档审阅与修订工具。从 doc-格式化 (docx-spec-formatter) v0.6.0 分叉。
  继承全套文档分析、格式校验和修复引擎，面向文档审阅场景扩展。
  核心特性：所有格式修改自动插入 OOXML 修订标记（w:rPrChange / w:pPrChange），
  使 Word/WPS 能够以"修订模式"展示所有格式变更，支持逐条审阅。
tags:
  - docx
  - 审阅
  - 修订
  - 校验
  - 文档
  - track-changes
version: 0.5.0
agent_created: true
forked_from: doc-格式化
original_version: 0.6.0
---

# doc-审阅修订

docx 文档审阅与修订工具。从 doc-格式化 v0.6.0 分叉，继承全套文档分析和格式操作引擎。

## 工作方式（给 AI 的指令）

用户只需说一句话，例如：

> "使用 docx-审阅修订 skill，用 hz 模板，格式化 射频前端研制总结.docx"

AI 自动执行以下完整流水线，**不需要用户知道任何 CLI 命令**。

### 第 1 步：确定模板

skill 内置 3 套模板配置，根据用户指定的名称选择：

| 用户说 | 实际文件 | 规范 |
|--------|---------|------|
| "默认模板" / "default" | `templates/default-spec.json` | 宋体/TNR/1.5倍行距/A4左右1.91cm |
| "GA模板" / "GA" | `templates/GA-spec.json` | G01.0403 V2.0 技术文件格式 |
| "hz模板" / "航天模板" | `templates/hz-spec.json` | 航天射频产品（黑体标题/25磅固定行距/30mm边距） |

如果用户未指定模板，使用 GA-spec.json。

### 第 2 步：复制输入文件

将用户提供的输入 docx 复制到 skill 目录下的临时文件：

```bash
cp "用户路径/输入.docx" input_temp.docx
```

### 第 3 步：执行格式化（后台 CLI）

```bash
cd 本skill目录
python scripts/cli.py format -i input_temp.docx -s templates/xxx-spec.json -o output.docx
```

### 第 4 步：自动验证（四层防御体系）

format 命令内部自动执行全部四层防御：

```
第 1 层 — 格式规则校验
  Phase 4 统一校验 43 项硬性规则（字体/字号/边距/行距/对齐/列表缩进等）
  每项输出：通过 / 失败 / 警告，失败项进入修复循环

第 2 层 — 参考文档差异比对（可选）
  如果用户提供了参考文档（如"参照 05_DH2007_final_v4.docx 格式"），
  自动执行 diff-check 比对标题分布/列表级数/表格数等结构特征
  命令：python scripts/cli.py diff-check output.docx --ref 参考文档.docx

第 3 层 — 语义缺陷自审
  18 条检测模式自动扫描输出文档：
  · 标题类（编号跳跃/无空格/style污染/无outlineLvl等）7条
  · 列表类（未重置/级别跳跃）2条
  · 区域类（边界误判/封面溢出）2条
  · 格式类（对齐不一致/行距不匹配/section边距/字体遗漏）5条
  · 追踪类（修订覆盖/样式库残留）2条
  其中 4 条可自动修复（数字空格/行距/style污染/numPr残留）
  结果写入 final-report.json 的 self_review 字段

第 4 层 — 缺陷模式库回灌
  如果用户反馈了新模式检测不到的问题：
  · 我在 feedback.py 中追加新模式的检测逻辑
  · 新模式永久固化到 _defect_patterns.py
  · 下次格式化自动扫描新模式
  · 每次反馈都变成一次自动化能力增长

此外，format 自动输出：
· final-report.json（含校验结果 + 自审结果 + 修复记录）
· report.html（可视化报告，可直接用浏览器打开）
· 格式变更统计（标题层级/修订标记数/列表段落/表格数等 7 个维度）
```

### 第 4.5 步：AI 视觉自审查（新增，自动执行）

每次格式化完成后，**必须**执行 AI 结构化评审，发现规则引擎漏掉的问题：

```bash
python scripts/cli.py ai-review output.docx -s templates/xxx-spec.json -o _ai_review_data.txt
```

然后读取 `_ai_review_data.txt` 中的结构化数据，以 AI 视角逐项评审：

1. **标题检测完整性** — 所有应被识别的标题都被识别了吗？有无遗漏或误判？
2. **标题层级正确性** — 层级关系与文档结构一致吗？有无跳级？
3. **列表编号连续性** — 每级列表编号是否连续无跳号？
4. **区域划分** — 封面/目录/正文边界准确吗？（看 section 边距）
5. **修订覆盖合理性** — 有没有段落应有修订但没有？
6. **异常段落** — 有没有段落格式明显与同类段落不一致？

对每项输出：通过 / 发现问题（严重程度+段落索引+修复建议）。
评审结果附在最终回复中，**不能仅在后台运行**。

### 第 5 步：交付

使用 `deliver_attachments` 工具将 output.docx 发送给用户。
同时在回复中附上格式变更摘要和 AI 评审结论。

---

## 按需使用（用户额外要求时执行）

### 缺陷反馈回路如果用户要求"检查质量"或"评审结果"，提取文档结构化数据并做 AI 评审：

```bash
python scripts/cli.py ai-review output.docx -s templates/xxx-spec.json -o prompt.txt
```
阅读 prompt.txt 中的结构化数据，按 6 个维度逐项评审并回复自然语言结果。

### 缺陷反馈回路

如果用户反馈某个缺陷模式没有检测到，执行：

```bash
python scripts/cli.py feedback  # 交互式录入新模式
```
或直接告诉我问题描述，我在 _defect_patterns.py 中追加对应的 detect 函数。

如果用户要求检查缺陷或质量，执行：

```bash
python scripts/cli.py self-check output.docx -s templates/xxx-spec.json
```
解析结果中的 self_review 数据，用自然语言回复用户。

---

## 模板定义

所有模板文件位于 `templates/` 目录：

```
templates/
├── default-spec.json    默认（宋体/1.5倍行距）
├── GA-spec.json     GA（G01.0403 V2.0）
└── hz-spec.json         航天射频产品（黑体/25磅固定/30mm边距）
```

用户可以通过 `spec-init` 命令创建副本进行定制：

```bash
python scripts/cli.py spec-init --template hz -o 我的规范.json
```

---

## 核心模块

```
scripts/
├── cli.py                  统一命令行入口
├── spec_loader.py          规范加载与校验
├── doc_analyzer.py         文档结构分析
├── format_applier.py       格式应用引擎（含自审/统计/修订追踪）
├── validator.py            校验引擎（43项检查 + 自审集成）
├── fix_engine.py           修复引擎（迭代循环）
├── font_manager.py         中西文字体管理
├── track_changes.py        Track Changes 修订追踪
├── _defect_patterns.py     语义缺陷模式库（18条规则）
├── auto_fix.py             自动修复器（修复可修复缺陷）
├── diff_check.py           参考文档差异比对
├── report_html.py          HTML 可视化报告生成器
├── ai_review.py            AI 评审数据提取器
├── batch.py                批量格式化
├── feedback.py             缺陷反馈回路
└── utils.py                工具函数
```

## 工作流

```
用户一句话指令
       │
  AI 自动执行:
  1. 确定模板
  2. 复制输入文件到工作目录
  3. format（后台 CLI，含 7 阶段流水线）
  4. 解析校验结果
  5. deliver_attachments 交付文件
  6. 在回复中附上变更摘要
       │
用户可直接用 WPS 打开输出文档查看结果
（含修订标记，可在"审阅"选项卡逐条接受/拒绝）
```

## 核心能力

- **一句话操作**：用户只需指定模板和文档，AI 完成全部流程
- **规范驱动**：JSON 格式规范文件是唯一真相源
- **中西文分离**：CJK 字体和 Latin 字体独立配置
- **区域识别**：自动检测封面、目录、正文、修订记录
- **列表自动编号**：L1 a)/L2 1) 有序 + L3-L5 无序，5级缩进
- **页码插入**：X/Y 格式 PAGE/NUMPAGES 域，覆盖全文档
- **标题层级**：自动应用 Heading 样式 + outlineLvl，WPS 导航可见
- **全表格式化**：表头/表体字体、边框、背景色统一处理
- **迭代校验**：校验→修复→再校验，直到全部通过
- **修订追踪**：所有格式修改自动插入 OOXML 修订标记
- **语义自审**：18 条缺陷模式自动检测 + 4 类自动修复
- **自动修复**：数字空格、行距、样式污染等静默修正
- **HTML 报告**：每次格式化自动生成可视化报告
- **差异比对**：可与参考文档结构比对（--ref 参数）
- **纯 Python**：无 .NET 依赖，UTF-8 全链路原生

## 版本路线

- **v0.1.0**：从 doc-格式化 v0.6.0 分叉，继承全部格式引擎 ✅
- **v0.2.0**：Track Changes 修订追踪 ✅
- **v0.2.4**：修复中文方块/问号乱码 ✅
- **v0.2.3**：修复乱码问题 — 二次 ZIP 修复 ✅
- **v0.2.2**：修复空修订问题 ✅
- **v0.2.1**：修正 settings.xml 缺失 trackRevisions bug ✅
- **v0.5.0**：标题层级（Heading 样式 + outlineLvl）✅
- **v0.5.1**：语义自审 + 自动修复 + HTML 报告 + 差异比对 ✅
- **v0.6.0**：AI 评审数据提取 — 待规划
- **v1.0.0**：正式发布 — 测试与优化
