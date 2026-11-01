"""
format_applier.py — 格式应用引擎

负责：
1. 逐区域应用格式规范（页面设置、封面、目录、正文、修订记录）
2. 协调 font_manager、doc_analyzer 等模块
3. 写回 docx 并输出格式化后的文档
"""

from pathlib import Path
from copy import deepcopy
import re
from docx import Document
from docx.shared import Pt, Cm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from utils import log, backup_file, safe_write_docx, enable_track_revisions_in_doc
from track_changes import RevisionTracker
from font_manager import (
    FontPair, apply_font_to_paragraph, apply_font_to_run,
    apply_page_margins, apply_page_size, apply_alignment,
    apply_line_spacing, apply_first_line_indent, apply_paragraph_spacing,
    apply_table_header_font, apply_table_header_bold,
    apply_table_header_shading, apply_table_borders,
    set_default_body_font, apply_left_indent, clear_paragraph_indent,
    add_page_number_to_section, _get_or_create_ind,
    has_cjk, apply_paragraph_xml_settings, apply_outline_level,
)
from doc_analyzer import analyze_document, Region
from lxml import etree

# ──────────────────────────────────────────────
# 列表自动编号 — 编号定义 ID 常量
# ──────────────────────────────────────────────

# 抽象编号 ID
_ABSTRACT_NUM_ID_LETTERED = 100   # a), b), c)...
_ABSTRACT_NUM_ID_DECIMAL = 101    # 1), 2), 3)...
_ABSTRACT_NUM_ID_BULLET_DASH = 102  # - 无序列表
_ABSTRACT_NUM_ID_BULLET_BLACK = 103  # ● 无序列表
_ABSTRACT_NUM_ID_BULLET_WHITE = 104  # ○ 无序列表

# 编号实例 ID
_NUM_ID_LETTERED = 100
_NUM_ID_DECIMAL = 101
_NUM_ID_BULLET_DASH = 102
_NUM_ID_BULLET_BLACK = 103
_NUM_ID_BULLET_WHITE = 104


# ──────────────────────────────────────────────
# 格式应用上下文
# ──────────────────────────────────────────────

class FormatContext:
    """格式应用上下文，持有分析结果和规范。"""

    def __init__(self, analysis, spec, track_changes: bool = True):
        self.analysis = analysis
        self.spec = spec
        self.applied_count = 0
        self.errors = []
        self.track_changes = track_changes
        self.tracker = RevisionTracker() if track_changes else None

    def log_apply(self, msg: str):
        self.applied_count += 1
        log.info(f"  [{self.applied_count}] {msg}")

    def log_error(self, msg: str):
        self.errors.append(msg)
        log.warning(f"  [ERR] {msg}")


# ──────────────────────────────────────────────
# 主入口 + 标题样式初始化
# ──────────────────────────────────────────────

def _normalize_heading_style(style_elem, level: int):
    """将 Heading 样式的 XML 定义规范化为符合 G01.0403 标准。

    解决两个问题：
    1. 清除自带 numPr（避免标题前出现"附录X"等自动编号）
    2. 清除冲突的默认格式（居中、错误字体行距等），防止覆盖 spec 的格式设置

    所有实际格式由 _apply_heading_format 在段落级应用，
    样式级仅保留 outlineLvl 和必要的 pPr 结构。
    """
    # 找 pPr
    pPr = style_elem.find(qn('w:pPr'))
    if pPr is None:
        pPr = etree.SubElement(style_elem, qn('w:pPr'))

    # 清除 numPr（避免自动编号干扰）
    numPr = pPr.find(qn('w:numPr'))
    if numPr is not None:
        pPr.remove(numPr)

    # 设置左对齐（覆盖可能存在的居中）
    jc = pPr.find(qn('w:jc'))
    if jc is None:
        jc = etree.SubElement(pPr, qn('w:jc'))
    jc.set(qn('w:val'), 'left')

    # 清除 spacing（由段落级控制）
    spacing = pPr.find(qn('w:spacing'))
    if spacing is not None:
        pPr.remove(spacing)

    # 设置 outlineLvl（确保存在且正确）
    outline = pPr.find(qn('w:outlineLvl'))
    if outline is None:
        outline = etree.SubElement(pPr, qn('w:outlineLvl'))
    outline.set(qn('w:val'), str(level - 1))

    # 清除 run 级默认格式（由段落级 apply_font_to_paragraph 控制）
    rPr = style_elem.find(qn('w:rPr'))
    if rPr is not None:
        style_elem.remove(rPr)


def _ensure_heading_styles(doc):
    """确保文档包含规范化的 Heading 1~4 样式。

    参考文档 05_DH2007_final_v4.docx 的标题使用 pStyle 引用 Heading 样式，
    WPS 导航窗格依赖此结构识别标题层级。

    本函数：
    1. 创建缺失的 Heading 2/3/4 样式
    2. 规范化所有 Heading 样式（清除 numPr、冲突格式等）
    3. 样式级仅保留 outlineLvl，实际格式由段落级控制
    """
    from docx.enum.style import WD_STYLE_TYPE

    # 先确保 Heading 1 存在，作为基础
    try:
        h1 = doc.styles['Heading 1']
    except KeyError:
        log.warning("文档中无 Heading 1 样式，尝试创建")
        h1 = doc.styles.add_style('Heading 1', WD_STYLE_TYPE.PARAGRAPH)

    # 创建缺失的 Heading 2/3/4
    for level in [2, 3, 4]:
        style_name = f'Heading {level}'
        try:
            _ = doc.styles[style_name]
            log.info(f"Heading {level} 样式已存在")
        except KeyError:
            try:
                new_style = doc.styles.add_style(style_name, WD_STYLE_TYPE.PARAGRAPH)
                new_style.base_style = h1
                log.info(f"已创建缺失的 {style_name}")
            except Exception as e:
                log.warning(f"创建 {style_name} 失败: {e}")

    # 规范化所有 Heading 1~4 样式定义
    for level in range(1, 5):
        try:
            hs = doc.styles[f'Heading {level}']
            _normalize_heading_style(hs._element, level)
            log.info(f"Heading {level} 样式已规范化")
        except KeyError:
            pass


def apply_format(input_path: str, spec, output_path: str) -> str:
    """
    完整格式应用流程。

    Args:
        input_path: 输入 docx 文件路径
        spec: Spec 对象
        output_path: 输出 docx 文件路径

    Returns:
        输出文件路径
    """
    input_path = str(Path(input_path).resolve())
    output_path = str(Path(output_path).resolve())

    log.info(f"开始格式应用: {input_path} → {output_path}")

    # 重置封面表格索引（每次调用独立）
    global _COVER_TABLE_INDICES
    _COVER_TABLE_INDICES = set()

    # 1. 分析文档
    analysis = analyze_document(input_path, spec)
    ctx = FormatContext(analysis, spec)

    # 2. 打开文档
    doc = Document(input_path)

    # 2.5 确保 Heading 1~4 样式存在（用于 WPS 导航窗格）
    _ensure_heading_styles(doc)

    # 3. 页面设置（所有 sections）
    _apply_page_setup(doc, ctx)

    # 3.5 设置列表自动编号（在正文格式化之前）
    _setup_list_numbering(doc, ctx.spec)

    # 4. 默认字体（Normal 样式）
    _apply_default_font(doc, ctx)

    # 5. 按区域应用格式
    for region in analysis.regions:
        if region.type == Region.COVER:
            _apply_cover_format(doc, ctx, region)
        elif region.type == Region.TOC:
            _apply_toc_format(doc, ctx, region)
        elif region.type == Region.BODY:
            _apply_body_format(doc, ctx, region)
        elif region.type == Region.REVISION:
            _apply_revision_format(doc, ctx, region)

    # 6. 页眉页脚
    _apply_header_footer(doc, ctx)

    # 7. 所有表格的字体格式化（统一处理，含表头和表体）
    _apply_all_tables_format(doc, ctx)

    # 8. 保存前启用修订追踪
    if ctx.tracker is not None:
        enable_track_revisions_in_doc(doc)

    # 8.5 自审：语义级缺陷检测（仅日志输出，不中断流程）
    try:
        from _defect_patterns import run_all_checks, print_report as _print_defect_report
        _defect_results = run_all_checks(doc, ctx.spec)
        if _defect_results:
            log.info("自审发现以下潜在缺陷：")
            import io
            _buf = io.StringIO()
            _old_stdout = __builtins__._print if hasattr(__builtins__, '_print') else print
            # 捕获 print_report 输出到 log
            for _r in _defect_results:
                _sev_label = {'error': '错误', 'warning': '警告', 'info': '提示'}.get(_r['severity'], _r['severity'])
                _pos_summary = ', '.join([f"P[{p}]" for p, _ in _r['positions'][:5]])
                log.info(f"  [{_sev_label}] {_r['id']} {_r['name']} @ {_pos_summary}")
                log.info(f"    修复建议: {_r['fix_hint']}")
                if len(_r['positions']) > 5:
                    log.info(f"    ... 还有 {len(_r['positions'])-5} 处")
        else:
            log.info("自审通过：未发现已知缺陷模式")
    except Exception as _e:
        log.warning(f"自审跳过（模块未就绪）: {_e}")

    # 8.6 格式变更统计
    _log_change_stats(doc, ctx)

    # 9. 保存
    log.info(f"共应用 {ctx.applied_count} 项格式设置，{len(ctx.errors)} 个错误")
    log.info(f"写入输出文件: {output_path}")
    safe_write_docx(doc, output_path)

    return output_path


