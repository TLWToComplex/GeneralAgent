#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文件齐套性核查 — 数据提取 + 报告生成。

本脚本拆分为两个独立模式：
  --mode extract   从 DOCX 要求表和 ZIP 项目包中提取结构化数据，输出 JSON。
  --mode generate  读取 LLM 匹配结果 JSON，生成《文件齐套性核查记录.docx》。

匹配决策（阶段 4/5）由大模型完成，脚本只负责数据提取和文档生成。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import unicodedata
import zipfile
from dataclasses import asdict, dataclass, field
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Sequence, Tuple
import xml.etree.ElementTree as ET

import docio

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
ET.register_namespace("w", W_NS)
HEX_ESCAPE = re.compile(r"#U([0-9A-Fa-f]{4})")
PAREN_RE = re.compile(r"[（(].*?[）)]")
PUNCT_RE = re.compile(r"[\s\-—_./\\、,，;；:：()（）\[\]【】{}<>《》'\"`]+")
VERSION_RE = re.compile(r"(?:v|ver|版本)?\d+(?:\.\d+){0,3}$", re.I)
MAX_ZIP_MEMBERS = 20_000
MAX_MEMBER_SIZE = 64 * 1024 * 1024
MAX_PREVIEW_SIZE = 8 * 1024 * 1024
STATUS_ORDER = ["已匹配", "部分满足", "疑似匹配", "未找到", "待确认适用性"]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class Requirement:
    stage: str
    table_index: int
    sequence: int
    name: str
    remark: str = ""


@dataclass
class ArchiveFile:
    raw_path: str
    path: str
    stem: str
    suffix: str
    size: int
    preview: str = ""


@dataclass
class Candidate:
    path: str
    score: float = 0.0
    reason: str = ""
    preview: str = ""


@dataclass
class Result:
    requirement: Requirement
    status: str
    files: List[str] = field(default_factory=list)
    review_files: List[Candidate] = field(default_factory=list)
    candidates: List[Candidate] = field(default_factory=list)
    basis: str = ""
    covered: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------
def decode_hash_u(value: str) -> str:
    """Decode #U9879-style escaped Chinese paths used by some archive exports."""
    def repl(match: re.Match[str]) -> str:
        try:
            return chr(int(match.group(1), 16))
        except ValueError:
            return match.group(0)
    return HEX_ESCAPE.sub(repl, value)


def text_of(node: ET.Element) -> str:
    return "".join(t.text or "" for t in node.findall(".//w:t", NS)).strip()


def normalize_name(value: str) -> str:
    value = decode_hash_u(value or "")
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("\u3000", " ").strip()
    value = re.sub(r"\.[A-Za-z0-9]{1,8}$", "", value)
    value = PAREN_RE.sub("", value)
    value = PUNCT_RE.sub("", value)
    value = value.lower()
    value = VERSION_RE.sub("", value)
    return value


def clean_stage(value: str, fallback: str) -> str:
    text = re.sub(r"\s+", "", value)
    if not text:
        return fallback
    text = re.sub(r"^表[^方案样机研制性能验证]*", "", text)
    return text or fallback


def visible_stem(path: str) -> str:
    name = PurePosixPath(path).name
    if "." in name:
        name = name.rsplit(".", 1)[0]
    return name


def is_ignored_member(raw_path: str) -> bool:
    path = raw_path.replace("\\", "/")
    name = PurePosixPath(path).name
    return (
        not name
        or path.startswith("__MACOSX/")
        or name == ".DS_Store"
        or name.startswith("~$")
    )


def short_path(path: str) -> str:
    return PurePosixPath(path).name


def short_stage(value: str) -> str:
    text = re.sub(r"文件齐套性要求$", "", value or "")
    text = re.sub(r"齐套性要求$", "", text)
    return text.strip(" ：:—- ") or (value or "未命名阶段")


# ---------------------------------------------------------------------------
# Phase 1: Extract requirements from DOCX
# ---------------------------------------------------------------------------
def extract_requirements(path: str) -> List[Requirement]:
    """读取要求清单，按实际格式分派：DOCX / XLSX / PDF（文本型）。

    格式判定用 magic bytes（docio.detect_format），不信任文件后缀。
    """
    fmt = docio.detect_format(path)
    if fmt == "docx":
        return _requirements_from_docx(path)
    if fmt == "xlsx":
        items = docio.requirements_from_xlsx(path)
    elif fmt == "pdf":
        items = docio.requirements_from_pdf(path)
    else:
        raise RuntimeError(
            f"不支持的要求文件格式：{docio.describe_format(fmt)}（{Path(path).name}）。"
            "支持 .docx / .xlsx / .pdf（文本型，非扫描件）。")

    if not items:
        raise RuntimeError(
            f"未从 {Path(path).name} 中提取到含「文件名称」列的要求表格。")

    return [
        Requirement(
            stage=item["stage"],
            table_index=item["table_index"],
            sequence=item["sequence"],
            name=item["name"],
            remark=item.get("remark", ""),
        )
        for item in items
    ]


