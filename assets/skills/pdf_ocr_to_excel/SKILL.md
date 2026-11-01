---
name: pdf_ocr_to_excel
description: "对 PDF 文件进行 OCR 解析，提取其中的表格并导出为 Excel。当用户上传 PDF 文件、提及 PDF 表格识别、OCR 提取表格、从 PDF 中提取表格图片内容、或任何涉及从 PDF 中获取表格数据的请求时，**必须首先使用本技能**，禁止尝试 pdfplumber、pypdf 等其他库。"
license: Proprietary
---

# PDF OCR 表格提取到 Excel Skill

## ⚠️ 强制约束（必须遵守）

- **唯一入口**：必须且只能运行 `scripts/pdf_ocr_to_excel.py` 脚本，**禁止**使用 `pdfplumber`、`pypdf`、`PyPDF2`、`pytesseract` 等任何其他库直接解析 PDF。
- **不得跳过任何步骤**：严格按下方工作流程顺序执行。
- **遇到错误**：立即报告错误信息并停止，不得自行尝试替代方案。
- **脚本输出的表格数据中，空单元格是正常的**：部分扫描件中表格数据可能因颜色、字体或 OCR 模型限制而无法识别，这些单元格将被保留为空字符串。  

## 自动触发条件（必须遵守）
- 用户上传了 PDF 文件（无论是否明确说“提取表格”） → **自动触发本技能**
- 用户提到：“OCR”、“表格识别”、“扫描件转 Excel”、“提取表格数据” → **自动触发本技能**
- **禁止**在未调用本技能的情况下，使用 pdfplumber、pypdf、camelot 等工具直接解析 PDF。

## 工作流程

**严格按照以下流程步骤来运行，每一步都不能跳过**。

1. 接收用户上传的 PDF 文件（平台自动注入文件路径）
2. **执行命令**：`python scripts/pdf_ocr_to_excel.py --input <pdf_path> --output <xlsx_path>`（脚本内部会自动将每页转为图片，调用 minerU API 进行 OCR）。
3. 脚本内部流程：
   - **渲染图片**：使用系统命令 `pdftoppm`（来自 poppler-utils）将 PDF 每页渲染为 PNG 图片（DPI=200）。
   - **OCR 解析**：每张图片发送至 minerU `/api/parse_to_markdown` 接口（优先使用 `/api/process` 并设置 `process_type=mineru`）。
   - 合并所有页的 Markdown 结果。
   - **从返回内容中提取表格**：
     - 优先解析 `<table>` 标签（直接 HTML 表格）；
     - 若未找到，则识别 `[TABLE]` / `[/TABLE]` 包裹的 Markdown 表格；
   - 对提取的表格进行**结构校验与修复**（确保每行列数一致，空单元格填充为空字符串）。
   - 将表格写入 Excel，每个表格一个 sheet，根据合并信息调用 `merge_cells` 合并单元格，表头加粗、居中、浅蓝背景，所有单元格带边框。
4. 返回 Excel 文件

> **强制约束**：在处理 PDF 表格提取任务时，不要先调用 pdfplumber、pypdf 等工具，也不要自行编写 OCR 代码。必须先使用该 skill 提供的 `scripts/pdf_ocr_to_excel.py` 脚本。

## OCR Prompt

```text
您的任务是将文件内容转录并格式化为 markdown。您的目标是创建一个结构良好、可读性强的 markdown 文档，该文档准确表示原始内容，同时添加适当的格式和标签。

请按照以下说明完成任务：
1. 仔细阅读整个文件内容。
2. 将内容转录为 markdown 格式，密切关注现有的格式和结构。
3. 如果您在原始内容中发现任何不清楚的格式，请自行判断添加适当的 markdown 格式以提高可读性和结构。
4. 对于表格、标题和目录，请添加以下标签：
   - 表格：将整个表格括在 [TABLE] 和 [/TABLE] 标签中。如果表格内容在下一页继续，请合并表格内容。
   - 标题（在每页开头重复的完整字符串）：括在 markdown 文件内的 [HEADER] 和 [/HEADER] 标签中。
   - 目录：用 [TOC] 和 [/TOC] 标签括起来
5. 转录表格时：
   - 如果表格跨越多页，请将内容合并为一个连贯的表格。
   - 使用适当的 markdown 表格格式，表格结构使用竖线 (|) 和连字符 (-)。
6. 不要在转录中包含分页符。
7. 保持文档的逻辑流程和结构，确保使用 markdown 标题正确格式化章节和小节（# 表示主标题，## 表示副标题等）。
8. 根据需要对其他格式元素（如粗体、斜体、列表和代码块）使用适当的 markdown 语法。
10. 仅返回 markdown 格式的解析内容，包括表格、标题和目录的指定标签。
```

