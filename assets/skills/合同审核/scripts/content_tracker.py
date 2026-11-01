#!/usr/bin/env python3
"""
内容级审阅追踪模块 — 对原始合同 DOCX 进行批注、高亮、修订建议标记。

用法：
    from content_tracker import ContentTracker

    tracker = ContentTracker("原始合同.docx")
    tracker.add_review_comment(para_index=5, text="此条款违约金过高...", risk_level="high")
    tracker.add_suggestion(para_index=8, original="甲方不承担任何责任",
                           suggested="甲方仅在故意或重大过失时承担相应责任")
    tracker.save("合同审核（批注版）.docx")
"""

from __future__ import annotations

import copy
import io
import logging
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lxml import etree
from docx import Document
from docx.oxml.ns import qn, nsmap
from docx.shared import RGBColor, Pt, Inches, Cm
from docx.enum.text import WD_COLOR_INDEX

logger = logging.getLogger(__name__)

# OOXML 命名空间
NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"

# 风险等级 → 高亮颜色映射
RISK_HIGHLIGHT = {
    "high":   WD_COLOR_INDEX.RED,
    "medium": WD_COLOR_INDEX.YELLOW,
    "low":    WD_COLOR_INDEX.BRIGHT_GREEN,
    "none":   None,
}

RISK_COLORS = {
    "high":   RGBColor(0xCC, 0x00, 0x00),
    "medium": RGBColor(0xCC, 0x88, 0x00),
    "low":    RGBColor(0x00, 0x88, 0x00),
    "none":   RGBColor(0x66, 0x66, 0x66),
}


