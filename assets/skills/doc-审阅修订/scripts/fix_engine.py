"""
fix_engine.py — 修复引擎

负责：
1. 读取校验报告中的未通过项
2. 执行针对性修复
3. 支持迭代循环：修复 → 校验 → 再修复，直到全部通过或达到最大重试
"""

from pathlib import Path
from copy import deepcopy
from docx import Document
from docx.shared import Pt, Cm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from utils import log, safe_write_docx, enable_track_revisions_in_doc
from font_manager import (
    FontPair, apply_font_to_paragraph, set_run_font_xml,
    apply_page_margins, apply_page_size,
    apply_alignment, apply_line_spacing, apply_first_line_indent,
    apply_paragraph_spacing, apply_table_header_font,
    apply_table_borders, apply_left_indent, clear_paragraph_indent,
    has_cjk, apply_paragraph_xml_settings,
)
from doc_analyzer import analyze_document, Region


# ──────────────────────────────────────────────
# 主入口：迭代修复循环
# ──────────────────────────────────────────────

def fix_and_retry(filepath: str, spec, report,
                  max_retries: int = None) -> tuple:
    """
    迭代修复循环。

    Args:
        filepath: 待修复的 docx 文件路径
        spec: Spec 对象
        report: ValidationReport 对象（包含失败项）
        max_retries: 最大重试次数，None 时从 spec 读取

    Returns:
        (文件路径, 最终校验报告, 修复次数)
    """
    if max_retries is None:
        max_retries = spec.validation.get('max_retries', 5)

    filepath = str(Path(filepath).resolve())
    retry_count = 0

    # 延迟导入避免循环依赖
    from validator import validate_document, Result

    while retry_count < max_retries:
        failed = report.failed_items
        if not failed:
            log.info("全部检查通过，无需修复")
            break

        retry_count += 1
        log.info(f"── 第 {retry_count}/{max_retries} 轮修复 ──")
        log.info(f"  待修复: {len(failed)} 项")

        # 执行修复
        doc = Document(filepath)
        analysis = analyze_document(filepath, spec)

        # 确保列表编号定义存在（fix 阶段也需要）
        from format_applier import _setup_list_numbering
        _setup_list_numbering(doc, spec)

        for check in failed:
            fixer = FIX_HANDLERS.get(check.check_id)
            if fixer:
                fixer(doc, analysis, spec, check)

        # 保存前启用修订追踪
        enable_track_revisions_in_doc(doc)

        # 保存
        safe_write_docx(doc, filepath)

        # 重新校验
        report = validate_document(filepath, spec)

    if retry_count >= max_retries and report.failed_items:
        log.warning(f"达到最大重试次数 ({max_retries})，仍有 {len(report.failed_items)} 项未通过")
    else:
        log.info(f"修复完成: {retry_count} 轮, {len(report.failed_items)} 项残留")

    return filepath, report, retry_count


# ──────────────────────────────────────────────
# 各修复处理函数
# ──────────────────────────────────────────────

def _fix_page_margins(doc, analysis, spec, check):
    """修复页面边距。"""
    for section in doc.sections:
        apply_page_margins(section, spec)
    log.info(f"  [fix] 页面边距 → 上{spec.page['margin_top_cm']}/下{spec.page['margin_bottom_cm']}"
             f"/左{spec.page['margin_left_cm']}/右{spec.page['margin_right_cm']} cm")


def _fix_page_size(doc, analysis, spec, check):
    """修复页面尺寸。"""
    for section in doc.sections:
        apply_page_size(section, spec)
    log.info(f"  [fix] 页面尺寸 → {spec.page['size']} {spec.page.get('orientation', 'portrait')}")


def _fix_body_fonts(doc, analysis, spec, check):
    """修复正文字体。"""
    body_region = analysis.get_region(Region.BODY)
    if not body_region:
        return

    body_paras = analysis.get_body_paragraphs()
    expected_cjk = spec.font_pair('body')['cjk']
    expected_latin = spec.font_pair('body')['latin']
    size_pt = spec.size_pt('body_pt')

    fp = FontPair(expected_cjk, expected_latin, size_pt=size_pt)

    for pi in body_paras:
        if not pi.text.strip():
            continue
        from format_applier import _detect_heading_level
        if _detect_heading_level(pi.text.strip()):
            continue  # 不修复标题的字体

        para = doc.paragraphs[pi.index]
        for run in para.runs:
            if run.text.strip():
                set_run_font_xml(run, fp)

    log.info(f"  [fix] 正文字体 → {expected_cjk}")


