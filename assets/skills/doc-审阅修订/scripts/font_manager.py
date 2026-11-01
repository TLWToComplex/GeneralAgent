"""
font_manager.py — 中西文字体管理器

负责：
1. {cjk, latin} 字体对管理
2. 正确设置 w:rFonts 的四个属性（eastAsia / ascii / hAnsi / cs）
3. Paragraph 和 Run 级别的字体应用
4. 样式（Style）级别的字体设置（影响整篇文档的默认字体）
5. Track Changes 修订追踪（v0.2.0）：所有格式修改可选记录 w:rPrChange/w:pPrChange

核心原理：
  Word 文档中，w:rFonts 有四个独立属性：
  - w:eastAsia → CJK 字体（中文、日文、韩文）
  - w:ascii    → ASCII 字体（英文、数字、基本标点）
  - w:hAnsi    → High ANSI 字体（西欧语言）
  - w:cs       → 复杂脚本字体（阿拉伯文等）

  大多数工具只设一个字体，导致中文和英文共用同一字体。
  本模块确保每次操作都同时设置所有四个属性。
"""

import re
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, Cm, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from utils import log, NSMAP


# ──────────────────────────────────────────────
# CJK 字符检测
# ──────────────────────────────────────────────

_CJK_RE = re.compile(
    r'[\u4e00-\u9fff\u3400-\u4dbf'          # CJK Unified Ideographs + Ext-A
    r'\uf900-\ufaff'                         # CJK Compatibility Ideographs
    r'\U0002f800-\U0002fa1f'                 # CJK Compatibility Ideographs Supplement
    r'\u3040-\u309f\u30a0-\u30ff'           # Hiragana + Katakana
    r'\uac00-\ud7af\uff00-\uffef'           # Hangul + Fullwidth forms
    r'\u3000-\u303f'                         # CJK Symbols and Punctuation
    r']'
)


def has_cjk(text: str) -> bool:
    """检测字符串是否包含 CJK 字符（中文、日文、韩文）。"""
    return bool(_CJK_RE.search(text))


def apply_paragraph_xml_settings(para, spec, tracker=None):
    """设置段落的 XML 级属性（snapToGrid、contextualSpacing）。

    G01.0403 2.3: 不对齐网格、不设置增加间距。
    这些属性通过 w:pPr 中的 w:snapToGrid 和 w:contextualSpacing 控制。

    Args:
        para: python-docx 段落对象
        spec: Spec 对象
        tracker: RevisionTracker（可选）
    """
    from docx.oxml.ns import qn
    from lxml import etree

    spacing = spec.spacing if hasattr(spec, 'spacing') else {}
    snap_to_grid = spacing.get('snap_to_grid', True)
    contextual_spacing = spacing.get('contextual_spacing', False)

    pPr = para._p.find(qn('w:pPr'))
    if pPr is None:
        pPr = etree.SubElement(para._p, qn('w:pPr'))

    # w:snapToGrid（对齐网格）
    snap_el = pPr.find(qn('w:snapToGrid'))
    if snap_el is None:
        snap_el = etree.SubElement(pPr, qn('w:snapToGrid'))
    snap_el.set(qn('w:val'), '0' if not snap_to_grid else '1')

    # w:contextualSpacing（增加间距）
    ctx_el = pPr.find(qn('w:contextualSpacing'))
    if ctx_el is None:
        ctx_el = etree.SubElement(pPr, qn('w:contextualSpacing'))
    ctx_el.set(qn('w:val'), '1' if contextual_spacing else '0')


# ──────────────────────────────────────────────
# 字体对管理
# ──────────────────────────────────────────────

class FontPair:
    """中西文字体配对。"""

    def __init__(self, cjk: str, latin: str, size_pt: float = None,
                 bold: bool = None, italic: bool = None):
        self.cjk = cjk
        self.latin = latin
        self.size_pt = size_pt
        self.bold = bold
        self.italic = italic

    def __repr__(self):
        return f"FontPair(CJK={self.cjk}, Latin={self.latin}, size={self.size_pt}pt)"

    @classmethod
    def from_spec(cls, font_pair: dict, size_pt: float = None,
                  bold: bool = None, italic: bool = None):
        """从规范中的 {cjk, latin} 创建。"""
        return cls(
            cjk=font_pair['cjk'],
            latin=font_pair['latin'],
            size_pt=size_pt,
            bold=bold,
            italic=italic
        )


