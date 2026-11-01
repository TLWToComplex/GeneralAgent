#!/usr/bin/env python3
"""
cli.py — docx-spec-formatter 统一命令行入口

用法:
    python cli.py spec-load   <spec.json>           → 验证并加载规范
    python cli.py analyze     <input.docx>           → 分析文档结构
    python cli.py format      -i in.docx -o out.docx → 主流程（规范驱动格式化）
    python cli.py validate    <output.docx> [-s spec.json] → 独立校验
    python cli.py fix         <output.docx> [-s spec.json] → 修复
    python cli.py show-config [-s spec.json]         → 展示规范摘要
    python cli.py spec-init   [--template name] [-o out.json] → 创建规范模板
"""

import sys
import argparse
from pathlib import Path

# 确保脚本目录在 path 中
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from spec_loader import load_spec, export_spec, DEFAULT_SPEC
from doc_analyzer import analyze_document, print_analysis_report
from format_applier import apply_format
from validator import validate_document, ValidationReport
from fix_engine import fix_and_retry
from diff_check import compare_features, print_diff_report
from _defect_patterns import run_all_checks, print_report as print_defect_report
from ai_review import extract_for_review, build_review_prompt
from utils import (
    log, print_banner, validate_input_file, resolve_path,
    backup_file, timestamp, safe_write_docx
)


# ──────────────────────────────────────────────
# 子命令：spec-load
# ──────────────────────────────────────────────

def cmd_spec_load(args):
    """验证并加载格式规范文件。"""
    spec = load_spec(args.spec_file)
    print(f"\n规范名称: {spec.meta.get('name', '未命名')}")
    print(f"版本:     {spec.version}")
    print(f"字体配置: {len(spec.fonts)} 项")
    print(f"字号配置: {len(spec.sizes)} 项")
    print(f"校验规则: {len(spec.validation['checks'])} 项")
    return 0


# ──────────────────────────────────────────────
# 子命令：analyze
# ──────────────────────────────────────────────

def cmd_analyze(args):
    """分析 docx 文档结构。"""
    spec = load_spec(args.spec_file) if args.spec_file else None
    analysis = analyze_document(args.input, spec)
    report = print_analysis_report(analysis)

    if args.output:
        out = Path(args.output)
        out.write_text(report, encoding='utf-8')
        log.info(f"分析报告已保存到: {args.output}")
    return 0


# ──────────────────────────────────────────────
# 子命令：format（主流程）
# ──────────────────────────────────────────────

def cmd_format(args):
    """主流程：规范驱动格式化。"""
    print(print_banner())

    # Step 0: 验证输入
    validate_input_file(args.input)
    spec = load_spec(args.spec_file)
    output = Path(args.output)

    if args.analyze_only:
        # 仅分析模式
        analysis = analyze_document(args.input, spec)
        print_analysis_report(analysis)
        return 0

    # Step 1-2: 文档分析（format_applier 内部完成）
    log.info("Phase 1-2: 加载规范 + 分析文档")

    # Step 3: 格式应用 + 写输出
    log.info("Phase 3: FORMAT-APPLY 开始...")
    apply_format(args.input, spec, str(output))

    # Step 4: 校验
    if not args.skip_validate:
        log.info("Phase 4: VALIDATE 开始...")
        report = validate_document(str(output), spec)

        # 保存校验报告
        report_file = output.with_suffix('.report.json')
        report_file.write_text(report.to_json(), encoding='utf-8')
        log.info(f"校验报告已保存: {report_file}")

        # Step 5: 自动修复（基于自审结果）
        if not args.no_autofix and report.self_review_results:
            log.info("Phase 5: AUTO-FIX 开始...")
            from docx import Document as _Doc
            from auto_fix import auto_fix as _auto_fix
            _fix_doc = _Doc(str(output))
            _fix_log = _auto_fix(_fix_doc, spec, report.self_review_results)
            if _fix_log:
                from utils import safe_write_docx
                safe_write_docx(_fix_doc, str(output))
                log.info(f"自动修复完成：{sum(r['count'] for r in _fix_log)} 处")
                # 修复后重新校验
                report = validate_document(str(output), spec)
            else:
                log.info("自动修复：无可修复项")

        # Step 6: 格式修复循环
        if not args.skip_fix and not report.passed:
            log.info("Phase 6: FIX & RETRY 开始...")
            final_path, final_report, retry_count = fix_and_retry(
                str(output), spec, report)

            # 最终报告 = 包含修复后的校验 + 自审
            final_report_file = output.with_suffix('.final-report.json')
            final_report_file.write_text(final_report.to_json(), encoding='utf-8')
            log.info(f"最终校验报告已保存: {final_report_file}")
        else:
            # 未修复，最终报告 = 初验报告（含自审）
            final_report = report

        # --strict 模式：自审发现 error 时终止
        if args.strict:
            sr_errors = sum(1 for r in final_report.self_review_results
                           if r.get('severity') == 'error')
            sr_warnings = sum(1 for r in final_report.self_review_results
                             if r.get('severity') == 'warning')
            if sr_errors > 0:
                log.error(f"严格模式：自审发现 {sr_errors} 个错误，终止")
                return 1
            if sr_warnings > 0:
                log.warning(f"严格模式：自审发现 {sr_warnings} 个警告")

        # 差异比对（--ref 指定参考文档时自动执行）
        if hasattr(args, 'ref') and args.ref:
            log.info("Phase 7: DIFF-CHECK 开始...")
            from diff_check import compare_features, print_diff_report
            try:
                diffs = compare_features(str(output), args.ref)
                print_diff_report(diffs)
                sig_count = sum(1 for d in diffs if d['significant'])
                if sig_count > 0:
                    log.warning(f"结构差异：发现 {sig_count} 项重要差异")
            except Exception as e:
                log.warning(f"差异比对跳过: {e}")

        # 自动生成 HTML 报告
        if not args.no_html:
            try:
                from report_html import generate_html as _gen_html
                _report_data = final_report.to_dict()
                _html_path = output.with_suffix('.report.html')
                _gen_html(_report_data, str(_html_path), "格式校验报告")
            except Exception as e:
                log.warning(f"HTML报告生成跳过: {e}")
    else:
        log.info("跳过校验和修复阶段")

    log.info(f"完成! 输出文件: {output}")
    return 0