# ──────────────────────────────────────────────
# 格式变更统计
# ──────────────────────────────────────────────

def _log_change_stats(doc, ctx: FormatContext):
    """统计并输出格式变更摘要。"""
    from docx.oxml.ns import qn as _qn

    stats = {}

    # 1. 标题层级统计
    headings = {1: 0, 2: 0, 3: 0, 4: 0}
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        lv = _detect_heading_level(t, para=p)
        if lv and lv in headings:
            headings[lv] += 1
    active = {f'L{k}': v for k, v in headings.items() if v > 0}
    if active:
        stats['标题层级'] = active
        log.info(f"  标题层级: {'  '.join(f'{k}={v}' for k,v in active.items())} 合计={sum(active.values())}")

    # 2. 修订标记统计
    ppr_changes = 0
    rpr_changes = 0
    for p in doc.paragraphs:
        pPr = p._p.find(_qn('w:pPr'))
        if pPr is not None and pPr.find(_qn('w:pPrChange')) is not None:
            ppr_changes += 1
        for r in p._p.findall(_qn('w:r')):
            rPr = r.find(_qn('w:rPr'))
            if rPr is not None and rPr.find(_qn('w:rPrChange')) is not None:
                rpr_changes += 1
    if ppr_changes or rpr_changes:
        stats['修订标记'] = {'段落级': ppr_changes, 'run级': rpr_changes}
        log.info(f"  修订标记: 段落级={ppr_changes}  run级={rpr_changes}")

    # 3. 列表缩进统计
    list_paras = 0
    for p in doc.paragraphs:
        pPr = p._p.find(_qn('w:pPr'))
        if pPr is not None and pPr.find(_qn('w:numPr')) is not None:
            list_paras += 1
    if list_paras:
        stats['列表段落'] = list_paras
        log.info(f"  列表段落: {list_paras} 处")

    # 4. 页码 section 数
    section_count = len(list(doc.sections))
    stats['Section数'] = section_count
    log.info(f"  Section数: {section_count} (已插入 X/Y 页码)")

    # 5. 表格统计
    table_count = len(doc.tables)
    if table_count:
        stats['表格'] = table_count
        log.info(f"  表格格式化: {table_count} 个")

    # 6. 正文段落行距
    body_count = 0
    fixed_count = 0
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        body_count += 1
        pPr = p._p.find(_qn('w:pPr'))
        if pPr is not None:
            sp = pPr.find(_qn('w:spacing'))
            if sp is not None:
                rule = sp.get(_qn('w:lineRule'))
                if rule:
                    fixed_count += 1
    if body_count:
        ratio = round(fixed_count / body_count * 100, 1)
        log.info(f"  段落行距: {fixed_count}/{body_count} 已设行距 ({ratio}%)")

    # 7. 封面段落数
    cover_count = 0
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if not t:
            continue
        if _detect_heading_level(t, para=p) == 1:
            cover_count = i
            break
    if cover_count > 0:
        log.info(f"  封面段落: 前 {cover_count} 段")

    ctx._change_stats = stats

def _apply_page_setup(doc, ctx: FormatContext):
    """应用页面边距和尺寸到所有 sections。"""
    for i, section in enumerate(doc.sections):
        apply_page_margins(section, ctx.spec)
        apply_page_size(section, ctx.spec)
        ctx.log_apply(f"Section[{i}] 页面设置（{ctx.spec.page['size']} / "
                      f"上{ctx.spec.page['margin_top_cm']} 下{ctx.spec.page['margin_bottom_cm']} "
                      f"左{ctx.spec.page['margin_left_cm']} 右{ctx.spec.page['margin_right_cm']} cm）")


def _apply_default_font(doc, ctx: FormatContext):
    """设置 Normal 样式默认字体。"""
    body_pair = FontPair.from_spec(
        ctx.spec.font_pair('body'),
        size_pt=ctx.spec.size_pt('body_pt'),
    )
    set_default_body_font(doc, body_pair)
    ctx.log_apply(f"Normal 样式默认字体: {body_pair}")


# ──────────────────────────────────────────────
# 封面区域
# ──────────────────────────────────────────────

def _apply_cover_format(doc, ctx: FormatContext, region):
    """应用封面区域格式（含表格）。"""
    paras = ctx.analysis.paragraphs[region.start:region.end + 1]
    if not paras:
        return

    log.info(f"处理封面区域: {len(paras)} 个段落")

    # 准备三种字体对
    cover_cfg = ctx.spec.special_sections.get('cover', {})
    title_bold = cover_cfg.get('title_bold', True)
    subtitle_bold = cover_cfg.get('subtitle_bold', True)

    cover_title_fp = FontPair.from_spec(
        ctx.spec.font_pair('cover_title'),
        size_pt=ctx.spec.size_pt('cover_title_pt'),
        bold=title_bold,
    )
    cover_subtitle_fp = FontPair.from_spec(
        ctx.spec.font_pair('cover_subtitle'),
        size_pt=ctx.spec.size_pt('cover_subtitle_pt'),
        bold=subtitle_bold,
    )
    cover_info_fp = FontPair.from_spec(
        ctx.spec.font_pair('cover_info'),
        size_pt=ctx.spec.size_pt('cover_info_pt'),
    )

    # 仅统计有文本的段落，按非空顺序分配字号
    text_paras = []
    for pi in paras:
        if pi.text.strip():
            text_paras.append(pi)

    total_text = len(text_paras)
    if total_text == 0:
        return

    for idx, pi in enumerate(text_paras):
        para = doc.paragraphs[pi.index]

        # 封面段落分配策略（基于封面实际布局）：
        # - 前段（密级/编号）→ cover_info（左对齐，四号宋体14pt）
        # - 中段（产品名称/文件名称/文件编号/共页）→ cover_title（居中，二号黑体22pt）
        # - 末尾段（单位名称/年月）→ cover_company（居中，三号仿宋16pt）
        if idx == 0 or idx == 1:
            font_pair = cover_info_fp
            key = 'cover_info'
        elif idx >= total_text - 2:
            font_pair = FontPair.from_spec(
                ctx.spec.font_pair('cover_company'),
                size_pt=ctx.spec.size_pt('cover_company_pt'),
            )
            key = 'cover_company'
        elif idx == total_text - 3:
            font_pair = cover_subtitle_fp
            key = 'cover_subtitle'
        else:
            font_pair = cover_title_fp
            key = 'cover_title'

        apply_font_to_paragraph(para, font_pair, tracker=ctx.tracker)
        apply_alignment(para, ctx.spec.alignment_for(key), tracker=ctx.tracker)
        ctx.log_apply(f"封面段落[{pi.index}] → {key} ({font_pair.cjk} {font_pair.size_pt}pt)")

    # —— 封面表格处理 ——
    # 封面信息（项目令号/密级/文件编号/版本/阶段等）可能在表格中
    # 识别包含封面信息关键字的表格，统一应用 cover_info 字体
    global _COVER_TABLE_INDICES
    _COVER_TABLE_INDICES = _apply_cover_tables(doc, ctx, cover_info_fp)