def _requirements_from_docx(docx_path: str) -> List[Requirement]:
    try:
        with zipfile.ZipFile(docx_path) as docx:
            raw = docx.read("word/document.xml")
    except (OSError, zipfile.BadZipFile, KeyError) as exc:
        raise RuntimeError(f"无法读取要求 DOCX：{exc}") from exc

    root = ET.fromstring(raw)
    body = root.find("w:body", NS)
    if body is None:
        raise RuntimeError("要求 DOCX 缺少正文。")

    requirements: List[Requirement] = []
    current_stage = "未命名阶段"
    table_index = 0
    for child in list(body):
        if child.tag == f"{{{W_NS}}}p":
            paragraph = text_of(child)
            if "文件齐套性要求" in paragraph or ("阶段" in paragraph and "文件" in paragraph):
                # 与 xlsx（sheet 名）/ pdf（表格上方标题）共用同一套阶段清洗规则，
                # 保证三种格式抽出的 stage 完全一致
                current_stage = docio.clean_stage(paragraph, current_stage)
            continue
        if child.tag != f"{{{W_NS}}}tbl":
            continue

        table_index += 1
        rows: List[List[str]] = []
        for tr in child.findall("./w:tr", NS):
            row = [text_of(tc) for tc in tr.findall("./w:tc", NS)]
            if row:
                rows.append(row)
        if not rows:
            continue

        header = rows[0]
        header_norm = [normalize_name(h) for h in header]
        try:
            name_idx = header_norm.index(normalize_name("文件名称"))
        except ValueError:
            name_idx = 1 if len(header) > 1 else 0
        remark_idx = None
        for idx, value in enumerate(header_norm):
            if value in {normalize_name("备注"), normalize_name("说明")}:
                remark_idx = idx
                break

        sequence = 0
        for row in rows[1:]:
            if name_idx >= len(row):
                continue
            name = row[name_idx].strip()
            if not name or name in {"文件名称", "序号"}:
                continue
            sequence += 1
            remark = row[remark_idx].strip() if remark_idx is not None and remark_idx < len(row) else ""
            requirements.append(
                Requirement(
                    stage=current_stage or f"表格 {table_index}",
                    table_index=table_index,
                    sequence=sequence,
                    name=name,
                    remark=remark,
                )
            )
    if not requirements:
        raise RuntimeError('\u672a\u4ece DOCX \u8868\u683c\u4e2d\u63d0\u53d6\u5230\u201c\u6587\u4ef6\u540d\u79f0\u201d\u8981\u6c42\u9879\u3002')
    return requirements