def _fix_heading_fonts(doc, analysis, spec, check):
    """修复标题字体。"""
    body_region = analysis.get_region(Region.BODY)
    if not body_region:
        return

    from format_applier import _detect_heading_level

    body_paras = analysis.get_body_paragraphs()
    fixed = 0

    for pi in body_paras:
        level = _detect_heading_level(pi.text.strip())
        if level is None:
            continue

        key = f'h{level}'
        expected_cjk = spec.font_pair(key)['cjk']
        expected_latin = spec.font_pair(key)['latin']
        size_pt = spec.size_pt(f'{key}_pt')

        heading_cfg = spec.heading
        level_bold = heading_cfg.get('level_bold', {})
        bold = level_bold.get(f'h{level}', False)

        fp = FontPair(expected_cjk, expected_latin, size_pt=size_pt,
                      bold=bold)

        para = doc.paragraphs[pi.index]
        for run in para.runs:
            if run.text.strip():
                set_run_font_xml(run, fp)
        fixed += 1

    log.info(f"  [fix] 标题字体 → {fixed} 个标题")


def _fix_cover_fonts(doc, analysis, spec, check):
    """修复封面字体（段落 + 表格）。"""
    cover_region = analysis.get_region(Region.COVER)
    if not cover_region:
        return

    cover_paras = analysis.get_cover_paragraphs()
    total = len(cover_paras)
    fixed = 0

    for pi in cover_paras:
        if not pi.text.strip():
            continue
        pos = pi.index - cover_region.start

        # 按位置推断封面段落类型（与 format_applier._apply_cover_format 保持一致）
        if pos == 0:
            fp = FontPair.from_spec(
                spec.font_pair('cover_title'),
                size_pt=spec.size_pt('cover_title_pt'),
            )
            label = 'cover_title'
        elif pos == total - 1 or pos == total - 2:
            fp = FontPair.from_spec(
                spec.font_pair('cover_info'),
                size_pt=spec.size_pt('cover_info_pt'),
            )
            label = 'cover_info'
        else:
            fp = FontPair.from_spec(
                spec.font_pair('cover_subtitle'),
                size_pt=spec.size_pt('cover_subtitle_pt'),
            )
            label = 'cover_subtitle'

        para = doc.paragraphs[pi.index]
        for run in para.runs:
            if run.text.strip():
                set_run_font_xml(run, fp)
        fixed += 1

    # ── 封面表格修复 ──
    cover_cfg = spec.special_sections.get('cover', {})
    COVER_KEYWORDS = cover_cfg.get('detection_keywords',
                                   ['项目令号', '密级', '文件编号', '版本', '阶段', '拟制', '审核',
                                    '会签', '批准', '日期', '阶段标记'])
    info_fp = FontPair.from_spec(
        spec.font_pair('cover_info'),
        size_pt=spec.size_pt('cover_info_pt'),
    )
    table_fixed = 0
    for table in doc.tables:
        if not table.rows:
            continue
        first_cell = table.rows[0].cells[0].text.strip() if table.rows[0].cells else ''
        if not any(kw in first_cell for kw in COVER_KEYWORDS):
            continue
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    if para.text.strip():
                        for run in para.runs:
                            if run.text.strip():
                                set_run_font_xml(run, info_fp)
                        table_fixed += 1

    if table_fixed:
        log.info(f"  [fix] 封面字体 → {fixed} 段落 + {table_fixed} 表格单元格")
    else:
        log.info(f"  [fix] 封面字体 → {fixed} 段落（标题/副标题/信息行分别处理）")


def _fix_revision_section(doc, analysis, spec, check):
    """修复修订记录区域。"""
    rev_region = analysis.get_region(Region.REVISION)
    if not rev_region:
        return

    rev_paras = analysis.paragraphs[rev_region.start:rev_region.end + 1]
    if not rev_paras:
        return

    # 标题
    title_fp = FontPair.from_spec(
        spec.font_pair('revision_title'),
        size_pt=spec.size_pt('revision_title_pt'),
        bold=True,
    )
    title_para = doc.paragraphs[rev_paras[0].index]
    for run in title_para.runs:
        if run.text.strip():
            set_run_font_xml(run, title_fp)

    # 内容
    if len(rev_paras) > 1:
        body_fp = FontPair.from_spec(
            spec.font_pair('revision_body'),
            size_pt=spec.size_pt('revision_body_pt'),
        )
        for pi in rev_paras[1:]:
            para = doc.paragraphs[pi.index]
            for run in para.runs:
                if run.text.strip():
                    set_run_font_xml(run, body_fp)

    log.info(f"  [fix] 修订记录区域")


