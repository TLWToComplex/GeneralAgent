#!/usr/bin/env python3
"""
DOCX 合同审查报告生成脚本 — 替代 MD 报告，输出结构化 DOCX + 原始合同批注版。

用法：
    python scripts/generate_docx_report.py \
        --clauses "./contract review/extracted_clauses.json" \
        --risks "./contract review/risk_register.json" \
        --compliance "./contract review/compliance_report.json" \
        --suggestions "./contract review/suggestions.json" \
        --output "./合同审核报告.docx"
        [--annotate "原始合同.docx"]  可选，生成原始合同批注版
"""

import argparse
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from docx import Document
from docx.shared import (
    Inches, Pt, Cm, RGBColor, Emu
)
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# 常量
# ═══════════════════════════════════════════════════════════

RISK_COLORS = {
    "high":   RGBColor(0xCC, 0x00, 0x00),
    "medium": RGBColor(0xCC, 0x88, 0x00),
    "low":    RGBColor(0x00, 0x88, 0x00),
}

RISK_LABELS = {
    "high":   "高风险",
    "medium": "中风险",
    "low":    "低风险",
    "none":   "无风险",
}

RISK_EMOJI = {
    "high":   "●",
    "medium": "●",
    "low":    "●",
    "none":   "○",
}

# 中文风险类型映射
RISK_TYPE_CN = {
    "unlimited_liability": "无限责任",
    "unilateral_termination": "单方解除权",
    "unfair_penalty": "不合理违约金",
    "vague_terms": "模糊条款",
    "missing_protection": "缺少保护条款",
    "ip_risk": "知识产权风险",
    "payment_risk": "付款风险",
    "confidentiality_risk": "保密风险",
    "jurisdiction_risk": "管辖权风险",
    "auto_renewal_risk": "自动续约风险",
    "liability": "责任条款风险",
    "termination": "终止条款风险",
    "payment": "付款条款风险",
    "ip": "知识产权风险",
    "data": "数据保护风险",
    "confidentiality": "保密风险",
    "noncompete": "竞业限制风险",
    "governing_law": "管辖法律风险",
}

A4_WIDTH = Cm(21)
A4_HEIGHT = Cm(29.7)
MARGIN = Cm(2.54)


# ═══════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════

def load_json(path: Optional[str]) -> Optional[Dict]:
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("无法加载 %s: %s", path, e)
        return None


def fmt_risk(level: str) -> str:
    return RISK_LABELS.get(level, level)


def fmt_risk_color(level: str) -> RGBColor:
    return RISK_COLORS.get(level, RGBColor(0x66, 0x66, 0x66))


def fmt_risk_type(rt: str) -> str:
    return RISK_TYPE_CN.get(rt.lower(), rt)


# ═══════════════════════════════════════════════════════════
# 文档辅助
# ═══════════════════════════════════════════════════════════

def set_cell_border(cell, **kwargs):
    """设置单元格边框。"""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for edge, val in kwargs.items():
        element = OxmlElement(f'w:{edge}')
        element.set(qn('w:val'), val.get('val', 'single'))
        element.set(qn('w:sz'), val.get('sz', '4'))
        element.set(qn('w:color'), val.get('color', '000000'))
        tcBorders.append(element)
    tcPr.append(tcBorders)


def add_run_with_font(para, text: str, bold=False, size=Pt(11),
                      color=None, font_name="微软雅黑", font_name_west="Calibri"):
    """添加带格式的 run。"""
    run = para.add_run(text)
    run.bold = bold
    run.font.size = size
    if color:
        run.font.color.rgb = color
    run.font.name = font_name_west
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.insert(0, rFonts)
    rFonts.set(qn('w:eastAsia'), font_name)
    return run


def add_heading_styled(doc, text: str, level: int = 1):
    """添加带 CJK 字体的标题。"""
    para = doc.add_paragraph()
    if level == 0:
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = para.add_run(text)
        run.bold = True
        run.font.size = Pt(22)
        run.font.color.rgb = RGBColor(0x1A, 0x3C, 0x6E)
        run.font.name = "Calibri"
        rPr = run._element.get_or_add_rPr()
        rFonts = OxmlElement('w:rFonts')
        rFonts.set(qn('w:eastAsia'), "微软雅黑")
        rPr.insert(0, rFonts)
    else:
        para.style = doc.styles[f'Heading {level}']
        run = para.add_run(text)
        rPr = run._element.get_or_add_rPr()
        rFonts = OxmlElement('w:rFonts')
        rFonts.set(qn('w:eastAsia'), "黑体")
        rPr.insert(0, rFonts)
    return para