# ──────────────────────────────────────────────
# XML 级别的字体操作（核心）
# ──────────────────────────────────────────────

def set_run_font_xml(run, font_pair: FontPair, tracker=None):
    """
    在 XML 级别设置 run 的字体——同时设置四个 w:rFonts 属性。

    这是整个 font_manager 的核心，解决"中英文分别设置字体"的问题。

    Args:
        run:       python-docx Run 对象
        font_pair: FontPair 字体对
        tracker:   可选，RevisionTracker 实例；传入时启用 Track Changes 修订标记

    返回 None 成功，抛出异常时表示失败。
    """
    rPr = run._r.get_or_add_rPr()

    # Track Changes: 修改前深拷贝旧的 rPr
    if tracker is not None:
        from track_changes import deepcopy_element, track_rPr_change
        old_rPr = deepcopy_element(rPr)

    # 获取或创建 w:rFonts 元素
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.insert(0, rFonts)

    # 设置四个字体属性
    # 注意：不再删除 Theme 属性（w:asciiTheme 等），因为某些文档（如 WPS 生成）
    # 依赖 Theme 字体来渲染中文。当显式字体和 Theme 同时存在时，OOXML 规范
    # 规定显式字体优先，因此保留 Theme 不会影响实际效果。
    # 关键：对不含 CJK 字符的 run（纯英文/数字），把 eastAsia 也设为 latin 字体，
    # 避免从段落级继承 CJK 字体导致英文渲染成中文字体
    run_text = run.text if hasattr(run, 'text') else ''
    if has_cjk(run_text):
        rFonts.set(qn('w:eastAsia'), font_pair.cjk)
    else:
        rFonts.set(qn('w:eastAsia'), font_pair.latin)
    rFonts.set(qn('w:ascii'), font_pair.latin)
    rFonts.set(qn('w:hAnsi'), font_pair.latin)
    rFonts.set(qn('w:cs'), font_pair.latin)

    # 强制删除 hint 属性和 Theme 字体属性
    # w:hint 是 WPS 渲染的关键：当 hint=eastAsia 时，WPS 会忽略显式的
    # w:ascii/w:hAnsi 设置，将所有文字（包括英文和数字）都渲染为 eastAsia 字体。
    # Theme 属性（w:asciiTheme 等）在显式字体设置后是冗余的，但可能干扰 WPS 的字体回退逻辑。
    for attr in ['w:hint', 'w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme']:
        try:
            del rFonts.attrib[qn(attr)]
        except KeyError:
            pass

    # 字号
    if font_pair.size_pt is not None:
        sz = rPr.find(qn('w:sz'))
        if sz is None:
            sz = OxmlElement('w:sz')
            rPr.append(sz)
        sz.set(qn('w:val'), str(int(font_pair.size_pt * 2)))

        szCs = rPr.find(qn('w:szCs'))
        if szCs is None:
            szCs = OxmlElement('w:szCs')
            rPr.append(szCs)
        szCs.set(qn('w:val'), str(int(font_pair.size_pt * 2)))

    # 加粗
    if font_pair.bold is not None:
        b = rPr.find(qn('w:b'))
        if font_pair.bold:
            if b is None:
                b = OxmlElement('w:b')
                rPr.append(b)
        else:
            if b is not None:
                rPr.remove(b)

    # 斜体
    if font_pair.italic is not None:
        i = rPr.find(qn('w:i'))
        if font_pair.italic:
            if i is None:
                i = OxmlElement('w:i')
                rPr.append(i)
        else:
            if i is not None:
                rPr.remove(i)

    # Track Changes: 修改后插入修订标记
    if tracker is not None:
        track_rPr_change(rPr, old_rPr, tracker)