def _fix_toc_section(doc, analysis, spec, check):
    """修复目录区域。"""
    toc_region = analysis.get_region(Region.TOC)
    if not toc_region:
        return

    toc_paras = analysis.paragraphs[toc_region.start:toc_region.end + 1]
    if not toc_paras:
        return

    # 标题
    title_fp = FontPair.from_spec(
        spec.font_pair('toc_title'),
        size_pt=spec.size_pt('toc_title_pt'),
        bold=True,
    )
    title_para = doc.paragraphs[toc_paras[0].index]
    for run in title_para.runs:
        if run.text.strip():
            set_run_font_xml(run, title_fp)

    # 内容
    if len(toc_paras) > 1:
        body_fp = FontPair.from_spec(
            spec.font_pair('toc_body'),
            size_pt=spec.size_pt('toc_body_pt'),
        )
        for pi in toc_paras[1:]:
            para = doc.paragraphs[pi.index]
            for run in para.runs:
                if run.text.strip():
                    set_run_font_xml(run, body_fp)

    log.info(f"  [fix] 目录区域")


def _fix_line_spacing(doc, analysis, spec, check):
    """修复行距。"""
    body_region = analysis.get_region(Region.BODY)
    if not body_region:
        return

    body_paras = analysis.get_body_paragraphs()
    spacing_pt = spec.spacing['body_line_spacing_pt']
    spacing_mode = spec.spacing.get('body_line_spacing_mode', 'fixed')

    for pi in body_paras:
        if not pi.text.strip():
            continue
        para = doc.paragraphs[pi.index]
        apply_line_spacing(para, spacing_pt, spacing_mode)

    label = f"{spacing_pt}x" if spacing_mode == 'multiple' else f"{spacing_pt}pt"
    log.info(f"  [fix] 行距 → {label}")


def _fix_paragraph_alignment(doc, analysis, spec, check):
    """修复段落对齐。"""
    body_region = analysis.get_region(Region.BODY)
    if not body_region:
        return

    body_paras = analysis.get_body_paragraphs()
    alignment = spec.alignment_for('body')

    for pi in body_paras:
        if not pi.text.strip():
            continue
        para = doc.paragraphs[pi.index]
        apply_alignment(para, alignment)

    log.info(f"  [fix] 对齐方式 → {alignment}")


def _fix_first_line_indent(doc, analysis, spec, check):
    """修复首行缩进（CJK 感知）。"""
    body_region = analysis.get_region(Region.BODY)
    if not body_region:
        return

    font_size_pt = spec.size_pt('body_pt')
    body_paras = analysis.get_body_paragraphs()
    from format_applier import _detect_heading_level, _detect_list_level, _paragraph_has_numPr

    for pi in body_paras:
        if not pi.text.strip():
            continue
        text = pi.text.strip()
        if _detect_heading_level(text):
            continue
        # 样式级标题检测（fix_engine 首行缩进需同样跳过）
        para = doc.paragraphs[pi.index]
        style_name = (para.style.name or '').lower()
        if style_name.startswith('heading'):
            continue
        if _detect_list_level(text) is not None:
            continue
        pPr = para._p.find(qn('w:pPr'))
        if pPr is not None:
            ind = pPr.find(qn('w:ind'))
            if ind is not None:
                hanging = ind.get(qn('w:hanging'))
                if hanging is not None and int(hanging) > 0:
                    continue
        if _paragraph_has_numPr(para):
            continue
        # CJK 感知的首行缩进
        if has_cjk(text):
            indent_chars = spec.spacing.get('first_line_indent_chars', 2)
        else:
            indent_chars = spec.spacing.get('english_first_line_indent_chars', 4)
        apply_first_line_indent(para, indent_chars, font_size_pt)

    log.info(f"  [fix] 首行缩进 → CJK感知 (中文2字符/英文4字符)")


def _fix_table_borders(doc, analysis, spec, check):
    """修复表格边框。"""
    for table in doc.tables:
        apply_table_borders(table, 'single')
    log.info(f"  [fix] 表格边框 → {len(doc.tables)} 个表格")