def add_body_para(doc, text: str, indent=True):
    """添加正文段落。"""
    para = doc.add_paragraph()
    para.paragraph_format.line_spacing = 1.5
    para.paragraph_format.space_after = Pt(6)
    if indent:
        para.paragraph_format.first_line_indent = Cm(0.74)
    add_run_with_font(para, text, size=Pt(11), font_name="宋体")
    return para


def set_table_style(table):
    """统一表格样式。"""
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for row in table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                para.paragraph_format.space_before = Pt(2)
                para.paragraph_format.space_after = Pt(2)
                for run in para.runs:
                    run.font.size = Pt(9)
                    run.font.name = "Calibri"
                    rPr = run._element.get_or_add_rPr()
                    rFonts = OxmlElement('w:rFonts')
                    rFonts.set(qn('w:eastAsia'), "宋体")
                    rPr.insert(0, rFonts)


# ═══════════════════════════════════════════════════════════
# 报告生成主逻辑
# ═══════════════════════════════════════════════════════════

class DocxReportGenerator:
    """DOCX 合同审查报告生成器。"""

    def __init__(self):
        self.doc = Document()
        self._setup_page()

    def _setup_page(self):
        """设置 A4 页面。"""
        section = self.doc.sections[0]
        section.page_width = A4_WIDTH
        section.page_height = A4_HEIGHT
        section.top_margin = MARGIN
        section.bottom_margin = MARGIN
        section.left_margin = Cm(2.8)
        section.right_margin = Cm(2.8)

    # ── 封面 ──────────────────────────────────────────

    def build_cover(self, clauses_data: Dict, risk_data: Dict, comp_data: Dict):
        """构建封面页。"""
        metadata = clauses_data.get("metadata", {}) if clauses_data else {}
        filename = metadata.get("filename", "未知文件")
        contract_type = metadata.get("contract_type", "未知")

        # 空行撑开
        for _ in range(6):
            self.doc.add_paragraph()

        add_heading_styled(self.doc, "合同审查报告", level=0)

        para = self.doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_run_with_font(para, f"《{filename.replace('.docx','').replace('.pdf','')}审核》",
                          bold=True, size=Pt(16), color=RGBColor(0x33, 0x33, 0x33),
                          font_name="微软雅黑")

        self.doc.add_paragraph()

        # 基本信息表
        info_items = [
            ("合同类型", contract_type),
            ("审查日期", datetime.now().strftime("%Y年%m月%d日")),
            ("审查方式", "条款提取 → 合规检查（双轨制）→ 风险分析 → 修改建议"),
        ]

        overall_risk = "none"
        if risk_data:
            overall_risk = risk_data.get("overall_risk_level") or risk_data.get("overall_risk", "none")
        overall_comp = comp_data.get("overall_compliance", "unknown") if comp_data else "unknown"

        info_items.append(("整体风险等级", f"{fmt_risk(overall_risk)}"))
        info_items.append(("合规状态", "合规" if overall_comp == "compliant" else ("不合规" if overall_comp == "non_compliant" else "待审查")))

        table = self.doc.add_table(rows=len(info_items), cols=2)
        table.style = 'Table Grid'
        for i, (k, v) in enumerate(info_items):
            c0 = table.cell(i, 0)
            c1 = table.cell(i, 1)
            c0.width = Cm(4)
            c1.width = Cm(10)
            p0 = c0.paragraphs[0]
            p1 = c1.paragraphs[0]
            add_run_with_font(p0, k, bold=True, size=Pt(11), font_name="微软雅黑")
            add_run_with_font(p1, v, size=Pt(11), font_name="宋体")

        self.doc.add_page_break()

    # ── 一、执行摘要 ──────────────────────────────────

    def build_executive_summary(self, risk_data: Dict, comp_data: Dict, sugg_data: Dict):
        """构建执行摘要。"""
        add_heading_styled(self.doc, "一、执行摘要", level=1)

        # 统计
        findings = risk_data.get("findings", []) if risk_data else []
        comp_findings = comp_data.get("findings", []) if comp_data else []
        suggestions = sugg_data.get("suggestions", []) if sugg_data else []

        high = sum(1 for f in findings if f.get("risk_level") == "high")
        medium = sum(1 for f in findings if f.get("risk_level") == "medium")
        low = sum(1 for f in findings if f.get("risk_level") == "low")

        summary_lines = [
            f"本次审查共发现 {high} 个高风险问题、{medium} 个中风险问题、{low} 个低风险问题。",
            f"合规检查发现 {len(comp_findings)} 条合规问题（含缺失条款）。",
            f"共生成 {len(suggestions)} 条修改建议（按优先级排列）。",
        ]
        for line in summary_lines:
            add_body_para(self.doc, line)

        # 法规覆盖
        checked_regs = comp_data.get("checked_regulations", []) if comp_data else []
        if checked_regs:
            add_body_para(self.doc, "已检查的法规：")
            for item in checked_regs:
                if isinstance(item, dict):
                    reg = item.get("regulation", "")
                    arts = item.get("articles", [])
                    arts_str = f"（条文：{'、'.join(arts)}）" if arts else ""
                    p = self.doc.add_paragraph()
                    p.paragraph_format.left_indent = Cm(1)
                    add_run_with_font(p, f"• {reg}{arts_str}", size=Pt(10), font_name="宋体")

        self.doc.add_page_break()

    # ── 二、条款审查（按合同顺序）────────────────────

    def build_clause_review(
        self,
        clauses_data: Dict,
        risk_data: Dict,
        comp_data: Dict,
        sugg_data: Dict,
    ):
        """按合同原文条款顺序逐条审查。"""
        add_heading_styled(self.doc, "二、条款审查（按合同原文顺序）", level=1)

        clauses = clauses_data.get("clauses", []) if clauses_data else []
        if not clauses:
            add_body_para(self.doc, "（无条款数据）")
            return

        # 收集所有发现并按 clause_id 建索引
        all_findings_by_clause: Dict[str, List[Dict]] = {}

        # 风险发现
        if risk_data:
            raw = risk_data.get("findings", [])
            # 兼容嵌套格式
            for item in raw:
                if "findings" in item and isinstance(item["findings"], list):
                    cid = item.get("clause_id", "")
                    for sub in item["findings"]:
                        all_findings_by_clause.setdefault(cid, []).append({
                            "type": "风险",
                            "risk_level": sub.get("risk_level", "medium"),
                            "risk_type": sub.get("dimension", sub.get("risk_type", "")),
                            "description": sub.get("dimension_name", sub.get("description", "")),
                            "rationale": ", ".join(sub.get("signals", [])) or sub.get("rationale", ""),
                            "recommendation": sub.get("recommendation", ""),
                        })
                else:
                    cid = item.get("clause_id", "")
                    all_findings_by_clause.setdefault(cid, []).append({
                        "type": "风险",
                        "risk_level": item.get("risk_level", "medium"),
                        "risk_type": item.get("risk_type", ""),
                        "description": item.get("description", ""),
                        "rationale": item.get("rationale", ""),
                        "buyer_impact": item.get("buyer_impact", ""),
                        "seller_impact": item.get("seller_impact", ""),
                        "recommendation": item.get("recommendation", ""),
                    })

        # 合规发现
        if comp_data:
            for f in comp_data.get("findings", []):
                cid = f.get("clause_id", "")
                all_findings_by_clause.setdefault(cid, []).append({
                    "type": "合规",
                    "risk_level": f.get("risk_level", "medium"),
                    "regulation": f.get("regulation", ""),
                    "issue": f.get("issue", ""),
                    "reason": f.get("reason", ""),
                    "recommendation": f.get("recommendation", ""),
                })

        # 建议索引
        sugg_by_clause: Dict[str, List[Dict]] = {}
        if sugg_data:
            for s in sugg_data.get("suggestions", []):
                cid = s.get("clause_id", "")
                sugg_by_clause.setdefault(cid, []).append(s)

        # 遍历条款
        has_any_finding = False
        for clause in clauses:
            cid = clause.get("id", "")
            title = clause.get("title", "")
            text = clause.get("text", "")

            findings_for_clause = all_findings_by_clause.get(cid, [])
            suggs_for_clause = sugg_by_clause.get(cid, [])

            # 条款标题
            p_title = self.doc.add_paragraph()
            p_title.paragraph_format.space_before = Pt(12)
            clause_label = f"第{cid}条" if cid.isdigit() else cid
            if title and title != "全文":
                clause_label += f"  {title}"
            add_run_with_font(p_title, clause_label, bold=True, size=Pt(13),
                              font_name="黑体", font_name_west="Calibri")

            if findings_for_clause:
                has_any_finding = True
                # 按风险等级排序
                risk_order = {"high": 0, "medium": 1, "low": 2}
                findings_for_clause.sort(key=lambda f: risk_order.get(f.get("risk_level", "low"), 3))

                for fi, f in enumerate(findings_for_clause):
                    rl = f.get("risk_level", "medium")
                    color = fmt_risk_color(rl)
                    emoji = RISK_EMOJI.get(rl, "○")

                    # 风险标记段落
                    p_mark = self.doc.add_paragraph()
                    p_mark.paragraph_format.left_indent = Cm(0.5)
                    add_run_with_font(p_mark, f"{emoji} ", bold=True, size=Pt(12), color=color)
                    add_run_with_font(p_mark, f"[{fmt_risk(rl)}] ", bold=True, size=Pt(10), color=color)

                    if f["type"] == "合规":
                        desc = f.get("issue", "")
                        add_run_with_font(p_mark, desc, size=Pt(10), font_name="宋体")
                    else:
                        desc = f.get("description", "")
                        rt = fmt_risk_type(f.get("risk_type", ""))
                        if rt:
                            desc = f"[{rt}] {desc}"
                        add_run_with_font(p_mark, desc, size=Pt(10), font_name="宋体")

                    # 详细说明
                    detail_parts = []
                    if f.get("regulation"):
                        detail_parts.append(f"法规出处：{f['regulation']}")
                    if f.get("reason"):
                        detail_parts.append(f"原因：{f['reason']}")
                    elif f.get("rationale"):
                        detail_parts.append(f"依据：{f['rationale']}")
                    if f.get("buyer_impact"):
                        detail_parts.append(f"对甲方影响：{f['buyer_impact']}")
                    if f.get("seller_impact"):
                        detail_parts.append(f"对乙方影响：{f['seller_impact']}")

                    for dp in detail_parts:
                        p_det = self.doc.add_paragraph()
                        p_det.paragraph_format.left_indent = Cm(1.5)
                        add_run_with_font(p_det, dp, size=Pt(9),
                                          font_name="宋体",
                                          color=RGBColor(0x55, 0x55, 0x55))

                    # 建议
                    if f.get("recommendation"):
                        p_rec = self.doc.add_paragraph()
                        p_rec.paragraph_format.left_indent = Cm(1.5)
                        add_run_with_font(p_rec, "建议：", bold=True, size=Pt(9), font_name="微软雅黑")
                        add_run_with_font(p_rec, f['recommendation'], size=Pt(9), font_name="宋体",
                                          color=RGBColor(0x00, 0x66, 0xCC))

                # 该条款的修改建议
                if suggs_for_clause:
                    for s in suggs_for_clause:
                        p_sugg = self.doc.add_paragraph()
                        p_sugg.paragraph_format.left_indent = Cm(1.5)
                        add_run_with_font(p_sugg, "修订建议：", bold=True, size=Pt(9),
                                          font_name="微软雅黑", color=RGBColor(0x00, 0x66, 0xCC))
                        if s.get("original_text"):
                            add_run_with_font(p_sugg, f"\n原文：{s['original_text'][:120]}",
                                              size=Pt(8), font_name="宋体",
                                              color=RGBColor(0xCC, 0x00, 0x00))
                        if s.get("suggested_text"):
                            add_run_with_font(p_sugg, f"\n修改为：{s['suggested_text'][:120]}",
                                              size=Pt(8), font_name="宋体",
                                              color=RGBColor(0x00, 0x66, 0x00))
            else:
                # 无风险
                p_ok = self.doc.add_paragraph()
                p_ok.paragraph_format.left_indent = Cm(0.5)
                add_run_with_font(p_ok, "✓ 本条未发现明显风险", size=Pt(10),
                                  font_name="宋体", color=RGBColor(0x66, 0x99, 0x66))

        if not has_any_finding:
            add_body_para(self.doc, "✅ 整体未发现明显风险问题。")

        # 处理无条款归属的发现（clause_id 为空的合规审查项）
        uncategorized = all_findings_by_clause.get("", [])
        if uncategorized:
            self.doc.add_paragraph()
            p_uncat = self.doc.add_paragraph()
            add_run_with_font(p_uncat, "▎ 合同整体审查项", bold=True, size=Pt(13),
                              font_name="黑体", font_name_west="Calibri")
            for f in uncategorized:
                rl = f.get("risk_level", "medium")
                color = fmt_risk_color(rl)
                emoji = RISK_EMOJI.get(rl, "○")
                p_m = self.doc.add_paragraph()
                p_m.paragraph_format.left_indent = Cm(0.5)
                add_run_with_font(p_m, f"{emoji} [{fmt_risk(rl)}] ", bold=True, size=Pt(10), color=color)
                desc = f.get("issue") or f.get("description", "")
                add_run_with_font(p_m, desc, size=Pt(10), font_name="宋体")
                if f.get("reason"):
                    p_d = self.doc.add_paragraph()
                    p_d.paragraph_format.left_indent = Cm(1.5)
                    add_run_with_font(p_d, f"原因：{f['reason']}", size=Pt(9), font_name="宋体",
                                      color=RGBColor(0x55, 0x55, 0x55))
                if f.get("regulation"):
                    p_s = self.doc.add_paragraph()
                    p_s.paragraph_format.left_indent = Cm(1.5)
                    add_run_with_font(p_s, f"法规出处：{f['regulation']}", size=Pt(9), font_name="宋体",
                                      color=RGBColor(0x55, 0x55, 0x55))
                if f.get("recommendation"):
                    p_r = self.doc.add_paragraph()
                    p_r.paragraph_format.left_indent = Cm(1.5)
                    add_run_with_font(p_r, f"建议：{f['recommendation']}", size=Pt(9), font_name="宋体",
                                      color=RGBColor(0x00, 0x66, 0xCC))

        self.doc.add_page_break()

    # ── 三、合规检查 ──────────────────────────────────

    def build_compliance(self, comp_data: Dict):
        """构建合规检查章节。"""
        add_heading_styled(self.doc, "三、合规检查结果", level=1)

        if not comp_data:
            add_body_para(self.doc, "（无合规检查数据）")
            return

        overall = comp_data.get("overall_compliance", "unknown")
        status_text = {"compliant": "✅ 合规", "non_compliant": "❌ 不合规", "needs_review": "⚠️ 待审查"}
        add_body_para(self.doc, f"整体合规状态：{status_text.get(overall, overall)}")

        # 缺失条款
        missing_detail = comp_data.get("missing_clauses_detail", [])
        if missing_detail:
            add_heading_styled(self.doc, "缺失的必要条款", level=2)
            table = self.doc.add_table(rows=len(missing_detail) + 1, cols=4)
            table.style = 'Table Grid'
            headers = ["缺失条款", "风险等级", "法规出处", "建议"]
            for j, h in enumerate(headers):
                p = table.cell(0, j).paragraphs[0]
                add_run_with_font(p, h, bold=True, size=Pt(9), font_name="微软雅黑")
            for i, m in enumerate(missing_detail):
                row = table.rows[i + 1]
                add_run_with_font(row.cells[0].paragraphs[0], m.get("name", ""), size=Pt(9), font_name="宋体")
                add_run_with_font(row.cells[1].paragraphs[0], fmt_risk(m.get("risk_level", "medium")), size=Pt(9))
                add_run_with_font(row.cells[2].paragraphs[0], (m.get("source", "") or "")[:50], size=Pt(8), font_name="宋体")
                add_run_with_font(row.cells[3].paragraphs[0], (m.get("recommendation", "") or "")[:60], size=Pt(8), font_name="宋体")
            set_table_style(table)
            self.doc.add_paragraph()

        # 不合规/待审查
        findings = comp_data.get("findings", [])
        non_compliant = [f for f in findings if f.get("status") == "non_compliant"]
        needs_review = [f for f in findings if f.get("status") == "needs_review"]

        if non_compliant:
            add_heading_styled(self.doc, "不合规条款", level=2)
            self._build_compliance_table(non_compliant)

        if needs_review:
            add_heading_styled(self.doc, "待审查条款", level=2)
            self._build_compliance_table(needs_review)

        # 法规清单
        checked = comp_data.get("checked_regulations", [])
        skipped = comp_data.get("skipped_regulations", [])
        if checked:
            add_heading_styled(self.doc, "已检查的法规", level=2)
            for item in checked:
                if isinstance(item, dict):
                    reg = item.get("regulation", "")
                    arts = item.get("articles", [])
                    arts_str = f"  — 条文：{'、'.join(arts)}" if arts else ""
                    add_body_para(self.doc, f"📖 {reg}{arts_str}")
        if skipped:
            add_heading_styled(self.doc, "已跳过的法规（合同内容未触发）", level=2)
            for sr in skipped:
                if isinstance(sr, dict):
                    add_body_para(self.doc, f"⏭️ {sr.get('regulation', '')} — {sr.get('reason', '')}")

        self.doc.add_page_break()

    def _build_compliance_table(self, findings: List[Dict]):
        """构建合规发现表格。"""
        if not findings:
            return
        table = self.doc.add_table(rows=len(findings) + 1, cols=5)
        table.style = 'Table Grid'
        headers = ["条款ID", "风险等级", "法规出处", "问题", "建议"]
        for j, h in enumerate(headers):
            add_run_with_font(table.cell(0, j).paragraphs[0], h, bold=True, size=Pt(8), font_name="微软雅黑")
        for i, f in enumerate(findings):
            row = table.rows[i + 1]
            add_run_with_font(row.cells[0].paragraphs[0], f.get("clause_id", ""), size=Pt(8), font_name="宋体")
            add_run_with_font(row.cells[1].paragraphs[0], fmt_risk(f.get("risk_level", "medium")), size=Pt(8),
                              color=fmt_risk_color(f.get("risk_level", "medium")))
            add_run_with_font(row.cells[2].paragraphs[0], (f.get("regulation", ""))[:40], size=Pt(7), font_name="宋体")
            add_run_with_font(row.cells[3].paragraphs[0], (f.get("issue", ""))[:50], size=Pt(7), font_name="宋体")
            add_run_with_font(row.cells[4].paragraphs[0], (f.get("recommendation", ""))[:50], size=Pt(7), font_name="宋体")
        set_table_style(table)
        self.doc.add_paragraph()

    # ── 四、修改建议汇总 ──────────────────────────────

    def build_suggestions(self, sugg_data: Dict):
        """构建修改建议汇总。"""
        add_heading_styled(self.doc, "四、修改建议汇总", level=1)

        if not sugg_data:
            add_body_para(self.doc, "（无修改建议数据）")
            return

        suggestions = sugg_data.get("suggestions", [])
        if not suggestions:
            add_body_para(self.doc, "无修改建议。")
            return

        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        suggestions.sort(key=lambda s: priority_order.get(s.get("priority", "low"), 3))

        high_s = [s for s in suggestions if s.get("priority") == "high"]
        medium_s = [s for s in suggestions if s.get("priority") == "medium"]
        low_s = [s for s in suggestions if s.get("priority") == "low"]

        add_body_para(self.doc, f"共 {len(high_s)} 条高优先级、{len(medium_s)} 条中优先级、{len(low_s)} 条低优先级建议。")

        for priority, label, color in [("high", "高优先级（签署前必须解决）", RGBColor(0xCC, 0x00, 0x00)),
                                        ("medium", "中优先级（建议修改）", RGBColor(0xCC, 0x88, 0x00)),
                                        ("low", "低优先级（建议关注）", RGBColor(0x00, 0x88, 0x00))]:
            group = [s for s in suggestions if s.get("priority") == priority]
            if not group:
                continue

            add_heading_styled(self.doc, label, level=2)

            table = self.doc.add_table(rows=len(group) + 1, cols=4)
            table.style = 'Table Grid'
            headers = ["条款ID", "修改理由", "原文（摘要）", "建议修改"]
            for j, h in enumerate(headers):
                add_run_with_font(table.cell(0, j).paragraphs[0], h, bold=True, size=Pt(8), font_name="微软雅黑")
            for i, s in enumerate(group):
                row = table.rows[i + 1]
                add_run_with_font(row.cells[0].paragraphs[0], s.get("clause_id", ""), size=Pt(8), font_name="宋体")
                add_run_with_font(row.cells[1].paragraphs[0], (s.get("reason", "") or "")[:60], size=Pt(8), font_name="宋体")
                add_run_with_font(row.cells[2].paragraphs[0], (s.get("original_text", "") or "")[:60], size=Pt(7), font_name="宋体",
                                  color=RGBColor(0xCC, 0x00, 0x00))
                add_run_with_font(row.cells[3].paragraphs[0], (s.get("suggested_text", "") or "")[:60], size=Pt(7), font_name="宋体",
                                  color=RGBColor(0x00, 0x66, 0x00))
            set_table_style(table)
            self.doc.add_paragraph()

        self.doc.add_page_break()

    # ── 五、附录 ──────────────────────────────────────

    def build_appendix(self, risk_data: Dict, clauses_data: Dict):
        """构建附录：完整风险登记表。"""
        add_heading_styled(self.doc, "五、附录：完整风险登记表", level=1)

        raw = risk_data.get("findings", []) if risk_data else []
        if not raw:
            add_body_para(self.doc, "（无风险数据）")
            return

        # 获取条款标题映射
        clauses_map = {}
        if clauses_data:
            for c in clauses_data.get("clauses", []):
                clauses_map[c.get("id", "")] = c.get("title", "")

        # 展平
        flat = []
        for item in raw:
            if "findings" in item and isinstance(item["findings"], list):
                cid = item.get("clause_id", "")
                for sub in item["findings"]:
                    flat.append({
                        "clause_id": cid,
                        "risk_level": sub.get("risk_level", ""),
                        "risk_type": fmt_risk_type(sub.get("dimension", sub.get("risk_type", ""))),
                        "description": sub.get("dimension_name", sub.get("description", "")),
                    })
            else:
                flat.append({
                    "clause_id": item.get("clause_id", ""),
                    "risk_level": item.get("risk_level", ""),
                    "risk_type": fmt_risk_type(item.get("risk_type", "")),
                    "description": item.get("description", ""),
                })

        # 按风险等级排序
        risk_order = {"high": 0, "medium": 1, "low": 2, "none": 3}
        flat.sort(key=lambda f: risk_order.get(f.get("risk_level", "none"), 99))

        table = self.doc.add_table(rows=len(flat) + 1, cols=4)
        table.style = 'Table Grid'
        headers = ["条款", "风险等级", "风险类型", "风险描述"]
        for j, h in enumerate(headers):
            add_run_with_font(table.cell(0, j).paragraphs[0], h, bold=True, size=Pt(8), font_name="微软雅黑")
        for i, f in enumerate(flat):
            row = table.rows[i + 1]
            clause_title = clauses_map.get(f.get("clause_id", ""), "")
            clause_label = f"第{f['clause_id']}条 {clause_title}" if clause_title else f.get("clause_id", "")
            add_run_with_font(row.cells[0].paragraphs[0], clause_label, size=Pt(8), font_name="宋体")
            add_run_with_font(row.cells[1].paragraphs[0], fmt_risk(f.get("risk_level", "")), size=Pt(8),
                              color=fmt_risk_color(f.get("risk_level", "")))
            add_run_with_font(row.cells[2].paragraphs[0], f.get("risk_type", ""), size=Pt(8), font_name="宋体")
            add_run_with_font(row.cells[3].paragraphs[0], (f.get("description", "") or "")[:80], size=Pt(7), font_name="宋体")
        set_table_style(table)

        # 页脚
        self.doc.add_paragraph()
        p_footer = self.doc.add_paragraph()
        p_footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_run_with_font(p_footer,
                          "本报告由合同审核智能体自动生成，不构成正式法律意见。重大交易建议由执业律师复核。",
                          size=Pt(8), color=RGBColor(0x99, 0x99, 0x99), font_name="宋体")

    # ── 汇总生成 ──────────────────────────────────────

    def generate(self, output_path: str):
        """保存报告。"""
        self.doc.save(output_path)
        logger.info("DOCX 审查报告已保存: %s", output_path)


