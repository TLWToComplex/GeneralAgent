#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF OCR 表格提取到 Excel 的辅助工具模块。

功能：
- 从 markdown 文本中提取表格标题。
- 将表格列表保存到 Excel，支持空表格提示、sheet 命名、表头样式和边框。
"""

import re
from pathlib import Path
from typing import List
from typing import List, Optional, Union, Dict

from openpyxl import Workbook
from openpyxl.styles import Border, Side, PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter


# Excel sheet 名非法字符
_SHEET_NAME_INVALID = re.compile(r"[\\/*?:\[\]]")


def _clean_sheet_name(name: str, fallback: str = "Sheet") -> str:
    """清理 sheet 名，限制 31 字符并替换非法字符"""
    if not name:
        return fallback
    name = str(name).strip()
    name = _SHEET_NAME_INVALID.sub("_", name)
    name = name[:31].strip()
    if not name:
        return fallback
    return name


def extract_table_titles(markdown: str) -> List[str]:
    """
    遍历 [TABLE] 块，提取每个表格上方最近的候选标题。
    返回与表格顺序一致的标题列表。
    """
    if not markdown:
        return []

    pattern = re.compile(r"\[TABLE\]\s*(.*?)\s*\[/TABLE\]", re.DOTALL | re.IGNORECASE)
    titles = []
    for idx, m in enumerate(pattern.finditer(markdown), start=1):
        before = markdown[: m.start()]
        candidate = _find_nearest_title(before)
        if candidate:
            titles.append(candidate)
        else:
            titles.append(f"表格{idx}")
    return titles


def _find_nearest_title(markdown_before: str, max_lines: int = 5) -> str:
    """从 [TABLE] 标签前的文本中提取表格标题候选"""
    lines = [line.strip() for line in markdown_before.splitlines() if line.strip()]
    candidate = ""
    for line in lines[-max_lines:]:
        # 过滤目录、页眉标签
        if line.startswith("[TOC]") or line.startswith("[/TOC]"):
            continue
        if line.startswith("[HEADER]") or line.startswith("[/HEADER]"):
            continue
        # 标题行优先
        if line.startswith("#"):
            candidate = line.lstrip("#").strip()
            break
        candidate = line

    # 清理 markdown 粗体、斜体标记
    candidate = re.sub(r"\*+", "", candidate).strip()
    return candidate


def _detect_header_rows(table: List[List[str]]) -> int:
    """
    简单启发式判断表头行数：
    - 第一行与后续行内容类型差异较大时认为第一行是表头。
    返回表头行数（至少 1 行，若表格为空则 0）。
    """
    if not table:
        return 0
    if len(table) <= 1:
        return 1

    # 取第一行，若包含常见的表头关键词则认为是表头
    header_keywords = {"项目", "名称", "序号", "编号", "单位", "金额", "日期", "合计", "总计"}
    first_row = [str(cell).strip() for cell in table[0]]
    if any(keyword in cell for cell in first_row for keyword in header_keywords):
        return 1

    # 若第二行与第一行类型差异较大（第一行多为文本，第二行开始出现数字），也认为是表头
    def _is_number(value: str) -> bool:
        v = value.replace(",", "").replace("%", "").strip()
        try:
            float(v)
            return True
        except ValueError:
            return False

    second_row = [str(cell).strip() for cell in table[1] if str(cell).strip()]
    if second_row and all(_is_number(v) for v in second_row[:3]):
        return 1

    return 1


def _col_letter(col_idx: int) -> str:
    """将列序号转换为 Excel 列字母"""
    from openpyxl.utils import get_column_letter
    return get_column_letter(col_idx)



def validate_and_fix_table(table: List[List[str]]) -> List[List[str]]:
    """
    校验并修复二维表格，确保每行长度一致（用空字符串补齐）。
    若表格为空，返回空列表。
    若某行长度超出最大列宽，截断。
    """
    if not table:
        return []
    # 计算最大列数
    max_cols = max((len(row) for row in table), default=0)
    if max_cols == 0:
        return []
    fixed = []
    for row in table:
        if len(row) < max_cols:
            # 补齐空字符串
            fixed.append(row + [""] * (max_cols - len(row)))
        elif len(row) > max_cols:
            # 截断多余列（通常不会发生，但以防万一）
            fixed.append(row[:max_cols])
        else:
            fixed.append(row)
    # 检查所有单元格是否为字符串，若 None 则转为空字符串
    fixed = [[str(cell) if cell is not None else "" for cell in row] for row in fixed]
    return fixed

# def save_tables_to_excel(
#     tables: List[List[List[str]]],
#     output_path: str,
#     table_titles: List[str] = None,
#     empty_prompt: str = "未识别到表格，已生成空 Excel 文件。",
# ):
#     """
#     将表格列表保存到 Excel，每个表格一个 sheet。
#     写入前会自动调用 validate_and_fix_table 进行结构修复。
#     """
#     output_path = Path(output_path)
#     output_path.parent.mkdir(parents=True, exist_ok=True)

#     wb = Workbook()
#     wb.remove(wb.active)

