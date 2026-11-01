"""
auto_fix.py — 自审缺陷自动修复器

当自审发现可修复的缺陷模式时，自动执行修复操作。
无需人工介入的修复项在 format 管道中静默执行。
"""
import re
from docx.oxml.ns import qn
from lxml import etree

from utils import log
from font_manager import clear_paragraph_indent, apply_line_spacing


# ──────────────────────────────────────────────
# 修复器注册表：模式 ID → 修复函数
# ──────────────────────────────────────────────

_FIXERS = {}


def _register_fixer(pattern_id: str, func):
    """注册一个修复器。"""
    _FIXERS[pattern_id] = func


def get_fixer(pattern_id: str):
    """获取修复器函数。"""
    return _FIXERS.get(pattern_id)


# ══════════════════════════════════════════════
# 修复函数
# ══════════════════════════════════════════════

def _fix_heading_numPr(doc, defect):
    """DP002: 清除标题段落残留的自动编号。"""
    fixes = []
    for pos, desc in defect.get('positions', []):
        try:
            p = doc.paragraphs[pos]
            pPr = p._p.find(qn('w:pPr'))
            if pPr is not None:
                numPr = pPr.find(qn('w:numPr'))
                if numPr is not None:
                    pPr.remove(numPr)
                    fixes.append(pos)
        except Exception:
            pass
    return fixes


def _fix_heading_no_space(doc, defect):
    """DP012: 在数字与文字之间插入空格。"""
    fixes = []
    for pos, desc in defect.get('positions', []):
        try:
            p = doc.paragraphs[pos]
            text = p.text
            # 在第一个数字和文字之间插入空格
            m = re.match(r'^(\d+)(\S)', text)
            if m and m.group(2) and not m.group(2).isspace():
                # 修改第一个 run 的文本
                for r in p._p.findall(qn('w:r')):
                    for t in r.findall(qn('w:t')):
                        old_text = t.text or ''
                        if old_text.strip():
                            m2 = re.match(r'^(\d+)(\S.*)', old_text)
                            if m2:
                                t.text = m2.group(1) + ' ' + m2.group(2)
                                fixes.append(pos)
                                break
                    if pos in fixes:
                        break
        except Exception:
            pass
    return fixes


def _fix_body_spacing(doc, defect, spec):
    """DP015: 修复 Normal 段落行距为 spec 要求值。"""
    fixes = []
    expected_spacing = spec.spacing.get('body_line_spacing_pt', 25)
    expected_mode = spec.spacing.get('body_line_spacing_mode', 'fixed')

    for i, p in enumerate(doc.paragraphs):
        style_name = (p.style.name or '').lower()
        if style_name != 'normal':
            continue
        pf = p.paragraph_format
        if pf.line_spacing_rule is None or str(pf.line_spacing_rule) != 'EXACTLY':
            try:
                apply_line_spacing(p, expected_spacing, expected_mode)
                fixes.append(i)
            except Exception:
                pass
    return fixes


def _fix_heading_style_pollution(doc, defect):
    """DP018: 重新规范化 Heading 样式。"""
    fixes = []
    for lv in range(1, 5):
        try:
            s = doc.styles[f'Heading {lv}']
        except KeyError:
            continue
        pPr = s._element.find(qn('w:pPr'))
        if pPr is None:
            continue
        # 清除 numPr
        numPr = pPr.find(qn('w:numPr'))
        if numPr is not None:
            pPr.remove(numPr)
            fixes.append(0)
        # 设置左对齐
        jc = pPr.find(qn('w:jc'))
        if jc is not None and jc.get(qn('w:val')) != 'left':
            jc.set(qn('w:val'), 'left')
            if 0 not in fixes:
                fixes.append(0)
        # 清除 spacing
        spacing = pPr.find(qn('w:spacing'))
        if spacing is not None:
            pPr.remove(spacing)
            if 0 not in fixes:
                fixes.append(0)
    return fixes


# ──────────────────────────────────────────────
# 注册可自动修复的模式
# ──────────────────────────────────────────────

_register_fixer('DP002', _fix_heading_numPr)
_register_fixer('DP012', _fix_heading_no_space)
_register_fixer('DP015', _fix_body_spacing)
_register_fixer('DP018', _fix_heading_style_pollution)


# ──────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────

def auto_fix(doc, spec, defect_results):
    """对自审发现的可修复缺陷执行自动修复。

    Args:
        doc: python-docx Document 对象
        spec: Spec 对象
        defect_results: run_all_checks 的返回结果

    Returns:
        list of dict: [{"id": "DP002", "fixes": [3, 7, ...]}, ...]
    """
    repair_log = []

    for defect in defect_results:
        pid = defect['id']
        fixer = get_fixer(pid)
        if fixer is None:
            continue  # 该模式无自动修复

        try:
            if pid == 'DP015':
                # DP015 需要 spec 参数
                fix_positions = fixer(doc, defect, spec)
            else:
                fix_positions = fixer(doc, defect)

            if fix_positions:
                repair_log.append({
                    "id": pid,
                    "name": defect.get('name', ''),
                    "fixes": fix_positions,
                    "count": len(fix_positions),
                })
                log.info(f"  自动修复 {pid}: {len(fix_positions)} 处")
        except Exception as e:
            log.warning(f"  自动修复 {pid} 失败: {e}")

    return repair_log