def _fix_table_header_fonts(doc, analysis, spec, check):
    """修复表头字体。"""
    header_fp = FontPair.from_spec(
        spec.font_pair('revision_header'),
        size_pt=spec.size_pt('revision_header_pt'),
        bold=True,
    )

    for table in doc.tables:
        apply_table_header_font(table, header_fp)

    log.info(f"  [fix] 表头字体 → {header_fp.cjk}")


def _fix_table_body_fonts(doc, analysis, spec, check):
    """修复所有表格表体字体。"""
    body_fp = FontPair.from_spec(
        spec.font_pair('body'),
        size_pt=spec.size_pt('body_pt'),
    )

    fixed = 0
    for table in doc.tables:
        if len(table.rows) <= 1:
            continue
        for row_idx in range(1, len(table.rows)):
            for cell in table.rows[row_idx].cells:
                for para in cell.paragraphs:
                    if para.text.strip():
                        for run in para.runs:
                            if run.text.strip():
                                set_run_font_xml(run, body_fp)
                        fixed += 1

    log.info(f"  [fix] 表体字体 → {body_fp.cjk} ({fixed} cells)")


def _fix_header_fonts(doc, analysis, spec, check):
    """修复页眉字体。"""
    header_fp = FontPair.from_spec(
        spec.font_pair('header'),
        size_pt=spec.size_pt('header_pt'),
    )

    for section in doc.sections:
        header = section.header
        if not header or not hasattr(header, 'paragraphs'):
            continue
        if hasattr(header, 'is_linked_to_previous') and header.is_linked_to_previous:
            continue
        for para in header.paragraphs:
            if para.text.strip():
                for run in para.runs:
                    if run.text.strip():
                        set_run_font_xml(run, header_fp)

    log.info(f"  [fix] 页眉字体 → {header_fp.cjk} {header_fp.size_pt}pt")


def _fix_footer_fonts(doc, analysis, spec, check):
    """修复页脚字体。"""
    footer_fp = FontPair.from_spec(
        spec.font_pair('page_number'),
        size_pt=spec.size_pt('page_number_pt'),
    )

    for section in doc.sections:
        footer = section.footer
        if not footer or not hasattr(footer, 'paragraphs'):
            continue
        for para in footer.paragraphs:
            if para.text.strip():
                for run in para.runs:
                    if run.text.strip():
                        set_run_font_xml(run, footer_fp)

    log.info(f"  [fix] 页脚字体 → {footer_fp.cjk} {footer_fp.size_pt}pt")


def _fix_list_indent(doc, analysis, spec, check):
    """修复列表缩进和自动编号。

    G01.0403 V2.0:
      L1: a), b), c)... 有序 左0
      L2: 1), 2), 3)... 有序 左0.74cm
      L3: - 无序 左1.48cm
      L4: ● 无序 左2.22cm
      L5: ○ 无序 左2.96cm
    """
    body_region = analysis.get_region(Region.BODY)
    if not body_region:
        return

    import re as _re
    from format_applier import _detect_heading_level, _detect_list_level, _apply_list_numbering
    from format_applier import (
        _NUM_ID_LETTERED, _NUM_ID_DECIMAL,
        _NUM_ID_BULLET_DASH, _NUM_ID_BULLET_BLACK, _NUM_ID_BULLET_WHITE,
        _LIST_L1_TEXT_RE, _LIST_L2_TEXT_RE,
    )

    body_paras = analysis.get_body_paragraphs()
    indent_map = {1: 0, 2: 0.74, 3: 1.48, 4: 2.22, 5: 2.96}
    num_id_map = {
        1: _NUM_ID_LETTERED,
        2: _NUM_ID_DECIMAL,
        3: _NUM_ID_BULLET_DASH,
        4: _NUM_ID_BULLET_BLACK,
        5: _NUM_ID_BULLET_WHITE,
    }

    for pi in body_paras:
        text = pi.text.strip()
        if not text:
            continue
        if _detect_heading_level(text) is not None:
            continue

        level = _detect_list_level(text)
        if level is None:
            continue

        para = doc.paragraphs[pi.index]
        # 应用自动编号
        num_id = num_id_map.get(level)
        if num_id is not None:
            _apply_list_numbering(para, num_id)

        # 移除手动序号前缀
        if level == 1:
            for run in para.runs:
                m = _re.match(r'^[a-zA-Z][)]\s*', run.text or '')
                if m:
                    run.text = run.text[m.end():]
                    break
        elif level == 2:
            for run in para.runs:
                m = _re.match(r'^\d+[)）]\s*', run.text or '')
                if m:
                    run.text = run.text[m.end():]
                    break

        clear_paragraph_indent(para)

    log.info(f"  [fix] 列表缩进+编号 → L1=0/L2=0.74/L3=1.48/L4=2.22/L5=2.96cm")


