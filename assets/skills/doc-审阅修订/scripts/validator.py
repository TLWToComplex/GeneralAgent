"""
validator.py — 逐项校验引擎

负责：
1. 打开格式化后的 docx，逐项校验格式合规性
2. 与 Spec 进行对比
3. 生成结构化校验报告（通过/失败/警告）
4. 返回未通过项列表供 fix_engine 使用
"""

from pathlib import Path
import json
import re
from docx import Document
from docx.shared import Cm, Pt
from docx.oxml.ns import qn

from utils import log
from doc_analyzer import analyze_document, Region, RunInfo
from font_manager import ALIGNMENT_MAP, has_cjk

# 缺陷模式库（可选，不存在时跳过自审）
try:
    from _defect_patterns import run_all_checks as _run_defect_checks
except ImportError:
    _run_defect_checks = None


# ──────────────────────────────────────────────
# 校验结果类型
# ──────────────────────────────────────────────

class Result:
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


class CheckResult:
    """单条检查结果。"""

    def __init__(self, check_id: str, status: str, message: str,
                 actual: str = None, expected: str = None, location: str = None):
        self.check_id = check_id
        self.status = status
        self.message = message
        self.actual = actual
        self.expected = expected
        self.location = location

    def to_dict(self):
        return {
            'check_id': self.check_id,
            'status': self.status,
            'message': self.message,
            'actual': self.actual,
            'expected': self.expected,
            'location': self.location,
        }

    def __repr__(self):
        emoji = {'PASS': '✓', 'FAIL': '✗', 'WARN': '⚠', 'SKIP': '⊘'}
        return f"[{emoji[self.status]} {self.check_id}] {self.message}"