def set_default_paragraph_font(para, font_pair: FontPair, tracker=None):
    """
    设置段落的默认字体——通过 w:pPr/w:rPr/w:rFonts。

    这会覆盖段落级别（而非 run 级别）的字体设置。
    如果 run 已经有独立的 rFonts，则以 run 的为准。

    CJK 感知：检测段落整体文本是否含 CJK 字符。不含则 eastAsia 也设为 latin
    字体，避免 WPS 用段落级 hint=default 覆盖 run 级的英文字体设置。

    Args:
        tracker: 可选，RevisionTracker 实例；传入时启用 Track Changes 修订标记
    """
    pPr = para._p.get_or_add_pPr()

    # Track Changes: 修改前深拷贝旧的 pPr
    if tracker is not None:
        from track_changes import deepcopy_element, track_pPr_change
        old_pPr = deepcopy_element(pPr)

    rPr = pPr.find(qn('w:rPr'))
    if rPr is None:
        rPr = OxmlElement('w:rPr')
        pPr.append(rPr)

    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.insert(0, rFonts)

    # CJK 感知：段落整体不含 CJK → eastAsia 也设为 latin 字体
    para_text = para.text if hasattr(para, 'text') else ''
    if has_cjk(para_text):
        rFonts.set(qn('w:eastAsia'), font_pair.cjk)
    else:
        rFonts.set(qn('w:eastAsia'), font_pair.latin)
    rFonts.set(qn('w:ascii'), font_pair.latin)
    rFonts.set(qn('w:hAnsi'), font_pair.latin)
    rFonts.set(qn('w:cs'), font_pair.latin)

    # 强制删除 hint 属性和 Theme 字体属性（同 set_run_font_xml 注释）
    for attr in ['w:hint', 'w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme']:
        try:
            del rFonts.attrib[qn(attr)]
        except KeyError:
            pass

    if font_pair.size_pt is not None:
        sz = rPr.find(qn('w:sz'))
        if sz is None:
            sz = OxmlElement('w:sz')
            rPr.append(sz)
        sz.set(qn('w:val'), str(int(font_pair.size_pt * 2)))

    # Track Changes: 修改后插入修订标记
    if tracker is not None:
        track_pPr_change(pPr, old_pPr, tracker)


def clear_run_fonts(run):
    """清除 run 的所有字体设置（重置为继承）。"""
    rPr = run._r.find(qn('w:rPr'))
    if rPr is None:
        return

    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is not None:
        rPr.remove(rFonts)


# ──────────────────────────────────────────────
# 段落字体应用（Python-docx 高级 API）
# ──────────────────────────────────────────────

def apply_font_to_paragraph(para, font_pair: FontPair, tracker=None):
    """
    将 FontPair 应用到段落的所有 run。

    策略：
    1. 先清除段落内所有 run 的字体设置
    2. 再统一设置为目标字体
    3. 同时设置段落级默认字体（后备）

    Args:
        tracker: 可选，RevisionTracker 实例；传入时启用 Track Changes 修订标记
    """
    # 段落级默认
    set_default_paragraph_font(para, font_pair, tracker=tracker)

    for run in para.runs:
        if run.text.strip():
            set_run_font_xml(run, font_pair, tracker=tracker)


def apply_font_to_run(run, font_pair: FontPair, tracker=None):
    """将 FontPair 应用到单个 run。

    Args:
        tracker: 可选，RevisionTracker 实例；传入时启用 Track Changes 修订标记
    """
    set_run_font_xml(run, font_pair, tracker=tracker)


def apply_font_to_all_paragraphs(paragraphs: list, font_pair: FontPair, tracker=None):
    """批量应用字体到段落列表。

    Args:
        tracker: 可选，RevisionTracker 实例；传入时启用 Track Changes 修订标记
    """
    count = 0
    for para in paragraphs:
        apply_font_to_paragraph(para, font_pair, tracker=tracker)
        count += 1
    log.info(f"字体应用完成: {count} 个段落 → {font_pair}")


# ──────────────────────────────────────────────
# 样式级别操作
# ──────────────────────────────────────────────

def set_style_font(style, font_pair: FontPair):
    """
    设置 Word 样式的默认字体。

    这会修改 document.xml 中 styles.xml 的对应条目，
    影响使用该样式的所有段落。
    """
    rPr = style.element.find(qn('w:rPr'))
    if rPr is None:
        rPr = OxmlElement('w:rPr')
        style.element.append(rPr)

    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.insert(0, rFonts)

    rFonts.set(qn('w:eastAsia'), font_pair.cjk)
    rFonts.set(qn('w:ascii'), font_pair.latin)
    rFonts.set(qn('w:hAnsi'), font_pair.latin)
    rFonts.set(qn('w:cs'), font_pair.latin)

    # 强制删除 hint 属性和 Theme 字体属性
    for attr in ['w:hint', 'w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme']:
        try:
            del rFonts.attrib[qn(attr)]
        except KeyError:
            pass

    if font_pair.size_pt is not None:
        sz = rPr.find(qn('w:sz'))
        if sz is None:
            sz = OxmlElement('w:sz')
            rPr.append(sz)
        sz.set(qn('w:val'), str(int(font_pair.size_pt * 2)))