# ──────────────────────────────────────────────
# 子命令：validate
# ──────────────────────────────────────────────

def cmd_validate(args):
    """独立校验文档格式。"""
    spec = load_spec(args.spec_file)
    log.info(f"校验文档: {args.input}")
    
    report = validate_document(args.input, spec)
    
    if args.verbose:
        for r in report.results:
            print(f"  {r}")
    
    if args.report_only:
        print(report.to_json())
    else:
        report.print_summary()
    
    return 0 if report.passed else 1


# ──────────────────────────────────────────────
# 子命令：fix
# ──────────────────────────────────────────────

def cmd_fix(args):
    """修复文档格式。"""
    spec = load_spec(args.spec_file)
    log.info(f"修复文档: {args.input}")
    
    # 先校验
    report = validate_document(args.input, spec)
    
    if report.passed:
        log.info("文档已通过全部校验，无需修复")
        return 0
    
    # 执行修复
    final_path, final_report, retry_count = fix_and_retry(
        args.input, spec, report)
    
    log.info(f"修复完成: {retry_count} 轮, "
             f"通过 {final_report.summary['passed']}/{final_report.summary['total']}")
    
    if not final_report.passed:
        log.warning(f"仍有 {final_report.summary['failed']} 项未通过:")
        for r in final_report.failed_items:
            log.warning(f"  - {r.check_id}: {r.message}")
    
    return 0 if final_report.passed else 1


# ──────────────────────────────────────────────
# 子命令：diff-check
# ──────────────────────────────────────────────

def cmd_diff_check(args):
    """对比输出文档与参考文档的结构特征。"""
    log.info(f"输出文档: {args.output}")
    log.info(f"参考文档: {args.ref}")

    diffs = compare_features(args.output, args.ref)
    print_diff_report(diffs)

    sig_count = sum(1 for d in diffs if d['significant'])
    if sig_count > 0:
        log.warning(f"发现 {sig_count} 项重要差异")
    else:
        log.info("无显著差异")
    return sig_count


# ──────────────────────────────────────────────
# 子命令：self-check
# ──────────────────────────────────────────────

def cmd_self_check(args):
    """对格式化后的文档运行语义级自审。"""
    from docx import Document
    spec = load_spec(args.spec_file)
    doc = Document(args.input)

    log.info(f"文档: {args.input}, 规范: {spec.meta.get('name', '?')}")
    results = run_all_checks(doc, spec)
    print_defect_report(results)

    err_count = sum(1 for r in results if r['severity'] == 'error')
    if err_count > 0:
        log.warning(f"发现 {err_count} 个错误")
    return err_count


# ──────────────────────────────────────────────
# 子命令：show-config
# ──────────────────────────────────────────────