## 依赖

```bash
pip install requests openpyxl beautifulsoup4
```

扫描版/图片型 PDF 需要额外安装 PyMuPDF：

```bash
pip install pymupdf
```

同时需要安装poppler-utils（提供 pdftoppm 命令，用于将 PDF 转为图片）

## 使用方式

```bash
python scripts/pdf_ocr_to_excel.py --input "path/to/input.pdf" --output "path/to/output.xlsx"
```

可选参数：

- `--base-url`: 自定义 minerU API 基础地址（默认：`http://172.16.235.50:8200/`）
- `--token`: minerU API token；也可通过环境变量 `MINERU_TOKEN` 传入
- `--markdown-only`: 仅输出解析后的 markdown，不生成 Excel

使用示例：

```bash
# 普通 PDF
python scripts/pdf_ocr_to_excel.py --input "doc.pdf" --output "doc.xlsx"
```

## API 调用说明

脚本与 minerU 服务交互时，使用如下接口：

- **接口地址**：`/api/parse_to_markdown`
- **请求方法**：POST
- **请求格式**：multipart/form-data
- **请求参数**：
  - `files`：图片文件数组（数组格式），每页 PDF 对应一张图片
- **响应结构**：`MarkdownResponse`
  - `success`：是否成功（bool）
  - `markdown`：解析后的 Markdown 文本（string）
  - `filenames`：文件名列表（array<string>）

脚本内部处理流程：

1. 读取 PDF 文件
2. 使用 `pdf2image.convert_from_path` 将 PDF 每页转换为图片
3. 将图片列表作为 `files` 字段，调用 `/api/parse_to_markdown`
4. 合并返回的 `markdown` 内容
5. 从合并后的结果中 **优先解析 HTML `<table>` 标签**，直接转换为二维表格；若结果是 Markdown 表格，再识别 `[TABLE]` / `[/TABLE]` 或原生 markdown 表格
6. 对异常的 `colspan` / `rowspan` 进行结构校验与修正，最后将表格写入 Excel

## 输出约定
**必须遵守约定**
- 如果 PDF 中没有表格，生成一个空 Excel 文件，并提示用户
- 一个表格一个 sheet，sheet 名用原始表格标题或者内容关键词命名 `利润总额（1-16）`、`主要经营指标完成情况（含华录）`...
- 合并单元格等复杂结构尽可能保留原值，填充到左上单元格
- markdown 中的 `[TABLE]` / `[/TABLE]`、`[HEADER]` / `[/HEADER]`、`[TOC]` / `[/TOC]` 标签会被保留并用于辅助表格定位
- 表格中如果原始输入有标题要保留原有标题
- 要保留表格边框，可以用色块来填充和区分表头单元栏等
- 表格中的空单元格会保留为空字符串，确保列数和行数与原始表格一致

## 表格检查与修正（强制步骤）

表格从 markdown 中提取出来后，**必须**经过 `scripts/excel_utils.py` 统一处理，不能直接写入 Excel。处理内容包括：

1. **标题提取**：使用 `extract_table_titles(markdown)`，从 `[TABLE]` 块上方最近的 markdown 标题/候选文本中提取表格标题，用于 sheet 命名。
2. **空表格兜底**：若未识别到任何表格，生成仅包含 `Sheet1` 的 Excel，并在 A1 单元格提示“未识别到表格，已生成空 Excel 文件。”
3. **工作表命名**：使用表格标题命名 sheet，非法字符替换为下划线，限制 31 字符，重复时自动加序号后缀。
4. **表头样式**：表头行添加浅蓝背景、加粗、居中对齐。
5. **边框与对齐**：所有单元格添加细边框，开启自动换行，列宽默认 16。
6. **复杂结构处理**：合并单元格只保留左上角值，其余位置填充空字符串，确保行列数与原始表格一致。
7. **空单元格处理**：所有 `None` 或空值统一保存为空字符串。

> **强制约束**：表格提取后的检查、修正与 Excel 写入，必须且只能使用 `scripts/excel_utils.py` 提供的 `extract_table_titles` 与 `save_tables_to_excel`，禁止在 `pdf_ocr_to_excel.py` 中另行实现保存逻辑或跳过该步骤。

## 文件结构

```
pdf_ocr_to_excel/
├── SKILL.md
└── scripts/
    ├── pdf_ocr_to_excel.py
    ├── html_table_parser.py
    └── test_api.py
```