def set_default_body_font(doc, font_pair: FontPair):
    """设置整篇文档的默认正文字体（修改 Normal 样式）。"""
    try:
        normal_style = doc.styles['Normal']
        set_style_font(normal_style, font_pair)
        log.info(f"默认正文字体已设置: {font_pair}")
    except KeyError:
        log.warning("未找到 Normal 样式，跳过默认字体设置")


# ──────────────────────────────────────────────
# 对齐方式
# ──────────────────────────────────────────────

ALIGNMENT_MAP = {
    'left':   WD_ALIGN_PARAGRAPH.LEFT,
    'center': WD_ALIGN_PARAGRAPH.CENTER,
    'right':  WD_ALIGN_PARAGRAPH.RIGHT,
    'both':   WD_ALIGN_PARAGRAPH.JUSTIFY,
}


def apply_alignment(para, alignment: str, tracker=None):
    """设置段落对齐方式。

    Args:
        tracker: 可选，RevisionTracker 实例；传入时启用 Track Changes 修订标记
    """
    if alignment in ALIGNMENT_MAP:
        # Track Changes: 修改前深拷贝 pPr
        if tracker is not None:
            from track_changes import deepcopy_element, track_pPr_change
            pPr = para._p.get_or_add_pPr()
            old_pPr = deepcopy_element(pPr)

        para.alignment = ALIGNMENT_MAP[alignment]

        # Track Changes: 修改后插入修订标记
        if tracker is not None:
            track_pPr_change(pPr, old_pPr, tracker)


def apply_line_spacing(para, line_spacing_pt: float, mode: str = 'fixed', tracker=None):
    """设置段落行距。

    Args:
        para: 段落对象
        line_spacing_pt: 固定值则为 pt 数，倍数模式则为倍数值（如 1.5）
        mode: 'fixed' 固定行距, 'multiple' 倍数行距
        tracker: 可选，RevisionTracker 实例；传入时启用 Track Changes 修订标记
    """
    # Track Changes: 修改前深拷贝 pPr
    if tracker is not None:
        from track_changes import deepcopy_element, track_pPr_change
        pPr = para._p.get_or_add_pPr()
        old_pPr = deepcopy_element(pPr)

    from docx.enum.text import WD_LINE_SPACING
    pf = para.paragraph_format
    if mode == 'multiple':
        mult = float(line_spacing_pt)
        if abs(mult - 1.5) < 0.01:
            pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        elif abs(mult - 2.0) < 0.01:
            pf.line_spacing_rule = WD_LINE_SPACING.DOUBLE
        else:
            pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
            pf.line_spacing = mult
    else:
        pf.line_spacing = Pt(line_spacing_pt)

    # Track Changes: 修改后插入修订标记
    if tracker is not None:
        track_pPr_change(pPr, old_pPr, tracker)


def apply_first_line_indent(para, indent_chars: float, font_size_pt: float = 16, tracker=None):
    """设置首行缩进（字符数 → 磅数 → EMU）。

    Args:
        tracker: 可选，RevisionTracker 实例；传入时启用 Track Changes 修订标记
    """
    # Track Changes: 修改前深拷贝 pPr
    if tracker is not None:
        from track_changes import deepcopy_element, track_pPr_change
        pPr = para._p.get_or_add_pPr()
        old_pPr = deepcopy_element(pPr)

    indent_pt = indent_chars * font_size_pt
    pf = para.paragraph_format
    pf.first_line_indent = Pt(indent_pt)

    # Track Changes: 修改后插入修订标记
    if tracker is not None:
        track_pPr_change(pPr, old_pPr, tracker)


def _get_or_create_ind(para) -> "OxmlElement":
    """获取或创建段落的 w:ind 元素，并确保 w:left/w:firstLine 存在。

    python-docx 的 paragraph_format.left_indent / first_line_indent 在设零值时
    不可靠（部分版本将 EMU=0 当作 None 处理，不写 XML 属性）。
    因此直接操作底层 XML，确保缩进被正确写入。
    """
    pPr = para._p.get_or_add_pPr()
    ind = pPr.find(qn('w:ind'))
    if ind is None:
        ind = OxmlElement('w:ind')
        # 插入到 pPr 的最前面（在 <w:jc> 等之前），遵循 OOXML 惯例
        pPr.insert(0, ind)
    return ind