#     if not tables:
#         ws = wb.create_sheet(title="Sheet1")
#         ws["A1"] = empty_prompt
#         ws["A1"].font = Font(bold=True, color="FF0000")
#         ws.column_dimensions["A"].width = min(len(empty_prompt) + 2, 80)
#         wb.save(output_path)
#         return

#     thin_side = Side(style="thin", color="000000")
#     thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
#     header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

#     for idx, raw_table in enumerate(tables, start=1):
#         # 先校验并修复表格
#         table = validate_and_fix_table(raw_table)
#         if not table:
#             # 如果修复后为空，跳过该表格（或创建空 sheet？此处选择跳过，但会记录）
#             continue

#         title = table_titles[idx - 1] if table_titles and idx - 1 < len(table_titles) else None
#         if not title:
#             title = f"表格{idx}"

#         sheet_name = _clean_sheet_name(title, fallback=f"Sheet{idx}")
#         if sheet_name in wb.sheetnames:
#             sheet_name = _clean_sheet_name(f"{title}_{idx}", fallback=f"Sheet{idx}")
#         if sheet_name in wb.sheetnames:
#             sheet_name = f"Sheet{idx}"
#         ws = wb.create_sheet(title=sheet_name)

#         header_rows = _detect_header_rows(table)

#         for r_idx, row in enumerate(table, start=1):
#             for c_idx, value in enumerate(row, start=1):
#                 cell_value = "" if value is None else str(value)
#                 cell = ws.cell(row=r_idx, column=c_idx, value=cell_value)
#                 cell.border = thin_border
#                 cell.alignment = Alignment(vertical="center", wrap_text=True)
#                 if r_idx <= header_rows:
#                     cell.fill = header_fill
#                     cell.font = Font(bold=True)
#                     cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

#         max_cols = max((len(r) for r in table), default=0)
#         for col_idx in range(1, max_cols + 1):
#             col_letter = _col_letter(col_idx)
#             ws.column_dimensions[col_letter].width = 16

#     wb.save(output_path)
def save_tables_to_excel(
    tables: List[Union[List[List[str]], List[List[Optional[Dict]]]]],
    output_path: str,
    table_titles: List[str] = None,
    empty_prompt: str = "未识别到表格，已生成空 Excel 文件。",
):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    wb.remove(wb.active)

    if not tables:
        ws = wb.create_sheet("Sheet1")
        ws["A1"] = empty_prompt
        ws["A1"].font = Font(bold=True, color="FF0000")
        ws.column_dimensions["A"].width = min(len(empty_prompt) + 2, 80)
        wb.save(output_path)
        return

    thin_side = Side(style="thin", color="000000")
    thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

    for idx, table in enumerate(tables, start=1):
        if not table:
            continue

        # 判断是否为结构化表格（含合并信息）
        is_structured = table and isinstance(table[0][0], dict)

        # 提取 sheet 名
        title = table_titles[idx-1] if table_titles and idx-1 < len(table_titles) else f"表格{idx}"
        sheet_name = _clean_sheet_name(title, f"Sheet{idx}")
        if sheet_name in wb.sheetnames:
            sheet_name = _clean_sheet_name(f"{title}_{idx}", f"Sheet{idx}")
        if sheet_name in wb.sheetnames:
            sheet_name = f"Sheet{idx}"
        ws = wb.create_sheet(sheet_name)

        if is_structured:
            # ------ 处理结构化表格（HTML 表格） ------
            rows = len(table)
            cols = len(table[0]) if rows > 0 else 0
            header_rows = _detect_header_rows(table)  # 通常为1

            for r in range(rows):
                for c in range(cols):
                    cell_obj = table[r][c]
                    if cell_obj is None:
                        continue  # 被合并区域，跳过
                    value = cell_obj.get('value', '') or ''
                    excel_cell = ws.cell(row=r+1, column=c+1, value=value)
                    excel_cell.border = thin_border
                    excel_cell.alignment = Alignment(vertical='center', horizontal='center' if r < header_rows else 'left', wrap_text=True)
                    if r < header_rows:
                        excel_cell.fill = header_fill
                        excel_cell.font = Font(bold=True)
                    # 应用合并
                    rs = cell_obj.get('rowspan', 1)
                    cs = cell_obj.get('colspan', 1)
                    if rs > 1 or cs > 1:
                        ws.merge_cells(start_row=r+1, start_column=c+1, end_row=r+rs, end_column=c+cs)

            # 列宽
            for c in range(1, cols+1):
                ws.column_dimensions[get_column_letter(c)].width = 16

        else:
            # ------ 处理普通二维表格（Markdown） ------
            fixed_table = validate_and_fix_table(table)
            if not fixed_table:
                continue
            header_rows = _detect_header_rows(fixed_table)
            for r, row in enumerate(fixed_table, start=1):
                for c, value in enumerate(row, start=1):
                    cell = ws.cell(row=r, column=c, value=value)
                    cell.border = thin_border
                    cell.alignment = Alignment(vertical='center', wrap_text=True)
                    if r <= header_rows:
                        cell.fill = header_fill
                        cell.font = Font(bold=True)
                        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            max_cols = max((len(r) for r in fixed_table), default=0)
            for c in range(1, max_cols+1):
                ws.column_dimensions[get_column_letter(c)].width = 16

    wb.save(output_path)