class ValidationReport:
    """校验报告。"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.results = []
        self.self_review_results = []  # 语义级自审结果
        self.summary = {
            'total': 0, 'passed': 0, 'failed': 0, 'warned': 0, 'skipped': 0
        }

    def add(self, result: CheckResult):
        self.results.append(result)
        self.summary['total'] += 1
        if result.status == Result.PASS:
            self.summary['passed'] += 1
        elif result.status == Result.FAIL:
            self.summary['failed'] += 1
        elif result.status == Result.WARN:
            self.summary['warned'] += 1
        elif result.status == Result.SKIP:
            self.summary['skipped'] += 1

    @property
    def passed(self):
        return self.summary['failed'] == 0

    @property
    def failed_items(self):
        return [r for r in self.results if r.status == Result.FAIL]

    @property
    def warn_items(self):
        return [r for r in self.results if r.status == Result.WARN]

    def to_dict(self):
        base = {
            'filepath': self.filepath,
            'summary': self.summary,
            'results': [r.to_dict() for r in self.results],
        }
        if self.self_review_results:
            base['self_review'] = self.self_review_results
            self_review_errors = sum(1 for r in self.self_review_results
                                     if r.get('severity') == 'error')
            self_review_warnings = sum(1 for r in self.self_review_results
                                       if r.get('severity') == 'warning')
            base['self_review_summary'] = {
                'total': len(self.self_review_results),
                'error': self_review_errors,
                'warning': self_review_warnings,
                'info': sum(1 for r in self.self_review_results
                            if r.get('severity') == 'info'),
            }
        return base

    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def print_summary(self):
        lines = []
        lines.append("=" * 60)
        lines.append(f"校验报告: {self.filepath}")
        lines.append(f"  总计: {self.summary['total']}  |  "
                     f"通过: {self.summary['passed']}  |  "
                     f"失败: {self.summary['failed']}  |  "
                     f"警告: {self.summary['warned']}  |  "
                     f"跳过: {self.summary['skipped']}")
        lines.append("-" * 60)
        for r in self.results:
            if r.status in (Result.FAIL, Result.WARN):
                lines.append(f"  {r}")
        lines.append("=" * 60)
        report = "\n".join(lines)
        log.info(f"\n{report}")
        return report


# ──────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────

def validate_document(filepath: str, spec) -> ValidationReport:
    """
    逐项校验文档格式合规性。

    Args:
        filepath: 待校验的 docx 文件路径
        spec: Spec 对象

    Returns:
        ValidationReport 对象
    """
    filepath = str(Path(filepath).resolve())
    log.info(f"开始校验文档: {filepath}")

    report = ValidationReport(filepath)
    doc = Document(filepath)
    analysis = analyze_document(filepath, spec)

    # 按 spec.validation.checks 顺序执行
    checks = spec.validation.get('checks', [])

    for check_name in checks:
        handler = CHECK_HANDLERS.get(check_name)
        if handler:
            handler(doc, analysis, spec, report)
        else:
            report.add(CheckResult(check_name, Result.SKIP,
                                   f"未知检查项: {check_name}"))

    report.print_summary()

    # 自审：语义级缺陷检测（追加到最终报告）
    if _run_defect_checks is not None:
        try:
            defect_results = _run_defect_checks(doc, spec)
            if defect_results:
                report.self_review_results = defect_results
                log.info(f"自审完成：发现 {len(defect_results)} 项语义缺陷")
                for d in defect_results:
                    sev = {'error': '错误', 'warning': '警告', 'info': '提示'}.get(d['severity'], '?')
                    pos_info = ', '.join([f"P[{p}]" for p, _ in d['positions'][:3]])
                    log.info(f"  [{sev}] {d['id']} {d['name']} @ {pos_info}")
            else:
                log.info("自审通过：未发现已知缺陷模式")
        except Exception as e:
            log.warning(f"自审执行异常: {e}")

    return report


# ──────────────────────────────────────────────
# 各检查项处理函数
# ──────────────────────────────────────────────

def _check_page_margins(doc, analysis, spec, report: ValidationReport):
    """检查页面边距。"""
    page = spec.page
    # EMU → cm: 1 cm = 360000 EMU
    EMU_PER_CM = 360000
    for i, section in enumerate(doc.sections):
        loc = f"Section[{i}]"

        checks = [
            ('上边距', section.top_margin, page['margin_top_cm']),
            ('下边距', section.bottom_margin, page['margin_bottom_cm']),
            ('左边距', section.left_margin, page['margin_left_cm']),
            ('右边距', section.right_margin, page['margin_right_cm']),
        ]
        for label, actual_emu, expected_cm in checks:
            actual_cm = actual_emu / EMU_PER_CM
            expected_emu = Cm(expected_cm)
            if abs(actual_emu - expected_emu) > Cm(0.15):
                report.add(CheckResult('page_margins', Result.FAIL,
                    f"{label}不符", f"{actual_cm:.2f}cm", f"{expected_cm}cm", loc))
            else:
                report.add(CheckResult('page_margins', Result.PASS,
                    f"{label}通过", f"{actual_cm:.2f}cm", f"{expected_cm}cm", loc))


def _check_page_size(doc, analysis, spec, report: ValidationReport):
    """检查页面尺寸。"""
    page = spec.page
    sizes = {
        'A4': (21.0, 29.7),
        'A3': (29.7, 42.0),
        'Letter': (21.59, 27.94),
        'Legal': (21.59, 35.56),
    }
    expected_w, expected_h = sizes.get(page['size'], sizes['A4'])
    if page.get('orientation') == 'landscape':
        expected_w, expected_h = expected_h, expected_w

    for i, section in enumerate(doc.sections):
        loc = f"Section[{i}]"
        actual_w = section.page_width / 360000  # EMU → cm
        actual_h = section.page_height / 360000

        if abs(actual_w - expected_w) > 0.3:
            report.add(CheckResult('page_size', Result.FAIL,
                f"页面宽度不符", f"{actual_w:.1f}cm", f"{expected_w:.1f}cm", loc))
        else:
            report.add(CheckResult('page_size', Result.PASS,
                f"页面宽度通过", f"{actual_w:.1f}cm", f"{expected_w:.1f}cm", loc))

        if abs(actual_h - expected_h) > 0.3:
            report.add(CheckResult('page_size', Result.FAIL,
                f"页面高度不符", f"{actual_h:.1f}cm", f"{expected_h:.1f}cm", loc))
        else:
            report.add(CheckResult('page_size', Result.PASS,
                f"页面高度通过", f"{actual_h:.1f}cm", f"{expected_h:.1f}cm", loc))


def _check_cover_fonts(doc, analysis, spec, report: ValidationReport):
    """检查封面字体（段落+表格，含 CJK 和 Latin 校验）。"""
    cover_region = analysis.get_region(Region.COVER)
    if not cover_region:
        report.add(CheckResult('cover_fonts', Result.SKIP, "未检测到封面区域"))
        return

    from format_applier import _detect_heading_level

    cover_paras = analysis.get_cover_paragraphs()
    total = len(cover_paras)
    issues = []
    latin_issues = 0

    for pi in cover_paras:
        if not pi.text.strip():
            continue
        pos = pi.index - cover_region.start

        # 按位置推断封面段落类型（与 format_applier 保持一致）
        if pos == 0:
            expected_cjk = spec.font_pair('cover_title')['cjk']
            expected_latin = spec.font_pair('cover_title')['latin']
            label = 'cover_title'
        elif pos == total - 1 or pos == total - 2:
            expected_cjk = spec.font_pair('cover_info')['cjk']
            expected_latin = spec.font_pair('cover_info')['latin']
            label = 'cover_info'
        else:
            expected_cjk = spec.font_pair('cover_subtitle')['cjk']
            expected_latin = spec.font_pair('cover_subtitle')['latin']
            label = 'cover_subtitle'

        for run in pi.runs:
            # CJK 字体检查（仅含 CJK 字符的 run）
            if has_cjk(run.text) and run.cjk_font and run.cjk_font != expected_cjk:
                issues.append(f"P[{pi.index}]({label}) cjk={run.cjk_font}≠{expected_cjk}")
                break
            # Latin 字体检查（所有有文本的 run）
            actual_latin = run.latin_font
            if actual_latin and actual_latin != expected_latin:
                latin_issues += 1

    # —— 封面表格字体检查 ——
    cover_cfg = spec.special_sections.get('cover', {})
    COVER_KEYWORDS = cover_cfg.get('detection_keywords',
                                   ['项目令号', '密级', '文件编号', '版本', '阶段', '拟制', '审核',
                                    '会签', '批准', '日期', '阶段标记'])
    expected_latin_cover = spec.font_pair('cover_info')['latin']
    expected_cjk_cover = spec.font_pair('cover_info')['cjk']
    table_cjk_issues = 0
    table_latin_issues = 0

    for table in doc.tables:
        if not table.rows:
            continue
        first_cell = table.rows[0].cells[0].text.strip() if table.rows[0].cells else ''
        if not any(kw in first_cell for kw in COVER_KEYWORDS):
            continue

        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    for run in para.runs:
                        if not run.text.strip():
                            continue
                        rPr = run._r.find(qn('w:rPr'))
                        if rPr is not None:
                            rFonts = rPr.find(qn('w:rFonts'))
                            if rFonts is not None:
                                cjk = rFonts.get(qn('w:eastAsia'), '')
                                if cjk and cjk != expected_cjk_cover and has_cjk(run.text):
                                    table_cjk_issues += 1
                                latin = rFonts.get(qn('w:ascii'), '')
                                if latin and latin != expected_latin_cover:
                                    table_latin_issues += 1

    if table_cjk_issues > 0:
        issues.append(f"封面表格 CJK={table_cjk_issues}处")
    if table_latin_issues > 0:
        latin_issues += table_latin_issues
        issues.append(f"封面表格 Latin={table_latin_issues}处")

    if issues:
        report.add(CheckResult('cover_fonts', Result.FAIL,
            f"封面字体不符", f"{len(issues)} 类: {issues[:3]}", "-",
            f"段落 {cover_region.start}-{cover_region.end}"))
    else:
        report.add(CheckResult('cover_fonts', Result.PASS,
            f"封面字体通过 (CJK+Latin)", expected_cjk, expected_latin))

    if latin_issues > 0:
        report.add(CheckResult('cover_fonts', Result.WARN,
            f"封面 Latin 字体可能不符", f"{latin_issues} 处 run", expected_latin))


def _check_body_fonts(doc, analysis, spec, report: ValidationReport):
    """检查正文字体（跳过标题段落）。"""
    body_region = analysis.get_region(Region.BODY)
    if not body_region:
        report.add(CheckResult('body_fonts', Result.SKIP, "未检测到正文区域"))
        return

    from format_applier import _detect_heading_level

    body_paras = analysis.get_body_paragraphs()
    expected_cjk = spec.font_pair('body')['cjk']
    expected_latin = spec.font_pair('body')['latin']

    cjk_issues = 0
    latin_issues = 0

    for pi in body_paras:
        # 跳过标题段落
        if _detect_heading_level(pi.text.strip()) is not None:
            continue
        for run in pi.runs:
            if not run.text.strip():
                continue
            # 纯英文/数字的 run 不需要 eastAsia，跳过 CJK 检查
            if has_cjk(run.text):
                if not run.cjk_font or run.cjk_font != expected_cjk:
                    cjk_issues += 1
            if run.latin_font and run.latin_font != expected_latin:
                latin_issues += 1

    if cjk_issues > 0:
        report.add(CheckResult('body_fonts', Result.FAIL,
            f"正文 CJK 字体不符", f"{cjk_issues} 处非 {expected_cjk}", expected_cjk,
            f"段落 {body_region.start}-{body_region.end}"))
    else:
        report.add(CheckResult('body_fonts', Result.PASS,
            f"正文 CJK 字体通过", expected_cjk, expected_cjk))

    if latin_issues > 0:
        report.add(CheckResult('body_fonts', Result.WARN,
            f"正文 Latin 字体不符", f"{latin_issues} 处非 {expected_latin}", expected_latin))


def _check_heading_fonts(doc, analysis, spec, report: ValidationReport):
    """检查标题字体。"""
    body_region = analysis.get_region(Region.BODY)
    if not body_region:
        report.add(CheckResult('heading_fonts', Result.SKIP, "未检测到正文区域"))
        return

    from format_applier import _detect_heading_level

    body_paras = analysis.get_body_paragraphs()
    heading_issues = 0

    for pi in body_paras:
        level = _detect_heading_level(pi.text.strip())
        if level is None:
            continue
        key = f'h{level}'
        expected_cjk = spec.font_pair(key)['cjk']

        for run in pi.runs:
            if not run.text.strip():
                continue
            # 纯英文/数字的 run 不需要 eastAsia
            if has_cjk(run.text) and run.cjk_font and run.cjk_font != expected_cjk:
                heading_issues += 1

    if heading_issues > 0:
        report.add(CheckResult('heading_fonts', Result.FAIL,
            f"标题字体不符", f"{heading_issues} 处", "",
            f"段落 {body_region.start}-{body_region.end}"))
    else:
        report.add(CheckResult('heading_fonts', Result.PASS,
            "标题字体通过"))


def _check_revision_section(doc, analysis, spec, report: ValidationReport):
    """检查修订记录区域。"""
    rev_region = analysis.get_region(Region.REVISION)
    if not rev_region:
        report.add(CheckResult('revision_section', Result.WARN,
            "未检测到修订记录区域"))
        return

    rev_paras = analysis.paragraphs[rev_region.start:rev_region.end + 1]
    if not rev_paras:
        return

    expected_cjk = spec.font_pair('revision_title')['cjk']
    expected_latin = spec.font_pair('revision_title')['latin']
    title_text = rev_paras[0].text[:30]

    # 标题字体检查（CJK + Latin）
    title_ok = True
    latin_issues = 0
    for run in rev_paras[0].runs:
        if not run.text.strip():
            continue
        # CJK 检查
        if has_cjk(run.text) and run.cjk_font and run.cjk_font != expected_cjk:
            title_ok = False
            break
        # Latin 检查
        if run.latin_font and run.latin_font != expected_latin:
            latin_issues += 1

    if title_ok:
        if latin_issues > 0:
            report.add(CheckResult('revision_section', Result.WARN,
                f"修订记录标题 CJK 通过, Latin 可能有 {latin_issues} 处问题: \"{title_text}\"",
                f"Latin期望={expected_latin}", f"CJK={expected_cjk}"))
        else:
            report.add(CheckResult('revision_section', Result.PASS,
                f"修订记录标题字体通过 (CJK+Latin): \"{title_text}\"",
                expected_cjk, expected_latin))
    else:
        report.add(CheckResult('revision_section', Result.FAIL,
            f"修订记录标题字体不符: \"{title_text}\"", "", expected_cjk))


def _check_toc_section(doc, analysis, spec, report: ValidationReport):
    """检查目录区域。"""
    toc_region = analysis.get_region(Region.TOC)
    if not toc_region:
        report.add(CheckResult('toc_section', Result.WARN,
            "未检测到目录区域"))
        return

    toc_paras = analysis.paragraphs[toc_region.start:toc_region.end + 1]
    if not toc_paras:
        return

    expected_cjk = spec.font_pair('toc_title')['cjk']
    title_text = toc_paras[0].text[:30]

    title_ok = True
    for run in toc_paras[0].runs:
        if run.cjk_font and run.cjk_font != expected_cjk:
            title_ok = False
            break

    if title_ok:
        report.add(CheckResult('toc_section', Result.PASS,
            f"目录标题字体通过: \"{title_text}\"", expected_cjk, expected_cjk))
    else:
        report.add(CheckResult('toc_section', Result.FAIL,
            f"目录标题字体不符: \"{title_text}\"", "", expected_cjk))


def _check_line_spacing(doc, analysis, spec, report: ValidationReport):
    """检查行距（仅正文段落，跳过标题）。"""
    body_region = analysis.get_region(Region.BODY)
    if not body_region:
        report.add(CheckResult('line_spacing', Result.SKIP, "未检测到正文区域"))
        return

    from format_applier import _detect_heading_level

    body_paras = analysis.get_body_paragraphs()
    line_spacing_mode = spec.spacing.get('body_line_spacing_mode', 'fixed')

    if line_spacing_mode == 'multiple':
        expected_mult = float(spec.spacing['body_line_spacing_pt'])
        body_paras_list = []
        for pi in body_paras:
            if not pi.text.strip():
                continue
            if _detect_heading_level(pi.text.strip()) is not None:
                continue
            body_paras_list.append(pi)

        # 抽样检查（倍数行距需要实际 paragraph 对象）
        issues = 0
        for pi in body_paras_list:
            para = doc.paragraphs[pi.index]
            pf = para.paragraph_format
            from docx.enum.text import WD_LINE_SPACING
            rule = pf.line_spacing_rule
            actual_mult = float(pf.line_spacing) if pf.line_spacing else 0
            # MULTIPLE (5), ONE_POINT_FIVE (1), DOUBLE (2) 都是倍数模式
            if rule == WD_LINE_SPACING.ONE_POINT_FIVE and abs(expected_mult - 1.5) < 0.1:
                continue  # ONE_POINT_FIVE 对 1.5x 规范通过
            if rule not in (WD_LINE_SPACING.MULTIPLE, WD_LINE_SPACING.ONE_POINT_FIVE, WD_LINE_SPACING.DOUBLE):
                issues += 1
            elif abs(actual_mult - expected_mult) > 0.1:
                issues += 1

        if issues > 0:
            report.add(CheckResult('line_spacing', Result.FAIL,
                f"行距不符", f"{issues} 处", f"{expected_mult}x"))
        else:
            report.add(CheckResult('line_spacing', Result.PASS,
                f"行距通过", f"{expected_mult}x"))
    else:
        expected = Pt(spec.spacing['body_line_spacing_pt'])
        tol = spec.validation.get('tolerances', {}).get('line_spacing_pt', 1.0)
        tolerance = Pt(tol)

        issues = 0
        for pi in body_paras:
            if not pi.text.strip():
                continue
            if _detect_heading_level(pi.text.strip()) is not None:
                continue
            actual = pi.para_format.get('line_spacing')
            if actual and abs(actual - expected) > tolerance:
                issues += 1

        if issues > 0:
            report.add(CheckResult('line_spacing', Result.FAIL,
                f"行距不符", f"{issues} 处", f"{spec.spacing['body_line_spacing_pt']}pt"))
        else:
            report.add(CheckResult('line_spacing', Result.PASS,
                f"行距通过", f"{spec.spacing['body_line_spacing_pt']}pt"))


def _check_paragraph_alignment(doc, analysis, spec, report: ValidationReport):
    """检查段落对齐（仅正文段落，跳过标题）。"""
    body_region = analysis.get_region(Region.BODY)
    if not body_region:
        report.add(CheckResult('paragraph_alignment', Result.SKIP, "未检测到正文区域"))
        return

    from format_applier import _detect_heading_level

    body_paras = analysis.get_body_paragraphs()
    expected_alignment = spec.alignment_for('body').upper()

    # JUSTIFY == BOTH (两端对齐)
    EQUIVALENT = {
        'BOTH': {'BOTH', 'JUSTIFY'},
        'JUSTIFY': {'BOTH', 'JUSTIFY'},
        'LEFT': {'LEFT'},
        'CENTER': {'CENTER'},
        'RIGHT': {'RIGHT'},
    }
    valid_aliases = EQUIVALENT.get(expected_alignment, {expected_alignment})

    misaligned = 0
    for pi in body_paras:
        if not pi.text.strip():
            continue
        if _detect_heading_level(pi.text.strip()) is not None:
            continue
        a = str(pi.alignment).upper() if pi.alignment else 'NONE'
        if not any(alias in a for alias in valid_aliases):
            misaligned += 1

    if misaligned > 0:
        report.add(CheckResult('paragraph_alignment', Result.WARN,
            f"对齐方式不符", f"{misaligned} 处", expected_alignment))
    else:
        report.add(CheckResult('paragraph_alignment', Result.PASS,
            f"对齐方式通过", expected_alignment))


def _check_first_line_indent(doc, analysis, spec, report: ValidationReport):
    """检查首行缩进。"""
    body_region = analysis.get_region(Region.BODY)
    if not body_region:
        report.add(CheckResult('first_line_indent', Result.SKIP, "未检测到正文区域"))
        return

    font_size_pt = spec.size_pt('body_pt')

    body_paras = analysis.get_body_paragraphs()
    issues = 0
    for pi in body_paras:
        if not pi.text.strip():
            continue
        text = pi.text.strip()
        from format_applier import _detect_heading_level, _detect_list_level, _paragraph_has_numPr
        from font_manager import has_cjk
        if _detect_heading_level(text):
            continue  # 跳过标题
        if _detect_list_level(text) is not None:
            continue
        # CJK 感知的首行缩进期望值
        if has_cjk(text):
            indent_chars = spec.spacing.get('first_line_indent_chars', 2)
        else:
            indent_chars = spec.spacing.get('english_first_line_indent_chars', 4)
        expected = Pt(indent_chars * font_size_pt)
    tol = spec.validation.get('tolerances', {}).get('first_line_indent_pt', 3)
    tolerance = Pt(tol)

    body_paras = analysis.get_body_paragraphs()
    issues = 0
    for pi in body_paras:
        if not pi.text.strip():
            continue
        from format_applier import _detect_heading_level, _detect_list_level, _paragraph_has_numPr
        if _detect_heading_level(pi.text.strip()):
            continue  # 跳过标题
        # 跳过列表项（列表项使用悬挂缩进，不需要首行缩进）
        if _detect_list_level(pi.text.strip()) is not None:
            continue
        # 跳过有悬挂缩进的段落（_apply_existing_numPr_indent 处理的列表项）
        # 注意：python-docx 的 para_format.get('hanging') 不可靠，
        # 需要从 XML 级别读取 w:hanging 属性
        para = doc.paragraphs[pi.index]
        pPr = para._p.find(qn('w:pPr'))
        if pPr is not None:
            ind = pPr.find(qn('w:ind'))
            if ind is not None:
                hanging_val = ind.get(qn('w:hanging'))
                if hanging_val is not None and int(hanging_val) > 0:
                    continue
        # 跳过有 numPr 的段落（原始文档的自动编号，不应设首行缩进）
        if _paragraph_has_numPr(doc.paragraphs[pi.index]):
            continue
        actual = pi.para_format.get('first_line_indent')
        if actual and abs(actual - expected) > tolerance:
            issues += 1

    if issues > 0:
        report.add(CheckResult('first_line_indent', Result.FAIL,
            f"首行缩进不符", f"{issues} 处", f"{indent_chars}字符"))
    else:
        report.add(CheckResult('first_line_indent', Result.PASS,
            f"首行缩进通过", f"{indent_chars}字符"))


def _check_page_numbers(doc, analysis, spec, report: ValidationReport):
    """检查页码。"""
    has_page_numbers = False
    for section in doc.sections:
        footer = section.footer
        if footer and footer.paragraphs:
            for para in footer.paragraphs:
                if para.text.strip():
                    has_page_numbers = True
                    break

    if has_page_numbers:
        report.add(CheckResult('page_numbers', Result.PASS, "页脚检测到内容"))
    else:
        report.add(CheckResult('page_numbers', Result.WARN, "未检测到页脚内容，可能需要手动添加页码"))


def _check_table_borders(doc, analysis, spec, report: ValidationReport):
    """检查表格边框。"""
    tables = doc.tables
    if not tables:
        report.add(CheckResult('table_borders', Result.SKIP, "文档无表格"))
        return

    border_ok = 0
    border_nok = 0
    for i, table in enumerate(tables):
        tblPr = table._tbl.find(qn('w:tblPr'))
        if tblPr is not None:
            borders = tblPr.find(qn('w:tblBorders'))
            if borders is not None:
                border_ok += 1
            else:
                border_nok += 1
        else:
            border_nok += 1

    if border_nok > 0:
        report.add(CheckResult('table_borders', Result.FAIL,
            f"表格缺少边框", f"{border_nok}/{len(tables)} 个表格", "全部应有边框"))
    else:
        report.add(CheckResult('table_borders', Result.PASS,
            f"表格边框通过", f"{len(tables)} 个表格"))


def _check_table_header_fonts(doc, analysis, spec, report: ValidationReport):
    """检查表格表头字体。"""
    tables = doc.tables
    if not tables:
        report.add(CheckResult('table_header_fonts', Result.SKIP, "文档无表格"))
        return

    expected_cjk = spec.font_pair('revision_header')['cjk']
    issues = 0

    for i, table in enumerate(tables):
        if not table.rows:
            continue
        for cell in table.rows[0].cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    rPr = run._r.find(qn('w:rPr'))
                    if rPr is not None:
                        rFonts = rPr.find(qn('w:rFonts'))
                        if rFonts is not None:
                            cjk = rFonts.get(qn('w:eastAsia'), '')
                            # 纯英文/数字 run 的 eastAsia 被设为 TNR（避免继承错误 CJK 字体），跳过检查
                            if cjk and cjk != expected_cjk and has_cjk(run.text):
                                issues += 1

    if issues > 0:
        report.add(CheckResult('table_header_fonts', Result.FAIL,
            f"表头字体不符", f"{issues} 处", expected_cjk))
    else:
        report.add(CheckResult('table_header_fonts', Result.PASS,
            f"表头字体通过", expected_cjk))


def _check_table_body_fonts(doc, analysis, spec, report: ValidationReport):
    """检查所有表格表体（第2行起）的字体。"""
    tables = doc.tables
    if not tables:
        report.add(CheckResult('table_body_fonts', Result.SKIP, "文档无表格"))
        return

    expected_cjk = spec.font_pair('body')['cjk']
    expected_latin = spec.font_pair('body')['latin']
    issues = 0

    for i, table in enumerate(tables):
        if len(table.rows) <= 1:
            continue  # 只有表头，无表体
        for row_idx in range(1, len(table.rows)):
            for cell in table.rows[row_idx].cells:
                for para in cell.paragraphs:
                    for run in para.runs:
                        if not run.text.strip():
                            continue
                        rPr = run._r.find(qn('w:rPr'))
                        if rPr is not None:
                            rFonts = rPr.find(qn('w:rFonts'))
                            if rFonts is not None:
                                cjk = rFonts.get(qn('w:eastAsia'), '')
                                if cjk and cjk != expected_cjk and has_cjk(run.text):
                                    issues += 1
                                latin = rFonts.get(qn('w:ascii'), '')
                                if latin and latin != expected_latin:
                                    issues += 1

    if issues > 0:
        report.add(CheckResult('table_body_fonts', Result.FAIL,
            f"表体字体不符", f"{issues} 处", f"CJK={expected_cjk}, Latin={expected_latin}"))
    else:
        report.add(CheckResult('table_body_fonts', Result.PASS,
            f"表体字体通过", f"CJK={expected_cjk}, Latin={expected_latin}"))


def _check_header_fonts(doc, analysis, spec, report: ValidationReport):
    """检查页眉字体。"""
    expected_cjk = spec.font_pair('header')['cjk']
    expected_latin = spec.font_pair('header')['latin']
    issues = 0

    for i, section in enumerate(doc.sections):
        header = section.header
        if not header or not hasattr(header, 'paragraphs'):
            continue

        # 跳过后链接的页眉
        if hasattr(header, 'is_linked_to_previous') and header.is_linked_to_previous:
            continue

        for para in header.paragraphs:
            if not para.text.strip():
                continue
            for run in para.runs:
                if not run.text.strip():
                    continue
                rPr = run._r.find(qn('w:rPr'))
                if rPr is not None:
                    rFonts = rPr.find(qn('w:rFonts'))
                    if rFonts is not None:
                        cjk = rFonts.get(qn('w:eastAsia'), '')
                        if cjk and cjk != expected_cjk and has_cjk(run.text):
                            issues += 1
                        latin = rFonts.get(qn('w:ascii'), '')
                        if latin and latin != expected_latin:
                            issues += 1

    if issues > 0:
        report.add(CheckResult('header_fonts', Result.FAIL,
            f"页眉字体不符", f"{issues} 处", f"CJK={expected_cjk}, Latin={expected_latin}"))
    else:
        report.add(CheckResult('header_fonts', Result.PASS,
            f"页眉字体通过", f"CJK={expected_cjk}, Latin={expected_latin}"))


def _check_footer_fonts(doc, analysis, spec, report: ValidationReport):
    """检查页脚字体。"""
    expected_cjk = spec.font_pair('page_number')['cjk']
    expected_latin = spec.font_pair('page_number')['latin']
    issues = 0

    for i, section in enumerate(doc.sections):
        footer = section.footer
        if not footer or not hasattr(footer, 'paragraphs'):
            continue

        for para in footer.paragraphs:
            if not para.text.strip():
                continue
            for run in para.runs:
                if not run.text.strip():
                    continue
                rPr = run._r.find(qn('w:rPr'))
                if rPr is not None:
                    rFonts = rPr.find(qn('w:rFonts'))
                    if rFonts is not None:
                        cjk = rFonts.get(qn('w:eastAsia'), '')
                        if cjk and cjk != expected_cjk and has_cjk(run.text):
                            issues += 1
                        latin = rFonts.get(qn('w:ascii'), '')
                        if latin and latin != expected_latin:
                            issues += 1

    if issues > 0:
        report.add(CheckResult('footer_fonts', Result.FAIL,
            f"页脚字体不符", f"{issues} 处", f"CJK={expected_cjk}, Latin={expected_latin}"))
    else:
        report.add(CheckResult('footer_fonts', Result.PASS,
            f"页脚字体通过", f"CJK={expected_cjk}, Latin={expected_latin}"))


# ──────────────────────────────────────────────
# 列表缩进检查
# ──────────────────────────────────────────────

_LIST_L1_RE = re.compile(r'^[a-zA-Z][)]\s*')
_LIST_L2_RE = re.compile(r'^\d+[)）]\s*')
_LIST_L3_RE = re.compile(r'^[-–—]\s+')
_LIST_L4_RE = re.compile(r'^[●■□▪▫►▸•·]\s*')
_LIST_L5_RE = re.compile(r'^[○◇◆]\s*')


def _check_list_indent(doc, analysis, spec, report: ValidationReport):
    """检查列表项缩进：L1=0, L2=0.74cm, L3=1.48cm, L4=2.22cm, L5=2.96cm。"""
    body_region = analysis.get_region(Region.BODY)
    if not body_region:
        report.add(CheckResult('list_indent', Result.SKIP, "未检测到正文区域"))
        return

    from format_applier import _detect_heading_level

    body_paras = analysis.get_body_paragraphs()
    indent_map = {1: 0, 2: 0.74, 3: 1.48, 4: 2.22, 5: 2.96}
    issues = 0

    for pi in body_paras:
        text = pi.text.strip()
        if not text:
            continue
        if _detect_heading_level(text) is not None:
            continue

        level = None
        if _LIST_L5_RE.match(text):
            level = 5
        elif _LIST_L4_RE.match(text):
            level = 4
        elif _LIST_L3_RE.match(text):
            level = 3
        elif _LIST_L2_RE.match(text):
            level = 2
        elif _LIST_L1_RE.match(text):
            level = 1
        else:
            continue

        expected = indent_map[level]
        # 检查左缩进（自动编号下由 hanging indent 控制）
        actual_left = pi.para_format.get('left_indent')
        if actual_left is not None:
            actual_cm = actual_left / 360000  # EMU to cm
            tol = spec.validation.get('tolerances', {}).get('list_indent_cm', 0.25)
            if abs(actual_cm - expected) > tol:  # 放宽容差（自动编号有偏移）
                issues += 1
                continue
        # 检查首行缩进（应为 0）
        actual_first = pi.para_format.get('first_line_indent')
        tol = spec.validation.get('tolerances', {}).get('heading_indent_pt', 1.0)
        if actual_first is not None and abs(actual_first) > Pt(tol):
            issues += 1

    if issues > 0:
        report.add(CheckResult('list_indent', Result.FAIL,
            f"列表缩进不符", f"{issues} 处", f"L1=0/L2=0.74/L3=1.48/L4=2.22/L5=2.96cm"))
    else:
        report.add(CheckResult('list_indent', Result.PASS,
            f"列表缩进通过", "L1=0, L2=0.74, L3=1.48, L4=2.22, L5=2.96cm"))


def _check_heading_indent(doc, analysis, spec, report: ValidationReport):
    """检查标题缩进：全部 left=0, first_line=0。"""
    body_region = analysis.get_region(Region.BODY)
    if not body_region:
        report.add(CheckResult('heading_indent', Result.SKIP, "未检测到正文区域"))
        return

    from format_applier import _detect_heading_level

    body_paras = analysis.get_body_paragraphs()
    issues = 0

    for pi in body_paras:
        level = _detect_heading_level(pi.text.strip())
        if level is None:
            # 检查段落样式是否为 Word Heading
            para = doc.paragraphs[pi.index]
            style_name = (para.style.name or '').lower()
            if style_name.startswith('heading'):
                try:
                    level = int(style_name.split()[-1])
                except (ValueError, IndexError):
                    level = 1
        if level is None:
            continue
        tol = spec.validation.get('tolerances', {}).get('heading_indent_pt', 1.0)
        # 检查左缩进
        actual_left = pi.para_format.get('left_indent')
        if actual_left is not None and abs(actual_left) > Pt(tol):
            issues += 1
        # 检查首行缩进
        actual_first = pi.para_format.get('first_line_indent')
        if actual_first is not None and abs(actual_first) > Pt(tol):
            issues += 1

    if issues > 0:
        report.add(CheckResult('heading_indent', Result.FAIL,
            f"标题缩进不符", f"{issues} 处", "left=0, first_line=0"))
    else:
        report.add(CheckResult('heading_indent', Result.PASS,
            "标题缩进通过"))


# 图标题 / 表标题 检测正则
_FIGURE_RE = re.compile(
    r'^(图\s*\d+(-\d+)?|Figure\s*\d+|Fig\.?\s*\d+)', re.IGNORECASE)
_TABLE_RE = re.compile(
    r'^(表\s*\d+(-\d+)?|Table\s*\d+)', re.IGNORECASE)


def _check_figure_caption(doc, analysis, spec, report: ValidationReport):
    """检查图标题格式。"""
    body_region = analysis.get_region(Region.BODY)
    if not body_region:
        report.add(CheckResult('figure_caption', Result.SKIP, "未检测到正文区域"))
        return

    fig_regex = spec.figure_caption.get('detection_regex',
        r'^(图\s*\d+(-\d+)?|Figure\s*\d+|Fig\.?\s*\d+)')
    import re as _re
    _RE = _re.compile(fig_regex, _re.IGNORECASE)

    body_paras = analysis.get_body_paragraphs()
    expected_pt = spec.size_pt('figure_caption_pt')
    expected_cjk = spec.font_pair('figure_caption')['cjk']
    fig_align = spec.alignment_for('figure_caption', default='center')
    issues = 0
    found = 0

    for pi in body_paras:
        text = pi.text.strip()
        if not _RE.match(text):
            continue
        found += 1
        para = doc.paragraphs[pi.index]
        for run in para.runs:
            if run.font.size and abs(run.font.size.pt - expected_pt) > 0.5:
                issues += 1
                break
        a = str(pi.alignment).upper() if pi.alignment else ''
        align_upper = fig_align.upper()
        if align_upper not in a:
            issues += 1

    if found == 0:
        report.add(CheckResult('figure_caption', Result.SKIP, "未检测到图标题"))
    elif issues > 0:
        report.add(CheckResult('figure_caption', Result.FAIL,
            f"图标题格式不符", f"{issues} 处/{found}个", f"{fig_align} {expected_cjk} {expected_pt}pt"))
    else:
        report.add(CheckResult('figure_caption', Result.PASS,
            f"图标题格式通过 ({found}个)", f"{fig_align} {expected_cjk} {expected_pt}pt"))


def _check_table_caption(doc, analysis, spec, report: ValidationReport):
    """检查表标题格式。"""
    body_region = analysis.get_region(Region.BODY)
    if not body_region:
        report.add(CheckResult('table_caption', Result.SKIP, "未检测到正文区域"))
        return

    tbl_regex = spec.table_caption.get('detection_regex',
        r'^(表\s*\d+(-\d+)?|Table\s*\d+)')
    import re as _re
    _RE = _re.compile(tbl_regex, _re.IGNORECASE)
    body_paras = analysis.get_body_paragraphs()
    expected_pt = spec.size_pt('table_caption_pt')
    expected_cjk = spec.font_pair('table_caption')['cjk']
    tbl_align = spec.alignment_for('table_caption', default='center')
    issues = 0
    found = 0

    for pi in body_paras:
        text = pi.text.strip()
        if not _RE.match(text):
            continue
        found += 1
        para = doc.paragraphs[pi.index]

        # 字号
        for run in para.runs:
            if run.font.size and abs(run.font.size.pt - expected_pt) > 0.5:
                issues += 1
                break

        # 对齐
        a = str(pi.alignment).upper() if pi.alignment else ''
        align_upper = tbl_align.upper()
        if align_upper not in a:
            issues += 1

    if found == 0:
        report.add(CheckResult('table_caption', Result.SKIP, "未检测到表标题"))
    elif issues > 0:
        report.add(CheckResult('table_caption', Result.FAIL,
            f"表标题格式不符", f"{issues} 处/{found}个", f"{tbl_align} {expected_cjk} {expected_pt}pt"))
    else:
        report.add(CheckResult('table_caption', Result.PASS,
            f"表标题格式通过 ({found}个)", f"{tbl_align} {expected_cjk} {expected_pt}pt"))


# ──────────────────────────────────────────────
# 检查项处理器注册表
# ──────────────────────────────────────────────

CHECK_HANDLERS = {
    'page_margins':         _check_page_margins,
    'page_size':            _check_page_size,
    'cover_fonts':          _check_cover_fonts,
    'body_fonts':           _check_body_fonts,
    'heading_fonts':        _check_heading_fonts,
    'revision_section':     _check_revision_section,
    'toc_section':          _check_toc_section,
    'line_spacing':         _check_line_spacing,
    'paragraph_alignment':  _check_paragraph_alignment,
    'first_line_indent':    _check_first_line_indent,
    'page_numbers':         _check_page_numbers,
    'table_borders':        _check_table_borders,
    'table_header_fonts':   _check_table_header_fonts,
    'table_body_fonts':     _check_table_body_fonts,
    'header_fonts':         _check_header_fonts,
    'footer_fonts':         _check_footer_fonts,
    'list_indent':          _check_list_indent,
    'heading_indent':       _check_heading_indent,
    'figure_caption':       _check_figure_caption,
    'table_caption':        _check_table_caption,
}
