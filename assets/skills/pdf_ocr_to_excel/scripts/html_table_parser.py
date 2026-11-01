#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML 表格解析与结构校验模块

从 markdown 文本中解析 <table> HTML，处理异常的 rowspan/colspan，
输出结构化的二维表（单元格为字符串或 None）。

处理策略：
1. 从 markdown 文本中提取 <table>...</table> 的 HTML 片段。
2. 使用 BeautifulSoup 解析 HTML，保留每个单元格的 text、rowspan、colspan。
3. 推断标准列数：优先从完整行（所有单元格 rowspan=1 且 colspan=1）中统计列数，使用众数。
4. 对每一行，按逻辑宽度展开（sum(colspan)）。
5. 当发现某行的逻辑宽度小于标准列数时，使用动态规划（DP）根据字段画像
   将单元格对齐到标准列位，缺失位置填 None。
6. 数据区域的 rowspan 一律视为 1，不向下复制内容；多级表头单独处理。
"""

import re
from collections import Counter
from typing import List, Optional, Dict, Any, Union
from bs4 import BeautifulSoup


# 中文表头列名 -> 字段类型画像的简单映射，用于完整行信息不足时增强对齐。
_HEADER_TYPE_HINTS = {
    "编号": {"code", "integer"},
    "序号": {"code", "integer"},
    "代码": {"code"},
    "编码": {"code"},
    "名称": {"text"},
    "项目": {"text"},
    "品名": {"text"},
    "型号": {"code", "text"},
    "规格": {"code", "text"},
    "数量": {"integer", "number"},
    "金额": {"integer", "number"},
    "单价": {"integer", "number"},
    "总价": {"integer", "number"},
    "日期": {"date"},
    "时间": {"date"},
}


def _value_type(value: Optional[str]) -> str:
    """对单元格文本进行简单类型判断"""
    if value is None:
        return "empty"
    value = value.strip()
    if not value:
        return "empty"
    if re.fullmatch(r"\d+", value):
        return "integer"
    if re.fullmatch(r"\d+(\.\d+)?", value):
        return "number"
    if re.fullmatch(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}", value):
        return "date"
    if re.fullmatch(r"[A-Za-z0-9_-]+", value):
        return "code"
    return "text"


def extract_html_tables_from_markdown(markdown: str) -> List[str]:
    """从 markdown 文本中提取 <table>...</table> 的 HTML 片段"""
    tables = []
    if not markdown:
        return tables
    pattern = re.compile(r"<table\b[^>]*>(.*?)</table\s*>", re.DOTALL | re.IGNORECASE)
    for match in pattern.finditer(markdown):
        full = match.group(0)
        tables.append(full)
    return tables


def parse_html_table(html: str) -> List[dict]:
    """解析 HTML 表格，返回每行的单元格信息列表

    数据区 rowspan 视为 1，不向下复制；多级表头单独处理。
    """
    soup = BeautifulSoup(html, "html.parser")
    result = []
    for tr in soup.select("tr"):
        cells = []
        for td in tr.find_all(["td", "th"], recursive=False):
            text = td.get_text(" ", strip=True)
            # 保留原始 rowspan 和 colspan
            try:
                rowspan = max(1, int(td.get("rowspan", 1) or 1))
            except (TypeError, ValueError):
                rowspan = 1
            try:
                colspan = max(1, int(td.get("colspan", 1) or 1))
            except (TypeError, ValueError):
                colspan = 1
            cells.append({
                "text": text,
                "rowspan": rowspan,
                "colspan": colspan,
            })
        result.append({"cells": cells})
    return result

def _split_table_lines(markdown: str) -> List[List[List[str]]]:
    """从 [TABLE]...[/TABLE] 块中提取 Markdown 表格（二维字符串）"""
    tables = []
    pattern = re.compile(r"\[TABLE\]\s*(.*?)\s*\[/TABLE\]", re.DOTALL | re.IGNORECASE)
    for match in pattern.finditer(markdown):
        block = match.group(1).strip()
        if not block:
            continue
        rows = []
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line or not line.startswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            rows.append(cells)
        # 去掉表头分隔行
        if len(rows) >= 2 and all(c in "-: \t" for c in "".join(rows[1])):
            rows = [rows[0]] + rows[2:]
        if rows:
            tables.append(rows)
    return tables


def _row_logical_width(row: dict) -> int:
    """计算一行的逻辑宽度 = sum(colspan)"""
    return sum(cell["colspan"] for cell in row["cells"])


def _infer_column_count(rows: List[dict]) -> int:
    """从完整行中推断标准列数，优先使用众数"""
    plain_widths = [
        _row_logical_width(row)
        for row in rows
        if all(cell["rowspan"] == 1 and cell["colspan"] == 1 for cell in row["cells"])
    ]
    if plain_widths:
        counter = Counter(plain_widths)
        return counter.most_common(1)[0][0]
    widths = [_row_logical_width(row) for row in rows]
    if widths:
        counter = Counter(widths)
        return counter.most_common(1)[0][0]
    return 0


def _build_profiles(rows: List[dict], column_count: int) -> List[dict]:
    """从完整行统计每列的字段类型画像"""
    profiles = [set() for _ in range(column_count)]
    for row in rows:
        if _row_logical_width(row) != column_count:
            continue
        if not all(cell["rowspan"] == 1 and cell["colspan"] == 1 for cell in row["cells"]):
            continue
        for idx, cell in enumerate(row["cells"]):
            if idx >= column_count:
                break
            profiles[idx].add(_value_type(cell["text"]))

    # 若某列完全无法从完整行推断出类型，则基于表头行的列名做弱画像。
    if rows and len(rows[0]["cells"]) == column_count and all(cell["rowspan"] == 1 and cell["colspan"] == 1 for cell in rows[0]["cells"]):
        for idx, profile in enumerate(profiles):
            if not profile:
                header_text = rows[0]["cells"][idx].get("text", "")
                if header_text in _HEADER_TYPE_HINTS:
                    profile.update(_HEADER_TYPE_HINTS[header_text])
                elif _value_type(header_text) in ("code", "integer", "number"):
                    profile.add("code")
                else:
                    profile.add("text")

    # 将表头语义与数据推断的类型合并，构建更稳定的列画像。
    for idx, profile in enumerate(profiles):
        if rows and len(rows[0]["cells"]) == column_count:
            header_text = rows[0]["cells"][idx].get("text", "")
            if header_text in _HEADER_TYPE_HINTS:
                profile.update(_HEADER_TYPE_HINTS[header_text])
    return [{"types": p or {"text"}} for p in profiles]


def _compatibility(text: Optional[str], profile: dict) -> int:
    """判断某个文本与字段画像的匹配得分"""
    current_type = _value_type(text)
    if current_type == "empty":
        return 0
    if current_type in profile["types"]:
        return 3
    return -2


def _align_cells(texts: List[str], profiles: List[dict], column_count: int) -> List[Optional[str]]:
    """用动态规划将单元格序列对齐到固定列位，允许跳过某些标准列"""
    m = len(texts)
    n = column_count
    negative_inf = float("-inf")

    dp = [[negative_inf] * (n + 1) for _ in range(m + 1)]
    previous = [[None] * (n + 1) for _ in range(m + 1)]

    dp[0][0] = 0

    for col in range(n):
        if dp[0][col] != negative_inf:
            dp[0][col + 1] = dp[0][col] - 1
            previous[0][col + 1] = (0, col, "empty")

    for i in range(m + 1):
        for col in range(n):
            if dp[i][col] == negative_inf:
                continue

            # 跳过当前标准列（视为空）
            empty_score = dp[i][col] - 1
            if empty_score > dp[i][col + 1]:
                dp[i][col + 1] = empty_score
                previous[i][col + 1] = (i, col, "empty")

            # 将当前文本放入当前标准列
            if i < m:
                match_score = dp[i][col] + _compatibility(texts[i], profiles[col])
                if match_score > dp[i + 1][col + 1]:
                    dp[i + 1][col + 1] = match_score
                    previous[i + 1][col + 1] = (i, col, "match")

    if dp[m][n] == negative_inf:
        result = [None] * n
        for i, t in enumerate(texts[:n]):
            result[i] = t
        return result

    result = [None] * n
    i, col = m, n
    while i > 0 or col > 0:
        step = previous[i][col]
        if step is None:
            break
        prev_i, prev_col, action = step
        if action == "match":
            result[prev_col] = texts[prev_i]
        i, col = prev_i, prev_col

    # 当相邻两列画像都允许 text 且匹配得分相同时，DP 可能把文本放到右侧。
    # 这里做后处理：对明显应该左对齐的文本，尝试往更左侧的空位移动，
    # 优先保持“从左到右填充”的直观顺序。
    result = _shift_left_for_same_type(result, profiles)

    return result


def _shift_left_for_same_type(result: List[Optional[str]], profiles: List[dict]) -> List[Optional[str]]:
    """当某列空着而左侧同类型列存在文本时，把文本向左移动，保持顺序"""
    n = len(result)
    for col in range(1, n):
        if result[col] is None:
            continue
        # 向左找最近的空位，仅当目标列与当前列画像兼容时移动
        for target in range(col - 1, -1, -1):
            if result[target] is not None:
                break
            if _compatibility(result[col], profiles[target]) >= 0:
                result[target] = result[col]
                result[col] = None
                break
    return result


def _expand_merged_cells(rows: List[dict]) -> List[List[str]]:
    """把 HTML 表格的 rowspan/colspan 展开为二维表。

    合并单元格的值仅保留在左上单元格，其余位置填充空字符串，
    从而保证最终行列数与原始表格一致。
    """
    if not rows:
        return []

    # 计算最大逻辑列数
    max_cols = max(
        (sum(cell["colspan"] for cell in row["cells"]) for row in rows),
        default=0,
    )
    if max_cols == 0:
        return []

    grid: List[List[str]] = []
    occupied: List[List[bool]] = []

    row_idx = 0
    for raw_row in rows:
        # 确保当前行存在
        while row_idx >= len(grid):
            grid.append([""] * max_cols)
            occupied.append([False] * max_cols)

        col = 0
        for cell in raw_row["cells"]:
            # 跳过被上方 rowspan 占用的列
            while col < max_cols and occupied[row_idx][col]:
                col += 1
            if col >= max_cols:
                break

            text = cell["text"]
            colspan = min(cell["colspan"], max_cols - col)
            rowspan = cell["rowspan"]

            # 在左上角单元格保留原值
            grid[row_idx][col] = text

            # 标记整个合并区域为已占用
            for r in range(row_idx, row_idx + rowspan):
                while len(grid) <= r:
                    grid.append([""] * max_cols)
                    occupied.append([False] * max_cols)
                for c in range(col, col + colspan):
                    occupied[r][c] = True

            col += colspan

        row_idx += 1

    return grid


def normalize_html_table_rows(rows: List[dict]) -> List[List[Optional[str]]]:
    """将解析出的 HTML 表格行规范化为二维表"""
    if not rows:
        return []

    # 优先使用合并单元格展开逻辑，保留原值到左上单元格
    expanded = _expand_merged_cells(rows)
    if expanded:
        return expanded

    # 退化场景：按字段画像做 DP 对齐
    column_count = _infer_column_count(rows)
    if column_count == 0:
        column_count = max((_row_logical_width(row) for row in rows), default=0)

    profiles = _build_profiles(rows, column_count)

    normalized_rows = []
    for row in rows:
        cells = row["cells"]
        logical_texts = [cell["text"] for cell in cells]

        if len(logical_texts) < column_count:
            aligned = _align_cells(logical_texts, profiles, column_count)
        elif len(logical_texts) > column_count:
            aligned = logical_texts[:column_count]
        else:
            aligned = logical_texts

        normalized_rows.append([v if v is not None else "" for v in aligned])

    return normalized_rows

def _extract_inline_tables(markdown: str) -> List[List[List[str]]]:
    """从原生 Markdown 表格（|...|）中提取二维字符串"""
    tables = []
    if not markdown:
        return tables
    pattern = re.compile(r"(\|[^\n]*\|\n\|[-:\s|]+\|\n\|[^\n]*\|\n)", re.MULTILINE)
    for match in pattern.finditer(markdown):
        table_text = match.group(1)
        rows = []
        for raw_line in table_text.strip().splitlines():
            line = raw_line.strip()
            if not line.startswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            rows.append(cells)
        if len(rows) >= 2:
            rows = [rows[0]] + rows[2:]
        if rows:
            tables.append(rows)
    return tables

def html_table_to_2d(html: str) -> List[List[str]]:
    """对外接口：HTML table -> 二维字符串表"""
    rows = parse_html_table(html)
    return normalize_html_table_rows(rows)

def html_table_to_structured(html: str) -> List[List[Optional[Dict[str, Union[str, int]]]]]:
    """
    将 HTML 表格解析为二维结构化网格，每个元素为 {'value': str, 'rowspan': int, 'colspan': int}
    仅左上角单元格有值，其余被合并区域为 None。
    """
    rows = parse_html_table(html)
    if not rows:
        return []
    max_cols = max((sum(cell['colspan'] for cell in row['cells']) for row in rows), default=0)
    if max_cols == 0:
        return []
    grid = [[None for _ in range(max_cols)] for _ in range(len(rows))]
    occupied = [[False for _ in range(max_cols)] for _ in range(len(rows))]
    for i, row in enumerate(rows):
        col = 0
        for cell in row['cells']:
            while col < max_cols and occupied[i][col]:
                col += 1
            if col >= max_cols:
                break
            rs, cs = cell['rowspan'], cell['colspan']
            for r in range(i, min(i+rs, len(grid))):
                for c in range(col, min(col+cs, max_cols)):
                    occupied[r][c] = True
            grid[i][col] = {'value': cell['text'], 'rowspan': rs, 'colspan': cs}
            col += cs
    return grid

# ---------- 修改 extract_tables_from_markdown（优先返回结构化） ----------
def extract_tables_from_markdown(markdown: str) -> List[Union[List[List[str]], List[List[Optional[Dict]]]]]:
    """
    从 markdown 中提取所有表格。
    返回列表，每个元素：
      - 如果是 HTML 表格：为结构化网格（含合并信息）
      - 如果是 Markdown 表格：为二维字符串列表（无合并）
    """
    if not markdown:
        return []
    # 1. 优先解析 HTML <table> 标签
    html_fragments = extract_html_tables_from_markdown(markdown)
    if html_fragments:
        structured_tables = []
        for html in html_fragments:
            grid = html_table_to_structured(html)
            if grid:
                structured_tables.append(grid)
        if structured_tables:
            return structured_tables
    # 2. 解析 [TABLE]...[/TABLE] 包裹的 markdown 表格（返回二维字符串）
    table_blocks = _split_table_lines(markdown)
    if table_blocks:
        return table_blocks
    # 3. 回退到原生 markdown 表格
    return _extract_inline_tables(markdown)