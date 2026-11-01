#!/usr/bin/env python3
"""
报告生成脚本 — 将审查中间结果合并为一份 Markdown 报告。

Usage:
    python scripts/generate_report.py \\
        --clauses extracted_clauses.json \\
        --risks risk_register.json \\
        --compliance compliance_report.json \\
        --suggestions suggestions.json \\
        --output contract_review_report.md
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# 风险类型中英文映射
RISK_TYPE_MAP = {
    "unlimited_liability": "无限责任",
    "unilateral_termination": "单方解除权",
    "unfair_penalty": "不合理违约金",
    "vague_terms": "模糊条款",
    "missing_protection": "缺少保护条款",
    "ip_risk": "知识产权风险",
    "payment_risk": "付款风险",
    "confidentiality_risk": "保密风险",
    "jurisdiction_risk": "管辖权风险",
    "auto_renewal_risk": "自动续约风险",
}

def format_risk_type(risk_type: str) -> str:
    """将英文风险类型转为中文。"""
    return RISK_TYPE_MAP.get(risk_type.lower(), risk_type)  # 若未匹配则保留原值

# 实体类型中英文映射
ENTITY_TYPE_MAP = {
    "party_a": "甲方",
    "party_b": "乙方",
    "amount": "金额",
    "date": "日期",
    "subject": "标的物/服务内容",
    "duration": "期限",
    "address": "地址",
    "governing_law": "适用法律",
    "jurisdiction": "管辖地",
}

def format_entity_type(entity_type: str) -> str:
    """将英文实体类型转为中文。"""
    return ENTITY_TYPE_MAP.get(entity_type.lower(), entity_type)


def load_json(path: Optional[str]) -> Optional[Dict]:
    """加载 JSON 文件，若不存在或出错则返回 None。"""
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"无法加载 {path}: {e}")
        return None


def format_risk_level(level: str) -> str:
    """将风险等级转为带表情符号的 Markdown 格式。"""
    emojis = {
        "high": "🔴 **高**",
        "medium": "🟡 **中**",
        "low": "🟢 **低**",
        "none": "⚪ **无**",
    }
    return emojis.get(level.lower(), level)


def format_compliance_status(status: str) -> str:
    """将合规状态转为带表情符号的 Markdown 格式。"""
    emojis = {
        "compliant": "✅ 合规",
        "non_compliant": "❌ 不合规",
        "needs_review": "⚠️ 待审查",
    }
    return emojis.get(status.lower(), status)


def build_metadata_section(metadata: Dict) -> str:
    """构建元数据章节。"""
    lines = ["## 📋 合同元数据", ""]
    lines.append(f"- **文件名**：{metadata.get('filename', '未知')}")
    lines.append(f"- **合同类型**：{metadata.get('contract_type', '未知')}")
    lines.append(f"- **适用法律**：{metadata.get('governing_law', '未指定')}")
    lines.append(f"- **管辖地**：{metadata.get('jurisdiction', '未指定')}")
    
    parties = metadata.get("parties", [])
    if parties:
        lines.append("- **签约各方**：")
        for p in parties:
            lines.append(f"  - {p.get('entity_type')}：{p.get('value')}")
    else:
        lines.append("- **签约各方**：未识别")
    
    return "\n".join(lines)


def _flatten_risk_findings(raw_findings: List[Dict]) -> List[Dict]:
    """
    将嵌套或扁平的 risk findings 归一化为扁平列表。
    
    analyze_risks.py 输出嵌套格式：
      [{clause_id, clause_title, findings: [{dimension, dimension_name, risk_level, signals, recommendation}]}]
    
    compliance_check.py → update_risk_register 输出扁平格式：
      [{clause_id, risk_level, risk_type, description, rationale, recommendation, ...}]
    
    此函数检测并统一两种格式。
    """
    flat = []
    for item in raw_findings:
        # 嵌套格式：item 有 'findings' 子列表
        if "findings" in item and isinstance(item["findings"], list):
            parent_id = item.get("clause_id", "")
            parent_title = item.get("clause_title", "")
            for sub in item["findings"]:
                flat.append({
                    "clause_id": parent_id,
                    "clause_title": parent_title,
                    "risk_level": sub.get("risk_level", "medium"),
                    "risk_type": sub.get("dimension", sub.get("risk_type", "")),
                    "description": sub.get("dimension_name", sub.get("description", "")),
                    "buyer_impact": sub.get("buyer_impact", ""),
                    "seller_impact": sub.get("seller_impact", ""),
                    "rationale": ", ".join(sub.get("signals", [])) or sub.get("rationale", ""),
                    "recommendation": sub.get("recommendation", ""),
                })
        else:
            # 扁平格式：直接使用
            flat.append(item)
    return flat


def build_risk_section(risk_data: Dict) -> str:
    """构建风险发现章节。兼容嵌套（analyze_risks.py）和扁平（compliance_check合并）两种格式。"""
    raw_findings = risk_data.get("findings", []) if risk_data else []
    # 兼容两种 overall_risk 键名：analyze_risks.py 用 'overall_risk'，LLM 输出用 'overall_risk_level'
    overall = (
        risk_data.get("overall_risk_level", None)
        or risk_data.get("overall_risk", "none")
    ) if risk_data else "unknown"

    lines = ["## 🔍 风险发现", ""]
    lines.append(f"**整体风险等级**：{format_risk_level(overall)}")

    if risk_data and risk_data.get("risk_summary"):
        lines.append(f"**风险摘要**：{risk_data.get('risk_summary')}")

    lines.append("")

    if not raw_findings:
        lines.append("✅ 未检测到明显风险。")
        return "\n".join(lines)

    # 归一化
    findings = _flatten_risk_findings(raw_findings)

    # 按风险等级分组
    high = [f for f in findings if f.get("risk_level") == "high"]
    medium = [f for f in findings if f.get("risk_level") == "medium"]
    low = [f for f in findings if f.get("risk_level") == "low"]

    lines.append(f"共发现 **{len(high)}** 个高风险、**{len(medium)}** 个中风险、**{len(low)}** 个低风险问题。")
    lines.append("")

    # 高风险表格
    if high:
        lines.append("### 🔴 高风险发现")
        lines.append("")
        lines.append("| 条款ID | 风险类型 | 描述 | 对买方影响 | 对卖方影响 |")
        lines.append("|--------|----------|------|------------|------------|")
        for f in high:
            buyer = f.get('buyer_impact', '') or '—'
            seller = f.get('seller_impact', '') or '—'
            lines.append(
                f"| {f.get('clause_id', '')} "
                f"| {format_risk_type(f.get('risk_type', ''))} "
                f"| {f.get('description', '')[:50]}… "
                f"| {buyer[:30]}… "
                f"| {seller[:30]}… |"
            )
        lines.append("")

    # 中风险表格
    if medium:
        lines.append("### 🟡 中风险发现")
        lines.append("")
        lines.append("| 条款ID | 风险类型 | 描述 | 依据 |")
        lines.append("|--------|----------|------|------|")
        for f in medium:
            lines.append(
                f"| {f.get('clause_id', '')} "
                f"| {format_risk_type(f.get('risk_type', ''))} "
                f"| {f.get('description', '')[:50]}… "
                f"| {f.get('rationale', '')[:40]}… |"
            )
        lines.append("")

    # 低风险表格
    if low:
        lines.append("### 🟢 低风险发现")
        lines.append("")
        lines.append("| 条款ID | 风险类型 | 描述 |")
        lines.append("|--------|----------|------|")
        for f in low:
            lines.append(
                f"| {f.get('clause_id', '')} "
                f"| {format_risk_type(f.get('risk_type', ''))} "
                f"| {f.get('description', '')[:50]}… |"
            )
        lines.append("")

    return "\n".join(lines)


def build_compliance_section(comp_data: Dict) -> str:
    """构建合规检查章节。适配新版 compliance_report.json（含 risk_level、reason、source 等字段）。"""
    if not comp_data:
        return "## ⚖️ 合规检查\n\n⚠️ 合规检查未执行或无数据。"

    findings = comp_data.get("findings", [])
    missing = comp_data.get("missing_clauses", [])
    missing_detail = comp_data.get("missing_clauses_detail", [])
    overall = comp_data.get("overall_compliance", "unknown")

    lines = ["## ⚖️ 合规检查", ""]
    lines.append(f"**整体合规状态**：{format_compliance_status(overall)}")
    lines.append("")

    # ---- 已检查法规概览 ----
    checked_regs = comp_data.get("checked_regulations", [])
    skipped_regs = comp_data.get("skipped_regulations", [])
    if checked_regs:
        lines.append("### 📜 已检查的法规")
        lines.append("")
        for item in checked_regs:
            if isinstance(item, dict):
                # 结构化格式：{"regulation": "《民法典》", "articles": ["第497条", "第585条"]}
                reg_name = item.get("regulation", "")
                articles = item.get("articles", [])
                if articles:
                    articles_str = "、".join(articles)
                    lines.append(f"- 📖 {reg_name} — 已检查条文：{articles_str}")
                else:
                    lines.append(f"- 📖 {reg_name}")
            else:
                # 兼容旧格式（纯字符串）
                lines.append(f"- 📖 {item}")
        lines.append("")
    if skipped_regs:
        lines.append("### ⏭️ 已跳过的法规（合同内容未触发）")
        lines.append("")
        for sr in skipped_regs:
            if isinstance(sr, dict):
                lines.append(f"- ⏭️ {sr.get('regulation', '')} — {sr.get('reason', '')}")
            else:
                lines.append(f"- ⏭️ {sr}")
        lines.append("")

    # ---- 缺失条款（增强版：含风险等级和出处） ----
    if missing_detail:
        lines.append("### 📋 缺失的必要条款")
        lines.append("")
        lines.append("| 缺失条款 | 风险等级 | 法规出处 | 原因 | 建议 |")
        lines.append("|----------|----------|----------|------|------|")
        for m in missing_detail:
            lines.append(
                f"| {m.get('name', '')} "
                f"| {format_risk_level(m.get('risk_level', 'medium'))} "
                f"| {m.get('source', '')[:40]}… "
                f"| {m.get('reason', '')[:40]}… "
                f"| {m.get('recommendation', '')[:40]}… |"
            )
        lines.append("")
    elif missing:
        # 兼容旧格式（简单字符串列表）
        lines.append("### 📋 缺失的必要条款")
        lines.append("")
        for m in missing:
            lines.append(f"- ❌ **{m}**")
        lines.append("")
    else:
        lines.append("✅ 所有必要条款均已包含。")
        lines.append("")

    # ---- 不合规发现 ----
    non_compliant = [f for f in findings if f.get("status") == "non_compliant"]

    if non_compliant:
        lines.append("### ❌ 不合规条款")
        lines.append("")
        # 检查是否为新版字段（有 risk_level）
        has_new_fields = any(
            f.get("risk_level") or f.get("reason") or f.get("source")
            for f in non_compliant
        )
        if has_new_fields:
            lines.append("| 条款ID | 风险等级 | 法规出处 | 问题 | 原因 | 建议 |")
            lines.append("|--------|----------|----------|------|------|------|")
            for f in non_compliant:
                lines.append(
                    f"| {f.get('clause_id', '')} "
                    f"| {format_risk_level(f.get('risk_level', 'high'))} "
                    f"| {f.get('regulation', '')[:30]}… "
                    f"| {f.get('issue', '')[:30]}… "
                    f"| {f.get('reason', '')[:30]}… "
                    f"| {f.get('recommendation', '')[:30]}… |"
                )
        else:
            # 旧格式兼容
            lines.append("| 条款ID | 法规 | 问题 | 建议 |")
            lines.append("|--------|------|------|------|")
            for f in non_compliant:
                lines.append(
                    f"| {f.get('clause_id', '')} "
                    f"| {f.get('regulation', '')} "
                    f"| {f.get('issue', '')[:40]}… "
                    f"| {f.get('recommendation', '')[:40]}… |"
                )
        lines.append("")

    # ---- 待审查发现 ----
    needs_review = [f for f in findings if f.get("status") == "needs_review"]

    if needs_review:
        lines.append("### ⚠️ 待审查条款")
        lines.append("")
        has_new_fields = any(
            f.get("risk_level") or f.get("reason")
            for f in needs_review
        )
        if has_new_fields:
            lines.append("| 条款ID | 风险等级 | 法规出处 | 问题 | 原因 | 建议 |")
            lines.append("|--------|----------|----------|------|------|------|")
            for f in needs_review:
                lines.append(
                    f"| {f.get('clause_id', '')} "
                    f"| {format_risk_level(f.get('risk_level', 'medium'))} "
                    f"| {f.get('regulation', '')[:30]}… "
                    f"| {f.get('issue', '')[:30]}… "
                    f"| {f.get('reason', '')[:30]}… "
                    f"| {f.get('recommendation', '')[:30]}… |"
                )
        else:
            lines.append("| 条款ID | 问题 | 建议 |")
            lines.append("|--------|------|------|")
            for f in needs_review:
                lines.append(
                    f"| {f.get('clause_id', '')} "
                    f"| {f.get('issue', '')[:40]}… "
                    f"| {f.get('recommendation', '')[:40]}… |"
                )
        lines.append("")

    return "\n".join(lines)

# 优先级中英文映射
PRIORITY_MAP = {
    "high": "高",
    "medium": "中",
    "low": "低",
}

def format_priority(priority: str) -> str:
    """将英文优先级转为中文。"""
    return PRIORITY_MAP.get(priority.lower(), priority)

def build_suggestion_section(sugg_data: Dict) -> str:
    """构建修改建议章节。"""
    if not sugg_data:
        return "## ✏️ 修改建议\n\n⚠️ 修改建议未生成或无数据。"
    
    suggestions = sugg_data.get("suggestions", [])
    version_diff = sugg_data.get("version_diff", "")
    
    lines = ["## ✏️ 修改建议", ""]
    
    if not suggestions:
        lines.append("✅ 暂无修改建议。")
        return "\n".join(lines)
    
    # 按优先级分组
    high = [s for s in suggestions if s.get("priority") == "high"]
    medium = [s for s in suggestions if s.get("priority") == "medium"]
    low = [s for s in suggestions if s.get("priority") == "low"]
    
    lines.append(f"共生成 **{len(high)}** 条高优先级、**{len(medium)}** 条中优先级、**{len(low)}** 条低优先级建议。")
    lines.append("")
    
    # 建议表格（全部）
    lines.append("| 优先级 | 条款ID | 修改理由 | 建议修改（摘要） |")
    lines.append("|--------|--------|----------|------------------|")
    for s in suggestions:
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(s.get("priority", "low"), "⚪")
        suggested_preview = s.get("suggested_text", "")[:40]
        if len(s.get("suggested_text", "")) > 40:
            suggested_preview += "…"
        lines.append(
            f"| {priority_icon} {format_priority(s.get('priority', ''))} "
            f"| {s.get('clause_id', '')} "
            f"| {s.get('reason', '')[:40]}… "
            f"| {suggested_preview} |"
        )
    lines.append("")
    
    # 版本差异（如果有）
    if version_diff and version_diff != "无修改":
        lines.append("### 📝 版本对比（Semantic Diff）")
        lines.append("")
        lines.append("```diff")
        lines.append(version_diff)
        lines.append("```")
        lines.append("")
    
    return "\n".join(lines)


def build_entity_section(entities: List[Dict]) -> str:
    """构建实体提取章节。"""
    if not entities:
        return "## 🏷️ 提取的实体\n\n⚠️ 未提取到实体。"
    
    lines = ["## 🏷️ 提取的实体", ""]
    
    # 按类型分组
    grouped = {}
    for e in entities:
        etype = e.get("entity_type", "other")
        if etype not in grouped:
            grouped[etype] = []
        grouped[etype].append(e)
    
    lines.append("| 实体类型 | 值 | 位置 |")
    lines.append("|----------|----|------|")
    for etype, items in grouped.items():
        for item in items:
            lines.append(f"| {etype} | {format_entity_type(item.get('value', ''))} | {format_entity_type(item.get('location', ''))} |")
    lines.append("")
    
    return "\n".join(lines)


def generate_report(
    clauses_data: Optional[Dict],
    risk_data: Optional[Dict],
    comp_data: Optional[Dict],
    sugg_data: Optional[Dict],
) -> str:
    """组装完整的 Markdown 报告。"""
    
    metadata = clauses_data.get("metadata", {}) if clauses_data else {}
    entities = clauses_data.get("entities", []) if clauses_data else []
    
    title = f"# 📄 合同审查报告"
    subtitle = f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    separator = "---"
    
    sections = [
        title,
        "",
        subtitle,
        "",
        separator,
        "",
        build_metadata_section(metadata),
        "",
        separator,
        "",
        build_risk_section(risk_data),
        "",
        separator,
        "",
        build_compliance_section(comp_data),
        "",
        separator,
        "",
        build_suggestion_section(sugg_data),
        "",
        separator,
        "",
        build_entity_section(entities),
        "",
        separator,
        "",
        "## 📎 附录",
        "",
        "### 审查流程摘要",
        "",
        "1. **预处理**：使用 LLM 将合同文本切分为条款，提取元数据与实体。",
        "2. **风险分析**：采用规则引擎 + LLM 双引擎识别风险（规则引擎扫描关键词，LLM 深度语义分析）。",
        "3. **合规检查**：采用双轨制——必查法规（民法典、劳动合同法、所内合同管理办法）全量执行，行业法规（安全生产法、建筑法、消防法等）根据合同内容关键词自动匹配触发。每条发现包含风险等级、法规出处原文引用和修改建议。",
        "4. **修改建议**：基于风险与合规结果生成具体、可操作的修改建议。",
        "",
        "---",
        "",
        f"*本报告由 Contract Review Skill 自动生成，共包含 {len(entities)} 个实体、{len(risk_data.get('findings', [])) if risk_data else 0} 个风险发现、{len(comp_data.get('findings', [])) if comp_data else 0} 个合规发现、{len(sugg_data.get('suggestions', [])) if sugg_data else 0} 条修改建议。*",
    ]
    
    return "\n".join(sections)


def main():
    parser = argparse.ArgumentParser(description="生成合同审查 Markdown 报告")
    parser.add_argument("--clauses", required=True, help="extracted_clauses.json 路径")
    parser.add_argument("--risks", required=True, help="risk_register.json 路径")
    parser.add_argument("--compliance", required=False, help="compliance_report.json 路径（可选）")
    parser.add_argument("--suggestions", required=False, help="suggestions.json 路径（可选）")
    parser.add_argument("--output", required=True, help="输出的 Markdown 报告路径")
    args = parser.parse_args()
    
    # 加载所有 JSON
    clauses_data = load_json(args.clauses)
    risk_data = load_json(args.risks)
    comp_data = load_json(args.compliance)
    sugg_data = load_json(args.suggestions)
    
    if not clauses_data:
        logger.error("必须加载条款数据，退出")
        return
    
    # 生成报告
    report = generate_report(clauses_data, risk_data, comp_data, sugg_data)
    
    # 写入文件
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    logger.info(f"报告已生成：{output_path}")


if __name__ == "__main__":
    main()