# ═══════════════════════════════════════════════════════════
# 原始合同批注版生成
# ═══════════════════════════════════════════════════════════

def generate_annotated_contract(
    original_docx: str,
    output_path: str,
    clauses_data: Dict,
    risk_data: Dict,
    comp_data: Dict,
    sugg_data: Dict,
):
    """生成原始合同的审阅批注版。"""
    try:
        from content_tracker import ContentTracker, map_clauses_to_paragraphs
    except ImportError:
        logger.warning("content_tracker 模块不可用，跳过批注版生成")
        return

    tracker = ContentTracker(original_docx)

    clauses = clauses_data.get("clauses", []) if clauses_data else []
    clause_para_map = map_clauses_to_paragraphs(original_docx, clauses)

    # 收集发现
    all_findings = []
    if risk_data:
        for item in risk_data.get("findings", []):
            if "findings" in item and isinstance(item["findings"], list):
                cid = item.get("clause_id", "")
                for sub in item["findings"]:
                    all_findings.append({
                        "clause_id": cid,
                        "risk_level": sub.get("risk_level", "medium"),
                        "description": sub.get("dimension_name", sub.get("description", "")),
                        "recommendation": sub.get("recommendation", ""),
                    })
            else:
                all_findings.append({
                    "clause_id": item.get("clause_id", ""),
                    "risk_level": item.get("risk_level", "medium"),
                    "description": item.get("description", ""),
                    "recommendation": item.get("recommendation", ""),
                })

    if comp_data:
        for f in comp_data.get("findings", []):
            all_findings.append({
                "clause_id": f.get("clause_id", ""),
                "risk_level": f.get("risk_level", "medium"),
                "regulation": f.get("regulation", ""),
                "description": f.get("issue", ""),
                "recommendation": f.get("recommendation", ""),
            })

    # 为每条发现添加批注
    para_indices_used = set()
    for finding in all_findings:
        cid = finding.get("clause_id", "")
        paras = clause_para_map.get(cid, [])
        if not paras:
            continue

        # 优先使用未标注的段落
        available = [p for p in paras if p not in para_indices_used]
        if not available:
            available = paras
        para_idx = available[0]
        para_indices_used.add(para_idx)

        summary = finding.get("description", "")
        tracker.add_review_comment(
            paragraph_index=para_idx,
            summary=summary,
            detail="",
            risk_level=finding.get("risk_level", "medium"),
            regulation=finding.get("regulation", ""),
            recommendation=finding.get("recommendation", ""),
        )

    # 添加修改建议
    if sugg_data:
        for s in sugg_data.get("suggestions", []):
            cid = s.get("clause_id", "")
            if cid == "new":
                continue
            paras = clause_para_map.get(cid, [])
            if not paras:
                continue
            para_idx = paras[0]
            tracker.add_suggestion(
                paragraph_index=para_idx,
                original_text=s.get("original_text", ""),
                suggested_text=s.get("suggested_text", ""),
                reason=s.get("reason", ""),
            )

    tracker.save_final(output_path)
    logger.info("批注版合同已保存: %s", output_path)


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="生成合同审查报告（DOCX + 批注版 + Markdown 三份文件）。")
    parser.add_argument("--clauses", required=True, help="extracted_clauses.json 路径")
    parser.add_argument("--risks", required=True, help="risk_register.json 路径")
    parser.add_argument("--compliance", help="compliance_report.json 路径")
    parser.add_argument("--suggestions", help="suggestions.json 路径")
    parser.add_argument("--output", required=True, help="输出的 DOCX 报告路径")
    parser.add_argument("--annotate", required=True, help="原始合同 DOCX 路径（如非 DOCX 则跳过批注版）")
    parser.add_argument("--md-output", help="Markdown 报告输出路径（默认与 DOCX 同目录）")
    args = parser.parse_args()

    # 加载数据
    clauses_data = load_json(args.clauses)
    risk_data = load_json(args.risks)
    comp_data = load_json(args.compliance)
    sugg_data = load_json(args.suggestions)

    if not clauses_data:
        logger.error("必须提供 clauses 数据，退出")
        return

    # ============================================================
    # 一、生成结构化 DOCX 报告（强制）
    # ============================================================
    gen = DocxReportGenerator()
    gen.build_cover(clauses_data, risk_data, comp_data)
    gen.build_executive_summary(risk_data, comp_data, sugg_data)
    gen.build_clause_review(clauses_data, risk_data, comp_data, sugg_data)
    gen.build_compliance(comp_data)
    gen.build_suggestions(sugg_data)
    gen.build_appendix(risk_data, clauses_data)
    gen.generate(args.output)
    logger.info("【文件1/3】DOCX 结构化报告: %s", args.output)

    # ============================================================
    # 二、生成原始合同批注版（强制，但仅限 DOCX 输入）
    # ============================================================
    orig_path = Path(args.annotate)
    if orig_path.exists() and orig_path.suffix.lower() == ".docx":
        annotate_output = str(Path(args.output).with_name(
            Path(args.output).stem + "（批注版）.docx"
        ))
        try:
            generate_annotated_contract(
                str(orig_path), annotate_output,
                clauses_data, risk_data, comp_data, sugg_data
            )
            logger.info("【文件2/3】批注版合同: %s", annotate_output)
        except Exception as e:
            logger.error("批注版生成失败: %s", e)
    else:
        logger.warning("【文件2/3】批注版跳过: 原始合同非 DOCX 格式（%s），无法添加批注",
                       orig_path.suffix if orig_path.exists() else "文件不存在")

    # ============================================================
    # 三、生成 Markdown 报告（强制）
    # ============================================================
    md_output = args.md_output or str(Path(args.output).with_suffix(".md"))
    try:
        from generate_report import generate_report as build_md_report
        md_text = build_md_report(clauses_data, risk_data, comp_data, sugg_data)
        Path(md_output).parent.mkdir(parents=True, exist_ok=True)
        Path(md_output).write_text(md_text, encoding="utf-8")
        logger.info("【文件3/3】Markdown 报告: %s", md_output)
    except ImportError:
        logger.warning("generate_report 模块不可用，跳过 MD 报告生成")
    except Exception as e:
        logger.error("Markdown 报告生成失败: %s", e)


if __name__ == "__main__":
    main()