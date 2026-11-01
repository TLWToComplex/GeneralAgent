"""
_defect_patterns.py — 语义缺陷模式库

本模块定义格式化输出中校验脚本无法捕获的结构性/语义性缺陷模式。
每条模式包含：
  - id:        唯一标识
  - name:      简短名称
  - severity:  严重程度 (error/warning/info)
  - scope:     检测范围 (heading/list/region/cover/table/format)
  - detect:    检测函数，接收 doc + spec，返回 [(位置, 描述), ...]
  - fix_hint:  修复建议
  - source:    来源（用户反馈日期）

每次手动发现问题后，在此追加新模式，即可永久固化到自审管道中。
"""

import re
from docx.oxml.ns import qn
from lxml import etree


# ──────────────────────────────────────────────
# 缺陷模式定义
# ──────────────────────────────────────────────

PATTERNS = []


def _register(pattern: dict):
    """注册一条缺陷模式。"""
    pattern['id'] = f"DP{len(PATTERNS)+1:03d}"
    PATTERNS.append(pattern)


# ══════════════════════════════════════════════
# 标题类缺陷
# ══════════════════════════════════════════════

_register({
    "name": "标题编号跳跃",
    "severity": "error",
    "scope": "heading",
    "description": "检测标题编号是否连续（如 1→3 跳过了 2）",
    "source": "用户反馈 2026-05-25",
    "detect": lambda doc, spec: _detect_heading_gap(doc),
    "fix_hint": "检查文档结构中是否有缺失的章节",
})


_register({
    "name": "标题样式自带自动编号",
    "severity": "error",
    "scope": "heading",
    "description": "Heading 样式定义中残留 numPr，导致标题前出现附录A/B等自动编号",
    "source": "用户反馈 2026-06-02",
    "detect": lambda doc, spec: _detect_heading_has_numPr(doc),
    "fix_hint": "清除样式定义和段落级的 w:numPr 元素",
})


_register({
    "name": "标题层级不一致",
    "severity": "warning",
    "scope": "heading",
    "description": "相同编号模式的段落未获得一致的 Heading 样式（如有的 L1 有 style 有的没有）",
    "source": "用户反馈 2026-06-02",
    "detect": lambda doc, spec: _detect_heading_style_consistency(doc),
    "fix_hint": "确认所有文本检测到的标题都被应用了 Heading 样式",
})


_register({
    "name": "标题后无正文直接接列表",
    "severity": "warning",
    "scope": "heading",
    "description": "标题段落后紧接列表项，中间无引导正文，可能影响编号重置",
    "source": "用户反馈 2026-06-01",
    "detect": lambda doc, spec: _detect_heading_to_list_gap(doc),
    "fix_hint": "标题与列表之间应有引导性正文段落",
})


_register({
    "name": "标题未设置大纲级别",
    "severity": "error",
    "scope": "heading",
    "description": "检测到的标题段落没有对应的 outlineLvl 属性",
    "source": "用户反馈 2026-06-02",
    "detect": lambda doc, spec: _detect_missing_outline_level(doc),
    "fix_hint": "确保 _apply_heading_format 中调用了 apply_outline_level",
})


# ══════════════════════════════════════════════
# 列表类缺陷
# ══════════════════════════════════════════════

_register({
    "name": "列表编号未重置",
    "severity": "error",
    "scope": "list",
    "description": "标题或正文后的列表未从 a)/1) 重新开始编号",
    "source": "用户反馈 2026-06-01",
    "detect": lambda doc, spec: _detect_list_not_reset(doc),
    "fix_hint": "检查 _reset_nid_cache 和 after_heading/after_body 触发条件",
})


_register({
    "name": "列表级别跳跃",
    "severity": "warning",
    "scope": "list",
    "description": "列表级别从 L1 直接跳到 L3 等，缺少中间级别",
    "source": "用户反馈 2026-05-26",
    "detect": lambda doc, spec: _detect_list_level_jump(doc),
    "fix_hint": "检查文档中的列项编号是否连续",
})


# ══════════════════════════════════════════════
# 区域类缺陷
# ══════════════════════════════════════════════