class ContentTracker:
    """对 DOCX 文档进行内容级审阅标注（Word 批注 + 高亮 + 建议修订）。"""

    def __init__(self, docx_path: str, author: str = "合同审核智能体"):
        self.docx_path = Path(docx_path)
        self.author = author
        self.doc = Document(str(docx_path))
        self.comment_id = 0
        self._comments_etree: Optional[etree._Element] = None
        self._setup()

    # ── 初始化 ──────────────────────────────────────────────

    def _setup(self):
        """加载或创建 comments.xml 部分。"""
        # python-docx 不直接暴露 comments part，需要通过底层 XML 操作
        doc_part = self.doc.part
        try:
            comments_part = doc_part.part_related_by(RT.COMMENTS)
        except (KeyError, AttributeError):
            comments_part = None

        if comments_part is None:
            # 新建 comments.xml
            self._comments_etree = etree.fromstring(
                f'<w:comments xmlns:w="{NS_W}"></w:comments>'
            )
        else:
            self._comments_etree = etree.fromstring(comments_part.blob)

    # ── 公有 API ────────────────────────────────────────────

    def add_review_comment(
        self,
        paragraph_index: int,
        summary: str,
        detail: str = "",
        risk_level: str = "medium",
        regulation: str = "",
        recommendation: str = "",
    ) -> int:
        """
        在指定段落上添加 Word 审阅批注。

        返回 comment_id（可用于后续引用）。
        """
        if paragraph_index < 0 or paragraph_index >= len(self.doc.paragraphs):
            logger.warning("段落索引 %d 超出范围（共 %d 段），跳过", paragraph_index, len(self.doc.paragraphs))
            return -1

        para = self.doc.paragraphs[paragraph_index]
        cid = self.comment_id
        self.comment_id += 1

        # 构建批注文本
        lines = [f"【{risk_level.upper()}】{summary}"]
        if regulation:
            lines.append(f"法规出处：{regulation}")
        if detail:
            lines.append(f"详细说明：{detail}")
        if recommendation:
            lines.append(f"修改建议：{recommendation}")

        self._insert_comment_xml(para, cid, "\n".join(lines))
        self._highlight_paragraph(para, risk_level)

        logger.debug("已添加批注 #%d 到段落 %d", cid, paragraph_index)
        return cid

    def add_suggestion(
        self,
        paragraph_index: int,
        original_text: str,
        suggested_text: str,
        reason: str = "",
    ):
        """
        在指定段落中标记文本修订建议（原文删除线 + 建议文蓝色插入）。

        如果能在段落中找到 original_text，则在原位标记删除+插入；
        否则在段落末尾追加修订标注。
        """
        if paragraph_index < 0 or paragraph_index >= len(self.doc.paragraphs):
            return

        para = self.doc.paragraphs[paragraph_index]

        # 尝试定位原文
        found = self._replace_text_in_para(para, original_text, suggested_text)
        if not found:
            # 在段落末尾追加修订标注
            self._append_revision_to_para(para, original_text, suggested_text, reason)

    def add_clause_header(self, paragraph_index: int, clause_title: str):
        """在段落前插入条款标题书签，便于导航。"""
        if paragraph_index < 0 or paragraph_index >= len(self.doc.paragraphs):
            return
        para = self.doc.paragraphs[paragraph_index]
        # 插入书签标记
        bookmark_id = paragraph_index
        self._insert_bookmark(para, f"clause_{bookmark_id}", clause_title)

    def save(self, output_path: str):
        """保存带全部审阅标记的文档。"""
        output = Path(output_path)

        # 1. 写入 comments.xml
        self._save_comments_part()

        # 2. 用 python-docx 保存（会保留所有 run/paragraph 级别的修改）
        self.doc.save(str(output))
        logger.info("审阅标注文档已保存: %s", output)

    # ── 内部: Word 批注 XML 操作 ─────────────────────────────

    def _insert_comment_xml(self, para, comment_id: int, text: str):
        """在段落中插入 commentRangeStart/End 和 commentReference。"""
        para_elem = para._element

        # 创建 commentRangeStart
        start = etree.SubElement(para_elem, qn("w:commentRangeStart"))
        start.set(qn("w:id"), str(comment_id))

        # 在段落末尾添加 commentRangeEnd + commentReference
        end = etree.Element(qn("w:commentRangeEnd"))
        end.set(qn("w:id"), str(comment_id))
        para_elem.append(end)

        # commentReference run
        r = etree.SubElement(para_elem, qn("w:r"))
        rpr = etree.SubElement(r, qn("w:rPr"))
        rstyle = etree.SubElement(rpr, qn("w:rStyle"))
        rstyle.set(qn("w:val"), "CommentReference")
        ref = etree.SubElement(r, qn("w:commentReference"))
        ref.set(qn("w:id"), str(comment_id))

        # 构建 comment 元素
        comment = etree.SubElement(self._comments_etree, qn("w:comment"))
        comment.set(qn("w:id"), str(comment_id))
        comment.set(qn("w:author"), self.author)
        comment.set(qn("w:date"), self._now_iso())

        # comment 内的段落
        cp = etree.SubElement(comment, qn("w:p"))
        cpr = etree.SubElement(cp, qn("w:r"))
        # 字体
        cprPr = etree.SubElement(cpr, qn("w:rPr"))
        cFont = etree.SubElement(cprPr, qn("w:rFonts"))
        cFont.set(qn("w:eastAsia"), "微软雅黑")
        sz = etree.SubElement(cprPr, qn("w:sz"))
        sz.set(qn("w:val"), "20")
        ct = etree.SubElement(cpr, qn("w:t"))
        ct.text = text
        ct.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

    def _save_comments_part(self):
        """将 comments XML 序列化并存入 docx package。"""
        doc_part = self.doc.part
        package = doc_part.package

        # 序列化 comments XML
        comments_xml = etree.tostring(
            self._comments_etree, xml_declaration=True, encoding="UTF-8", standalone=True
        )

        # 通过 package 的底层 zip 写入（python-docx 的 part 机制比较受限）
        # 重新保存时写入 comments
        # 这里使用后处理方式：先保存，再打开 zip 注入 comments
        self._pending_comments_xml = comments_xml

    def _inject_comments_into_zip(self, output_path: str):
        """在已保存的 docx zip 中注入 comments.xml 和相关关系。"""
        # 读取刚保存的文件
        with zipfile.ZipFile(output_path, "r") as zin:
            all_files = zin.namelist()
            files = {name: zin.read(name) for name in all_files}

        # 添加/替换 comments.xml
        files["word/comments.xml"] = self._pending_comments_xml

        # 更新 [Content_Types].xml
        ct_xml = files["[Content_Types].xml"]
        ct_root = etree.fromstring(ct_xml)
        ns_ct = NS_CT
        # 检查是否已有 comments 类型
        existing = ct_root.findall(f'{{http://schemas.openxmlformats.org/package/2006/content-types}}Override[@PartName="/word/comments.xml"]')
        if not existing:
            override = etree.SubElement(ct_root, f"{{{ns_ct}}}Override")
            override.set("PartName", "/word/comments.xml")
            override.set("ContentType",
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml")
            files["[Content_Types].xml"] = etree.tostring(ct_root, xml_declaration=True, encoding="UTF-8", standalone=True)

        # 更新 word/_rels/document.xml.rels 添加 comments 关系
        rels_path = "word/_rels/document.xml.rels"
        if rels_path in files:
            rels_xml = files[rels_path]
            rels_root = etree.fromstring(rels_xml)
            existing_rel = rels_root.findall(f'{{http://schemas.openxmlformats.org/package/2006/relationships}}Relationship[@Target="comments.xml"]')
            if not existing_rel:
                rel = etree.SubElement(rels_root,
                    f"{{{NS_R}}}Relationship")
                rel.set("Id", f"rId_comments_{self.comment_id}")
                rel.set("Type",
                        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments")
                rel.set("Target", "comments.xml")
                files[rels_path] = etree.tostring(rels_root, xml_declaration=True, encoding="UTF-8", standalone=True)

        # 重新写入 zip
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for name, data in files.items():
                zout.writestr(name, data)

    # ── 内部: 段落高亮 ─────────────────────────────────────

    def _highlight_paragraph(self, para, risk_level: str):
        """按风险等级高亮段落文字。"""
        color = RISK_HIGHLIGHT.get(risk_level)
        if color is None:
            return
        for run in para.runs:
            run.font.highlight_color = color

    # ── 内部: 文本替换 ─────────────────────────────────────

    def _replace_text_in_para(self, para, original: str, suggested: str) -> bool:
        """在段落中查找 original 文本并替换为建议文本（加删除线+蓝色插入）。"""
        full_text = para.text
        if original not in full_text:
            return False

        # 清除原段落所有 run，重建
        # 找到 original 在全文中的位置
        idx = full_text.find(original)
        before = full_text[:idx]
        after = full_text[idx + len(original):]

        # 清空段落（必须转为 list 避免迭代中修改导致的跳过）
        for run in list(para.runs):
            run._element.getparent().remove(run._element)

        # 重建: before + 删除线原文 + 建议插入
        if before:
            r = para.add_run(before)

        # 删除线原文
        r_del = para.add_run(original)
        r_del.font.strike = True
        r_del.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)

        # 建议文本
        if suggested:
            r_ins = para.add_run(f" → {suggested}")
            r_ins.font.color.rgb = RGBColor(0x00, 0x66, 0xCC)
            r_ins.font.bold = True

        if after:
            para.add_run(after)

        return True

    def _append_revision_to_para(self, para, original: str, suggested: str, reason: str):
        """在段落末尾追加修订标注块。"""
        r_sep = para.add_run("\n【审阅建议】")
        r_sep.font.size = Pt(9)
        r_sep.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

        if reason:
            r_reason = para.add_run(f"\n原因：{reason}")
            r_reason.font.size = Pt(9)
            r_reason.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

        r_orig = para.add_run(f"\n原文：{original}")
        r_orig.font.size = Pt(9)
        r_orig.font.strike = True
        r_orig.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)

        r_sugg = para.add_run(f"\n建议：{suggested}")
        r_sugg.font.size = Pt(9)
        r_sugg.font.color.rgb = RGBColor(0x00, 0x66, 0xCC)
        r_sugg.font.bold = True

    # ── 内部: 书签 ────────────────────────────────────────

    def _insert_bookmark(self, para, bookmark_name: str, text: str):
        """在段落中插入书签。"""
        para_elem = para._element
        start = etree.Element(qn("w:bookmarkStart"))
        start.set(qn("w:id"), str(hash(bookmark_name) % 100000))
        start.set(qn("w:name"), bookmark_name)
        para_elem.insert(0, start)
        end = etree.Element(qn("w:bookmarkEnd"))
        end.set(qn("w:id"), str(hash(bookmark_name) % 100000))
        para_elem.append(end)

    # ── 工具 ──────────────────────────────────────────────

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def save_final(self, output_path: str):
        """完整保存流程：先保存 docx，再注入 comments。"""
        self.save(output_path)
        if self._comments_etree is not None and len(self._comments_etree):
            self._inject_comments_into_zip(output_path)


