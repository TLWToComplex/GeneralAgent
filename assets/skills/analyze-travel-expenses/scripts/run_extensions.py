#!/usr/bin/env python3
"""Discover and run removable analysis modules."""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

from analyze_expenses import choose, clean_header, files_under, number, rows_from_file, text, write_json
from config_loader import load_config


def _collect(input_path: Path, config: dict, kinds) -> tuple[list[dict], dict]:
    records, seen = [], set()
    raw = duplicates = 0
    wanted = set(kinds)
    for path in files_under(input_path):
        for _sheet, headers, rows in rows_from_file(path):
            headers = [clean_header(h) for h in headers]
            for values in rows:
                if not any(v not in (None, "") for v in values):
                    continue
                raw += 1
                row = {headers[i]: values[i] if i < len(values) else None for i in range(len(headers)) if headers[i]}
                kind = text(row.get("消费类型"), "")
                if kind not in wanted:
                    continue
                _, key_value = choose(row, config["unique_key_candidates"])
                key = text(key_value, "")
                if key and config.get("deduplicate", True):
                    if key in seen:
                        duplicates += 1; continue
                    seen.add(key)
                source, amount = choose(row, config["amount_precedence"])
                row["amount"] = number(amount) or 0.0
                row["amount_source"] = source
                records.append(row)
    return records, {"raw_input_rows": raw, "included_rows": len(records), "duplicates_removed": duplicates}


def load_records(input_path: Path, config: dict) -> tuple[list[dict], dict]:
    records, stats = _collect(input_path, config, ["住宿"])
    return records, {"raw_input_rows": stats["raw_input_rows"], "hotel_rows": len(records),
                     "hotel_duplicates_removed": stats["duplicates_removed"]}


def load_travel_records(input_path: Path, config: dict) -> tuple[dict, dict]:
    records, stats = _collect(input_path, config, ["机票", "火车票", "住宿"])
    return ({"flight": [r for r in records if text(r.get("消费类型"), "") in ("机票", "火车票")],
             "hotel": [r for r in records if text(r.get("消费类型"), "") == "住宿"]},
            {"raw_input_rows": stats["raw_input_rows"], "flight_rows": 0, "hotel_rows": 0,
             "travel_duplicates_removed": stats["duplicates_removed"]})


def run(input_path: Path, config: dict) -> dict:
    records, validation = load_records(input_path, config)
    modules = []
    for name in config.get("enabled_modules", []):
        if not name.replace("_", "").isalnum():
            continue
        try:
            modules.append((name, importlib.import_module(f"analysis_modules.{name}")))
        except Exception:
            modules.append((name, None))
    need_travel = any("flight" in getattr(m, "RECORD_TYPES", ()) for _n, m in modules if m is not None)
    travel = None
    if need_travel:
        travel, travel_stats = load_travel_records(input_path, config)

    results, errors = {}, {}
    for name, module in modules:
        if module is None:
            errors[name] = "模块无法加载"
            continue
        if getattr(module, "CROSS", False):
            continue  # 交叉模块在二阶段运行
        try:
            if getattr(module, "MODULE_NAME", None) != name:
                raise ValueError("MODULE_NAME 与配置不一致")
            module_input = travel if "flight" in getattr(module, "RECORD_TYPES", ()) else records
            results[name] = module.analyze(module_input, config)
        except Exception as exc:
            errors[name] = f"{type(exc).__name__}: {exc}"
    # 交叉模块二阶段：依赖其他模块结果，必须在主流程全部完成后运行
    for name, module in modules:
        if module is None or not getattr(module, "CROSS", False) or name in results:
            continue
        try:
            module_input = travel if "flight" in getattr(module, "RECORD_TYPES", ()) else records
            results[name] = module.analyze(module_input, config, results)
        except Exception as exc:
            errors[name] = f"{type(exc).__name__}: {exc}"
    if travel:
        validation = {**validation, "flight_rows": len(travel["flight"]),
                      "hotel_rows_total": len(travel["hotel"])}
    return {"module_count": len(results), "enabled_modules": config.get("enabled_modules", []),
            "validation": validation, "errors": errors, "results": results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config", default=str(Path(__file__).parents[1] / "config" / "config.json"))
    args = parser.parse_args()
    config = load_config(args.config)
    result = run(Path(args.input), config)
    write_json(Path(args.output), result)
    print(json.dumps({"output": args.output, "modules": result["module_count"], "errors": result["errors"],
                      **result["validation"]}, ensure_ascii=False))
    if result["errors"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
