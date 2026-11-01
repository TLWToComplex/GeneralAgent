"""docio.py — 格式无关的文档读取层。

本模块把「要求清单」和「文件内容摘要」从具体格式里解耦出来，
让 check_completeness.py 不必关心用户给的是 DOCX、XLSX 还是 PDF。

支持：
    docx  — 由 check_completeness.py 现有的 XML 逻辑读取（本模块只负责识别与预览）
    xlsx  — openpyxl（read_only + data_only）
    pdf   — pdfplumber（文本型 PDF）；扫描件不支持，会给出可操作报错

依赖策略：
    所有第三方库都在函数内部 import，缺失时抛 RuntimeError 并给出安装/替代方案，
    不会让整个脚本 import 阶段就崩掉。

边界与约定：
    * 合并单元格：openpyxl 的 data_only=True 只在左上角有值，与 DOCX 语义一致，不做二次填充。
    * 安全：处理 ZIP 成员内容时只接受 bytes（BytesIO），绝不把不可信成员落盘。
    * 阶段（stage）：xlsx 用 sheet 名；pdf 用表格上方的标题行；docx 用原有段落规则。
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

Source = Union[str, Path, bytes]
Row = List[str]

PREVIEW_LIMIT = 240
HEADER_SCAN_ROWS = 5          # 表头可能不在第一行（常有合并的大标题行）
MAX_PREVIEW_SIZE = 8 * 1024 * 1024

# 「文件名称」列的可能叫法
NAME_ALIASES = ("文件名称", "文件名称/资料名称", "资料名称", "名称", "文件", "资料名称及编号")
# 「备注」列的可能叫法
REMARK_ALIASES = ("备注", "说明", "要求", "备注/说明")
# 「序号」列的可能叫法
SEQ_ALIASES = ("序号", "编号", "序 号")

STAGE_SUFFIX_RE = re.compile(r"文件齐套性要求$|齐套性要求$|要求$")
STAGE_HINT_RE = re.compile(r"文件齐套性要求|齐套性|阶段")


# ---------------------------------------------------------------------------
# 格式识别
# ---------------------------------------------------------------------------
def _open_bytes(source: Source) -> bytes:
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)
    return Path(source).read_bytes()


def detect_format(source: Source) -> str:
    """按文件头（magic bytes）判断格式，而不是相信后缀。

    返回: 'pdf' | 'docx' | 'xlsx' | 'zip' | 'unknown'
    """
    try:
        head = _open_bytes(source)[:8] if not isinstance(source, (str, Path)) else _head_of(Path(source))
    except OSError:
        return "unknown"

    if head[:4] == b"%PDF":
        return "pdf"
    if head[:2] == b"PK":
        try:
            buf = io.BytesIO(_open_bytes(source))
            with zipfile.ZipFile(buf) as zf:
                names = set(zf.namelist())
        except Exception:
            return "unknown"
        if "word/document.xml" in names:
            return "docx"
        if "xl/workbook.xml" in names:
            return "xlsx"
        return "zip"
    return "unknown"


def _head_of(path: Path) -> bytes:
    with open(path, "rb") as fh:
        return fh.read(8)


def suffix_of(source: Source) -> str:
    if isinstance(source, (str, Path)):
        return Path(source).suffix.lower()
    return ""


def describe_format(fmt: str) -> str:
    return {
        "docx": "Word 文档",
        "xlsx": "Excel 工作簿",
        "pdf": "PDF",
        "zip": "压缩包",
        "unknown": "未知格式",
    }.get(fmt, fmt)


# ---------------------------------------------------------------------------
# 通用：单元格与表头
# ---------------------------------------------------------------------------
def cell_text(value) -> str:
    """把任意单元格值转成去空白字符串。"""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return re.sub(r"\s+", " ", str(value)).strip()


def _norm(value: str) -> str:
    return re.sub(r"[\s\-—_./\\、,，;；:：()（）\[\]【】]+", "", value or "")


def locate_header(rows: Sequence[Row],
                  name_aliases: Sequence[str] = NAME_ALIASES,
                  remark_aliases: Sequence[str] = REMARK_ALIASES,
                  seq_aliases: Sequence[str] = SEQ_ALIASES
                  ) -> Tuple[int, Optional[int], Optional[int], Optional[int]]:
    """在前若干行里定位表头。

    Returns: (header_row_index, name_col, remark_col, seq_col)
    找不到「文件名称」列时 header_row_index = -1。
    """
    name_set = {_norm(a) for a in name_aliases}
    remark_set = {_norm(a) for a in remark_aliases}
    seq_set = {_norm(a) for a in seq_aliases}

    limit = min(len(rows), HEADER_SCAN_ROWS)
    for row_idx in range(limit):
        cells = [_norm(c) for c in rows[row_idx]]
        name_col = next((i for i, c in enumerate(cells) if c in name_set), None)
        if name_col is None:
            continue
        remark_col = next((i for i, c in enumerate(cells) if c in remark_set), None)
        seq_col = next((i for i, c in enumerate(cells) if c in seq_set), None)
        return row_idx, name_col, remark_col, seq_col

    return -1, None, None, None


def clean_stage(value: str, fallback: str = "未命名阶段") -> str:
    text = re.sub(r"\s+", "", value or "")
    text = STAGE_SUFFIX_RE.sub("", text)
    return text.strip(" ：:—-") or fallback


def _rows_to_requirements(rows: Sequence[Row], stage: str, table_index: int) -> List[Dict]:
    """把一张二维表转成要求条目列表（统一结构）。"""
    header_idx, name_col, remark_col, seq_col = locate_header(rows)
    if header_idx < 0 or name_col is None:
        return []

    out: List[Dict] = []
    sequence = 0
    for row in rows[header_idx + 1:]:
        if name_col >= len(row):
            continue
        name = row[name_col].strip()
        if not name or _norm(name) in {_norm(a) for a in NAME_ALIASES}:
            continue
        if seq_col is not None and seq_col < len(row) and row[seq_col].strip():
            seq_text = row[seq_col].strip()
        else:
            seq_text = ""
        sequence += 1
        remark = row[remark_col].strip() if remark_col is not None and remark_col < len(row) else ""
        out.append({
            "stage": stage or f"表格 {table_index}",
            "table_index": table_index,
            "sequence": sequence,
            "name": name,
            "remark": remark,
            "source_seq": seq_text,
        })
    return out


# ---------------------------------------------------------------------------
# XLSX
# ---------------------------------------------------------------------------
def requirements_from_xlsx(source: Source) -> List[Dict]:
    """从 Excel 要求清单读取条目。每个 sheet 视为一个阶段。"""
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError(
            "读取 .xlsx 需要 openpyxl。请先安装 openpyxl，或把要求清单另存为 .docx。")\
            from exc

    data = _open_bytes(source) if not isinstance(source, (str, Path)) else source
    # openpyxl 会校验后缀并拒绝“改名文件”；此时改用内存流读取（按 magic bytes 已经确认是 xlsx）
    if isinstance(data, (str, Path)) and Path(data).suffix.lower() not in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        data = io.BytesIO(Path(data).read_bytes())
    wb = load_workbook(data, read_only=True, data_only=True)
    results: List[Dict] = []
    table_index = 0
    try:
        for ws in wb.worksheets:
            rows: List[Row] = []
            for raw in ws.iter_rows(values_only=True):
                rows.append([cell_text(c) for c in raw])
            if not any(cell for row in rows for cell in row):
                continue
            table_index += 1
            stage = clean_stage(ws.title) if ws.title else "未命名阶段"
            results.extend(_rows_to_requirements(rows, stage, table_index))
    finally:
        try:
            wb.close()
        except Exception:
            pass
    return results


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
def _stage_above_table(page, table_bbox) -> str:
    """取表格上方的最后一行“阶段”标题。"""
    try:
        top = table_bbox[1] if table_bbox else 0
        area = page.crop((0, 0, page.width, max(0.0, top))) if top > 1 else None
        text = area.extract_text() if area is not None else ""
    except Exception:
        return ""
    if not text:
        return ""
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line and STAGE_HINT_RE.search(line):
            return clean_stage(line)
    return ""


def requirements_from_pdf(source: Source) -> List[Dict]:
    """从文本型 PDF 的要求清单读取条目。

    扫描件（无文本层）会抛 RuntimeError，并给出可操作建议——
    本 skill 有意不接 OCR，避免把离线脚本变成外部服务依赖。
    """
    if not isinstance(source, (str, Path)):
        raise RuntimeError("PDF 需要文件路径（pdfplumber 不支持纯内存流）。")
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError(
            "读取 .pdf 需要 pdfplumber。请安装 pdfplumber，或把要求清单另存为 .docx / .xlsx。")\
            from exc

    path = Path(source)
    results: List[Dict] = []
    table_index = 0
    has_text = False

    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                has_text = True

            # find_tables() 返回带 bbox 的 Table 对象，才能取到表格上方的阶段标题
            try:
                table_objs = page.find_tables() or []
            except Exception:
                table_objs = []
            if table_objs:
                for tobj in table_objs:
                    raw_rows = tobj.extract() or []
                    rows: List[Row] = [[cell_text(c) for c in row] for row in raw_rows]
                    if not any(cell for row in rows for cell in row):
                        continue
                    header_idx, _, _, _ = locate_header(rows)
                    if header_idx < 0:
                        continue
                    table_index += 1
                    stage = _stage_above_table(page, getattr(tobj, "bbox", None)) \
                        or f"第{getattr(page, 'page_number', 0)}页"
                    results.extend(_rows_to_requirements(rows, stage, table_index))
                continue

            # 兜底：没有 Table 对象时退化为纯文本表
            for table in page.extract_tables() or []:
                rows = [[cell_text(c) for c in row] for row in (table or [])]
                if not any(cell for row in rows for cell in row):
                    continue
                header_idx, _, _, _ = locate_header(rows)
                if header_idx < 0:
                    continue
                table_index += 1
                stage = f"第{getattr(page, 'page_number', 0)}页"
                results.extend(_rows_to_requirements(rows, stage, table_index))

    if not has_text:
        raise RuntimeError(
            f"PDF 无文本层（疑似扫描件）：{path.name}。"
            "本技能不内置 OCR；请提供 .docx / .xlsx 版要求清单，或先 OCR 转成可复制文本的 PDF。")
    if not results:
        raise RuntimeError(
            f"未从 PDF 中提取到含「文件名称」列的要求表格：{path.name}。"
            "请确认表格是带框线的文本表格，或改用 .docx / .xlsx。")
    return results


# ---------------------------------------------------------------------------
# 预览（给 LLM 做匹配用）
# ---------------------------------------------------------------------------
def _clip(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:PREVIEW_LIMIT]


def xlsx_preview(blob: bytes) -> str:
    """Excel 预览：sheet 名 + 表头 + 前 3 行，压到 240 字。"""
    if len(blob) > MAX_PREVIEW_SIZE:
        return ""
    try:
        from openpyxl import load_workbook
    except ImportError:
        return ""
    try:
        wb = load_workbook(io.BytesIO(blob), read_only=True, data_only=True)
    except Exception:
        return ""
    parts: List[str] = []
    try:
        for ws in wb.worksheets[:2]:
            rows = []
            for raw in ws.iter_rows(values_only=True, max_row=4):
                rows.append([cell_text(c) for c in raw])
            while rows and not any(rows[0]):
                rows.pop(0)
            head = " / ".join(c for c in (rows[0] if rows else []) if c)
            body = " | ".join(" / ".join(c for c in row if c) for row in rows[1:3])
            segment = f"[{ws.title}] {head}"
            if body:
                segment += f" :: {body}"
            parts.append(segment)
    finally:
        try:
            wb.close()
        except Exception:
            pass
    return _clip(" ｜ ".join(parts))


def pdf_preview(blob: bytes) -> str:
    """PDF 预览：前 2 页文本开头。无文本层则返回空串（不报错、不 OCR）。"""
    if len(blob) > MAX_PREVIEW_SIZE:
        return ""
    text = ""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(blob))
        for page in reader.pages[:2]:
            text += (page.extract_text() or "") + "\n"
    except Exception:
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(blob)) as pdf:
                for page in pdf.pages[:2]:
                    text += (page.extract_text() or "") + "\n"
        except Exception:
            return ""
    return _clip(text)


def read_preview(blob: bytes, suffix: str) -> str:
    """按后缀分派预览。docx 由调用方处理（保持原有实现）。"""
    suffix = (suffix or "").lower()
    if suffix in (".xlsx", ".xlsm"):
        return xlsx_preview(blob)
    if suffix == ".pdf":
        return pdf_preview(blob)
    return ""


# ---------------------------------------------------------------------------
# 把非 DOCX 的要求条目渲染成可标注的 DOCX 模板
# ---------------------------------------------------------------------------
def render_requirements_docx(items: Sequence[Dict], out_path: Union[str, Path]) -> None:
    """根据要求条目生成一份最小 DOCX（阶段段落 + 表格：序号|文件名称|备注）。

    用途：核查记录是「在原要求文档上标注」的，要求清单若是 xlsx/pdf 就没有可标注的
    文档骨架。这里先合成一个结构等价的 DOCX 当模板，再走原有的标注/追加报告流程。

    table_index / sequence 必须与 extract 阶段一致，否则标注会对不上行。
    """
    try:
        from docx import Document
    except ImportError as exc:
        raise RuntimeError(
            "把 .xlsx / .pdf 要求转为可标注的 Word 模板需要 python-docx。"
            "请安装 python-docx，或把要求清单另存为 .docx。") from exc

    def _get(item, key, default=""):
        return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)

    doc = Document()
    current_table: Optional[int] = None
    current_stage: Optional[str] = None
    table = None

    for item in items:
        table_index = _get(item, "table_index", 0)
        stage = _get(item, "stage", "未命名阶段")
        if table_index != current_table:
            if stage != current_stage:
                doc.add_paragraph(str(stage))
            table = doc.add_table(rows=1, cols=3)
            table.style = "Table Grid"          # 必须有边框，标注逻辑依赖真实表格结构
            header = table.rows[0].cells
            header[0].text = "序号"
            header[1].text = "文件名称"
            header[2].text = "备注"
            current_table = table_index
            current_stage = stage
        row = table.add_row().cells
        row[0].text = str(_get(item, "sequence", ""))
        row[1].text = str(_get(item, "name", ""))
        row[2].text = str(_get(item, "remark", ""))

    doc.save(str(out_path))