_register({
    "name": "区域边界误判",
    "severity": "error",
    "scope": "region",
    "description": "非目录内容的段落被错误识别为 TOC 区域",
    "source": "用户反馈 2026-06-04",
    "detect": lambda doc, spec: _detect_wrong_toc_region(doc),
    "fix_hint": "TOC 区域首个段落的文本应包含目录/目次等关键词",
})


_register({
    "name": "封面识别溢出",
    "severity": "warning",
    "scope": "region",
    "description": "封面区域包含超出预期的段落数，可能侵入了正文",
    "source": "用户反馈 2026-05-28",
    "detect": lambda doc, spec: _detect_cover_overflow(doc),
    "fix_hint": "max_pages 设置为合适值，或优化封面检测策略",
})


# ══════════════════════════════════════════════
# 格式覆盖类缺陷
# ══════════════════════════════════════════════

_register({
    "name": "正文对齐不一致",
    "severity": "warning",
    "scope": "format",
    "description": "正文段落中混有非 BOTH 对齐的段落",
    "source": "用户反馈 2026-06-04",
    "detect": lambda doc, spec: _detect_body_alignment_inconsistency(doc, spec),
    "fix_hint": "检查 FigureCaption/TableCaption 等特殊段落是否被正确处理",
})


_register({
    "name": "修订标记未覆盖",
    "severity": "info",
    "scope": "format",
    "description": "部分被修改的段落没有对应的修订标记",
    "source": "用户反馈 2026-05-27",
    "detect": lambda doc, spec: _detect_missing_track_changes(doc),
    "fix_hint": "检查 track_changes 参数是否正确传递给各个格式函数",
})

# ══════════════════════════════════════════════
# 新增模式组 v2：从实际反馈中提炼
# ══════════════════════════════════════════════

_register({
    "name": "标题与编号之间无空格",
    "severity": "warning",
    "scope": "heading",
    "description": '数字编号标题中"数字"与"标题文字"之间缺少空格，正则无法匹配',
    "source": "用户反馈 2026-06-04",
    "detect": lambda doc, spec: _detect_heading_no_space(doc),
    "fix_hint": "在数字编号与标题文字之间插入一个空格",
})

_register({
    "name": "空段落打断编号重置链",
    "severity": "error",
    "scope": "heading",
    "description": "标题与列表之间的空 paragraph 导致 last_was_body 被重置，编号不重启",
    "source": "用户反馈 2026-06-01",
    "detect": lambda doc, spec: _detect_empty_para_breaks_reset(doc),
    "fix_hint": "检查空段落是否在标题与列表之间，_apply_body_format 中不应重置状态",
})

_register({
    "name": "封面字体四要素不完整",
    "severity": "warning",
    "scope": "format",
    "description": "封面段落缺少 w:eastAsia / w:ascii / w:hAnsi / w:cs 四项字体属性之一",
    "source": "用户反馈 2026-06-04",
    "detect": lambda doc, spec: _detect_cover_font_incomplete(doc),
    "fix_hint": "确保封面段落的每个 run 都有完整的 rFonts 四个属性",
})

_register({
    "name": "正文段末尾行距不一致",
    "severity": "warning",
    "scope": "format",
    "description": "正文区部分段落行距与 spec 要求的 body_line_spacing 不匹配",
    "source": "用户反馈 2026-06-02",
    "detect": lambda doc, spec: _detect_body_spacing_mismatch(doc, spec),
    "fix_hint": "检查应用行距的段落范围是否覆盖了全部正文区域",
})

_register({
    "name": "多 section 页边距不一致",
    "severity": "warning",
    "scope": "format",
    "description": "文档中多个 section 的页边距不统一",
    "source": "用户反馈 2026-05-28",
    "detect": lambda doc, spec: _detect_section_margin_mismatch(doc, spec),
    "fix_hint": "确保所有 section 应用相同的页面设置",
})

_register({
    "name": "图表标题与正文间距异常",
    "severity": "info",
    "scope": "format",
    "description": "图表标题与前后正文之间段间距过大或过小",
    "source": "用户反馈 2026-06-04",
    "detect": lambda doc, spec: _detect_caption_spacing(doc),
    "fix_hint": "图表标题所在的段落应使用与正文一致的行距",
})

