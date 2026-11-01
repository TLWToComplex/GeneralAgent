"""
batch.py — 批量文档格式化工具

对目录下多个文档使用同一规范一次性批量格式化，
输出汇总报告。
"""
import sys
from pathlib import Path
from utils import log


def batch_format(input_dir: str, spec_path: str, output_dir: str,
                 pattern: str = "*.docx", strict: bool = False,
                 skip_errors: bool = False) -> dict:
    """批量格式化一个目录下的所有 docx 文件。

    Args:
        input_dir: 输入目录
        spec_path: 规范文件路径
        output_dir: 输出目录
        pattern: 文件匹配模式，默认 *.docx
        strict: 是否启用严格模式
        skip_errors: 遇到错误是否跳过继续

    Returns:
        dict: { "total": N, "success": N, "failed": N, "results": [...] }
    """
    import os
    sys.path.insert(0, str(Path(__file__).parent))
    from cli import cmd_format
    import argparse

    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    files = sorted(input_path.glob(pattern))
    if not files:
        log.warning("未找到匹配的文件: %s/%s" % (input_dir, pattern))
        return {"total": 0, "success": 0, "failed": 0, "results": []}

    results = []
    for f in files:
        out_file = output_path / f.name
        log.info("=" * 50)
        log.info("处理: %s → %s" % (f.name, out_file))

        # 构造命令行参数
        class Args:
            input = str(f)
            output = str(out_file)
            spec_file = spec_path
            skip_validate = False
            skip_fix = False
            no_autofix = False
            no_html = True
            strict = strict
            ref = None
            analyze_only = False
            func = None

        try:
            exit_code = cmd_format(Args())
            if exit_code == 0:
                results.append({"file": f.name, "status": "success"})
                log.info("✅ %s 完成" % f.name)
            else:
                results.append({"file": f.name, "status": "strict_fail"})
                log.warning("⚠️ %s 严格模式未通过" % f.name)
        except Exception as e:
            results.append({"file": f.name, "status": "error", "error": str(e)})
            log.warning("❌ %s 失败: %s" % (f.name, e))
            if not skip_errors:
                break

    # 汇总
    success = sum(1 for r in results if r['status'] == 'success')
    failed = len(results) - success
    log.info("=" * 50)
    log.info("批量完成: 共 %d 个, 成功 %d, 失败 %d" % (len(files), success, failed))

    return {
        "total": len(files),
        "success": success,
        "failed": failed,
        "results": results,
    }
