# 格式规范文件说明 (spec-format.md)

格式规范文件是一个 JSON 文档，定义了 docx 文档所有格式要求的唯一真相源。

## 文件结构

```json
{
  "version": "1.0",
  "meta": { ... },
  "page": { ... },
  "fonts": { ... },
  "sizes": { ... },
  "spacing": { ... },
  "alignment": { ... },
  "special_sections": { ... },
  "validation": { ... }
}
```

## 各节说明

### meta — 元信息

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 规范名称 |
| description | string | 规范描述 |
| author | string | 作者 |

### page — 页面设置

| 字段 | 类型 | 合法值 | 说明 |
|------|------|--------|------|
| size | string | A4, A3, Letter, Legal | 纸张尺寸 |
| orientation | string | portrait, landscape | 纸张方向 |
| margin_top_cm | number | 0-10 | 上边距(cm) |
| margin_bottom_cm | number | 0-10 | 下边距(cm) |
| margin_left_cm | number | 0-10 | 左边距(cm) |
| margin_right_cm | number | 0-10 | 右边距(cm) |
| footer_distance_cm | number | 0-10 | 页脚距离(cm) |

### fonts — 字体配置

**核心设计**：每个元素配置 `{ cjk, latin }` 字体对。

| 键 | 适用区域 |
|----|----------|
| cover_title | 封面标题 |
| cover_subtitle | 封面副标题 |
| cover_info | 封面信息（作者/日期等） |
| body | 正文 |
| h1 / h2 / h3 / h4 | 各级标题 |
| toc_title | 目录标题 |
| toc_body | 目录正文 |
| revision_title | 修订记录标题 |
| revision_header | 修订记录表头 |
| revision_body | 修订记录表体 |
| page_number | 页码 |
| table_caption | 表格标题 |
| figure_caption | 图表标题 |

示例：
```json
"body": { "cjk": "仿宋_GB2312", "latin": "Times New Roman" }
```

运行时自动设置：
- `w:eastAsia` = cjk 值
- `w:ascii` = latin 值
- `w:hAnsi` = latin 值

### sizes — 字号

所有值单位为 pt（磅），合法范围 1-128。

### spacing — 间距

| 字段 | 说明 |
|------|------|
| body_line_spacing_pt | 正文行距(pt) |
| title_line_spacing_pt | 标题行距(pt) |
| first_line_indent_chars | 首行缩进字符数 |
| paragraph_before_pt | 段前间距(pt) |
| paragraph_after_pt | 段后间距(pt) |

### alignment — 对齐

合法值：`left`, `center`, `right`, `both`, `奇偶分页`

### special_sections — 特殊区域

#### revision_history — 修订记录

| 字段 | 说明 |
|------|------|
| enabled | 是否启用 |
| detection_keywords | 识别关键词列表 |
| table_columns | 表格列名 |
| column_widths_cm | 列宽(cm) |
| header_bold | 表头加粗 |
| header_shading | 表头背景色(十六进制) |
| border_style | 边框样式 |
| row_height_cm | 行高(cm) |

#### toc — 目录

| 字段 | 说明 |
|------|------|
| enabled | 是否启用 |
| detection_keywords | 识别关键词列表 |
| auto_generate | 是否自动生成目录 |

#### cover — 封面

| 字段 | 说明 |
|------|------|
| enabled | 是否启用 |
| detection_by | 检测方式 |
| max_pages | 最大页数 |

### validation — 校验配置

| 字段 | 说明 |
|------|------|
| strict_mode | 严格模式 |
| max_retries | 最大重试次数 |
| checks | 校验项列表 |

## 自定义规范

```bash
# 从默认模板创建
python scripts/cli.py spec-init --template default -o my_spec.json

# 编辑 my_spec.json 调整字体、边距等
# 使用自定义规范
python scripts/cli.py format -i in.docx -s my_spec.json -o out.docx
```