class RT:
    """关系类型常量。"""
    COMMENTS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"


# ============================================================
# 便捷函数：从 clause 文本匹配段落
# ============================================================

def find_paragraphs_by_clause(doc: Document, clause_text: str) -> List[int]:
    """
    根据条款文本在文档中查找匹配的段落索引。

    匹配策略：
    1. 精确匹配（条款文本完全包含段落文本）
    2. 前缀匹配（条款文本前 50 字匹配）
    3. 关键字匹配（条款标题中的数字/关键字匹配）
    """
    matches = []
    clause_clean = clause_text.strip().replace("\n", "").replace(" ", "")

    for i, para in enumerate(doc.paragraphs):
        para_text = para.text.strip().replace("\n", "").replace(" ", "")
        if not para_text:
            continue

        # 策略1: 精确子串
        if len(clause_clean) > 10 and clause_clean[:60] in para_text:
            matches.append(i)
            continue

        # 策略2: 前50字匹配
        if len(clause_clean) > 20 and para_text[:50] in clause_clean:
            matches.append(i)
            continue

    return matches


def map_clauses_to_paragraphs(
    docx_path: str,
    clauses: List[Dict],
) -> Dict[str, List[int]]:
    """
    建立 clause_id → 段落索引列表 的映射。

    Args:
        docx_path: 原始合同 DOCX 路径
        clauses: extracted_clauses.json 中的 clauses 列表

    Returns:
        {"1": [3, 4], "2": [7, 8, 9], ...}
    """
    doc = Document(docx_path)
    mapping = {}
    for clause in clauses:
        cid = clause.get("id", "")
        title = clause.get("title", "")
        text = clause.get("text", "")

        # 先用标题匹配
        paras = find_paragraphs_by_clause(doc, title)
        if not paras:
            # 再用正文前100字匹配
            paras = find_paragraphs_by_clause(doc, text[:100])

        if paras:
            mapping[cid] = paras

    logger.info("条款→段落映射：%d/%d 条匹配成功",
                len(mapping), len(clauses))
    return mapping