#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF OCR 表格提取到 Excel
调用 minerU /api/process（process_type=mineru）或 /api/parse_to_markdown 接口解析 PDF，
并将识别到的表格导出为 Excel。
"""

import argparse
import json
import mimetypes
import os
import re
import sys
import tempfile
import time
import uuid
from contextlib import ExitStack
from pathlib import Path
from typing import List, Tuple, Union
import subprocess
import requests
import openpyxl
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).parent))
from html_table_parser import extract_html_tables_from_markdown, html_table_to_2d, extract_tables_from_markdown
from excel_utils import extract_table_titles, save_tables_to_excel

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:  # pragma: no cover
    PYMUPDF_AVAILABLE = False
    fitz = None


# minerU API 配置，可通过命令行覆盖
MINERU_BASE_URL = "http://172.16.235.50:8200/"  # 默认本地服务地址
PARSE_ENDPOINT = "/api/parse_to_markdown"
PROCESS_ENDPOINT = "/api/process"

# 接口支持的后缀映射
SUPPORTED_EXTS = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
}


def get_token(cli_token: str = None) -> str:
    """从命令行参数或环境变量读取 minerU token"""
    if cli_token:
        return cli_token
    return os.environ.get("MINERU_TOKEN", "")


def _normalize_filename(name: str, fallback_ext: str = ".pdf") -> Tuple[str, str]:
    """
    确保上传文件名带有正确扩展名，返回 (filename, mime_type)。
    minerU 后端会根据扩展名判断文件类型，无扩展名可能导致解析失败。
    """
    path = Path(name)
    ext = path.suffix.lower()
    if not ext or ext not in SUPPORTED_EXTS:
        ext = fallback_ext
        filename = path.name + ext
    else:
        filename = path.name

    mime_type = SUPPORTED_EXTS.get(ext) or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return filename, mime_type

class MinerUAPIError(Exception):
    pass

def _open_files_for_upload(file_paths: List[str], stack: ExitStack):
    """打开文件并构造 requests 的 files 参数"""
    files = []
    for path in file_paths:
        f = stack.enter_context(open(path, "rb"))
        filename, mime_type = _normalize_filename(str(path))
        files.append(("files", (filename, f, mime_type)))
    return files


def _call_parse_api(file_paths: List[str], base_url: str, token: str = None) -> dict:
    """
    调用 minerU /api/parse_to_markdown 接口。
    file_paths 可以是单个文件路径或路径列表。
    """
    url = (base_url or MINERU_BASE_URL).rstrip("/") + PARSE_ENDPOINT
    auth_token = get_token(token)
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    if isinstance(file_paths, (str, Path)):
        file_paths = [file_paths]

    with ExitStack() as stack:
        files = _open_files_for_upload(file_paths, stack)
        response = requests.post(url, files=files, headers=headers, timeout=300)

    response.raise_for_status()
    data = response.json()

    if isinstance(data, dict) and not data.get("success"):
        message = data.get("message", "")
        detail = json.dumps(data, ensure_ascii=False)
        raise MinerUAPIError(f"minerU 解析失败: {message}\n详情: {detail}")

    return data


def _call_process_api(file_paths: List[str], base_url: str, token: str = None, process_type: str = "mineru") -> dict:
    """
    调用 minerU /api/process 接口。
    需要传入 conversation_id 和 files，支持 process_type 参数。
    """
    url = (base_url or MINERU_BASE_URL).rstrip("/") + PROCESS_ENDPOINT
    auth_token = get_token(token)
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    if isinstance(file_paths, (str, Path)):
        file_paths = [file_paths]

    conversation_id = str(uuid.uuid4())
    data = {
        "conversation_id": conversation_id,
        "process_type": process_type,
    }

    with ExitStack() as stack:
        files = _open_files_for_upload(file_paths, stack)
        response = requests.post(url, data=data, files=files, headers=headers, timeout=300)

    response.raise_for_status()
    resp_data = response.json()

    if isinstance(resp_data, dict) and not resp_data.get("success"):
        message = resp_data.get("message", "")
        detail = json.dumps(resp_data, ensure_ascii=False)
        raise MinerUAPIError(f"minerU /api/process 失败: {message}\n详情: {detail}")

    # 将 conversation_id 也返回，方便后续跟踪
    if isinstance(resp_data, dict):
        resp_data["_conversation_id"] = conversation_id

    return resp_data


def _call_api_with_fallback(file_paths: List[str], base_url: str, token: str = None) -> dict:
    """
    优先调用 /api/process，失败则回退到 /api/parse_to_markdown。
    """
    errors = []

    try:
        return _call_process_api(file_paths, base_url, token)
    except Exception as e:
        errors.append(f"/api/process 失败: {e}")
        # 等待一小段时间再尝试回退
        time.sleep(1)
        try:
            return _call_parse_api(file_paths, base_url, token)
        except Exception as e2:
            errors.append(f"/api/parse_to_markdown 失败: {e2}")
            raise MinerUAPIError("minerU 接口调用失败:\n" + "\n".join(errors))

def _pdf_pages_to_images(pdf_path: str, dpi: int = 200) -> List[str]:
    """使用 pdftoppm 将 PDF 每页转为 PNG 图片"""
    temp_dir = tempfile.mkdtemp(prefix="pdf_ocr_")
    base_name = os.path.join(temp_dir, "page")
    cmd = ['pdftoppm', '-png', '-r', str(dpi), pdf_path, base_name]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"pdftoppm 执行失败: {e.stderr.decode()}")
    image_paths = []
    for fname in sorted(os.listdir(temp_dir)):
        if fname.endswith('.png'):
            image_paths.append(os.path.join(temp_dir, fname))
    if not image_paths:
        raise RuntimeError("pdftoppm 未生成任何图片")
    return image_paths

def parse_pdf(pdf_path: str, base_url: str = None, token: str = None, image_mode: bool = False, auto_detect: bool = False) -> dict:
    """
    调用 minerU 接口解析 PDF，返回解析结果。

    模式说明：
    - image_mode=True：强制把 PDF 每页转为图片，逐页识别后合并。
    - 默认：直接上传原 PDF 识别。
    """
    path_obj = Path(pdf_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")
    
    # 检查 pdftoppm 是否可用
    import shutil
    if shutil.which('pdftoppm') is None:
        raise RuntimeError(
            "未找到 pdftoppm 命令，请安装 poppler-utils。\n"
            "Ubuntu/Debian: sudo apt install poppler-utils\n"
            "CentOS/RHEL: sudo yum install poppler-utils\n"
            "Windows: 从 https://github.com/oschwartz10612/poppler-windows/releases 下载并添加到 PATH"
        )

    # 前置校验：尝试用 PyMuPDF 检查 PDF 是否可读
    if PYMUPDF_AVAILABLE:
        try:
            doc = fitz.open(pdf_path)
            if len(doc) == 0:
                raise ValueError("PDF 文件为空或无法读取页面")
            doc.close()
        except Exception as e:
            raise RuntimeError(f"PDF 文件损坏或无法读取: {e}")
    else:
        print("警告: PyMuPDF 未安装，无法校验 PDF，继续尝试...")

    temp_dir = tempfile.mkdtemp(prefix="pdf_ocr_")
    try:
        print(f"正在将 PDF 每页渲染为图片（DPI=200）...")
        image_paths = _pdf_pages_to_images(str(path_obj), dpi=200)
        print(f"共 {len(image_paths)} 页，开始逐页 OCR...")

        markdown_parts = []
        for idx, image_path in enumerate(image_paths, start=1):
            print(f"正在处理第 {idx} 页...")
            result = _call_api_with_fallback(image_path, base_url, token)
            md = get_markdown_from_result(result)
            if md:
                markdown_parts.append(md)
            else:
                print(f"警告: 第 {idx} 页未返回有效 markdown")

        combined_markdown = "\n\n".join(markdown_parts)
        print("所有页面处理完成，开始提取表格...")
        return {"markdown": combined_markdown}
    finally:
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


def get_markdown_from_result(result: dict) -> str:
    """
    兼容多种返回结构，提取 markdown 字符串。
    支持的结构：
    - /api/parse_to_markdown: {success, message, markdown, filenames}
    - /api/process: {success, message, conversation_id, summary, document_chunks}
      document_chunks 数组中每个对象可能有 content / markdown / text 字段
    """
    if not isinstance(result, dict):
        return ""

    # 直接包含 markdown 字段
    if "markdown" in result:
        return result["markdown"]

    # result.markdown / data.markdown
    for key in ("result", "data"):
        value = result.get(key)
        if isinstance(value, dict) and "markdown" in value:
            return value["markdown"]
        if isinstance(value, str):
            return value

    # /api/process 的 document_chunks
    document_chunks = result.get("document_chunks")
    if isinstance(document_chunks, list):
        parts = []
        for chunk in document_chunks:
            if not isinstance(chunk, dict):
                continue
            for field in ("markdown", "content", "text"):
                if field in chunk and chunk[field]:
                    parts.append(str(chunk[field]))
                    break
        combined = "\n\n".join(parts)
        if combined:
            return combined

    return ""


def _split_table_lines(markdown: str) -> List[List[str]]:
    """
    将 markdown 文本中符合 [TABLE]...[/TABLE] 包裹的表格块提取出来，
    返回每张表格的所有行（包含表头行和分隔行）。
    """
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


def _extract_inline_tables(markdown: str) -> List[List[List[str]]]:
    """
    从 markdown 文本中提取所有 markdown 原生表格。
    返回: tables[table_index][row_index][cell_value]
    """
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


def _extract_html_tables(markdown: str) -> List[List[List[str]]]:
    """
    从 markdown 文本中解析 <table> HTML 标签，转换为二维表格。
    """
    tables = []
    html_tables = extract_html_tables_from_markdown(markdown)
    for html in html_tables:
        try:
            table_2d = html_table_to_2d(html)
            if table_2d:
                tables.append(table_2d)
        except Exception:
            # 解析失败时忽略单个表格
            continue
    return tables


def extract_tables_from_markdown(markdown: str) -> List[List[List[str]]]:
    """
    从 markdown 文本中提取所有表格。
    优先解析 <table> HTML 标签；
    其次识别 [TABLE]...[/TABLE] 包裹的 markdown 表格；
    如果 [TABLE] 标签未匹配到任何表格，则回退到原生 markdown 表格解析。
    """
    if not markdown:
        return []

    # 1. 优先解析 HTML <table> 标签
    html_tables = _extract_html_tables(markdown)
    if html_tables:
        return html_tables

    # 2. 解析 [TABLE]...[/TABLE] 包裹的 markdown 表格
    tables = _split_table_lines(markdown)
    valid_tables = [t for t in tables if len(t) > 0]
    if valid_tables:
        return valid_tables

    # 3. 回退到原生 markdown 表格解析
    return _extract_inline_tables(markdown)




def main():
    parser = argparse.ArgumentParser(description="PDF OCR 表格提取到 Excel")
    parser.add_argument("--input", "-i", required=True, help="输入 PDF 文件路径")
    parser.add_argument("--output", "-o", required=True, help="输出 Excel 文件路径")
    parser.add_argument("--base-url", default=None, help="minerU API 基础地址")
    parser.add_argument("--token", default=None, help="minerU API token；也可通过环境变量 MINERU_TOKEN 传入")
    parser.add_argument("--markdown-only", action="store_true", help="仅输出解析后的 markdown")
    parser.add_argument("--image-mode", action="store_true", help="强制图片模式：把 PDF 每页转为图片识别（需安装 PyMuPDF）")
    parser.add_argument("--auto-detect", action="store_true", help="已废弃，将被忽略")
    args = parser.parse_args()

    # 强制 image_mode 为 True（无论用户指定与否）
    result = parse_pdf(args.input, base_url=args.base_url, token=args.token, image_mode=True, auto_detect=False)
    markdown = get_markdown_from_result(result)

    if args.markdown_only:
        print(markdown)
        return

    tables = extract_tables_from_markdown(markdown)
    table_titles = extract_table_titles(markdown)
    # save_tables_to_excel 内部会调用 validate_and_fix_table
    save_tables_to_excel(tables, args.output, table_titles)

    print(f"提取到 {len(tables)} 个表格，已保存至: {args.output}")



if __name__ == "__main__":
    main()