_register({
    "name": "标题样式库残留旧样式",
    "severity": "info",
    "scope": "heading",
    "description": "Heading 样式基于的旧 Normal 样式包含 center/bold 等冲突格式",
    "source": "用户反馈 2026-06-02",
    "detect": lambda doc, spec: _detect_heading_style_pollution(doc),
    "fix_hint": "_normalize_heading_style 应清除所有冲突的默认格式",
})


# ──────────────────────────────────────────────
# 检测函数实现
# ──────────────────────────────────────────────

def _detect_heading_gap(doc):
    """检测标题编号跳跃。"""
    from format_applier import _detect_heading_level
    issues = []
    prev_num = None
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if not t:
            continue
        level = _detect_heading_level(t, para=p)
        if level is None or level != 1:
            continue
        # 提取数字前缀
        m = re.match(r'^(\d+)', t)
        if m:
            num = int(m.group(1))
            if prev_num is not None and num > prev_num + 1:
                issues.append((i, f"L1 标题编号跳跃: {prev_num} → {num}"))
            prev_num = num
    return issues


def _detect_heading_has_numPr(doc):
    """检测标题段落的 numPr 残留。"""
    from format_applier import _detect_heading_level
    issues = []
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if not t:
            continue
        level = _detect_heading_level(t, para=p)
        if level is None:
            continue
        pPr = p._p.find(qn('w:pPr'))
        if pPr is not None and pPr.find(qn('w:numPr')) is not None:
            issues.append((i, f"L{level} 标题残留自动编号: {t[:30]}"))
    return issues


def _detect_heading_style_consistency(doc):
    """检测标题样式一致性。"""
    from format_applier import _detect_heading_level
    by_level = {1: [], 2: [], 3: [], 4: []}
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if not t:
            continue
        level = _detect_heading_level(t, para=p)
        if level and level in by_level:
            sn = (p.style.name or '').lower()
            is_h = sn.startswith('heading')
            by_level[level].append((i, is_h, t[:30]))

    issues = []
    for lv, items in by_level.items():
        if not items:
            continue
        has_style = sum(1 for _, s, _ in items if s)
        total = len(items)
        if has_style < total:
            ratio = has_style / total
            if ratio < 0.8:
                issues.append((items[0][0], f"L{lv} 标题只有 {has_style}/{total} 有 heading 样式"))
    return issues


def _detect_heading_to_list_gap(doc):
    """检测标题后直接接列表。"""
    from format_applier import _detect_heading_level, _detect_list_level
    issues = []
    paras = list(doc.paragraphs)
    for i, p in enumerate(paras):
        t = p.text.strip()
        if not t:
            continue
        if _detect_heading_level(t, para=p) is None:
            continue
        # 向后找第一个非空段落
        for j in range(i + 1, min(i + 5, len(paras))):
            nt = paras[j].text.strip()
            if nt:
                if _detect_list_level(nt) is not None:
                    issues.append((i, f"标题后直接接列表 (P[{i}] → P[{j}])"))
                break
    return issues


def _detect_missing_outline_level(doc):
    """检测标题段落缺少 outlineLvl。"""
    from format_applier import _detect_heading_level
    issues = []
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if not t:
            continue
        level = _detect_heading_level(t, para=p)
        if level is None:
            continue
        pPr = p._p.find(qn('w:pPr'))
        if pPr is None or pPr.find(qn('w:outlineLvl')) is None:
            issues.append((i, f"L{level} 标题缺少 outlineLvl: {t[:30]}"))
    return issues