def _twips_from_cm(cm_val: float) -> int:
    """厘米转 twips（1 twip = 1/20 pt, 1 cm ≈ 567 twips）。"""
    return int(round(cm_val * 567))


def apply_left_indent(para, indent_cm: float, tracker=None):
    """设置左缩进（cm），并清除首行缩进。直接操作 w:ind XML。

    Args:
        tracker: 可选，RevisionTracker 实例；传入时启用 Track Changes 修订标记
    """
    # Track Changes: 修改前深拷贝 pPr（直接操作 ind，需要整个 pPr）
    if tracker is not None:
        from track_changes import deepcopy_element, track_pPr_change
        pPr = para._p.get_or_add_pPr()
        old_pPr = deepcopy_element(pPr)

    ind = _get_or_create_ind(para)
    ind.set(qn('w:left'), str(_twips_from_cm(indent_cm)))
    ind.set(qn('w:firstLine'), '0')
    # 同步更新 python-docx 缓存（避免后续读取不一致）
    para.paragraph_format.left_indent = Cm(indent_cm)
    para.paragraph_format.first_line_indent = Pt(0)

    # Track Changes: 修改后插入修订标记
    if tracker is not None:
        track_pPr_change(pPr, old_pPr, tracker)


def clear_paragraph_indent(para, tracker=None):
    """清除段落所有缩进（左缩进=0 + 首行缩进=0）。直接操作 w:ind XML。

    Args:
        tracker: 可选，RevisionTracker 实例；传入时启用 Track Changes 修订标记
    """
    # Track Changes: 修改前深拷贝 pPr
    if tracker is not None:
        from track_changes import deepcopy_element, track_pPr_change
        pPr = para._p.get_or_add_pPr()
        old_pPr = deepcopy_element(pPr)

    ind = _get_or_create_ind(para)
    ind.set(qn('w:left'), '0')
    ind.set(qn('w:firstLine'), '0')
    ind.set(qn('w:hanging'), '0')
    # 同步更新 python-docx 缓存
    para.paragraph_format.left_indent = Pt(0)
    para.paragraph_format.first_line_indent = Pt(0)

    # Track Changes: 修改后插入修订标记
    if tracker is not None:
        track_pPr_change(pPr, old_pPr, tracker)


def apply_outline_level(para, level: int, tracker=None):
    """设置段落的大纲级别（w:outlineLvl）。

    使 WPS/Word 导航窗格能正确识别标题层级，实现折叠/跳转功能。
    level 值：1→一级标题, 2→二级标题, 3→三级标题, 4→四级标题
    OOXML 中 outlineLvl 是 0 基：0=Heading1, 1=Heading2, ...

    Args:
        para: python-docx Paragraph 对象
        level: 标题级别（1-4）
        tracker: 可选，RevisionTracker 实例
    """
    if level < 1 or level > 9:
        return

    # Track Changes: 修改前深拷贝 pPr
    if tracker is not None:
        from track_changes import deepcopy_element, track_pPr_change
        pPr = para._p.get_or_add_pPr()
        old_pPr = deepcopy_element(pPr)

    pPr = para._p.get_or_add_pPr()
    outline_elem = pPr.find(qn('w:outlineLvl'))
    if outline_elem is None:
        outline_elem = OxmlElement('w:outlineLvl')
        pPr.append(outline_elem)

    # OOXML 是 0 基：level=1 → val=0, level=2 → val=1
    outline_elem.set(qn('w:val'), str(level - 1))

    # Track Changes: 修改后插入修订标记
    if tracker is not None:
        track_pPr_change(pPr, old_pPr, tracker)


def apply_paragraph_spacing(para, before_pt: float = 0, after_pt: float = 0, tracker=None):
    """设置段落前后间距。

    Args:
        tracker: 可选，RevisionTracker 实例；传入时启用 Track Changes 修订标记
    """
    # Track Changes: 修改前深拷贝 pPr
    if tracker is not None:
        from track_changes import deepcopy_element, track_pPr_change
        pPr = para._p.get_or_add_pPr()
        old_pPr = deepcopy_element(pPr)

    pf = para.paragraph_format
    pf.space_before = Pt(before_pt)
    pf.space_after = Pt(after_pt)

    # Track Changes: 修改后插入修订标记
    if tracker is not None:
        track_pPr_change(pPr, old_pPr, tracker)


