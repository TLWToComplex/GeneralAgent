"""
diff_check.py — 参考文档差异比对工具

比较输出文档与参考文档的结构特征，发现校验脚本无法捕获的语义差异。
"""
import re
from docx import Document
from docx.oxml.ns import qn


# ──────────────────────────────────────────────
# 文档特征提取
# ──────────────────────────────────────────────

def extract_features(doc_or_path):
    """提取文档的结构特征向量。

    Returns:
        dict: {
            "headings": {"L1": N, "L2": N, ...},  # 各层级标题数
            "heading_texts": {"L1": [(idx, text), ...], ...},  # 标题文本
            "heading_avg_len": {"L1": float, ...},  # 标题平均字数
            "lists": {"L1": N, "L2": N, ...},  # 各层级列表项数
            "tables": N,                       # 表格数
            "paragraphs": N,                   # 总段落数
            "region_boundaries": {"cover": (start,end), "toc": (start,end), ...},
            "cover_para_count": N,             # 封面段落数
        }
    """
    if isinstance(doc_or_path, str):
        doc = Document(doc_or_path)
    else:
        doc = doc_or_path

    # 标题特征
    try:
        from format_applier import _detect_heading_level
    except ImportError:
        # 如果模块路径问题，简单回退
        h1_re = re.compile(r'^\d+\s+\S')
        h2_re = re.compile(r'^\d+\.\d+\s+\S')

        def _detect_heading_level(t, para=None):
            if h1_re.match(t):
                after = t.split()[0]
                if '.' not in after and ')' not in after:
                    return 1
            if h2_re.match(t):
                return 2
            return None

    try:
        from format_applier import _detect_list_level
    except ImportError:
        def _detect_list_level(t):
            return None

    headings = {1: [], 2: [], 3: [], 4: []}
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if not t:
            continue
        lv = _detect_heading_level(t, para=p)
        if lv:
            headings.setdefault(lv, []).append((i, t))

    heading_counts = {f'L{k}': len(v) for k, v in headings.items() if v}
    heading_avg_len = {}
    for k, v in headings.items():
        if v:
            avg = sum(len(t) for _, t in v) / len(v)
            heading_avg_len[f'L{k}'] = round(avg, 1)

    # 列表特征
    lists = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        lv = _detect_list_level(t)
        if lv:
            lists[lv] = lists.get(lv, 0) + 1
    list_counts = {f'L{k}': v for k, v in lists.items() if v > 0}

    # 表格
    table_count = len(doc.tables)

    # 总段落
    para_count = len(doc.paragraphs)

    # 区域边界（粗略估算：查找关键段落）
    region_boundaries = {}
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if t and ('目次' in t or '目录' in t) and 'region_boundaries' not in region_boundaries:
            region_boundaries['toc'] = i
        if t and ('修订记录' in t or '版本历史' in t) and 'revision' not in region_boundaries:
            region_boundaries['revision'] = i

    # 封面段落数估算：从开头到第一个标题之间的段落数
    cover_count = 0
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if not t:
            continue
        if _detect_heading_level(t, para=p) == 1:
            cover_count = i
            break

    return {
        "headings": heading_counts,
        "heading_texts": {f'L{k}': [t for _, t in v[:10]] for k, v in headings.items() if v},
        "heading_avg_len": heading_avg_len,
        "lists": list_counts,
        "tables": table_count,
        "paragraphs": para_count,
        "cover_para_count": cover_count,
        "region_boundaries": region_boundaries,
    }


FEATURE_NAMES = {
    "headings": "标题数量分布",
    "heading_avg_len": "标题平均字数",
    "lists": "列表数量分布",
    "tables": "表格数",
    "paragraphs": "总段落数",
    "cover_para_count": "封面段落数",
}


def compare_features(output_doc, ref_doc):
    """比较两个文档的结构特征。

    Args:
        output_doc: 输出文档路径或 Document 对象
        ref_doc: 参考文档路径或 Document 对象

    Returns:
        list of dict: [
            {
                "feature": "标题数量分布",
                "key": "headings.L1",
                "output": N,
                "ref": N,
                "diff": ±N,
                "significant": bool,
                "suggestion": str
            },
            ...
        ]
    """
    out_feat = extract_features(output_doc)
    ref_feat = extract_features(ref_doc)

    differences = []

    # 比较数值特征
    for feat_name, display_name in FEATURE_NAMES.items():
        out_val = out_feat.get(feat_name, {})
        ref_val = ref_feat.get(feat_name, {})

        if isinstance(out_val, dict):
            all_keys = set(out_val.keys()) | set(ref_val.keys())
            for k in sorted(all_keys):
                o = out_val.get(k, 0)
                r = ref_val.get(k, 0)
                diff = o - r
                sig = abs(diff) > max(abs(r) * 0.3, 2) if r > 0 else bool(diff)
                if diff != 0:
                    suggestion = ''
                    if sig:
                        if feat_name == 'headings':
                            suggestion = f"输出文档的L1标题数与参考文档相差{diff}，可能需要检查章节结构"
                        elif feat_name == 'lists':
                            suggestion = f"输出文档的{k}列表项数与参考文档差异较大，可能影响格式一致性"
                        elif feat_name == 'paragraphs':
                            suggestion = "总段落数差异可能意味着结构变化"
                    differences.append({
                        "feature": display_name,
                        "key": f"{feat_name}.{k}",
                        "output": o,
                        "ref": r,
                        "diff": diff,
                        "significant": sig,
                        "suggestion": suggestion,
                    })
        else:
            o = out_val if out_val else 0
            r = ref_val if ref_val else 0
            diff = o - r
            sig = abs(diff) > max(abs(r) * 0.3, 2) if r > 0 else bool(diff)
            if diff != 0:
                differences.append({
                    "feature": display_name,
                    "key": feat_name,
                    "output": o,
                    "ref": r,
                    "diff": diff,
                    "significant": sig,
                    "suggestion": f"与参考文档差异{diff}，建议检查" if sig else "",
                })

    # 比较标题文本（抽样）
    out_ht = out_feat.get('heading_texts', {})
    ref_ht = ref_feat.get('heading_texts', {})
    for k in sorted(set(out_ht.keys()) | set(ref_ht.keys())):
        o_set = set(out_ht.get(k, []))
        r_set = set(ref_ht.get(k, []))
        missing = r_set - o_set
        extra = o_set - r_set
        if missing and len(missing) <= 5:
            differences.append({
                "feature": "标题文本差异",
                "key": f"{k} 参考文档有但输出无",
                "output": len(extra),
                "ref": len(missing),
                "diff": len(missing),
                "significant": True,
                "suggestion": f"参考文档中 {k} 标题 {', '.join(list(missing)[:3])} 在输出文档中未找到相同文本",
            })

    return differences


def print_diff_report(diffs):
    """打印差异报告。"""
    if not diffs:
        print("  结构对比通过：输出文档与参考文档无显著差异")
        return

    # 按显著性排序
    sig_diffs = [d for d in diffs if d['significant']]
    minor_diffs = [d for d in diffs if not d['significant']]

    if sig_diffs:
        print(f"  [重要差异] ({len(sig_diffs)}项)")
        for d in sig_diffs:
            print("    %s / %s: 输出=%s 参考=%s 差异=%s" % (d['feature'], d['key'], d['output'], d['ref'], d['diff']))
            if d['suggestion']:
                print(f"      建议: {d['suggestion']}")

    if minor_diffs:
        print(f"  [细微差异] ({len(minor_diffs)}项)")
        for d in minor_diffs[:5]:
            print(f"    {d['feature']} / {d['key']}: {d['diff']:+d}")