# ──────────────────────────────────────────────
# 目录区域
# ──────────────────────────────────────────────

def _apply_toc_format(doc, ctx: FormatContext, region):
    """应用目录区域格式。"""
    paras = ctx.analysis.paragraphs[region.start:region.end + 1]
    if not paras:
        return

    log.info(f"处理目录区域: {len(paras)} 个段落")

    title_para = paras[0]  # 第一个段落是"目录"标题

    # 目录标题
    title_fp = FontPair.from_spec(
        ctx.spec.font_pair('toc_title'),
        size_pt=ctx.spec.size_pt('toc_title_pt'),
        bold=True,
    )
    apply_font_to_paragraph(doc.paragraphs[title_para.index], title_fp, tracker=ctx.tracker)
    apply_alignment(doc.paragraphs[title_para.index], ctx.spec.alignment_for('toc_title'), tracker=ctx.tracker)
    ctx.log_apply(f"目录标题 → {title_fp.cjk}")

    # 目录内容
    body_fp = FontPair.from_spec(
        ctx.spec.font_pair('toc_body'),
        size_pt=ctx.spec.size_pt('toc_body_pt'),
    )
    for pi in paras[1:]:
        para = doc.paragraphs[pi.index]
        apply_font_to_paragraph(para, body_fp, tracker=ctx.tracker)

    ctx.log_apply(f"目录内容 ({len(paras) - 1}段) → {body_fp.cjk}")


# ──────────────────────────────────────────────
# 列表自动编号 — 编号定义管理
# ──────────────────────────────────────────────