# ──────────────────────────────────────────────
# 页面设置
# ──────────────────────────────────────────────

def apply_page_margins(section, spec):
    """应用页面边距到 section。"""
    page = spec.page
    section.top_margin = Cm(page['margin_top_cm'])
    section.bottom_margin = Cm(page['margin_bottom_cm'])
    section.left_margin = Cm(page['margin_left_cm'])
    section.right_margin = Cm(page['margin_right_cm'])

    # 页脚距离
    section.footer_distance = Cm(page.get('footer_distance_cm', 2.5))


def apply_page_size(section, spec):
    """应用页面尺寸和方向。"""
    page = spec.page
    # A4: 210mm x 297mm
    sizes = {
        'A4': (Cm(21.0), Cm(29.7)),
        'A3': (Cm(29.7), Cm(42.0)),
        'Letter': (Cm(21.59), Cm(27.94)),
        'Legal': (Cm(21.59), Cm(35.56)),
    }
    width, height = sizes.get(page['size'], sizes['A4'])
    if page.get('orientation') == 'landscape':
        width, height = height, width
    section.page_width = width
    section.page_height = height


# ──────────────────────────────────────────────
# 表格操作
# ──────────────────────────────────────────────

def apply_table_header_font(table, font_pair: FontPair, tracker=None):
    """设置表格第一行（表头）的字体。

    Args:
        tracker: 可选，RevisionTracker 实例；传入时启用 Track Changes 修订标记
    """
    if not table.rows:
        return
    header_row = table.rows[0]
    for cell in header_row.cells:
        for para in cell.paragraphs:
            apply_font_to_paragraph(para, font_pair, tracker=tracker)


def apply_table_header_bold(table):
    """设置表头加粗。"""
    if not table.rows:
        return

    for cell in table.rows[0].cells:
        for para in cell.paragraphs:
            for run in para.runs:
                run.bold = True


def apply_table_header_shading(table, color_hex: str):
    """设置表头背景色。"""
    if not table.rows:
        return

    for cell in table.rows[0].cells:
        tcPr = cell._tc.get_or_add_tcPr()
        shading = OxmlElement('w:shd')
        shading.set(qn('w:val'), 'clear')
        shading.set(qn('w:color'), 'auto')
        shading.set(qn('w:fill'), color_hex)
        tcPr.append(shading)


# ──────────────────────────────────────────────
# 页码插入（X/Y 格式）
# ──────────────────────────────────────────────