def _fix_heading_indent(doc, analysis, spec, check):
    """修复标题缩进。"""
    body_region = analysis.get_region(Region.BODY)
    if not body_region:
        return

    from format_applier import _detect_heading_level
    body_paras = analysis.get_body_paragraphs()

    for pi in body_paras:
        level = _detect_heading_level(pi.text.strip())
        if level is None:
            para = doc.paragraphs[pi.index]
            style_name = (para.style.name or '').lower()
            if style_name.startswith('heading'):
                try:
                    level = int(style_name.split()[-1])
                except (ValueError, IndexError):
                    level = 1
        if level is None:
            continue
        para = doc.paragraphs[pi.index]
        clear_paragraph_indent(para)

    log.info(f"  [fix] 标题缩进 → left=0, first_line=0")


def _fix_figure_caption(doc, analysis, spec, check):
    """修复图标题格式。"""
    body_region = analysis.get_region(Region.BODY)
    if not body_region:
        return

    fig_regex = spec.figure_caption.get('detection_regex',
        r'^(图\s*\d+(-\d+)?|Figure\s*\d+|Fig\.?\s*\d+)')
    import re as _re
    _FIG_RE = _re.compile(fig_regex, _re.IGNORECASE)
    body_paras = analysis.get_body_paragraphs()
    fp = FontPair.from_spec(
        spec.font_pair('figure_caption'),
        size_pt=spec.size_pt('figure_caption_pt'),
    )
    fig_align = spec.alignment_for('figure_caption', default='center')

    for pi in body_paras:
        if not _FIG_RE.match(pi.text.strip()):
            continue
        para = doc.paragraphs[pi.index]
        for run in para.runs:
            if run.text.strip():
                set_run_font_xml(run, fp)
        apply_alignment(para, fig_align)
        clear_paragraph_indent(para)

    log.info(f"  [fix] 图标题 → {fp.cjk} {fp.size_pt}pt {fig_align}")


def _fix_table_caption(doc, analysis, spec, check):
    """修复表标题格式。"""
    body_region = analysis.get_region(Region.BODY)
    if not body_region:
        return

    tbl_regex = spec.table_caption.get('detection_regex',
        r'^(表\s*\d+(-\d+)?|Table\s*\d+)')
    import re as _re
    _TAB_RE = _re.compile(tbl_regex, _re.IGNORECASE)
    body_paras = analysis.get_body_paragraphs()
    fp = FontPair.from_spec(
        spec.font_pair('table_caption'),
        size_pt=spec.size_pt('table_caption_pt'),
    )
    tbl_align = spec.alignment_for('table_caption', default='center')

    for pi in body_paras:
        if not _TAB_RE.match(pi.text.strip()):
            continue
        para = doc.paragraphs[pi.index]
        for run in para.runs:
            if run.text.strip():
                set_run_font_xml(run, fp)
        apply_alignment(para, tbl_align)
        apply_alignment(para, 'center')
        clear_paragraph_indent(para)

    log.info(f"  [fix] 表标题 → {fp.cjk} {fp.size_pt}pt 居中")


# ──────────────────────────────────────────────
# 修复处理器注册表
# ──────────────────────────────────────────────

FIX_HANDLERS = {
    'page_margins':          _fix_page_margins,
    'page_size':             _fix_page_size,
    'cover_fonts':           _fix_cover_fonts,
    'body_fonts':            _fix_body_fonts,
    'heading_fonts':         _fix_heading_fonts,
    'revision_section':      _fix_revision_section,
    'toc_section':           _fix_toc_section,
    'line_spacing':          _fix_line_spacing,
    'paragraph_alignment':   _fix_paragraph_alignment,
    'first_line_indent':     _fix_first_line_indent,
    'page_numbers':          None,  # 页码需手动通过 Word 添加
    'table_borders':         _fix_table_borders,
    'table_header_fonts':    _fix_table_header_fonts,
    'table_body_fonts':      _fix_table_body_fonts,
    'header_fonts':          _fix_header_fonts,
    'footer_fonts':          _fix_footer_fonts,
    'list_indent':           _fix_list_indent,
    'heading_indent':        _fix_heading_indent,
    'figure_caption':        _fix_figure_caption,
    'table_caption':         _fix_table_caption,
}