# ---------------------------------------------------------------------------
# Phase 2: Read ZIP inventory
# ---------------------------------------------------------------------------
def read_inventory(zip_path: str) -> List[ArchiveFile]:
    try:
        archive = zipfile.ZipFile(zip_path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise RuntimeError(f"无法读取项目 ZIP：{exc}") from exc

    inventory: List[ArchiveFile] = []
    try:
        infos = archive.infolist()
        if len(infos) > MAX_ZIP_MEMBERS:
            raise RuntimeError(f"ZIP 内成员数为 {len(infos)}，超过安全上限 {MAX_ZIP_MEMBERS}。")
        for info in infos:
            if info.is_dir() or is_ignored_member(info.filename):
                continue
            if info.file_size > MAX_MEMBER_SIZE:
                continue
            decoded = decode_hash_u(info.filename.replace("\\", "/"))
            suffix = PurePosixPath(decoded).suffix.lower()
            inventory.append(
                ArchiveFile(
                    raw_path=info.filename,
                    path=decoded,
                    stem=visible_stem(decoded),
                    suffix=suffix,
                    size=info.file_size,
                )
            )
    finally:
        archive.close()
    if not inventory:
        raise RuntimeError("项目 ZIP 中未发现可核查文件。")
    return inventory


def extract_docx_preview(blob: bytes) -> str:
    """Extract a compact title/heading preview from a DOCX blob."""
    try:
        with zipfile.ZipFile(BytesIO(blob)) as docx:
            raw = docx.read("word/document.xml")
    except Exception:
        return ""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return ""
    snippets: List[str] = []
    for p in root.findall(".//w:body/w:p", NS):
        part = re.sub(r"\s+", "", text_of(p))
        if part and part not in snippets:
            snippets.append(part)
        if len(snippets) >= 5 or sum(len(x) for x in snippets) >= 220:
            break
    return " / ".join(snippets)[:240]


def add_previews(zip_path: str, inventory: List[ArchiveFile]) -> None:
    """读取 ZIP 内 DOCX / XLSX / PDF 的内容摘要，供 LLM 匹配时参考。

    安全约定：只从内存（BytesIO）读取，绝不把不可信压缩包成员写到磁盘。
    """
    wanted = {".docx", ".xlsx", ".xlsm", ".pdf"}
    by_raw = {
        f.raw_path: f
        for f in inventory
        if f.suffix in wanted and f.size <= MAX_PREVIEW_SIZE
    }
    if not by_raw:
        return
    with zipfile.ZipFile(zip_path) as archive:
        for raw_path, record in by_raw.items():
            try:
                blob = archive.read(raw_path)
                if record.suffix == ".docx":
                    record.preview = extract_docx_preview(blob)
                else:
                    record.preview = docio.read_preview(blob, record.suffix)
            except Exception:
                record.preview = ""


# ---------------------------------------------------------------------------
# Mode: extract — output requirements + inventory as JSON
# ---------------------------------------------------------------------------
def mode_extract(requirements_path: str, project_path: str) -> None:
    requirements = extract_requirements(requirements_path)
    inventory = read_inventory(project_path)
    add_previews(project_path, inventory)

    output = {
        "requirements_path": str(Path(requirements_path).resolve()),
        "project_path": str(Path(project_path).resolve()),
        "requirements": [asdict(r) for r in requirements],
        "inventory": [asdict(f) for f in inventory],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Mode: generate — read LLM matching results, generate Word document
# ---------------------------------------------------------------------------
def load_matches(matches_path: str) -> dict:
    """Auto-detect format: JSON or TSV."""
    with open(matches_path, "r", encoding="utf-8") as fh:
        first = fh.read(200)
    if first.strip().startswith("{"):
        # JSON format
        with open(matches_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    # TSV format
    return {"_format": "tsv", "_path": matches_path}


def parse_tsv_matches(matches_path: str, requirements: List[Requirement]) -> List[dict]:
    """Parse TSV matching results.

    TSV format (one line per requirement, tab-separated, 7 columns):
      序号  status  formal_files  review_files  basis  covered  missing

    - formal_files: multiple files separated by ;; (double semicolon)
     - review_files: format is \u201cpath(\u539f\u56e0)\u201d, multiple separated by ;;
     - covered / missing: items separated by ;;
    - Lines starting with # are comments, blank lines are skipped.

    This format is minimal enough for a 32B-class LLM to generate reliably.
    """
    import re as _re
    results: List[dict] = []
    with open(matches_path, "r", encoding="utf-8") as fh:
        lines = [l.rstrip("\n\r") for l in fh if l.strip() and not l.strip().startswith("#")]

    if len(lines) != len(requirements):
        raise RuntimeError(
            f"TSV \u884c\u6570 ({len(lines)}) \u4e0e\u8981\u6c42\u6761\u76ee\u6570 ({len(requirements)}) \u4e0d\u4e00\u81f4\u3002"
        )

    for idx, line in enumerate(lines):
        cols = line.split("\t")
        # Pad to 7 columns
        while len(cols) < 7:
            cols.append("")
        seq, status, formal_str, review_str, basis, covered_str, missing_str = cols[:7]

        status = status.strip()
        if status not in STATUS_ORDER:
            status = "\u672a\u627e\u5230"

        # Parse formal files
        files = [f.strip() for f in formal_str.split(";;") if f.strip() and f.strip() != "-"]

        # Parse review files: format "path(reason)" or just "path"
        review_files = []
        for part in review_str.split(";;"):
            part = part.strip()
            if not part or part == "-":
                continue
            m = _re.match(r"^(.+?)\s*[（(]([^）)]*)[）)]$", part)
            if m:
                review_files.append({"path": m.group(1).strip(), "reason": m.group(2).strip(), "preview": ""})
            else:
                review_files.append({"path": part, "reason": "", "preview": ""})

        covered = [c.strip() for c in covered_str.split(";;") if c.strip() and c.strip() != "-"]
        missing = [m.strip() for m in missing_str.split(";;") if m.strip() and m.strip() != "-"]

        results.append({
            "status": status,
            "files": files,
            "review_files": review_files,
            "basis": basis.strip(),
            "covered": covered,
            "missing": missing,
        })

    return results


def build_results_from_matches(
    matches_data: dict,
    requirements: List[Requirement],
    inventory: List[ArchiveFile],
) -> List[Result]:
    """Convert LLM matching results into Result objects for document generation."""
    if matches_data.get("_format") == "tsv":
        match_list = parse_tsv_matches(matches_data["_path"], requirements)
    else:
        match_list = matches_data.get("matches", [])

    if len(match_list) != len(requirements):
        raise RuntimeError(
            f"匹配结果条目数 ({len(match_list)}) 与要求条目数 ({len(requirements)}) 不一致，"
            "每个要求条目必须有一条匹配结果。"
        )

    assigned_paths: set[str] = set()
    all_inventory_paths = {f.path for f in inventory}

    results: List[Result] = []
    for idx, match_entry in enumerate(match_list):
        req = requirements[idx]
        status = match_entry.get("status", "未找到")
        if status not in STATUS_ORDER:
            status = "未找到"

        files = list(dict.fromkeys(match_entry.get("files", [])))
        for path in files:
            if path in assigned_paths:
                raise RuntimeError(f'文件\u201c{short_path(path)}\u201d被重复分配（要求条目 {idx + 1}）。')
            assigned_paths.add(path)

        review_files = []
        for rf in match_entry.get("review_files", []):
            path = rf.get("path", "")
            if path in assigned_paths:
                raise RuntimeError(f'待确认文件\u201c{short_path(path)}\u201d被重复分配（要求条目 {idx + 1}）。')
            assigned_paths.add(path)
            review_files.append(Candidate(
                path=path,
                score=0.0,
                reason=rf.get("reason", ""),
                preview=rf.get("preview", ""),
            ))

        result = Result(
            requirement=req,
            status=status,
            files=files,
            review_files=review_files,
            candidates=review_files,
            basis=match_entry.get("basis", ""),
            covered=match_entry.get("covered", []),
            missing=match_entry.get("missing", []),
        )
        results.append(result)

    unassigned = all_inventory_paths - assigned_paths
    if unassigned:
        names = "、".join(short_path(p) for p in sorted(unassigned)[:10])
        raise RuntimeError(
            f"以下 {len(unassigned)} 个 ZIP 文件未被分配到任何要求条目：{names}"
        )

    return results


# ---------------------------------------------------------------------------
# Word document generation helpers
# ---------------------------------------------------------------------------
def qn(local: str) -> str:
    return f"{{{W_NS}}}{local}"


def wx(local: str, **attrs: str) -> ET.Element:
    element = ET.Element(qn(local))
    for key, value in attrs.items():
        if key.startswith("w:"):
            element.set(qn(key[2:]), str(value))
        else:
            element.set(key, str(value))
    return element


def make_run(text: str, *, bold: bool = False, color: str = "", size: int = 21) -> ET.Element:
    run = wx("r")
    rpr = wx("rPr")
    rpr.append(wx("rFonts", **{
        "w:ascii": "Arial",
        "w:hAnsi": "Arial",
        "w:eastAsia": "宋体",
        "w:cs": "Arial",
    }))
    if bold:
        rpr.append(wx("b"))
        rpr.append(wx("bCs"))
    if color:
        rpr.append(wx("color", **{"w:val": color}))
    if size:
        rpr.append(wx("sz", **{"w:val": str(size)}))
        rpr.append(wx("szCs", **{"w:val": str(size)}))
    run.append(rpr)
    text_node = wx("t")
    if text.startswith(" ") or text.endswith(" "):
        text_node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    text_node.text = text
    run.append(text_node)
    return run


def make_paragraph(
    text: str = "",
    *,
    bold: bool = False,
    color: str = "",
    size: int = 21,
    align: str = "left",
    before: int = 0,
    after: int = 90,
    keep_with_next: bool = False,
) -> ET.Element:
    paragraph = wx("p")
    ppr = wx("pPr")
    if align and align != "left":
        ppr.append(wx("jc", **{"w:val": align}))
    if before or after:
        ppr.append(wx("spacing", **{"w:before": str(before), "w:after": str(after), "w:line": "300", "w:lineRule": "auto"}))
    if keep_with_next:
        ppr.append(wx("keepNext"))
    paragraph.append(ppr)
    if text:
        paragraph.append(make_run(text, bold=bold, color=color, size=size))
    return paragraph


def make_page_break() -> ET.Element:
    paragraph = wx("p")
    run = wx("r")
    run.append(wx("br", **{"w:type": "page"}))
    paragraph.append(run)
    return paragraph


def insert_before_section(body: ET.Element, node: ET.Element) -> None:
    sect = body.find("w:sectPr", NS)
    if sect is None:
        body.append(node)
    else:
        body.insert(list(body).index(sect), node)


def clear_cell_keep_properties(cell: ET.Element) -> None:
    for child in list(cell):
        if child.tag != qn("tcPr"):
            cell.remove(child)


def add_cell_paragraph(
    cell: ET.Element,
    text: str,
    *,
    bold: bool = False,
    color: str = "",
    size: int = 19,
    align: str = "left",
    before: int = 0,
    after: int = 0,
) -> None:
    cell.append(make_paragraph(
        text,
        bold=bold,
        color=color,
        size=size,
        align=align,
        before=before,
        after=after,
    ))


def status_mark(result: Result) -> Tuple[str, str]:
    mapping = {
        "已匹配": ("√", "008000"),
        "部分满足": ("△", "C65911"),
        "疑似匹配": ("?", "1F4E79"),
        "未找到": ("×", "C00000"),
        "待确认适用性": ("?", "1F4E79"),
    }
    return mapping.get(result.status, ("?", "1F4E79"))


def fill_remark_cell(cell: ET.Element, result: Result) -> None:
    existing = text_of(cell).strip()
    mark, color = status_mark(result)
    clear_cell_keep_properties(cell)
    if existing:
        add_cell_paragraph(cell, existing, size=18, align="left")
    add_cell_paragraph(cell, mark, bold=True, color=color, size=26, align="center")


def locate_table_columns(rows: Sequence[Sequence[str]]) -> Tuple[int, Optional[int]]:
    header = list(rows[0]) if rows else []
    header_norm = [normalize_name(item) for item in header]
    try:
        name_idx = header_norm.index(normalize_name("文件名称"))
    except ValueError:
        name_idx = 1 if len(header) > 1 else 0
    remark_idx: Optional[int] = None
    for idx, value in enumerate(header_norm):
        if value in {normalize_name("备注"), normalize_name("说明")}:
            remark_idx = idx
            break
    return name_idx, remark_idx


def annotate_requirement_tables(body: ET.Element, results: Sequence[Result]) -> None:
    result_lookup = {
        (item.requirement.table_index, item.requirement.sequence): item
        for item in results
    }
    table_index = 0
    for child in list(body):
        if child.tag != qn("tbl"):
            continue
        table_index += 1
        tr_nodes = child.findall("./w:tr", NS)
        rows: List[List[str]] = []
        for tr in tr_nodes:
            rows.append([text_of(tc) for tc in tr.findall("./w:tc", NS)])
        if not rows:
            continue
        name_idx, remark_idx = locate_table_columns(rows)
        if remark_idx is None:
            continue
        sequence = 0
        for row_index, tr in enumerate(tr_nodes[1:], 1):
            cells = tr.findall("./w:tc", NS)
            if name_idx >= len(cells) or remark_idx >= len(cells):
                continue
            name = text_of(cells[name_idx]).strip()
            if not name or name in {"文件名称", "序号"}:
                continue
            sequence += 1
            result = result_lookup.get((table_index, sequence))
            if result is not None:
                fill_remark_cell(cells[remark_idx], result)


def table_cell(
    text: str,
    width: int,
    *,
    header: bool = False,
    align: str = "left",
    font_size: int = 18,
) -> ET.Element:
    cell = wx("tc")
    tcpr = wx("tcPr")
    tcpr.append(wx("tcW", **{"w:w": str(width), "w:type": "dxa"}))
    tcpr.append(wx("vAlign", **{"w:val": "center"}))
    if header:
        tcpr.append(wx("shd", **{"w:val": "clear", "w:fill": "D9EAF7"}))
    cell.append(tcpr)
    parts = str(text or "—").split("\n")
    for part in parts:
        add_cell_paragraph(
            cell,
            part,
            bold=header,
            color="1F1F1F",
            size=font_size,
            align=align if header else "left",
        )
    return cell


def make_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    widths: Sequence[int],
    *,
    font_size: int = 18,
) -> ET.Element:
    table = wx("tbl")
    tblpr = wx("tblPr")
    tblpr.append(wx("tblW", **{"w:w": "0", "w:type": "auto"}))
    tblpr.append(wx("tblLayout", **{"w:type": "fixed"}))
    tblpr.append(wx("tblCellMar"))
    borders = wx("tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        borders.append(wx(side, **{"w:val": "single", "w:sz": "4", "w:space": "0", "w:color": "8FAADC"}))
    tblpr.append(borders)
    table.append(tblpr)

    grid = wx("tblGrid")
    for width in widths:
        grid.append(wx("gridCol", **{"w:w": str(width)}))
    table.append(grid)

    all_rows = [list(headers)] + [list(row) for row in rows]
    for index, row in enumerate(all_rows):
        tr = wx("tr")
        trpr = wx("trPr")
        if index == 0:
            trpr.append(wx("tblHeader"))
        trpr.append(wx("cantSplit"))
        tr.append(trpr)
        for col_index, width in enumerate(widths):
            value = row[col_index] if col_index < len(row) else ""
            tr.append(table_cell(
                str(value),
                width,
                header=(index == 0),
                align="center" if index == 0 or col_index == 0 else "left",
                font_size=font_size,
            ))
        table.append(tr)
    return table


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------
def escape_cell(value: str) -> str:
    return (value or "").replace("|", "\\|").replace("\n", "<br>")


def compact_names(paths: Sequence[str], limit: int = 4) -> str:
    names = [short_path(p) for p in paths]
    if not names:
        return "—"
    if len(names) <= limit:
        return "、".join(f"`{escape_cell(name)}`" for name in names)
    shown = "、".join(f"`{escape_cell(name)}`" for name in names[:limit])
    return f"{shown} 等 {len(names)} 个文件"


def unique_paths(paths: Sequence[str]) -> List[str]:
    return list(dict.fromkeys(path for path in paths if path))


def review_file_candidates(result: Result) -> List[Candidate]:
    seen: set[str] = set()
    items: List[Candidate] = []
    for candidate in list(result.review_files) + list(result.candidates):
        if candidate.path and candidate.path not in seen:
            seen.add(candidate.path)
            items.append(candidate)
    return items


def requires_human_review(result: Result) -> bool:
    return result.status in {"疑似匹配", "待确认适用性"} or bool(review_file_candidates(result))


def actual_file_names(result: Result, *, include_candidates: bool = False) -> str:
    formal = [short_path(path) for path in unique_paths(result.files)]
    review = [short_path(candidate.path) for candidate in review_file_candidates(result)]
    lines: List[str] = []
    if formal:
        lines.extend(formal)
    if review:
        lines.append("待确认：" + "、".join(review))
    if not lines and include_candidates:
        alternatives = [short_path(candidate.path) for candidate in result.candidates]
        if alternatives:
            lines.append("待确认：" + "、".join(dict.fromkeys(alternatives)))
    return "\n".join(lines) if lines else "—"


def status_text(result: Result) -> str:
    labels = {
        "已匹配": "√ 已匹配",
        "部分满足": "△ 部分满足",
        "疑似匹配": "? 待人工确认",
        "未找到": "× 未找到",
        "待确认适用性": "? 待确认适用性",
    }
    return labels.get(result.status, result.status)


def stage_groups_in_source_order(results: Sequence[Result]) -> List[Tuple[str, List[Result]]]:
    groups: List[Tuple[str, List[Result]]] = []
    buckets: Dict[str, List[Result]] = {}
    for item in sorted(results, key=lambda r: (r.requirement.table_index, r.requirement.sequence)):
        stage = short_stage(item.requirement.stage)
        if stage not in buckets:
            bucket: List[Result] = []
            buckets[stage] = bucket
            groups.append((stage, bucket))
        buckets[stage].append(item)
    return groups


def partial_gap_text(result: Result) -> str:
    if result.status == "部分满足":
        return "、".join(result.missing) or "请按原要求复核"
    if result.status == "未找到":
        return "未发现对应文件，建议补充正式文件。"
    return "—"


def priority_for(result: Result) -> int:
    name = result.requirement.name
    if any(term in name for term in ("总体", "规范", "试验报告", "产品规范", "图样")):
        return 1
    if any(term in name for term in ("大纲", "计划", "报告", "说明书")):
        return 2
    return 3


def action_text(result: Result) -> str:
    if result.status == "未找到":
        return "未发现对应文件，建议补充正式文件。"
    if result.status == "部分满足":
        missing = "、".join(result.missing) or "按要求补齐缺项"
        return f"仍缺：{missing}。"
    if result.status == "疑似匹配":
        return "候选文件主题相关，但无法仅凭名称确认；请核对标题、对象、阶段和文件类型。"
    if result.status == "待确认适用性":
        return "请先确认该军种/方向/交付条件是否适用于本项目。"
    return ""


def report_conclusion(results: Sequence[Result]) -> Tuple[str, Dict[str, int]]:
    counts = {status: sum(item.status == status for item in results) for status in STATUS_ORDER}
    issues = counts["未找到"] + counts["部分满足"]
    reviews = sum(requires_human_review(item) for item in results)
    if issues == 0 and reviews == 0:
        return "本次核查范围内，项目资料名称齐套性初核通过。", counts
    if issues == 0:
        return f"未发现明确缺项，但仍有{reviews}项存在待人工确认文件或适用性问题。", counts
    return (
        f"当前资料暂不能判定为齐套：{counts['未找到']}项未找到、"
        f"{counts['部分满足']}项部分满足，另有{reviews}项存在待人工确认文件或适用性问题。",
        counts,
    )


# ---------------------------------------------------------------------------
# Build the final Word document
# ---------------------------------------------------------------------------
def build_docx_record(
    requirements_path: str,
    project_path: str,
    inventory: Sequence[ArchiveFile],
    results: Sequence[Result],
    output_path: str,
    requirements_label: str = "",
) -> None:
    """Copy the requirement DOCX, annotate its remarks cells, then append a report.

    requirements_label：报告里展示的“要求文件”名称（要求来自 xlsx/pdf 时，
    requirements_path 指向临时合成的模板，而展示的应是用户原始文件名）。
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(requirements_path) as source:
            parts = {
                info.filename: source.read(info.filename)
                for info in source.infolist()
                if not info.is_dir()
            }
    except (OSError, zipfile.BadZipFile) as exc:
        raise RuntimeError(f"无法以要求 DOCX 为模板生成核查记录：{exc}") from exc

    try:
        root = ET.fromstring(parts["word/document.xml"])
    except KeyError as exc:
        raise RuntimeError("要求 DOCX 缺少 word/document.xml。") from exc
    body = root.find("w:body", NS)
    if body is None:
        raise RuntimeError("要求 DOCX 缺少正文。")

    annotate_requirement_tables(body, results)
    conclusion, counts = report_conclusion(results)
    formal_paths = {path for item in results for path in item.files if path}
    review_paths = {candidate.path for item in results for candidate in review_file_candidates(item) if candidate.path}
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    # Start the explanatory report only after the complete source requirement table.
    insert_before_section(body, make_page_break())
    insert_before_section(body, make_paragraph(
        "文件齐套性核查报告",
        bold=True,
        size=34,
        align="center",
        before=0,
        after=240,
        keep_with_next=True,
    ))

    insert_before_section(body, make_paragraph("一、核查结论", bold=True, size=28, before=90, after=100, keep_with_next=True))
    insert_before_section(body, make_paragraph(conclusion, size=22, before=0, after=120))
    scope_rows = [
        ["要求文件", requirements_label or Path(requirements_path).name],
        ["项目文件包", Path(project_path).name],
        ["核查范围", f"ZIP 内{len(inventory)}个可核查文件；要求表共{len(results)}项"],
        [
            "项目文件唯一关联",
            (
                f"全部{len(inventory)}个项目文件均已唯一关联至某一要求项；"
                f"其中{len(formal_paths)}个作为正式齐套依据，{len(review_paths)}个标记为待人工确认且不计入齐套。"
            ),
        ],
        ["生成时间", now],
    ]
    insert_before_section(body, make_table(["项目", "内容"], scope_rows, [2200, 7200], font_size=18))
    insert_before_section(body, make_paragraph("", after=80))

    insert_before_section(body, make_paragraph("二、核查标记与统计", bold=True, size=28, before=120, after=100, keep_with_next=True))
    legend_rows = [
        ["√", "已匹配", "文件名称、文件类型或集合子项均有明确对应文件"],
        ["△", "部分满足", "已提供部分材料，仍需补齐列明的缺项"],
        ["?", "待人工确认", "文件已唯一关联至相对接近的要求项，但不计入齐套，须人工核对"],
        ["×", "未找到", "当前 ZIP 中未发现可支持该要求的正式齐套依据"],
    ]
    insert_before_section(body, make_table(["备注栏标记", "核查状态", "说明"], legend_rows, [1500, 2200, 5700], font_size=18))
    insert_before_section(body, make_paragraph("", after=80))
    count_rows = [[str(counts[s]) for s in STATUS_ORDER]]
    insert_before_section(body, make_table(STATUS_ORDER, count_rows, [1880, 1880, 1880, 1880, 1880], font_size=18))
    insert_before_section(body, make_paragraph("", after=80))

    # Show every original requirement in source order.
    insert_before_section(body, make_paragraph(
        "三、文件对应明细（要求文件 ↔ 实际文件）",
        bold=True,
        size=28,
        before=120,
        after=100,
        keep_with_next=True,
    ))
    phase_prefixes = ["（一）", "（二）", "（三）", "（四）"]
    for phase_index, (stage, stage_items) in enumerate(stage_groups_in_source_order(results)):
        prefix = phase_prefixes[phase_index] if phase_index < len(phase_prefixes) else f"（{phase_index + 1}）"
        insert_before_section(body, make_paragraph(
            f"{prefix}{stage}",
            bold=True,
            size=24,
            before=70,
            after=70,
            keep_with_next=True,
        ))
        detail_rows: List[List[str]] = []
        for item in stage_items:
            detail_rows.append([
                str(item.requirement.sequence),
                item.requirement.name,
                actual_file_names(item, include_candidates=True),
                status_text(item),
            ])
        insert_before_section(body, make_table(
            ["序号", "要求文件", "实际对应文件", "核查结果"],
            detail_rows,
            [600, 3000, 4300, 2100],
            font_size=17,
        ))
        insert_before_section(body, make_paragraph("", after=80))

    missing_or_partial = [item for item in results if item.status in {"未找到", "部分满足"}]
    insert_before_section(body, make_paragraph("四、需补齐文件", bold=True, size=28, before=120, after=100, keep_with_next=True))
    if missing_or_partial:
        gap_rows: List[List[str]] = []
        for number, item in enumerate(sorted(missing_or_partial, key=lambda r: (r.requirement.table_index, r.requirement.sequence)), 1):
            gap_rows.append([
                str(number),
                short_stage(item.requirement.stage),
                item.requirement.name,
                actual_file_names(item),
                partial_gap_text(item),
            ])
        insert_before_section(body, make_table(
            ["序号", "阶段", "要求文件", "已提供/待确认的实际文件", "仍需补齐"],
            gap_rows,
            [500, 1800, 2500, 3000, 2200],
            font_size=16,
        ))
    else:
        insert_before_section(body, make_paragraph("无明确缺失或部分满足项目。", size=21, after=100))
    insert_before_section(body, make_paragraph("", after=80))

    review_items = [item for item in results if requires_human_review(item)]
    insert_before_section(body, make_paragraph("五、需人工确认文件", bold=True, size=28, before=120, after=100, keep_with_next=True))
    if review_items:
        review_rows: List[List[str]] = []
        for number, item in enumerate(sorted(review_items, key=lambda r: (r.requirement.table_index, r.requirement.sequence)), 1):
            candidates = review_file_candidates(item)
            if candidates:
                names = "、".join(short_path(candidate.path) for candidate in candidates)
                explanations = "；".join(
                    f"{short_path(candidate.path)}：{candidate.reason or '与本项存在相近关系'}"
                    for candidate in candidates
                )
                prefix = "待确认文件已唯一关联至本项，不计入齐套。"
                if item.files:
                    prefix = f"已匹配依据：{'、'.join(short_path(path) for path in item.files)}。" + prefix
                detail = f"{prefix}\n待确认文件：{names}\n{explanations}\n请核对标题、对象、阶段及文件类型。"
            else:
                detail = "请先确认该军种、方向或交付条件是否适用于本项目。"
            review_rows.append([str(number), short_stage(item.requirement.stage), item.requirement.name, detail])
        insert_before_section(body, make_table(
            ["序号", "阶段", "要求文件", "确认事项"],
            review_rows,
            [550, 2100, 3500, 3350],
            font_size=17,
        ))
    else:
        insert_before_section(body, make_paragraph("无需要人工确认的项目。", size=21, after=100))
    insert_before_section(body, make_paragraph("", after=80))

    insert_before_section(body, make_paragraph("六、核查说明", bold=True, size=28, before=120, after=100, keep_with_next=True))
    notes = [
        "1. 前述要求表已按原文顺序保留，备注栏中的标记为本次名称齐套性初核结果。",
        "2. 第三部分按原要求表阶段和序号列出\u201c要求文件 \u2194 实际文件\u201d，用于追溯每一项的匹配依据。",
        "3. 文件名不完全一致时，由大模型根据语义、文件类型、集合要求及可读取的 DOCX 标题/首段综合判断。",
        "4. 同一个 ZIP 内实际文件只能唯一关联至一个要求项；该规则同时适用于正式匹配和待人工确认关联，任何文件不得在其他条目重复出现。",
        "5. 每一个 ZIP 内项目文件均须在第三部分对应到某一要求项，不得遗漏。",
        "6. 标记为\u201c待确认\u201d的文件不等于已满足，且不参与齐套数量统计；人工确认后可决定是否调整要求项、补充正式文件或变更归档关系。",
        "7. \u201c？\u201d不等于已满足；\u201c\u25b3\u201d表示存在明确缺项；\u201c\u00d7\u201d表示当前 ZIP 中未找到对应正式齐套依据。",
        "8. 本核查不审查文件正文质量、版本有效性、审批签署、保密属性及归档合规性；上述事项需结合原件另行复核。",
    ]
    for note in notes:
        insert_before_section(body, make_paragraph(note, size=18, before=0, after=25))

    parts["word/document.xml"] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, blob in parts.items():
            target.writestr(name, blob)


def mode_generate(matches_path: str, requirements_path: str, project_path: str, output_path: str) -> None:
    matches_data = load_matches(matches_path)

    # For JSON format, paths may be embedded; CLI args take priority
    if not requirements_path:
        requirements_path = matches_data.get("requirements_path", "")
    if not project_path:
        project_path = matches_data.get("project_path", "")

    if not requirements_path or not project_path:
        raise RuntimeError("缺少 --requirements 或 --project。")

    requirements = extract_requirements(requirements_path)
    inventory = read_inventory(project_path)
    add_previews(project_path, inventory)

    results = build_results_from_matches(matches_data, requirements, inventory)

    if not str(output_path).lower().endswith(".docx"):
        raise RuntimeError("核查结果只输出 Word 文档，请将 --output 指定为 .docx 文件。")

    # 要求清单不是 DOCX 时，先合成一份结构等价的 DOCX 当模板，再标注并追加报告
    tmp_template: Optional[Path] = None
    if docio.detect_format(requirements_path) != "docx":
        import os
        import tempfile

        fd, tmp_name = tempfile.mkstemp(prefix="req_tpl_", suffix=".docx")
        os.close(fd)
        tmp_template = Path(tmp_name)
        try:
            docio.render_requirements_docx([asdict(r) for r in requirements], tmp_template)
            build_docx_record(
                str(tmp_template), project_path, inventory, results, output_path,
                requirements_label=Path(requirements_path).name,
            )
        finally:
            tmp_template.unlink(missing_ok=True)
    else:
        build_docx_record(requirements_path, project_path, inventory, results, output_path)

    print(f"已生成唯一核查结果文件：{output_path}")


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="文件齐套性核查 — 数据提取 / 报告生成。"
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=["extract", "generate"],
        help="extract：提取要求和文件清单为 JSON；generate：读取匹配结果生成 Word 报告",
    )
    parser.add_argument("--requirements", help="要求文件 DOCX 路径")
    parser.add_argument("--project", help="项目文件 ZIP 路径")
    parser.add_argument(
        "--matches",
        help="LLM 匹配结果路径（generate 模式必需；支持 JSON 或 TSV 格式）",
    )
    parser.add_argument(
        "--output",
        default="文件齐套性核查记录.docx",
        help="输出文件路径（generate 模式，必须为 .docx）",
    )
    args = parser.parse_args()

    if args.mode == "extract":
        if not args.requirements or not args.project:
            parser.error("extract 模式需要 --requirements 和 --project")
        mode_extract(args.requirements, args.project)
    elif args.mode == "generate":
        if not args.matches:
            parser.error("generate 模式需要 --matches")
        if not args.requirements or not args.project:
            parser.error("generate 模式需要 --requirements 和 --project")
        mode_generate(args.matches, args.requirements, args.project, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())