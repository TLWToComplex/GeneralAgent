"""
Analyze extracted contract clauses against a risk checklist.

Usage:
    python scripts/analyze_risks.py --clauses extracted_clauses.json --output risk_register.json
"""

import argparse
import json
from pathlib import Path


DEFAULT_CHECKLIST_PATH = Path(__file__).parent.parent / "config" / "risk_checklist.json"


def load_checklist(path: str = None):
    p = Path(path or DEFAULT_CHECKLIST_PATH)
    return json.loads(p.read_text(encoding="utf-8"))


def analyze_clause(clause: dict, dimensions: list) -> list:
    """Return list of risk findings for a clause."""
    text = clause["text"].lower()
    findings = []
    for dim in dimensions:
        matched_signals = [signal for signal in dim["signals"] if signal.lower() in text]
        if matched_signals:
            findings.append({
                "dimension": dim["id"],
                "dimension_name": dim["name"],
                "risk_level": dim["risk_level"],
                "signals": matched_signals,
                "recommendation": dim["recommendation"],
            })
    return findings


def analyze(clauses_path: str, checklist_path: str = None) -> dict:
    data = json.loads(Path(clauses_path).read_text(encoding="utf-8"))
    checklist = load_checklist(checklist_path)
    dimensions = checklist.get("dimensions", [])

    findings_by_clause = []
    for clause in data["clauses"]:
        findings = analyze_clause(clause, dimensions)
        if findings:
            findings_by_clause.append({
                "clause_id": clause["id"],
                "clause_title": clause["title"],
                "findings": findings,
            })

    # 统计
    risk_counts = {"high": 0, "medium": 0, "low": 0}
    for item in findings_by_clause:
        for finding in item["findings"]:
            risk_counts[finding["risk_level"]] += 1

    return {
        "metadata": data.get("metadata", {}),
        "summary": risk_counts,
        "overall_risk": "high" if risk_counts["high"] else ("medium" if risk_counts["medium"] else "low"),
        "findings": findings_by_clause,
    }


def merge_risk_register(existing_path: str, new_result: dict) -> dict:
    """将新的规则引擎分析结果合并到已有的 risk_register.json 中。

    保护合规检查已合并的发现不被覆盖。
    """
    existing = {}
    if Path(existing_path).exists():
        try:
            existing = json.loads(Path(existing_path).read_text(encoding="utf-8"))
        except Exception:
            pass

    # 合并 findings：保留已有的所有条目，追加新条目（去重）
    existing_findings = existing.get("findings", [])
    new_findings = new_result.get("findings", [])

    # 用 (clause_id, 维度) 做去重
    existing_keys = set()
    for item in existing_findings:
        cid = item.get("clause_id", "")
        if "findings" in item and isinstance(item.get("findings"), list):
            for sub in item["findings"]:
                existing_keys.add((cid, sub.get("dimension", "")))
        else:
            existing_keys.add((cid, item.get("risk_type", "")))

    for item in new_findings:
        cid = item.get("clause_id", "")
        if "findings" in item and isinstance(item.get("findings"), list):
            # 过滤掉已存在的发现
            filtered = []
            for sub in item["findings"]:
                if (cid, sub.get("dimension", "")) not in existing_keys:
                    filtered.append(sub)
                    existing_keys.add((cid, sub.get("dimension", "")))
            if filtered:
                item_copy = dict(item)
                item_copy["findings"] = filtered
                existing_findings.append(item_copy)
        else:
            key = (cid, item.get("risk_type", ""))
            if key not in existing_keys:
                existing_findings.append(item)
                existing_keys.add(key)

    # 合并风险计数
    old_summary = existing.get("summary", {"high": 0, "medium": 0, "low": 0})
    new_summary = new_result.get("summary", {"high": 0, "medium": 0, "low": 0})
    merged_summary = {
        "high": old_summary.get("high", 0) + new_summary.get("high", 0),
        "medium": old_summary.get("medium", 0) + new_summary.get("medium", 0),
        "low": old_summary.get("low", 0) + new_summary.get("low", 0),
    }

    # 整体风险：取最高
    overall = "low"
    if merged_summary["high"] > 0:
        overall = "high"
    elif merged_summary["medium"] > 0:
        overall = "medium"

    return {
        "metadata": existing.get("metadata") or new_result.get("metadata", {}),
        "summary": merged_summary,
        "overall_risk": overall,
        "overall_risk_level": overall,
        "findings": existing_findings,
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze contract clauses for risks.")
    parser.add_argument("--clauses", required=True, help="Path to extracted_clauses.json.")
    parser.add_argument("--checklist", help="Path to risk_checklist.json.")
    parser.add_argument("--output", required=True, help="Path to output risk_register.json.")
    args = parser.parse_args()

    new_result = analyze(args.clauses, args.checklist)

    # 与已有的 risk_register.json 合并（保护合规检查已写入的发现）
    merged = merge_risk_register(args.output, new_result)

    Path(args.output).write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Risk register written to {args.output} (overall: {merged['overall_risk']}, "
          f"high:{merged['summary']['high']} medium:{merged['summary']['medium']} low:{merged['summary']['low']})")


if __name__ == "__main__":
    main()