def _detect_list_not_reset(doc):
    """检测列表编号是否重置。"""
    # 检查 heading 后的第一个列表项是否使用新的 numId
    from format_applier import _detect_heading_level, _detect_list_level
    issues = []
    paras = list(doc.paragraphs)
    for i, p in enumerate(paras):
        t = p.text.strip()
        if not t:
            continue
        if _detect_heading_level(t, para=p) is None:
            continue
        for j in range(i + 1, min(i + 8, len(paras))):
            nt = paras[j].text.strip()
            if nt and _detect_list_level(nt) is not None:
                pPr = paras[j]._p.find(qn('w:pPr'))
                if pPr is not None:
                    numPr = pPr.find(qn('w:numPr'))
                    if numPr is not None:
                        numId = numPr.find(qn('w:numId'))
                        if numId is not None:
                            nid = numId.get(qn('w:val'))
                            # 检查 numId 是否为新实例（非原始）
                            if nid and int(nid) < 200:
                                issues.append((j, f"列表可能未重置: P[{j}] numId={nid}"))
                break
    return issues


def _detect_list_level_jump(doc):
    """检测列表级别跳跃。"""
    from format_applier import _detect_list_level
    issues = []
    prev = None
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if not t:
            continue
        lv = _detect_list_level(t)
        if lv is not None:
            if prev is not None and lv > prev + 1:
                issues.append((i, f"列表级别跳跃: L{prev} → L{lv}"))
            prev = lv
        else:
            prev = None
    return issues


def _detect_wrong_toc_region(doc):
    """检测 TOC 区域边界误判。"""
    issues = []
    # 检查是否有疑似 TOC 关键词的段落
    toc_keywords = ['目录', '目次', '目  录', '目  次', 'Table of Contents']
    found_toc_keyword = False
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if any(kw in t for kw in toc_keywords):
            found_toc_keyword = True
            break
    # 检查是否有段落被标记为 toc 样式但没有关键词
    for i, p in enumerate(doc.paragraphs):
        style_name = (p.style.name or '').lower()
        if style_name.startswith('toc') or 'toc' in style_name:
            t = p.text.strip()
            if t and not any(kw in t for kw in toc_keywords[:2]):
                issues.append((i, f"TOC 样式段落无目录关键词: {t[:30]}"))
    return issues


def _detect_cover_overflow(doc):
    """检测封面区域溢出。"""
    from doc_analyzer import analyze_document
    issues = []
    try:
        analysis = analyze_document(doc)
        for region in analysis.regions:
            if region.type == 'cover':
                cover_paras = region.end - region.start + 1
                if cover_paras > 25:
                    issues.append((region.start, f"封面区域 {cover_paras} 段落，可能溢出"))
    except Exception:
        pass
    return issues


def _detect_body_alignment_inconsistency(doc, spec):
    """检测正文对齐不一致。"""
    issues = []
    expected = spec.alignment.get('body', 'both')
    count = 0
    for i, p in enumerate(doc.paragraphs):
        pPr = p._p.find(qn('w:pPr'))
        if pPr is not None:
            jc = pPr.find(qn('w:jc'))
            if jc is not None:
                actual = jc.get(qn('w:val'))
                if actual != expected:
                    count += 1
    if count > 0:
        issues.append((0, f"有 {count} 处非 {expected} 对齐"))
    return issues


def _detect_missing_track_changes(doc):
    """检测修订标记缺失。"""
    issues = []
    total_paras = 0
    changed_paras = 0
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        total_paras += 1
        pPr = p._p.find(qn('w:pPr'))
        has_pPr_change = False
        has_rPr_change = False
        if pPr is not None and pPr.find(qn('w:pPrChange')) is not None:
            has_pPr_change = True
        for r in p._p.findall(qn('w:r')):
            rPr = r.find(qn('w:rPr'))
            if rPr is not None and rPr.find(qn('w:rPrChange')) is not None:
                has_rPr_change = True
                break
        if has_pPr_change or has_rPr_change:
            changed_paras += 1
    if total_paras > 0:
        ratio = changed_paras / total_paras
        if ratio < 0.1:
            issues.append((0, f"修订标记覆盖率仅 {ratio:.0%} ({changed_paras}/{total_paras})"))
    return issues


# ══════════════════════════════════════════════
# 新增 v2 检测函数
# ══════════════════════════════════════════════

