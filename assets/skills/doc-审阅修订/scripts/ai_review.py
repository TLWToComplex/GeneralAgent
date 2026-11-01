"""
ai_review.py — AI 文档评审数据提取器

将格式化后的文档提取为结构化评审数据，
供 LLM 进行语义级评审。
"""
import re
from docx import Document
from docx.oxml.ns import qn


def extract_for_review(doc_or_path):
    """提取文档结构化数据，供 AI 评审。

    Returns:
        dict: 包含标题、列表、区域、表格、修订等信息的结构化数据
    """
    if isinstance(doc_or_path, str):
        doc = Document(doc_or_path)
    else:
        doc = doc_or_path

    try:
        from format_applier import _detect_heading_level, _detect_list_level
    except ImportError:
        h1 = re.compile(r'^\d+\s+\S')
        h2 = re.compile(r'^\d+\.\d+\s+\S')
        def _detect_heading_level(t, para=None):
            if h1.match(t) and '.' not in t.split()[0] and ')' not in t.split()[0]:
                return 1
            if h2.match(t): return 2
            return None
        _detect_list_level = lambda t, s=None: None

    review = {
        "标题": [],
        "列表": [],
        "区域": {},
        "段落总数": len(doc.paragraphs),
        "表格数": len(doc.tables),
        "Section数": len(list(doc.sections)),
        "修订覆盖": {},
    }

    # 标题结构
    prev_level = None
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if not t:
            continue
        lv = _detect_heading_level(t, para=p)
        if lv:
            style = p.style.name if p.style else ''
            review["标题"].append({
                "索引": i, "级别": lv, "文本": t[:60],
                "样式": style, "大纲": str(p.paragraph_format.outline_level) if hasattr(p.paragraph_format, 'outline_level') else ''
            })

    # 列表结构
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if not t:
            continue
        lv = _detect_list_level(t)
        if lv:
            pPr = p._p.find(qn('w:pPr'))
            num_str = ''
            if pPr is not None:
                numPr = pPr.find(qn('w:numPr'))
                if numPr is not None:
                    nid = numPr.find(qn('w:numId'))
                    if nid is not None:
                        num_str = f"numId={nid.get(qn('w:val'))}"
            review["列表"].append({
                "索引": i, "级别": lv, "文本": t[:40],
                "编号": num_str
            })

    # 修订标记统计
    ppr = 0; rpr = 0
    for p in doc.paragraphs:
        pp = p._p.find(qn('w:pPr'))
        if pp is not None and pp.find(qn('w:pPrChange')) is not None: ppr += 1
        for r in p._p.findall(qn('w:r')):
            rp = r.find(qn('w:rPr'))
            if rp is not None and rp.find(qn('w:rPrChange')) is not None: rpr += 1; break
    review["修订覆盖"] = {"段落级": ppr, "run级": rpr}

    # Section 边距
    margins = []
    for si, sec in enumerate(doc.sections):
        margins.append({
            "section": si,
            "上": f"{sec.top_margin.cm:.2f}cm",
            "下": f"{sec.bottom_margin.cm:.2f}cm",
            "左": f"{sec.left_margin.cm:.2f}cm",
            "右": f"{sec.right_margin.cm:.2f}cm",
        })
    review["页面边距"] = margins

    return review


def build_review_prompt(review_data: dict, spec_name: str = "") -> str:
    """从提取的结构化数据构建 AI 评审 Prompt。"""
    lines = []
    lines.append("## 文档结构化数据（用于 AI 格式评审）")
    lines.append("")
    if spec_name:
        lines.append(f"**规范**: {spec_name}")
    lines.append(f"**段落总数**: {review_data['段落总数']}")
    lines.append(f"**表格数**: {review_data['表格数']}")
    lines.append(f"**Section数**: {review_data['Section数']}")
    lines.append(f"**修订覆盖**: 段落级{review_data['修订覆盖']['段落级']}, run级{review_data['修订覆盖']['run级']}")
    lines.append("")

    # 标题
    lines.append("### 标题结构（索引 / 级别 / 文本 / 样式 / 大纲）")
    lines.append("")
    for h in review_data["标题"]:
        lines.append(f"- P[{h['索引']}] L{h['级别']} [{h['样式']}] ol={h['大纲']} {h['文本']}")
    lines.append("")

    # 列表
    if review_data["列表"]:
        lines.append("### 列表项")
        lines.append("")
        for li in review_data["列表"]:
            lines.append(f"- P[{li['索引']}] L{li['级别']} {li['编号']} {li['文本']}")
        lines.append("")

    # 边距
    if review_data.get("页面边距"):
        lines.append("### 页面边距")
        lines.append("")
        for m in review_data["页面边距"]:
            lines.append(f"- Section[{m['section']}]: 上{m['上']} 下{m['下']} 左{m['左']} 右{m['右']}")
        lines.append("")

    # 评审要求
    lines.append("### 评审要求")
    lines.append("")
    lines.append("基于以上结构化数据，逐项评审：")
    lines.append("")
    lines.append("1. **标题检测完整性**：所有应被识别的标题都被识别了吗？有无遗漏或误判？")
    lines.append("")
    lines.append("2. **标题层级正确性**：层级关系与文档结构一致吗？有无跳级？")
    lines.append("")
    lines.append("3. **列表编号连续性**：每级列表的编号是否连续（a)b)c) / 1)2)3)）？有无跳号？")
    lines.append("")
    lines.append("4. **区域划分**：如果知道原始文档的封面/目录/正文边界，判断区域划分是否准确。")
    lines.append("")
    lines.append("5. **修订覆盖合理性**：段落级修订数是否合理？有没有段落应有修订但没有？")
    lines.append("")
    lines.append("6. **异常段落**：有没有段落格式明显与同类段落不一致？")
    lines.append("")
    lines.append("### 输出格式")
    lines.append("")
    lines.append("对每一项评审，输出：")
    lines.append("- **发现的问题**（如有）")
    lines.append("- **严重程度**（错误/警告/提示）")
    lines.append("- **涉及的段落索引**")
    lines.append("- **修复建议**")
    lines.append('- **如无问题，标注"通过"**')

    return '\n'.join(lines)
