#!/usr/bin/env python3
"""固定流程第 0 步：把多个“同一张表”的 xlsx/csv 校验表头一致后拼接为单个 xlsx。

只依赖标准库 + openpyxl。所有输入文件的表头（去空白后）必须完全一致；
若某文件首行与参考表头不一致（表头缺失或表头不同），以退出码 2 结束并
打印差异，不写出任何文件，避免把脏数据拼进后续流程。

用法：
    python scripts/merge_inputs.py --input <文件或目录> --output <拼接输出.xlsx>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_expenses import files_under, rows_from_file  # noqa: E402
from openpyxl import Workbook  # noqa: E402


def _reference_header(files: list[Path]) -> list[str]:
    for path in files:
        for _sheet, headers, _rows in rows_from_file(path):
            headers = [h for h in headers if h]
            if headers:
                return headers
    raise SystemExit("输入文件中没有可用表头。")


def merge(input_path: Path, output_path: Path) -> dict:
    files = files_under(input_path)
    if not files:
        raise SystemExit(f"输入中未找到任何 .xlsx/.csv/.tsv 文件: {input_path}")

    reference = _reference_header(files)
    wb = Workbook(write_only=True)
    ws = wb.create_sheet("merged")
    ws.append(reference)

    manifests = []
    total = 0
    for path in files:
        for sheet, headers, rows in rows_from_file(path):
            headers = [h for h in headers if h]
            if headers != reference:
                missing = [h for h in reference if h not in headers]
                extra = [h for h in headers if h not in reference]
                raise SystemExit(
                    f"表头不一致: {path}::{sheet}。缺少列: {missing}; 多余列: {extra}。"
                    f"该文件可能缺少表头或为不同结构，请先修正再拼接。")
            count = 0
            for values in rows:
                row = list(values)
                if len(row) < len(reference):
                    row += [None] * (len(reference) - len(row))
                ws.append(row[:len(reference)])
                count += 1
                total += 1
            manifests.append({"path": str(path), "sheet": sheet, "rows": count})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return {"output": str(output_path),
            "file_count": len({m["path"] for m in manifests}),
            "header_columns": len(reference), "total_rows": total, "sources": manifests}


def main() -> None:
    parser = argparse.ArgumentParser(description="校验表头一致后拼接多张同构表为单个 xlsx。")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = merge(Path(args.input), Path(args.output))
    manifest_path = Path(args.output).with_name(Path(args.output).stem + "_manifest.json")
    manifest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": result["output"], "files": result["file_count"],
                      "rows": result["total_rows"], "manifest": str(manifest_path)},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()