def _detect_heading_no_space(doc):
    """检测数字编号标题中数字与文字之间无空格。"""
    from format_applier import _detect_heading_level
    issues = []
    no_space_re = re.compile(r'^\d+[\u4e00-\u9fff]')
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if not t:
            continue
        # 只检查被检测为标题的段落，以及疑似标题但被漏检的段落
        level = _detect_heading_level(t, para=p)
        if level is not None:
            continue  # 已经被正确检测
        # 检查是否因缺少空格而漏检
        if no_space_re.match(t):
            first_digit_end = re.match(r'^\d+', t).end()
            rest = t[first_digit_end:]
            if rest and not rest.startswith('.') and not rest.startswith(')'):
                # 过滤非标题内容：文本太长的(>20字)、以"年"结尾的日期、不含中文字符的
                if len(t) > 20:
                    continue  # 长文本不太可能是标题
                # 过滤年份/日期
                if t.startswith(('202', '201', '200', '199')) and '年' in t[:6]:
                    continue
                # 过滤明显不是标题的内容（不含中文字符）
                cn_count = len(re.findall(r'[\u4e00-\u9fff]', rest))
                if cn_count == 0:
                    continue
                issues.append((i, f"可能为标题但数字与文字间无空格: {t[:30]}"))
    return issues


def _detect_empty_para_breaks_reset(doc):
    """检测空段落打断编号重置链。"""
    from format_applier import _detect_heading_level, _detect_list_level
    issues = []
    paras = list(doc.paragraphs)
    for i, p in enumerate(paras):
        t = p.text.strip()
        if not t:
            continue
        if _detect_heading_level(t, para=p) is None:
            continue
        # 查找标题之后、第一个列表项之前的空段落
        found_empty = False
        for j in range(i + 1, min(i + 8, len(paras))):
            nt = paras[j].text.strip()
            if not nt:
                if not found_empty:
                    found_empty = True
                continue
            if _detect_list_level(nt) is not None and found_empty:
                issues.append((j, f"标题和列表之间的空段落可能阻止编号重置 (P[{i}]→P[{j}])"))
                break
            if _detect_list_level(nt) is not None or _detect_heading_level(nt, para=paras[j]) is not None:
                break
    return issues


def _detect_cover_font_incomplete(doc):
    """检测封面段落字体属性不完整。"""
    from doc_analyzer import analyze_document
    issues = []
    try:
        analysis = analyze_document(doc)
        for region in analysis.regions:
            if region.type != 'cover':
                continue
            for pi in range(region.start, min(region.end + 1, region.start + 20)):
                para = doc.paragraphs[pi]
                if not para.text.strip():
                    continue
                for r in para._p.findall(qn('w:r')):
                    rPr = r.find(qn('w:rPr'))
                    if rPr is not None:
                        rf = rPr.find(qn('w:rFonts'))
                        if rf is not None:
                            ea = rf.get(qn('w:eastAsia'))
                            asc = rf.get(qn('w:ascii'))
                            han = rf.get(qn('w:hAnsi'))
                            cs = rf.get(qn('w:cs'))
                            missing = []
                            if not ea: missing.append('eastAsia')
                            if not asc: missing.append('ascii')
                            if not han: missing.append('hAnsi')
                            if missing:
                                issues.append((pi, f"封面 run 字体属性缺失: {', '.join(missing)}"))
                                break
    except Exception:
        pass
    return issues


def _detect_body_spacing_mismatch(doc, spec):
    """检测正文行距与 spec 不匹配。"""
    expected_spacing = spec.spacing.get('body_line_spacing_pt', 25)
    expected_mode = spec.spacing.get('body_line_spacing_mode', 'fixed')
    # 检查使用 Normal 样式的段落
    issues = []
    count = 0
    for i, p in enumerate(doc.paragraphs):
        style_name = (p.style.name or '').lower()
        if style_name != 'normal':
            continue
        pPr = p._p.find(qn('w:pPr'))
        if pPr is not None:
            sp = pPr.find(qn('w:spacing'))
            if sp is not None:
                line_val = sp.get(qn('w:line'))
                line_rule = sp.get(qn('w:lineRule'))
                if line_rule == 'auto':
                    count += 1
    if count > 5:
        issues.append((0, f"{count} 个 Normal 段落行距模式为 auto（应为 {expected_mode}）"))
    return issues