def cmd_show_config(args):
    """展示规范配置摘要。"""
    spec = load_spec(args.spec_file)

    print(f"\n{'='*60}")
    print(f"  格式规范: {spec.meta.get('name', '未命名')}")
    print(f"  版本: {spec.version}")
    if spec.meta.get('description'):
        print(f"  描述: {spec.meta['description']}")
    print(f"{'='*60}\n")

    print("【页面设置】")
    p = spec.page
    print(f"  尺寸: {p['size']} ({p['orientation']})")
    print(f"  边距: 上{p['margin_top_cm']} 下{p['margin_bottom_cm']} "
          f"左{p['margin_left_cm']} 右{p['margin_right_cm']} cm")

    print("\n【字体配置】")
    for key, pair in spec.fonts.items():
        if key.startswith('_') or not isinstance(pair, dict):
            continue
        print(f"  {key:<20s} CJK: {pair['cjk']:<14s} Latin: {pair['latin']}")

    print("\n【字号配置 (pt)】")
    for key, val in spec.sizes.items():
        print(f"  {key:<20s} {val}")

    print(f"\n【行距设置】")
    s = spec.spacing
    print(f"  正文行距: {s['body_line_spacing_pt']} pt")
    print(f"  标题行距: {s['title_line_spacing_pt']} pt")
    print(f"  首行缩进: {s['first_line_indent_chars']} 字符")

    print(f"\n【特殊区域】")
    ss = spec.special_sections
    cover = ss.get('cover', {})
    toc = ss.get('toc', {})
    rev = ss.get('revision_history', {})
    print(f"  封面: {'启用' if cover.get('enabled') else '禁用'}")
    print(f"  目录: {'启用' if toc.get('enabled') else '禁用'}")
    print(f"  修订记录: {'启用' if rev.get('enabled') else '禁用'} "
          f"(关键词: {', '.join(rev.get('detection_keywords', [])[:3])})")

    print(f"\n【校验规则 ({len(spec.validation['checks'])} 项)】")
    for c in spec.validation['checks']:
        print(f"  - {c}")

    return 0


# ──────────────────────────────────────────────
# 子命令：spec-init
# ──────────────────────────────────────────────

def cmd_spec_init(args):
    """初始化格式规范文件。"""
    template = args.template or 'default'
    output = args.output or 'spec.json'

    # 查找模板文件
    template_dir = _SCRIPT_DIR.parent / 'templates'
    template_file = template_dir / f'{template}-spec.json'

    if template_file.exists():
        spec = load_spec(str(template_file))
    else:
        log.info(f"模板 '{template}' 不存在，使用内置默认值")
        from spec_loader import DEFAULT_SPEC
        from copy import deepcopy
        from spec_loader import Spec
        spec = Spec(deepcopy(DEFAULT_SPEC))

    export_spec(spec, output)
    print(f"\n规范模板已创建: {output}")
    print(f"请编辑此文件调整字体、字号、边距等设置。")
    return 0


# ──────────────────────────────────────────────
# 子命令：report
# ──────────────────────────────────────────────

def cmd_report(args):
    """从 JSON 报告生成 HTML。"""
    from report_html import generate_from_json
    generate_from_json(args.input, args.output)


# ──────────────────────────────────────────────
# 子命令：batch
# ──────────────────────────────────────────────

def cmd_batch(args):
    """批量格式化目录下的所有 docx 文件。"""
    from batch import batch_format
    result = batch_format(
        args.input_dir, args.spec_file, args.output_dir,
        pattern=args.pattern or '*.docx',
        strict=args.strict, skip_errors=args.skip_errors)
    if result['failed'] > 0:
        return 1
    return 0


# ──────────────────────────────────────────────
# 子命令：ai-review
# ──────────────────────────────────────────────

def cmd_ai_review(args):
    """提取文档结构数据供 AI 评审。"""
    from ai_review import extract_for_review, build_review_prompt
    from spec_loader import load_spec
    from docx import Document

    doc = Document(args.input)

    spec_name = ''
    if args.spec_file:
        spec = load_spec(args.spec_file)
        spec_name = spec.meta.get('name', '')

    review_data = extract_for_review(doc)
    prompt = build_review_prompt(review_data, spec_name)

    # 输出到文件
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(prompt)
        print(f"AI 评审 Prompt 已保存: {args.output}")
    else:
        print(prompt)

    return 0