def _setup_list_numbering(doc, spec=None):
    """在文档的 numbering.xml 中创建列表自动编号定义。

    从 spec.list.numbering_defs 读取编号定义参数，
    结合 spec.list.levels 中的 left/hanging 缩进。
    """
    W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

    # 从 spec 读取编号定义（回退硬编码默认值）
    numbering_defs = {}
    level_map = {}  # num_id → (left, hanging)
    if spec is not None:
        numbering_defs = spec.list.get('numbering_defs', {})
        for lv in spec.list.get('levels', []):
            level_map[str(lv.get('num_id'))] = (lv.get('left_twips', 0), lv.get('hanging_twips', 0))

    if not numbering_defs:
        # 无 spec 时使用硬编码默认值
        numbering_defs = {
            "100": {"numFmt":"lowerLetter","lvlText":"%1)","start":1},
            "101": {"numFmt":"decimal","lvlText":"%1)","start":1},
            "102": {"numFmt":"bullet","lvlText":"-","start":1},
            "103": {"numFmt":"bullet","lvlText":"●","bulletFont":"Times New Roman","start":1},
            "104": {"numFmt":"bullet","lvlText":"○","bulletFont":"Times New Roman","start":1},
        }
        level_map = {
            "100": (0, 420), "101": (420, 420), "102": (839, 420),
            "103": (1259, 420), "104": (1678, 420),
        }

    # 提取有效 id 列表
    needed_ids = [int(nid) for nid in numbering_defs
                  if not nid.startswith('_') and nid.lstrip('-').isdigit()]
    W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

    # 获取 numbering part（如果不存在则创建）
    try:
        numbering_part = doc.part.numbering_part
    except (KeyError, NotImplementedError):
        # 创建新的 numbering part
        from docx.opc.part import Part
        from docx.opc.packuri import PackURI
        partname = PackURI('/word/numbering.xml')
        content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml'
        number_elm = etree.Element(f'{{{W}}}numbering')
        numbering_part = Part(partname, content_type, etree.tostring(number_elm, xml_declaration=True, encoding='UTF-8', standalone=True), doc.part.package)
        doc.part.relate_to(numbering_part, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering')

    # 解析 numbering XML（优先用 _element，因为 python-docx 保存时用它序列化）
    try:
        numbering_xml = numbering_part._element
    except AttributeError:
        numbering_xml = etree.fromstring(numbering_part.blob)

    # 检查是否已有这些定义（避免重复添加）
    existing_ids = set()
    for an in numbering_xml.findall(f'{{{W}}}abstractNum'):
        aid = an.get(f'{{{W}}}abstractNumId')
        if aid:
            existing_ids.add(int(aid))

    needed_ids = [int(nid) for nid in numbering_defs if not nid.startswith('_') and nid.lstrip('-').isdigit()]
    if all(nid in existing_ids for nid in needed_ids):
        log.info(f"列表编号定义已存在，跳过创建")
        return

    # ── 从 spec 动态创建抽象编号定义和编号实例 ──

    def _make_abstract_num(abstract_num_id, lvl_configs):
        """创建 abstractNum 元素。"""
        an = etree.SubElement(numbering_xml, f'{{{W}}}abstractNum')
        an.set(f'{{{W}}}abstractNumId', str(abstract_num_id))
        multi = etree.SubElement(an, f'{{{W}}}multiLevelType')
        multi.set(f'{{{W}}}val', 'hybridMultilevel')

        for ilvl, cfg in enumerate(lvl_configs):
            lvl = etree.SubElement(an, f'{{{W}}}lvl')
            lvl.set(f'{{{W}}}ilvl', str(ilvl))
            start = etree.SubElement(lvl, f'{{{W}}}start')
            start.set(f'{{{W}}}val', str(cfg.get('start', 1)))
            numFmt = etree.SubElement(lvl, f'{{{W}}}numFmt')
            numFmt.set(f'{{{W}}}val', cfg['numFmt'])
            lvlText = etree.SubElement(lvl, f'{{{W}}}lvlText')
            lvlText.set(f'{{{W}}}val', cfg['lvlText'])
            lvlJc = etree.SubElement(lvl, f'{{{W}}}lvlJc')
            lvlJc.set(f'{{{W}}}val', cfg.get('jc', 'left'))

            # 缩进设置（从 level_map 读取）
            left_twips, hanging_twips = level_map.get(str(cfg.get('num_id', abstract_num_id)), (0, 420))
            pPr = etree.SubElement(lvl, f'{{{W}}}pPr')
            ind = etree.SubElement(pPr, f'{{{W}}}ind')
            ind.set(f'{{{W}}}left', str(left_twips))
            ind.set(f'{{{W}}}hanging', str(hanging_twips))

            # 如果是符号类型的 bullet，需要 rPr 指定字体
            bullet_char = cfg.get('bulletChar')
            if bullet_char:
                rPr = etree.SubElement(lvl, f'{{{W}}}rPr')
                rFonts = etree.SubElement(rPr, f'{{{W}}}rFonts')
                rFonts.set(f'{{{W}}}ascii', cfg.get('bulletFont', 'Symbol'))
                rFonts.set(f'{{{W}}}hAnsi', cfg.get('bulletFont', 'Symbol'))

    def _make_num(num_id, abstract_num_id):
        """创建 num 元素（编号实例），引用 abstractNum。"""
        for existing in numbering_xml.findall(f'{{{W}}}num'):
            if existing.get(f'{{{W}}}numId') == str(num_id):
                return
        num = etree.SubElement(numbering_xml, f'{{{W}}}num')
        num.set(f'{{{W}}}numId', str(num_id))
        ref = etree.SubElement(num, f'{{{W}}}abstractNumId')
        ref.set(f'{{{W}}}val', str(abstract_num_id))

    # 遍历 spec 中的 numbering_defs，动态创建
    created_count = 0
    for num_id_str, cfg in sorted(numbering_defs.items(), key=lambda x: int(x[0]) if x[0].lstrip('-').isdigit() else 0):
        if num_id_str.startswith('_'):
            continue  # 跳过注释键
        num_id = int(num_id_str)
        # abstractNumId 与 numId 相同（一对一映射）
        abstract_num_id = num_id

        # 构造 lvl config（加入 left/hanging）
        lvl_cfg = dict(cfg)  # 复制
        left_twips, hanging_twips = level_map.get(num_id_str, (0, 420))
        lvl_cfg['left'] = left_twips
        lvl_cfg['hanging'] = hanging_twips
        lvl_cfg['num_id'] = num_id

        _make_abstract_num(abstract_num_id, [lvl_cfg])
        _make_num(num_id, abstract_num_id)
        created_count += 1

    log.info(f"已创建 {created_count} 个列表编号定义（从 spec.list.numbering_defs）")


# 编号实例计数器（用于创建新的、带重置的 num 实例）
_list_num_counter = [200]  # 从 200 开始，避免与预定义 100-104 冲突


def _create_reset_num_instance(doc, abstract_num_id: int) -> int:
    """在 numbering.xml 中创建新的 num 实例，并添加 startOverride=1。

    Args:
        doc: python-docx Document 对象
        abstract_num_id: 引用的 abstractNum ID

    Returns:
        新创建的 numId
    """
    W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    from lxml import etree

    # 获取 numbering part
    try:
        numbering_part = doc.part.numbering_part
    except (KeyError, NotImplementedError):
        return abstract_num_id  # 失败时回退

    try:
        numbering_xml = numbering_part._element
    except AttributeError:
        return abstract_num_id

    # 获取新 numId
    _list_num_counter[0] += 1
    new_num_id = _list_num_counter[0]

    # 创建新的 num 元素
    num = etree.SubElement(numbering_xml, f'{{{W}}}num')
    num.set(f'{{{W}}}numId', str(new_num_id))

    # 引用 abstractNum
    ref = etree.SubElement(num, f'{{{W}}}abstractNumId')
    ref.set(f'{{{W}}}val', str(abstract_num_id))

    # 添加 lvlOverride + startOverride=1（重置编号）
    lvl_override = etree.SubElement(num, f'{{{W}}}lvlOverride')
    lvl_override.set(f'{{{W}}}ilvl', '0')
    start_override = etree.SubElement(lvl_override, f'{{{W}}}startOverride')
    start_override.set(f'{{{W}}}val', '1')

    return new_num_id



def _apply_list_numbering(para, num_id: int):
    """向段落的 pPr 添加 w:numPr，引用指定的编号实例。"""
    W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    pPr = para._p.get_or_add_pPr()

    # 移除旧的 numPr（如果存在）
    old_numPr = pPr.find(f'{{{W}}}numPr')
    if old_numPr is not None:
        pPr.remove(old_numPr)

    # 创建新的 numPr
    numPr = OxmlElement('w:numPr')
    ilvl = OxmlElement('w:ilvl')
    ilvl.set(qn('w:val'), '0')
    numId = OxmlElement('w:numId')
    numId.set(qn('w:val'), str(num_id))
    numPr.append(ilvl)
    numPr.append(numId)

    pPr.append(numPr)


# ──────────────────────────────────────────────
# 正文区域
# ──────────────────────────────────────────────

def _apply_body_format(doc, ctx: FormatContext, region):
    """应用正文区域格式。"""
    paras = ctx.analysis.paragraphs[region.start:region.end + 1]
    if not paras:
        return

    log.info(f"处理正文区域: {len(paras)} 个段落")

    body_fp = FontPair.from_spec(
        ctx.spec.font_pair('body'),
        size_pt=ctx.spec.size_pt('body_pt'),
    )

    # 从 spec 读取编号重置配置
    nr_cfg = ctx.spec.numbering_reset
    nr_enabled = nr_cfg.get('enabled', True)
    nr_triggers = nr_cfg.get('triggers', {})
    nr_levels = nr_cfg.get('levels', [1, 2])

    # 跟踪段落状态（用于重置列表编号）
    after_heading = False
    last_was_body = False
    prev_list_level = None  # 前一段落的列表级别
    _reset_nid_cache = {}   # level → reset numId (用于同组内共享重置实例)

    for pi in paras:
        para = doc.paragraphs[pi.index]
        text = pi.text.strip()

        if not text:
            # 空段落不重置 last_was_body（防止打断正文→列表的重置链）
            continue

        # 判断标题层级（使用 spec 中的检测正则 + style 回退）
        heading_level = _detect_heading_level(text, ctx.spec, para=para)

        if heading_level is not None:
            # 标题段落
            _apply_heading_format(doc, pi, para, heading_level, ctx)
            after_heading = True
            last_was_body = False
            prev_list_level = None
            _reset_nid_cache.clear()  # 新标题出现，清空重置缓存
        else:
            # ── 先检测列表 / 图标题 / 表标题 ──
            list_level = _detect_list_level(text, ctx.spec)
            is_figure = _detect_figure_caption(text, ctx.spec)
            is_table_cap = _detect_table_caption(text, ctx.spec)

            if list_level is not None:
                # 判断是否需要重置编号（从 spec 读取触发条件）
                needs_restart = False
                if nr_enabled and list_level in nr_levels:
                    if nr_triggers.get('after_heading', True) and after_heading:
                        needs_restart = True
                    elif nr_triggers.get('after_body_text', True) and last_was_body:
                        needs_restart = True
                    elif nr_triggers.get('on_level_change', True):
                        if prev_list_level is not None and prev_list_level > list_level:
                            needs_restart = True
                prev_list_level = list_level if not needs_restart else None
                apply_font_to_paragraph(para, body_fp, tracker=ctx.tracker)
                apply_alignment(para, ctx.spec.alignment_for('body'), tracker=ctx.tracker)
                body_line_spacing = ctx.spec.spacing['body_line_spacing_pt']
                body_line_mode = ctx.spec.spacing.get('body_line_spacing_mode', 'fixed')
                apply_line_spacing(para, body_line_spacing, body_line_mode, tracker=ctx.tracker)
                apply_paragraph_spacing(para,
                    ctx.spec.spacing.get('paragraph_before_pt', 0),
                    ctx.spec.spacing.get('paragraph_after_pt', 0),
                    tracker=ctx.tracker)
                _apply_list_format(para, list_level, ctx, needs_restart, doc, _reset_nid_cache)
                after_heading = False
                last_was_body = False

            elif is_figure:
                _apply_figure_caption_format(para, ctx)
                after_heading = False
                # 图标题不重置 last_was_body（不打断连续上下文）

            elif is_table_cap:
                _apply_table_caption_format(para, ctx)
                after_heading = False
                # 表标题不重置 last_was_body（不打断连续上下文）

            else:
                # 检查段落是否有已有的 w:numPr
                has_existing_numPr = _paragraph_has_numPr(para)

                if has_existing_numPr:
                    # 判断是否需要重置编号（从 spec 读取触发条件）
                    needs_restart = False
                    if nr_enabled:
                        if nr_triggers.get('after_heading', True) and after_heading:
                            needs_restart = True
                        elif nr_triggers.get('after_body_text', True) and last_was_body:
                            needs_restart = True
                    prev_list_level = None
                    apply_font_to_paragraph(para, body_fp, tracker=ctx.tracker)
                    apply_alignment(para, ctx.spec.alignment_for('body'), tracker=ctx.tracker)
                    body_line_spacing = ctx.spec.spacing['body_line_spacing_pt']
                    body_line_mode = ctx.spec.spacing.get('body_line_spacing_mode', 'fixed')
                    apply_line_spacing(para, body_line_spacing, body_line_mode, tracker=ctx.tracker)
                    apply_paragraph_spacing(para,
                        ctx.spec.spacing.get('paragraph_before_pt', 0),
                        ctx.spec.spacing.get('paragraph_after_pt', 0),
                        tracker=ctx.tracker)
                    _apply_existing_numPr_indent(para, ctx, needs_restart, doc, _reset_nid_cache)
                    after_heading = False
                    last_was_body = False

                else:
                    # 正文段落
                    after_heading = False
                    last_was_body = True
                    clear_paragraph_indent(para, tracker=ctx.tracker)
                    apply_font_to_paragraph(para, body_fp, tracker=ctx.tracker)
                    apply_alignment(para, ctx.spec.alignment_for('body'), tracker=ctx.tracker)
                    body_line_spacing = ctx.spec.spacing['body_line_spacing_pt']
                    body_line_mode = ctx.spec.spacing.get('body_line_spacing_mode', 'fixed')
                    apply_line_spacing(para, body_line_spacing, body_line_mode, tracker=ctx.tracker)

                    # CJK 感知的首行缩进：中文段 2 字符，英文段 4 字符
                    if has_cjk(text):
                        first_indent = ctx.spec.spacing.get('first_line_indent_chars', 2)
                    else:
                        first_indent = ctx.spec.spacing.get('english_first_line_indent_chars', 4)
                    if first_indent > 0:
                        apply_first_line_indent(para, first_indent, ctx.spec.size_pt('body_pt'), tracker=ctx.tracker)

                    # 设置段落 XML 属性（snapToGrid/contextualSpacing）
                    apply_paragraph_xml_settings(para, ctx.spec, tracker=ctx.tracker)
                    apply_paragraph_spacing(
                        para,
                        ctx.spec.spacing.get('paragraph_before_pt', 0),
                        ctx.spec.spacing.get('paragraph_after_pt', 0),
                        tracker=ctx.tracker,
                    )


def _detect_heading_level(text: str, spec=None, para=None):
    """
    检测标题层级。
    返回: 1, 2, 3, 4 或 None（非标题）

    检测策略（优先级从高到低）：
    1. Spec 配置的正则模式（heading.detection）
    2. 硬编码文本模式（多级编号、中文序数、数字编号等）
    3. Word 段落样式回退（Heading 1~4 / 标题 1~4）
    """
    text = text.strip()

    # ── 从 spec 读取检测正则（如果提供了 spec）──
    if spec is not None:
        h_detect = spec.heading.get('detection', {})
        if h_detect:
            for level_key, pattern in sorted(h_detect.items()):
                m = re.match(pattern, text)
                if m:
                    # level_key = "h1", "h2", "h3", "h4"
                    try:
                        return int(level_key[1])  # "h1" → 1
                    except (ValueError, IndexError):
                        pass

    # ── 多级编号（如 7.1.1 / 7.1.1.1 / 7.1.1.1.1）──
    # 先处理多级编号，避免被单数字点误判
    multi_match = re.match(r'^(\d+\.[\d.]+)\s*', text)
    if multi_match:
        prefix = multi_match.group(1)
        dots = prefix.count('.')
        if dots >= 3:
            return 4  # 7.1.1.1 / 7.1.1.1.1 → 四级
        elif dots == 2:
            return 3  # 7.1.1 → 三级
        elif dots == 1:
            return 2  # 7.1 → 二级

    # ── 一级标题：一、二、三、... 十、或 第一章/第1章 ──
    if text.startswith(('一、', '二、', '三、', '四、', '五、',
                        '六、', '七、', '八、', '九、', '十、')):
        return 1
    if text.startswith(('第一章', '第1章')):
        return 1

    # ── G01.0403 数字编号标题：1 标题、2 标题（数字+空格，无点无括号）──
    # 注意：必须放在列表检测之前，防止 "1 目的和范围" 被当作列表
    simple_num = re.match(r'^(\d+)\s+\S', text)
    if simple_num:
        # 确保不是 "1." 或 "1)" 格式（那些是标题/列表的变体）
        after_num = text[len(simple_num.group(1)):]
        if not after_num.startswith('.') and not after_num.startswith(')'):
            return 1

    # ── 数字直接接中文字无空格（如 "4试验情况"），同样是遗漏的标题 ──
    no_space_num = re.match(r'^(\d+)([\u4e00-\u9fff])', text)
    if no_space_num:
        # 过滤"2025年"等年份格式
        if not (text.startswith(('202', '201', '200', '199')) and '年' in text[:6]):
            return 1

    # ── 二级标题：（一）...（五）、X.（单数字点）──
    if text.startswith(('（一）', '（二）', '（三）', '（四）', '（五）')):
        return 2
    if len(text) > 2 and text[0].isdigit() and text[1] == '.':
        return 2

    # ── 三级标题：1. 到 9. ──
    if text.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
        return 2

    # ── 四级标题：（1）──
    if text.startswith(('（1）', '（2）', '（3）', '（4）', '（5）')):
        return 4

    # ── Word 段落样式回退检测（文本检测未命中时）──
    if para is not None:
        style_name = (para.style.name or '').lower()
        # 英文版 Word: Heading 1, Heading 2, Heading 3, Heading 4
        if style_name.startswith('heading'):
            try:
                return int(style_name.split()[-1])
            except (ValueError, IndexError):
                pass
        # 中文版 Word: 标题 1, 标题 2, 标题 3, 标题 4
        prefix_cn = '标题'
        if style_name.startswith(prefix_cn):
            remainder = style_name[len(prefix_cn):].strip()
            if remainder and remainder.isdigit():
                return int(remainder)

    return None


def _apply_heading_format(doc, pi, para, level: int, ctx: FormatContext):
    """应用标题格式。"""
    key = f'h{level}'

    # ── 设置 Word Heading 样式（使 WPS 导航窗格可识别标题层级）──
    # 仅在段落尚未使用 Heading 样式时应用
    style_name = (para.style.name or '').lower()
    heading_style_ids = {1: 'Heading1', 2: 'Heading2', 3: 'Heading3', 4: 'Heading4'}
    if not style_name.startswith('heading') and level in heading_style_ids:
        # Track Changes: 修改前深拷贝 pPr
        if ctx.tracker is not None:
            from track_changes import deepcopy_element, track_pPr_change
            pPr_before = para._p.find(qn('w:pPr'))
            old_pPr = deepcopy_element(pPr_before) if pPr_before is not None else None

        # 设置段落样式为 Heading {level}
        try:
            hs_name = f'Heading {level}'
            para.style = doc.styles[hs_name]
        except (KeyError, AttributeError):
            pass

        # Track Changes: 记录样式变更
        if ctx.tracker is not None and old_pPr is not None:
            pPr_after = para._p.find(qn('w:pPr'))
            if pPr_after is not None:
                track_pPr_change(pPr_after, old_pPr, ctx.tracker)

    # 清除段落级的 numPr（防止从样式继承的自动编号）
    # 样式级已在 _normalize_heading_style 中清除，但段落级残留或样式继承仍可能引入
    pPr_clean = para._p.find(qn('w:pPr'))
    if pPr_clean is not None:
        numPr_para = pPr_clean.find(qn('w:numPr'))
        if numPr_para is not None:
            if ctx.tracker is not None:
                from track_changes import deepcopy_element, track_pPr_change
                old_pPr2 = deepcopy_element(pPr_clean)
                pPr_clean.remove(numPr_para)
                track_pPr_change(pPr_clean, old_pPr2, ctx.tracker)
                log.info(f"  已清除标题段落中的自动编号 (numPr)")
            else:
                pPr_clean.remove(numPr_para)

    # 获取标题字体对
    try:
        font_pair_data = ctx.spec.font_pair(key)
    except KeyError:
        font_pair_data = ctx.spec.font_pair('h1')  # 回退到 h1

    # 标题字号（与正文字号相同）
    try:
        size = ctx.spec.size_pt(f'{key}_pt')
    except KeyError:
        size = ctx.spec.size_pt('body_pt')

    # 标题加粗：从 spec 读取（默认不加粗）
    heading_cfg = ctx.spec.heading
    bold = heading_cfg.get('bold', False)

    fp = FontPair.from_spec(font_pair_data, size_pt=size, bold=bold)
    apply_font_to_paragraph(para, fp, tracker=ctx.tracker)

    # 标题对齐：从 spec 读取（默认左对齐）
    heading_align = heading_cfg.get('alignment', 'left')
    apply_alignment(para, heading_align, tracker=ctx.tracker)

    # 标题缩进：全部不缩进（left=0, first_line=0）
    clear_paragraph_indent(para, tracker=ctx.tracker)

    # 标题行距
    title_spacing = ctx.spec.spacing.get('title_line_spacing_pt', 33)
    title_mode = ctx.spec.spacing.get('title_line_spacing_mode', 'fixed')
    apply_line_spacing(para, title_spacing, title_mode, tracker=ctx.tracker)

    # 设置大纲级别（w:outlineLvl），使 WPS/Word 导航窗格可识别标题层级
    # 默认开启，可通过 spec heading.set_outline_level 控制
    if heading_cfg.get('set_outline_level', True):
        apply_outline_level(para, level, tracker=ctx.tracker)


# ──────────────────────────────────────────────
# 列表检测与格式化
# ──────────────────────────────────────────────

# ── 列表检测正则（G01.0403 V2.0 规范）──
# L1: a), b), c)... 有序（字母+半角括号）
# L2: 1), 2), 3)... 有序（数字+半角括号）
# L3: - 无序
# L4: ● 无序
# L5: ○ 无序

_LIST_L1_RE = re.compile(
    r'^[a-zA-Z][)]\s*'                # a) / A)
    r'|^[·•]\s*'                       # U+00B7 / U+2022 圆点（常见中文列项符号）
)

_LIST_L2_RE = re.compile(
    r'^\d+[)]\s*'                      # 1) / 2)（半角括号）
    r'|^\d+[）]\s*'                    # 1）/ 2）（全角括号，兼容）
)

_LIST_L3_RE = re.compile(
    r'^[-–—]\s+'                       # - / – / — 短横/长横
)

_LIST_L4_RE = re.compile(
    r'^[●]\s*'                         # 黑色圆
    r'|^[■□▪▫►▸]\s*'                 # 其他项目符号（· 已移至 L1）
)

_LIST_L5_RE = re.compile(
    r'^[○]\s*'                         # 白色圆
    r'|^[◇◆]\s*'                      # 菱形（兼容）
)

# ── L1/L2 序号提取（用于移除手动输入的序号，改用自动编号）──
_LIST_L1_TEXT_RE = re.compile(r'^[a-zA-Z][)]\s*')
_LIST_L2_TEXT_RE = re.compile(r'^\d+[)）]\s*')


def _paragraph_has_numPr(para) -> bool:
    """检测段落是否有已有的 w:numPr（原始文档的编号定义）。

    原始文档可能使用 Word 的自动编号功能（w:numPr），
    但段落文本本身没有列表标记前缀（如 "a)"、"1)"），
    导致 _detect_list_level 无法识别。此函数检测这些情况。
    """
    pPr = para._p.find(qn('w:pPr'))
    if pPr is None:
        return False
    numPr = pPr.find(qn('w:numPr'))
    return numPr is not None


def _get_original_numfmt(para) -> str:
    """获取原始段落编号定义的 numFmt，用于区分列表级别。
    
    原始文档可能用不同的 numId（而非 ilvl）区分列表级别。
    例如 numId=39 → decimal (1)2)3), numId=40 → lowerLetter (a)b)c))。
    读取 numFmt → level 映射：lowerLetter=L1, decimal=L2, bullet=L3-L5。
    """
    from docx.oxml.ns import qn
    from lxml import etree
    
    pPr = para._p.find(qn('w:pPr'))
    if pPr is None:
        return ''
    numPr = pPr.find(qn('w:numPr'))
    if numPr is None:
        return ''
    nid_el = numPr.find(qn('w:numId'))
    if nid_el is None:
        return ''
    num_id = nid_el.get(qn('w:val'))
    if not num_id:
        return ''
    
    # 通过文档的 numbering part 查询 abstractNum
    try:
        numbering_part = para._part.numbering_part
        numbering_xml = numbering_part._element
        W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
        # 找到 num 元素
        for num in numbering_xml.findall(f'{{{W}}}num'):
            if num.get(f'{{{W}}}numId') == num_id:
                ref = num.find(f'{{{W}}}abstractNumId')
                if ref is None:
                    return ''
                aid = ref.get(f'{{{W}}}val')
                # 找到 abstractNum
                for ab in numbering_xml.findall(f'{{{W}}}abstractNum'):
                    if ab.get(f'{{{W}}}abstractNumId') == aid:
                        lvl = ab.find(f'{{{W}}}lvl')
                        if lvl is not None:
                            fmt = lvl.find(f'{{{W}}}numFmt')
                            if fmt is not None:
                                return fmt.get(f'{{{W}}}val', '')
    except Exception:
        pass
    return ''


def _apply_existing_numPr_indent(para, ctx: FormatContext, after_heading: bool = False, doc=None, reset_cache=None):
    """对已有 numPr 的段落应用列表缩进。

    根据 numPr 中的 ilvl 和原始 w:left 确定缩进级别。
    移除原始文档的 numPr（使用我们的自动编号系统），
    然后应用对应的列表缩进格式和自动编号。
    """
    from docx.oxml.ns import qn
    from font_manager import _get_or_create_ind

    # 读取 ilvl + 原始 left indent（在移除之前读取）
    pPr = para._p.find(qn('w:pPr'))
    old_ilvl = 0
    old_left = 0
    if pPr is not None:
        numPr = pPr.find(qn('w:numPr'))
        if numPr is not None:
            ilvl_el = numPr.find(qn('w:ilvl'))
            if ilvl_el is not None:
                try:
                    old_ilvl = int(ilvl_el.get(qn('w:val'), '0'))
                except (ValueError, TypeError):
                    old_ilvl = 0
        # 检查原始 w:left（有些文档用段落级 w:ind 而非 ilvl 区分级别）
        ind = pPr.find(qn('w:ind'))
        if ind is not None:
            left_val = ind.get(qn('w:left'))
            if left_val is not None:
                try:
                    old_left = int(left_val)
                except (ValueError, TypeError):
                    old_left = 0

    # 确定列表级别：
    # 1. 基于 ilvl 映射：0→L1, 1→L2, 2→L3, ...
    # 2. 如果原始段落有显著的 w:left（>360twips≈0.25cm），说明它是子级项，再深一级
    level = old_ilvl + 1
    if old_left > 360:
        level += 1
    level = min(max(level, 1), 5)

    # 映射到我们的自动编号 ID
    num_id_map = {
        1: _NUM_ID_LETTERED,      # L1: a), b), c)...
        2: _NUM_ID_DECIMAL,        # L2: 1), 2), 3)...
        3: _NUM_ID_BULLET_DASH,    # L3: -
        4: _NUM_ID_BULLET_BLACK,   # L4: ●
        5: _NUM_ID_BULLET_WHITE,   # L5: ○
    }
    num_id = num_id_map.get(level)

    # 应用自动编号（会移除旧 numPr 并添加新的）
    if num_id is not None:
        # 先检查缓存中是否有已创建的同组重置实例
        used_cache = False
        if level in (1, 2) and reset_cache is not None and doc is not None:
            cache_key = ('exist', level)
            if cache_key in reset_cache:
                num_id = reset_cache[cache_key]
                used_cache = True
        # 缓存未命中且需要重置时，创建新实例
        if not used_cache and after_heading and doc is not None:
            if level in (1, 2):
                num_id = _create_reset_num_instance(doc, num_id)
                if reset_cache is not None:
                    cache_key = ('exist', level)
                    reset_cache[cache_key] = num_id
        _apply_list_numbering(para, num_id)

    # 缩进映射：仅设置 w:left（悬挂缩进由编号定义处理）
    indent_left_map = {
        1: 0,      # L1: 左0
        2: 420,    # L2: 左0.74cm
        3: 839,    # L3: 左1.48cm
        4: 1259,   # L4: 左2.22cm
        5: 1678,   # L5: 左2.96cm
    }
    left_twips = indent_left_map.get(level, 0)

    # 清除旧缩进后仅设置 w:left
    clear_paragraph_indent(para, tracker=ctx.tracker)
    ind = _get_or_create_ind(para)
    ind.set(qn('w:left'), str(left_twips))

    ctx.log_apply(f"已有numPr段落 (ilvl={old_ilvl} left={old_left}) → L{level} "
                  f"左缩进 left={left_twips} numId={num_id}（悬挂缩进由编号定义处理）")


def _detect_list_level(text: str, spec=None) -> int:
    """检测列表层级（1-5），返回 None 表示非列表。

    先尝试 spec 中的 list.detection 正则，再回退模块级硬编码模式。
    """
    if not text:
        return None

    # ── 从 spec 读取检测正则（如果提供了 spec）──
    if spec is not None:
        l_detect = spec.list.get('detection', {})
        if l_detect:
            for level_key in ('L5', 'L4', 'L3', 'L2', 'L1'):
                pattern = l_detect.get(level_key)
                if pattern and re.match(pattern, text):
                    return int(level_key[1])

    # ── 回退模块级硬编码模式 ──
    if _LIST_L5_RE.match(text):
        return 5
    if _LIST_L4_RE.match(text):
        return 4
    if _LIST_L3_RE.match(text):
        return 3
    if _LIST_L2_RE.match(text):
        return 2
    if _LIST_L1_RE.match(text):
        return 1
    return None


def _apply_list_format(para, level: int, ctx: FormatContext, after_heading: bool = False, doc=None, reset_cache=None):
    """对列表项应用格式：字体 + 自动编号 + 缩进。

    L1/L2 → 有序自动编号
    L3/L4/L5 → 无序项目符号
    """
    # 列表字号：小四（12pt）——与正文一致
    body_fp = FontPair.from_spec(
        ctx.spec.font_pair('body'),
        size_pt=ctx.spec.size_pt('body_pt'),
    )
    apply_font_to_paragraph(para, body_fp, tracker=ctx.tracker)

    # 应用自动编号
    num_id_map = {
        1: _NUM_ID_LETTERED,      # a), b), c)...
        2: _NUM_ID_DECIMAL,        # 1), 2), 3)...
        3: _NUM_ID_BULLET_DASH,    # -
        4: _NUM_ID_BULLET_BLACK,   # ●
        5: _NUM_ID_BULLET_WHITE,   # ○
    }

    num_id = num_id_map.get(level)
    if num_id is not None:
        # 先检查缓存中是否有已创建的同组重置实例
        used_cache = False
        if level in (1, 2) and reset_cache is not None and doc is not None:
            cache_key = ('list', level)
            if cache_key in reset_cache:
                num_id = reset_cache[cache_key]
                used_cache = True
        # 缓存未命中且需要重置时，创建新实例
        if not used_cache and after_heading and doc is not None:
            if level in (1, 2):
                num_id = _create_reset_num_instance(doc, num_id)
                if reset_cache is not None:
                    cache_key = ('list', level)
                    reset_cache[cache_key] = num_id
        _apply_list_numbering(para, num_id)

    # 清除旧的手动序号（如 "a) " 或 "1) " 前缀），避免与自动编号重复
    # 先移除手动编号前缀
    text = para.text
    if text:
        para_text = ''
        if level == 1:
            para_text = _LIST_L1_TEXT_RE.sub('', text)
        elif level == 2:
            para_text = _LIST_L2_TEXT_RE.sub('', text)

        if para_text and para_text != text:
            # 找到第一个非空 run，替换其文本
            for run in para.runs:
                if run.text.strip():
                    old_run_text = run.text
                    # 计算前缀长度
                    if level == 1:
                        m = re.match(r'^[a-zA-Z][)]\s*', old_run_text)
                    else:
                        m = re.match(r'^\d+[)）]\s*', old_run_text)
                    if m:
                        run.text = old_run_text[m.end():]
                    break

    # 对齐
    apply_alignment(para, ctx.spec.alignment_for('body'), tracker=ctx.tracker)

    # 行距
    body_line_spacing = ctx.spec.spacing['body_line_spacing_pt']
    body_line_mode = ctx.spec.spacing.get('body_line_spacing_mode', 'fixed')
    apply_line_spacing(para, body_line_spacing, body_line_mode, tracker=ctx.tracker)

    apply_paragraph_spacing(para,
        ctx.spec.spacing.get('paragraph_before_pt', 0),
        ctx.spec.spacing.get('paragraph_after_pt', 0),
        tracker=ctx.tracker)

    # 缩进映射（left twips）：L1=0, L2=420, L3=839, L4=1259, L5=1678
    # 悬挂缩进由 numbering.xml 的编号定义（lvl/pPr/w:ind/hanging）处理
    indent_left_map = {
        1: 0,      # L1: a) 左0
        2: 420,    # L2: 1) 左0.74cm
        3: 839,    # L3: -  左1.48cm
        4: 1259,   # L4: ● 左2.22cm
        5: 1678,   # L5: ○ 左2.96cm
    }
    left_twips = indent_left_map.get(level, 0)

    # 清除旧缩进后仅设置 w:left（悬挂缩进由编号定义中的 lvl/pPr/w:ind/hanging 处理）
    clear_paragraph_indent(para, tracker=ctx.tracker)
    ind = _get_or_create_ind(para)
    ind.set(qn('w:left'), str(left_twips))

    ctx.log_apply(f"列表L{level} → 自动编号 + 左缩进 left={left_twips}（悬挂缩进由编号定义处理）")


# ──────────────────────────────────────────────
# 图标题 / 表标题 检测与格式化
# ──────────────────────────────────────────────

_FIGURE_RE = re.compile(
    r'^(图\s*\d+(-\d+)?|Figure\s*\d+|Fig\.?\s*\d+)', re.IGNORECASE
)
_TABLE_RE = re.compile(
    r'^(表\s*\d+(-\d+)?|Table\s*\d+)', re.IGNORECASE
)


def _detect_figure_caption(text: str, spec=None) -> bool:
    """检测是否为图标题（"图1"、"Figure 1"等开头）。"""
    if spec is not None:
        pattern = spec.figure_caption.get('detection_regex',
            r'^(图\s*\d+(-\d+)?|Figure\s*\d+|Fig\.?\s*\d+)')
        return bool(re.match(pattern, text, re.IGNORECASE))
    return bool(_FIGURE_RE.match(text))


def _detect_table_caption(text: str, spec=None) -> bool:
    """检测是否为表标题（"表1"、"Table 1"等开头）。"""
    if spec is not None:
        pattern = spec.table_caption.get('detection_regex',
            r'^(表\s*\d+(-\\d+)?|Table\s*\d+)')
        return bool(re.match(pattern, text, re.IGNORECASE))
    return bool(_TABLE_RE.match(text))


def _apply_figure_caption_format(para, ctx: FormatContext):
    """应用图标题格式：从 spec 读取对齐方式，默认居中，五号(10.5pt)。"""
    fp = FontPair.from_spec(
        ctx.spec.font_pair('figure_caption'),
        size_pt=ctx.spec.size_pt('figure_caption_pt'),
    )
    apply_font_to_paragraph(para, fp, tracker=ctx.tracker)
    fig_align = ctx.spec.alignment_for('figure_caption', default='center')
    apply_alignment(para, fig_align, tracker=ctx.tracker)
    clear_paragraph_indent(para, tracker=ctx.tracker)
    ctx.log_apply(f"图标题 → {fp.cjk} {fp.size_pt}pt {fig_align}")


def _apply_table_caption_format(para, ctx: FormatContext):
    """应用表标题格式：从 spec 读取对齐方式，默认居中，五号(10.5pt)。"""
    fp = FontPair.from_spec(
        ctx.spec.font_pair('table_caption'),
        size_pt=ctx.spec.size_pt('table_caption_pt'),
    )
    apply_font_to_paragraph(para, fp, tracker=ctx.tracker)
    tbl_align = ctx.spec.alignment_for('table_caption', default='center')
    apply_alignment(para, tbl_align, tracker=ctx.tracker)
    clear_paragraph_indent(para, tracker=ctx.tracker)
    ctx.log_apply(f"表标题 → {fp.cjk} {fp.size_pt}pt {tbl_align}")


# ──────────────────────────────────────────────
# 修订记录区域
# ──────────────────────────────────────────────

def _apply_revision_format(doc, ctx: FormatContext, region):
    """应用修订记录区域格式。"""
    paras = ctx.analysis.paragraphs[region.start:region.end + 1]
    if not paras:
        return

    log.info(f"处理修订记录区域: {len(paras)} 个段落")

    # 修订记录标题（第一个段落）
    title_pi = paras[0]
    title_fp = FontPair.from_spec(
        ctx.spec.font_pair('revision_title'),
        size_pt=ctx.spec.size_pt('revision_title_pt'),
        bold=True,
    )
    title_para = doc.paragraphs[title_pi.index]
    apply_font_to_paragraph(title_para, title_fp, tracker=ctx.tracker)
    apply_alignment(title_para, ctx.spec.alignment_for('revision_title'), tracker=ctx.tracker)
    ctx.log_apply(f"修订记录标题 → {title_fp.cjk}")

    # 修订记录内容段落
    if len(paras) > 1:
        body_fp = FontPair.from_spec(
            ctx.spec.font_pair('revision_body'),
            size_pt=ctx.spec.size_pt('revision_body_pt'),
        )
        for pi in paras[1:]:
            para = doc.paragraphs[pi.index]
            if pi.text.strip():
                apply_font_to_paragraph(para, body_fp, tracker=ctx.tracker)
        ctx.log_apply(f"修订记录内容 ({len(paras)-1}段) → {body_fp.cjk}")

    # 修订记录表格格式化
    _apply_revision_tables(doc, ctx)


def _apply_cover_tables(doc, ctx: FormatContext, cover_info_fp: FontPair):
    """处理封面区域的表格（布局表格，非数据表格）。

    识别特征：第一行第一列包含封面信息关键字（项目令号、密级、文件编号等）。
    对所有单元格统一应用 cover_info 字体，不进行表头加粗/蓝底处理。
    返回已处理的表格索引集合。
    """
    # 从 spec 读取封面检测关键词（回退硬编码默认值）
    COVER_KEYWORDS = (ctx.spec.special_sections.get('cover', {})
                      .get('detection_keywords', 
                           ['项目令号', '密级', '文件编号', '版本', '阶段', '拟制', '审核',
                            '会签', '批准', '日期', '阶段标记']))

    cover_indices = set()
    for t_idx, table in enumerate(doc.tables):
        if not table.rows:
            continue
        # 检查第一列第一行是否含封面关键字
        first_cell = table.rows[0].cells[0].text.strip() if table.rows[0].cells else ''
        is_cover = any(kw in first_cell for kw in COVER_KEYWORDS)
        if not is_cover:
            continue

        cover_indices.add(t_idx)
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    if para.text.strip():
                        apply_font_to_paragraph(para, cover_info_fp, tracker=ctx.tracker)
        ctx.log_apply(f"封面表格[{t_idx}] ({len(table.rows)}行×{len(table.columns)}列) → {cover_info_fp.cjk}")
    return cover_indices


# 保存封面表格索引，供 _apply_all_tables_format 跳过
_COVER_TABLE_INDICES = set()

# 保存修订记录表格索引，供 _apply_all_tables_format 跳过
_REVISION_TABLE_INDICES = set()


def _apply_revision_tables(doc, ctx: FormatContext):
    """格式化修订记录区域中的表格。"""
    rev_config = ctx.spec.special_sections.get('revision_history', {})
    if not rev_config.get('enabled'):
        return

    # 找到文档中的表格（修订记录表的特征：列数匹配）
    tables = doc.tables
    if not tables:
        return

    expected_cols = len(rev_config.get('table_columns', []))

    header_fp = FontPair.from_spec(
        ctx.spec.font_pair('revision_header'),
        size_pt=ctx.spec.size_pt('revision_header_pt'),
        bold=rev_config.get('header_bold', True),
    )
    body_fp = FontPair.from_spec(
        ctx.spec.font_pair('revision_body'),
        size_pt=ctx.spec.size_pt('revision_body_pt'),
    )

    for i, table in enumerate(tables):
        # 跳过封面布局表格（已在 _apply_cover_tables 中处理）
        if i in _COVER_TABLE_INDICES:
            continue
        cols = len(table.columns)
        # 列数匹配或至少 3 列的表
        if expected_cols == 0 or (cols >= 3):
            # 表头
            apply_table_header_font(table, header_fp, tracker=ctx.tracker)
            if rev_config.get('header_bold'):
                apply_table_header_bold(table)
            if rev_config.get('header_shading'):
                apply_table_header_shading(table, rev_config['header_shading'])

            # 表体
            for row_idx, row in enumerate(table.rows):
                if row_idx == 0:
                    continue  # 跳过表头
                for cell in row.cells:
                    for para in cell.paragraphs:
                        if para.text.strip():
                            apply_font_to_paragraph(para, body_fp, tracker=ctx.tracker)

            # 边框
            border = rev_config.get('border_style', 'single')
            apply_table_borders(table, border)

            ctx.log_apply(f"修订记录表[{i}] ({cols}列×{len(table.rows)}行) 格式化")
            _REVISION_TABLE_INDICES.add(i)


# ──────────────────────────────────────────────
# 页眉页脚
# ──────────────────────────────────────────────

def _apply_header_footer(doc, ctx: FormatContext):
    """应用页眉页脚格式。"""
    page_num_fp = FontPair.from_spec(
        ctx.spec.font_pair('page_number'),
        size_pt=ctx.spec.size_pt('page_number_pt'),
    )
    # 页眉字体（文件编号等）——独立配置，不套用正文字号
    header_fp = FontPair.from_spec(
        ctx.spec.font_pair('header'),
        size_pt=ctx.spec.size_pt('header_pt'),
    )

    for i, section in enumerate(doc.sections):
        # ── 设置页眉顶端距离 ──
        try:
            header_dist = ctx.spec.page.get('header_distance_cm')
            if header_dist is not None:
                from docx.shared import Cm
                section.header_distance = Cm(header_dist)
        except Exception:
            pass

        # ── 设置页脚底端距离 ──
        try:
            footer_dist = ctx.spec.page.get('footer_distance_cm')
            if footer_dist is not None:
                from docx.shared import Cm
                section.footer_distance = Cm(footer_dist)
        except Exception:
            pass

        # ── 页眉 ──
        header = section.header
        if header and hasattr(header, 'paragraphs'):
            if hasattr(header, 'is_linked_to_previous') and header.is_linked_to_previous:
                pass
            else:
                for para in header.paragraphs:
                    if para.text.strip():
                        apply_font_to_paragraph(para, header_fp, tracker=ctx.tracker)
                        apply_alignment(para, ctx.spec.alignment_for('header'), tracker=ctx.tracker)

                # 页眉行距（单倍行距）
                header_ls = ctx.spec.spacing.get('header_line_spacing_pt', 1.0)
                header_ls_mode = ctx.spec.spacing.get('header_line_spacing_mode', 'multiple')
                for para in header.paragraphs:
                    if para.text.strip():
                        apply_line_spacing(para, header_ls, header_ls_mode, tracker=ctx.tracker)
                        apply_paragraph_spacing(para, 0, 0, tracker=ctx.tracker)

                ctx.log_apply(f"Section[{i}] 页眉 → {header_fp.cjk} {header_fp.size_pt}pt 单倍行距 居中")

        # ── 页脚：插入页码（单个X格式，非X/Y）──
        add_page_number_to_section(section, page_num_fp, show_total=False)
        ctx.log_apply(f"Section[{i}] 页脚页码 → {page_num_fp.cjk} {page_num_fp.size_pt}pt 居中")


# ──────────────────────────────────────────────
# 全表格式化（所有表格统一处理）
# ──────────────────────────────────────────────

def _apply_all_tables_format(doc, ctx: FormatContext):
    """统一格式化文档中所有表格的字体和样式。

    处理每个表格的：
    - 表头：使用 revision_header 字体对（加粗、背景色）
    - 表体：使用 body 字体对（与正文一致）
    - 边框：统一单线边框
    - 对齐：单元格居中
    """
    tables = doc.tables
    if not tables:
        ctx.log_apply("文档无表格，跳过表格格式化")
        return

    header_fp = FontPair.from_spec(
        ctx.spec.font_pair('revision_header'),
        size_pt=ctx.spec.size_pt('revision_header_pt'),
        bold=True,
    )
    body_fp = FontPair.from_spec(
        ctx.spec.font_pair('body'),
        size_pt=ctx.spec.size_pt('table_body_pt'),
    )

    processed = 0
    total_rows = 0
    for i, table in enumerate(tables):
        if not table.rows:
            continue
        # 跳过封面布局表格（已在 _apply_cover_tables 中处理）
        if i in _COVER_TABLE_INDICES:
            continue
        # 跳过修订记录表格（已在 _apply_revision_tables 中处理）
        if i in _REVISION_TABLE_INDICES:
            continue

        processed += 1
        total_rows += len(table.rows)

        # 表头行（第一行）
        for cell in table.rows[0].cells:
            for para in cell.paragraphs:
                if para.text.strip():
                    apply_font_to_paragraph(para, header_fp, tracker=ctx.tracker)

        # 表体行（其余行）
        for row_idx in range(1, len(table.rows)):
            for cell in table.rows[row_idx].cells:
                for para in cell.paragraphs:
                    if para.text.strip():
                        apply_font_to_paragraph(para, body_fp, tracker=ctx.tracker)

        # 表头加粗和背景
        apply_table_header_bold(table)
        apply_table_header_shading(table, 'D9E2F3')

        # 表格边框
        apply_table_borders(table, 'single')

    ctx.log_apply(f"全表格式化: {processed} 个数据表格 ({total_rows} 行) → 表头{header_fp.cjk}加粗, 表体{body_fp.cjk}")