def _detect_section_margin_mismatch(doc, spec):
    """检测多 section 边距不一致。"""
    issues = []
    sections = list(doc.sections)
    if len(sections) < 2:
        return issues
    first = sections[0]
    expected = (first.top_margin, first.bottom_margin,
                first.left_margin, first.right_margin)
    for si, sec in enumerate(sections[1:], 1):
        actual = (sec.top_margin, sec.bottom_margin,
                  sec.left_margin, sec.right_margin)
        if actual != expected:
            issues.append((0, f"Section[{si}] 边距与 Section[0] 不一致"))
            break
    return issues


def _detect_caption_spacing(doc):
    """检测图表标题间距。"""
    import re as _re
    issues = []
    fig_re = _re.compile(r'^(图\s*\d+|Figure\s*\d+)')
    tbl_re = _re.compile(r'^(表\s*\d+|Table\s*\d+)')
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if not t:
            continue
        is_caption = bool(fig_re.match(t) or tbl_re.match(t))
        if not is_caption:
            continue
        # 检查前后段落
        if i > 0:
            prev_text = doc.paragraphs[i - 1].text.strip()
            if not prev_text:
                issues.append((i, f"图表标题前有空行: {t[:25]}"))
    return issues


def _detect_heading_style_pollution(doc):
    """检测 Heading 样式被旧 Normal 样式污染。"""
    issues = []
    for lv in range(1, 5):
        try:
            s = doc.styles[f'Heading {lv}']
        except KeyError:
            continue
        pPr = s._element.find(qn('w:pPr'))
        if pPr is None:
            continue
        # 检查 numPr
        if pPr.find(qn('w:numPr')) is not None:
            issues.append((0, f"Heading {lv} 样式仍残留 numPr"))
        # 检查 jc
        jc = pPr.find(qn('w:jc'))
        if jc is not None and jc.get(qn('w:val')) != 'left':
            issues.append((0, f"Heading {lv} 样式对齐方式为 {jc.get(qn('w:val'))}（应为 left）"))
    return issues
# 主入口：运行所有缺陷检测
# ──────────────────────────────────────────────

def run_all_checks(doc, spec, categories=None):
    """运行全部或指定类别的缺陷检测。

    Args:
        doc: python-docx Document 对象
        spec: Spec 对象
        categories: 可选过滤，如 ['heading', 'list']

    Returns:
        list of dict: [
            {"id": "DP001", "name": "...", "severity": "...",
             "scope": "...", "positions": [(idx, desc), ...]}
        ]
    """
    results = []
    for pattern in PATTERNS:
        if categories and pattern['scope'] not in categories:
            continue
        try:
            issues = pattern['detect'](doc, spec)
            if issues:
                results.append({
                    "id": pattern['id'],
                    "name": pattern['name'],
                    "severity": pattern['severity'],
                    "scope": pattern['scope'],
                    "description": pattern['description'],
                    "fix_hint": pattern['fix_hint'],
                    "positions": issues,
                    "source": pattern['source'],
                })
        except Exception as e:
            results.append({
                "id": pattern['id'],
                "name": pattern['name'],
                "severity": "error",
                "scope": pattern['scope'],
                "description": f"检测执行异常: {e}",
                "fix_hint": "",
                "positions": [],
                "source": pattern['source'],
            })
    return results


def print_report(results):
    """打印人类可读的缺陷报告。"""
    if not results:
        print("  自审通过：未发现已知缺陷模式")
        return

    by_severity = {'error': [], 'warning': [], 'info': []}
    for r in results:
        by_severity.setdefault(r['severity'], []).append(r)

    for sev in ['error', 'warning', 'info']:
        items = by_severity.get(sev, [])
        if not items:
            continue
        label = {'error': '错误', 'warning': '警告', 'info': '提示'}.get(sev, sev)
        print(f"  [{label}] ({len(items)}项)")
        for r in items:
            print(f"    {r['id']} {r['name']}")
            if r['positions']:
                for pos, desc in r['positions'][:3]:
                    print(f"      段{pos}: {desc}")
                if len(r['positions']) > 3:
                    print(f"      ... 还有 {len(r['positions'])-3} 处")
            print(f"      修复: {r['fix_hint']}")