def add_page_number_to_section(section, font_pair: FontPair, show_total: bool = True):
    """向 section 的页脚插入页码。

    格式规则要求：正文页码从"1"开始连续编号，封面、签署页无页码。
    默认生成 X/Y 格式（PAGE / NUMPAGES），通过 show_total=False 仅生成 X 格式。

    show_total=True:  "1 / 5" (PAGE / NUMPAGES)
    show_total=False: "1"     (PAGE only)

    在页脚中创建一个居中段落，包含 PAGE 和 NUMPAGES 两个 Word 域，
    中间用 " / " 分隔。覆盖已有的页脚内容。

    XML 结构:
      <w:p>
        <w:pPr><w:jc w:val="center"/></w:pPr>
        <w:r><w:rPr>...font...</w:rPr><w:fldChar w:fldCharType="begin"/></w:r>
        <w:r><w:instrText> PAGE </w:instrText></w:r>
        <w:r><w:fldChar w:fldCharType="separate"/></w:r>
        <w:r><w:t>1</w:t></w:r>
        <w:r><w:fldChar w:fldCharType="end"/></w:r>
        <w:r><w:t xml:space="preserve"> / </w:t></w:r>
        <w:r><w:fldChar w:fldCharType="begin"/></w:r>
        <w:r><w:instrText> NUMPAGES </w:instrText></w:r>
        <w:r><w:fldChar w:fldCharType="separate"/></w:r>
        <w:r><w:t>1</w:t></w:r>
        <w:r><w:fldChar w:fldCharType="end"/></w:r>
      </w:p>
    """
    footer = section.footer
    # 确保 footer 存在且未链接到前一节
    footer.is_linked_to_previous = False

    # 清空已有页脚段落
    for existing_para in list(footer.paragraphs):
        p_element = existing_para._element
        p_element.getparent().remove(p_element)

    # 创建新段落
    from docx.oxml import OxmlElement
    from docx.text.paragraph import Paragraph

    p = OxmlElement('w:p')
    pPr = OxmlElement('w:pPr')
    jc = OxmlElement('w:jc')
    jc.set(qn('w:val'), 'center')
    pPr.append(jc)
    p.append(pPr)

    def _make_fld_run(fld_char_type: str):
        """创建域字符 run。"""
        r = OxmlElement('w:r')
        rPr = OxmlElement('w:rPr')
        _apply_font_rPr(rPr, font_pair)
        r.append(rPr)
        fldChar = OxmlElement('w:fldChar')
        fldChar.set(qn('w:fldCharType'), fld_char_type)
        r.append(fldChar)
        return r

    def _make_text_run(text: str, preserve_space: bool = False):
        """创建普通文本 run。"""
        r = OxmlElement('w:r')
        rPr = OxmlElement('w:rPr')
        _apply_font_rPr(rPr, font_pair)
        r.append(rPr)
        t = OxmlElement('w:t')
        if preserve_space:
            t.set(qn('xml:space'), 'preserve')
        t.text = text
        r.append(t)
        return r

    def _make_instr_run(instr: str):
        """创建指令文本 run。"""
        r = OxmlElement('w:r')
        rPr = OxmlElement('w:rPr')
        _apply_font_rPr(rPr, font_pair)
        r.append(rPr)
        instrText = OxmlElement('w:instrText')
        instrText.set(qn('xml:space'), 'preserve')
        instrText.text = instr
        r.append(instrText)
        return r

    # PAGE 域
    p.append(_make_fld_run('begin'))
    p.append(_make_instr_run(' PAGE '))
    p.append(_make_fld_run('separate'))
    p.append(_make_text_run('1'))
    p.append(_make_fld_run('end'))

    if show_total:
        # 分隔符 " / "
        p.append(_make_text_run(' / ', preserve_space=True))

        # NUMPAGES 域
        p.append(_make_fld_run('begin'))
        p.append(_make_instr_run(' NUMPAGES '))
        p.append(_make_fld_run('separate'))
        p.append(_make_text_run('1'))
        p.append(_make_fld_run('end'))

    # 添加段落到页脚

    # 将段落添加到页脚
    footer._element.append(p)
    log.info(f"已插入页码 X/Y 格式 → {font_pair.cjk} {font_pair.size_pt}pt 居中")


def _apply_font_rPr(rPr, font_pair: FontPair):
    """设置 run 属性元素 (w:rPr) 的字体（供内部使用）。"""
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:eastAsia'), font_pair.cjk)
    rFonts.set(qn('w:ascii'), font_pair.latin)
    rFonts.set(qn('w:hAnsi'), font_pair.latin)
    rFonts.set(qn('w:cs'), font_pair.latin)

    # 强制删除 hint 属性和 Theme 字体属性
    for attr in ['w:hint', 'w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme']:
        try:
            del rFonts.attrib[qn(attr)]
        except KeyError:
            pass

    rPr.append(rFonts)

    if font_pair.size_pt is not None:
        sz_val = str(int(font_pair.size_pt * 2))
        sz = OxmlElement('w:sz')
        sz.set(qn('w:val'), sz_val)
        rPr.append(sz)
        szCs = OxmlElement('w:szCs')
        szCs.set(qn('w:val'), sz_val)
        rPr.append(szCs)


def apply_table_borders(table, border_style: str = 'single'):
    """设置表格边框。"""
    tbl = table._tbl
    tblPr = tbl.find(qn('w:tblPr'))
    if tblPr is None:
        tblPr = OxmlElement('w:tblPr')
        tbl.insert(0, tblPr)

    borders = tblPr.find(qn('w:tblBorders'))
    if borders is not None:
        tblPr.remove(borders)

    borders = OxmlElement('w:tblBorders')
    for border_name in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        border = OxmlElement(f'w:{border_name}')
        border.set(qn('w:val'), border_style)
        border.set(qn('w:sz'), '4')
        border.set(qn('w:space'), '0')
        border.set(qn('w:color'), '000000')
        borders.append(border)

    tblPr.append(borders)