# ──────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        prog='docx-spec-formatter',
        description='基于格式规范的 docx 自动排版与校验工具',
    )
    parser.add_argument('--version', action='version',
                        version='docx-spec-formatter v0.1.0')

    sub = parser.add_subparsers(dest='command', title='子命令')

    # spec-load
    p = sub.add_parser('spec-load', help='验证并加载格式规范文件')
    p.add_argument('spec_file', help='JSON 规范文件路径')
    p.set_defaults(func=cmd_spec_load)

    # analyze
    p = sub.add_parser('analyze', help='分析 docx 文档结构')
    p.add_argument('input', help='输入 .docx 文件')
    p.add_argument('-s', '--spec-file', help='格式规范文件（可选）')
    p.add_argument('-o', '--output', help='输出分析报告文件（可选）')
    p.set_defaults(func=cmd_analyze)

    # format（主流程）
    p = sub.add_parser('format', help='主流程：规范驱动格式化')
    p.add_argument('-i', '--input', required=True, help='输入 .docx 文件')
    p.add_argument('-s', '--spec-file', help='格式规范 JSON 文件')
    p.add_argument('-o', '--output', required=True, help='输出 .docx 文件')
    p.add_argument('-f', '--force', action='store_true', help='强制覆盖已有输出文件')
    p.add_argument('--skip-validate', action='store_true', help='跳过校验阶段')
    p.add_argument('--skip-fix', action='store_true', help='跳过修复阶段')
    p.add_argument('--no-autofix', action='store_true', help='关闭自动修复')
    p.add_argument('--no-html', action='store_true', help='关闭 HTML 报告生成')
    p.add_argument('--strict', action='store_true', help='严格模式：自审发现错误时终止')
    p.add_argument('--ref', help='参考文档路径（用于结构差异比对）')
    p.add_argument('--analyze-only', action='store_true', help='仅分析，不修改')
    p.set_defaults(func=cmd_format)

    # validate
    p = sub.add_parser('validate', help='独立校验文档格式合规性')
    p.add_argument('input', help='待校验 .docx 文件')
    p.add_argument('-s', '--spec-file', help='格式规范 JSON 文件')
    p.add_argument('--report-only', action='store_true', help='仅生成报告，不修改')
    p.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    p.set_defaults(func=cmd_validate)

    # fix
    p = sub.add_parser('fix', help='修复文档格式')
    p.add_argument('input', help='待修复 .docx 文件')
    p.add_argument('-s', '--spec-file', help='格式规范 JSON 文件')
    p.set_defaults(func=cmd_fix)

    # diff-check
    p = sub.add_parser('diff-check', help='对比输出文档与参考文档的结构特征')
    p.add_argument('output', help='输出 .docx 文件')
    p.add_argument('--ref', required=True, help='参考 .docx 文件')
    p.set_defaults(func=cmd_diff_check)

    # self-check
    p = sub.add_parser('self-check', help='对文档运行语义级自审')
    p.add_argument('input', help='待审查 .docx 文件')
    p.add_argument('-s', '--spec-file', help='格式规范 JSON 文件')
    p.set_defaults(func=cmd_self_check)

    # show-config
    p = sub.add_parser('show-config', help='展示规范配置摘要')
    p.add_argument('-s', '--spec-file', help='JSON 规范文件（不指定则显示默认配置）')
    p.set_defaults(func=cmd_show_config)

    # spec-init
    p = sub.add_parser('spec-init', help='初始化格式规范文件')
    p.add_argument('--template', help='模板名称 (default/corporate/academic)')
    p.add_argument('-o', '--output', help='输出 JSON 文件路径')
    p.set_defaults(func=cmd_spec_init)

    # report
    p = sub.add_parser('report', help='从 JSON 校验报告生成 HTML')
    p.add_argument('input', help='校验报告 JSON 文件')
    p.add_argument('-o', '--output', help='输出 HTML 文件路径')
    p.set_defaults(func=cmd_report)

    # batch
    p = sub.add_parser('batch', help='批量格式化目录下的所有 docx 文件')
    p.add_argument('input_dir', help='输入目录')
    p.add_argument('-s', '--spec-file', help='格式规范 JSON 文件')
    p.add_argument('-o', '--output-dir', default='./output', help='输出目录')
    p.add_argument('--pattern', default='*.docx', help='文件匹配模式')
    p.add_argument('--strict', action='store_true', help='严格模式')
    p.add_argument('--skip-errors', action='store_true', help='遇到错误跳过继续')
    p.set_defaults(func=cmd_batch)

    # ai-review
    p = sub.add_parser('ai-review', help='提取文档结构数据供 AI 评审')
    p.add_argument('input', help='待评审 .docx 文件')
    p.add_argument('-s', '--spec-file', help='格式规范 JSON 文件')
    p.add_argument('-o', '--output', help='输出 Prompt 文件路径')
    p.set_defaults(func=cmd_ai_review)

    return parser


def main():
    parser = build_parser()

    if len(sys.argv) == 1:
        parser.print_help()
        return 0

    args = parser.parse_args()

    if not hasattr(args, 'func'):
        parser.print_help()
        return 1

    try:
        return args.func(args)
    except FileNotFoundError as e:
        log.error(f"文件未找到: {e}")
        return 2
    except ValueError as e:
        log.error(f"参数错误: {e}")
        return 3
    except Exception as e:
        log.error(f"未预期的错误: {type(e).__name__}: {e}")
        return 4


if __name__ == '__main__':
    sys.exit(main())
