#!/usr/bin/env python3
"""一键流水线：按固定顺序执行 探查 → 主分析 → 扩展分析 → HTML 渲染。

不新增任何分析逻辑，只依次调用本技能已有脚本；任一步失败即以对应退出码结束。
用法（在技能根目录执行）：
    python scripts/pipeline.py --input <文件或目录> --output-dir <输出目录> --config config/config.json
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_script(name: str, *args: str) -> None:
    cmd = [sys.executable, str(Path("scripts") / name), *args]
    print(">>", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        sys.exit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description="一键执行差旅消费分析全部固定步骤")
    parser.add_argument("--input", required=True, help="输入 Excel/CSV/TSV 文件或目录")
    parser.add_argument("--output-dir", required=True, help="输出目录")
    parser.add_argument("--config", default=None, help="配置文件，默认 config/config.json")
    parser.add_argument("--skip-inspect", action="store_true", help="跳过探查步骤")
    args = parser.parse_args()

    config = Path(args.config) if args.config else (ROOT / "config" / "config.json")
    if not config.is_absolute():
        config = (ROOT / config).resolve()
    if not config.exists():
        sys.exit(f"配置文件不存在: {config}")
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.skip_inspect:
        run_script("analyze_expenses.py", "inspect",
                   "--input", args.input, "--output", str(out_dir / "inventory.json"))
    run_script("analyze_expenses.py", "analyze",
               "--input", args.input, "--output-dir", str(out_dir), "--config", str(config))
    run_script("run_extensions.py",
               "--input", args.input,
               "--output", str(out_dir / "extension_analysis.json"),
               "--config", str(config))
    run_script("render_extension_html.py",
               "--output-dir", str(out_dir), "--config", str(config))


if __name__ == "__main__":
    main()