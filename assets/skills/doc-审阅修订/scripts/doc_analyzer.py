"""
doc_analyzer.py — 文档结构分析器

负责：
1. 打开 .docx 文件，解包分析
2. 遍历 sections、paragraphs、runs
3. 识别文档区域：封面、目录、正文、修订记录
4. 提取当前格式信息用于对比
"""

from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from lxml import etree
from utils import log, NSMAP


# ──────────────────────────────────────────────
# 区域类型
# ──────────────────────────────────────────────

class Region:
    """文档区域。"""
    COVER = "cover"
    TOC = "toc"
    BODY = "body"
    REVISION = "revision_history"


class RegionInfo:
    """区域信息。"""
    def __init__(self, region_type: str, start_para_idx: int,
                 end_para_idx: int = -1, metadata: dict = None):
        self.type = region_type
        self.start = start_para_idx
        self.end = end_para_idx if end_para_idx >= 0 else start_para_idx
        self.metadata = metadata or {}

    def __repr__(self):
        return f"Region({self.type}, paras {self.start}-{self.end})"


# ──────────────────────────────────────────────
# 文档分析结果
# ──────────────────────────────────────────────

class DocAnalysis:
    """文档分析结果。"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.sections = []
        self.paragraphs = []
        self.regions = []  # list of RegionInfo
        self.tables = []
        self._doc = None

    @property
    def paragraph_count(self):
        return len(self.paragraphs)

    @property
    def section_count(self):
        return len(self.sections)

    def get_region(self, region_type: str):
        """获取指定类型的第一个区域。"""
        for r in self.regions:
            if r.type == region_type:
                return r
        return None

    def get_cover_paragraphs(self):
        """获取封面区域的所有段落。"""
        r = self.get_region(Region.COVER)
        if r is None:
            return []
        return self.paragraphs[r.start:r.end + 1]

    def get_body_paragraphs(self):
        """获取正文区域的所有段落。"""
        r = self.get_region(Region.BODY)
        if r is None:
            return self.paragraphs
        return self.paragraphs[r.start:r.end + 1]

    def get_revision_region(self):
        """获取修订记录区域。"""
        return self.get_region(Region.REVISION)

    def get_toc_region(self):
        """获取目录区域。"""
        return self.get_region(Region.TOC)


# ──────────────────────────────────────────────
# 段落信息
# ──────────────────────────────────────────────

class ParaInfo:
    """段落分析信息。"""

    def __init__(self, para, index: int):
        self.index = index
        self.text = para.text or ""
        self.style = para.style.name if para.style else "Normal"
        self.alignment = str(para.alignment) if para.alignment else None
        self.para_format = {}

        # 段落格式
        pf = para.paragraph_format
        self.para_format['line_spacing'] = pf.line_spacing
        self.para_format['left_indent'] = pf.left_indent
        self.para_format['first_line_indent'] = pf.first_line_indent
        self.para_format['space_before'] = pf.space_before
        self.para_format['space_after'] = pf.space_after

        # runs 信息
        self.runs = []
        for run in para.runs:
            self.runs.append(RunInfo(run))

        # 是否包含表格
        self.has_table = False

    @property
    def is_empty(self):
        return self.text.strip() == "" and not self.runs

    @property
    def is_centered(self):
        return self.alignment and 'CENTER' in str(self.alignment).upper()

    def __repr__(self):
        preview = self.text[:50].replace('\n', ' ')
        return f"ParaInfo[{self.index}]({self.style}): {preview}"


class RunInfo:
    """Run 分析信息。"""

    def __init__(self, run):
        self.text = run.text or ""
        self.bold = run.bold
        self.italic = run.italic

        # 字体信息
        rPr = run._r.find(qn('w:rPr'))
        if rPr is not None:
            rFonts = rPr.find(qn('w:rFonts'))
            if rFonts is not None:
                self.font_east_asia = rFonts.get(qn('w:eastAsia'), '')
                self.font_ascii = rFonts.get(qn('w:ascii'), '')
                self.font_hAnsi = rFonts.get(qn('w:hAnsi'), '')
            else:
                self.font_east_asia = ''
                self.font_ascii = ''
                self.font_hAnsi = ''

            sz = rPr.find(qn('w:sz'))
            self.size_pt = int(sz.get(qn('w:val'))) / 2 if sz is not None else None
        else:
            self.font_east_asia = ''
            self.font_ascii = ''
            self.font_hAnsi = ''
            self.size_pt = None

    @property
    def cjk_font(self):
        return self.font_east_asia

    @property
    def latin_font(self):
        return self.font_ascii or self.font_hAnsi


# ──────────────────────────────────────────────
# 区域识别器（region_detector）
# ──────────────────────────────────────────────

class RegionDetector:
    """识别文档中的不同区域。"""

    # 识别策略常量
    COVER_MAX_PARAS = 20       # 封面最多往前查 N 个段落
    TOC_KEYWORDS = ["目录", "目  录", "Table of Contents"]
    REVISION_KEYWORDS = ["修订记录", "版本历史", "修订历史", "Revision History", "变更记录"]

    def __init__(self, doc_analysis: DocAnalysis, spec=None):
        self.analysis = doc_analysis
        self.spec = spec
        self.paras = doc_analysis.paragraphs

    def detect_all(self) -> list:
        """识别所有区域，返回 RegionInfo 列表。"""
        regions = []

        # 1. 封面检测
        cover = self._detect_cover()
        if cover:
            regions.append(cover)

        # 2. 目录检测
        toc = self._detect_toc(cover)
        if toc:
            regions.append(toc)

        # 3. 修订记录检测
        revision = self._detect_revision()
        if revision:
            regions.append(revision)

        # 4. 正文 = 剩余部分
        body = self._detect_body(regions)
        if body:
            regions.append(body)

        # 按起始位置排序
        regions.sort(key=lambda r: r.start)
        self.analysis.regions = regions
        return regions

    def _detect_cover(self):
        """检测封面区域。"""
        doc = self.analysis._doc
        if doc is None:
            return None

        # 策略 1：检查第一个 section 是否为 titlePg
        if doc.sections and doc.sections[0].start_type is not None:
            sectPr = doc.sections[0]._sectPr
            titlePg = sectPr.find(qn('w:titlePg'))
            if titlePg is not None:
                # 封面 section 存在 — 计算封面段落范围
                # 封面通常是第一个区域的居中段落
                end = 0
                for i, para in enumerate(self.paras):
                    end = i
                    # 遇到目录关键词或标题关键词则结束
                    if any(kw in para.text for kw in self.TOC_KEYWORDS):
                        end = max(0, i - 1)
                        break
                    if para.text.strip().startswith(('一、', '1.', '第')) and i > 3:
                        end = max(0, i - 1)
                        break
                    if i >= self.COVER_MAX_PARAS:
                        break

                log.info(f"通过 titlePg 检测到封面 (段落 0-{end})")
                return RegionInfo(Region.COVER, 0, end,
                                  metadata={"method": "titlePg"})

        # 策略 2：回退 — 前 N 个居中段落
        end = -1
        for i, para in enumerate(self.paras):
            if i >= self.COVER_MAX_PARAS:
                end = i - 1
                break
            if any(kw in para.text for kw in self.TOC_KEYWORDS + self.REVISION_KEYWORDS):
                end = i - 1
                break
        if end >= 2:  # 至少有 3 个段落形成封面
            log.info(f"通过居中段落检测到封面 (段落 0-{end})")
            return RegionInfo(Region.COVER, 0, end,
                              metadata={"method": "centered_fallback"})

        return None

    def _detect_toc(self, cover: RegionInfo = None):
        """检测目录区域。"""
        start_from = cover.end + 1 if cover else 0
        for i in range(start_from, len(self.paras)):
            text = self.paras[i].text.strip()
            if any(kw in text for kw in self.TOC_KEYWORDS):
                # 找到目录标题，目录区域延伸到首个正文标题前
                end = i
                for j in range(i + 1, min(i + 30, len(self.paras))):
                    t = self.paras[j].text.strip()
                    if t.startswith(('一、', '1.', '第一章', '第1章')) and j > i + 1:
                        end = j - 1
                        break
                    end = j
                log.info(f"检测到目录区域 (段落 {i}-{end})")
                return RegionInfo(Region.TOC, i, end,
                                  metadata={"keyword": text[:20]})
        return None

    def _detect_revision(self):
        """检测修订记录区域。"""
        for i, para in enumerate(self.paras):
            text = para.text.strip()
            if any(kw in text for kw in self.REVISION_KEYWORDS):
                # 修订记录通常紧跟一个表格
                end = i
                for j in range(i + 1, min(i + 15, len(self.paras))):
                    if self.paras[j].text.strip().startswith(('一、', '1.', '附件')):
                        end = j - 1
                        break
                    end = j
                log.info(f"检测到修订记录区域 (段落 {i}-{end})")
                return RegionInfo(Region.REVISION, i, end,
                                  metadata={"keyword": text[:20]})
        return None

    def _detect_body(self, existing_regions: list):
        """正文 = 所有未被覆盖的段落。"""
        if not existing_regions:
            return RegionInfo(Region.BODY, 0, len(self.paras) - 1)

        covered = set()
        for r in existing_regions:
            for i in range(r.start, r.end + 1):
                covered.add(i)

        # 找第一个未被覆盖的段落
        start = None
        end = len(self.paras) - 1
        for i in range(len(self.paras)):
            if i not in covered:
                if start is None:
                    start = i
                end = i

        if start is not None:
            return RegionInfo(Region.BODY, start, end)
        return None


# ──────────────────────────────────────────────
# 主分析函数
# ──────────────────────────────────────────────

def analyze_document(filepath: str, spec=None) -> DocAnalysis:
    """
    分析 docx 文档结构。

    Args:
        filepath: .docx 文件路径
        spec: 格式规范（Spec 对象），用于区域识别参数

    Returns:
        DocAnalysis 对象
    """
    filepath = str(Path(filepath).resolve())
    if not Path(filepath).exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")

    log.info(f"开始分析文档: {filepath}")

    analysis = DocAnalysis(filepath)
    analysis._doc = Document(filepath)

    # 提取 sections 信息
    for i, section in enumerate(analysis._doc.sections):
        sec_info = {
            'index': i,
            'page_width': section.page_width,
            'page_height': section.page_height,
            'margin_top': section.top_margin,
            'margin_bottom': section.bottom_margin,
            'margin_left': section.left_margin,
            'margin_right': section.right_margin,
        }
        analysis.sections.append(sec_info)

    # 提取所有段落信息（包括表格内的段落）
    for i, para in enumerate(analysis._doc.paragraphs):
        pi = ParaInfo(para, i)
        analysis.paragraphs.append(pi)

    # 提取表格信息
    for i, table in enumerate(analysis._doc.tables):
        table_info = {
            'index': i,
            'rows': len(table.rows),
            'cols': len(table.columns),
            'header': [cell.text for cell in table.rows[0].cells] if table.rows else [],
        }
        analysis.tables.append(table_info)

    # 区域识别
    detector = RegionDetector(analysis, spec)
    regions = detector.detect_all()

    log.info(f"文档分析完成: {len(analysis.paragraphs)} 段落, "
             f"{len(analysis.tables)} 表格, "
             f"{len(regions)} 区域")

    return analysis


# ──────────────────────────────────────────────
# 分析报告生成
# ──────────────────────────────────────────────

def print_analysis_report(analysis: DocAnalysis):
    """打印人类可读的分析报告。"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"文档分析报告: {analysis.filepath}")
    lines.append("=" * 60)
    lines.append(f"  段落总数: {analysis.paragraph_count}")
    lines.append(f"  章节数:   {analysis.section_count}")
    lines.append(f"  表格数:   {len(analysis.tables)}")
    lines.append("")

    if analysis.regions:
        lines.append("  识别区域:")
        for r in analysis.regions:
            display_type = {
                Region.COVER: "封面",
                Region.TOC: "目录",
                Region.BODY: "正文",
                Region.REVISION: "修订记录",
            }.get(r.type, r.type)
            para_count = r.end - r.start + 1
            lines.append(f"    [{display_type}] 段落 {r.start}-{r.end} ({para_count}段)")
            if r.metadata:
                for k, v in r.metadata.items():
                    lines.append(f"        {k}: {v}")
    else:
        lines.append("  未识别出明确区域结构")

    lines.append("=" * 60)

    report = "\n".join(lines)
    log.info(f"\n{report}")
    return report
