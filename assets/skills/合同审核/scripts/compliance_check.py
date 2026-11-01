#!/usr/bin/env python3
"""
合规检查脚本 — 双轨制：必查法规 + 选查行业法规

用法：
    python scripts/compliance_check.py --input extracted_clauses.json --output compliance_report.json

法规配置来源：config/industry_regulations.json（如不存在则使用内置默认规则）
"""

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# -------- Logging --------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 默认路径
DEFAULT_REGULATIONS_PATH = Path(__file__).parent.parent / "config" / "industry_regulations.json"
DEFAULT_LAW_INDEX_PATH = Path(__file__).parent.parent / "config" / "law_index.json"
DEFAULT_LAWS_DIR = Path(__file__).parent.parent / "laws"

# -------- 内置兜底规则（当 JSON 配置文件加载失败时使用）--------
BUILTIN_MUST_CHECK = [
    {
        "rule_id": "civil_code_497",
        "regulation": "《中华人民共和国民法典》第497条",
        "category": "民法典",
        "keywords": ["免除己方责任", "排除对方主要权利", "加重对方责任"],
        "issue": "提供格式条款一方不合理地免除或者减轻其责任、加重对方责任、限制对方主要权利的，该格式条款无效。",
        "risk_level": "high",
    },
    {
        "rule_id": "civil_code_585",
        "regulation": "《中华人民共和国民法典》第585条",
        "category": "民法典",
        "keywords": ["违约金超过", "违约金过高"],
        "issue": "约定的违约金过分高于造成的损失的，当事人可以请求人民法院或者仲裁机构予以适当减少。",
        "risk_level": "high",
    },
    {
        "rule_id": "labor_law_19",
        "regulation": "《中华人民共和国劳动合同法》第19条",
        "category": "劳动合同法",
        "keywords": ["试用期超过", "试用期超过六个月"],
        "issue": "劳动合同期限三年以上的，试用期不得超过六个月。",
        "risk_level": "high",
    },
]

# ============================================================================
# 1. 加载法规配置
# ============================================================================

def _extract_base_regulation(regulation: str) -> str:
    """从完整法规字符串中提取基础法规名（去掉条文号）。
    
    >>> _extract_base_regulation("《中华人民共和国民法典》第497条")
    '《中华人民共和国民法典》'
    >>> _extract_base_regulation("二十所/电科西北《合同管理办法》（所综〔2026〕231号）第三十八条")
    '二十所/电科西北《合同管理办法》（所综〔2026〕231号）'
    """
    # 匹配 "第X条" 或 "第XX条" 或 "第三十八条" 等中文数字条文号
    result = re.sub(r'\s*第[一二三四五六七八九十百千\d]+条.*$', '', regulation)
    # 去掉尾部多余的标点空格
    return result.rstrip('，,;；')


def _build_checked_regulations(rules: List[Dict]) -> List[Dict]:
    """将规则列表按基础法规名分组，输出结构化已检查法规。
    
    返回格式：[{"regulation": "《民法典》", "articles": ["第497条", "第585条"]}, ...]
    """
    groups: Dict[str, List[str]] = {}
    # 保序
    order: List[str] = []
    for r in rules:
        full = r.get("regulation", "")
        base = _extract_base_regulation(full)
        # 提取条文号
        article_match = re.search(r'(第[一二三四五六七八九十百千\d]+条[^）\)]*)', full)
        article = article_match.group(1) if article_match else ""

        if base not in groups:
            groups[base] = []
            order.append(base)
        if article and article not in groups[base]:
            groups[base].append(article)

    return [{"regulation": base, "articles": groups[base]} for base in order]


def load_regulations(config_path: Optional[str] = None) -> Dict:
    """加载法规配置 JSON。若失败则回退到内置默认规则。"""
    path = Path(config_path) if config_path else DEFAULT_REGULATIONS_PATH
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("已加载法规配置：%d 条必查规则 + %d 条选查规则",
                        len(data.get("must_check", [])),
                        len(data.get("optional_check", [])))
            return data
        except Exception as e:
            logger.warning("法规配置文件加载失败 (%s)，使用内置默认规则", e)
    else:
        logger.warning("法规配置文件不存在: %s，使用内置默认规则", path)
    return {
        "version": "fallback",
        "must_check": BUILTIN_MUST_CHECK,
        "optional_check": [],
    }


def load_required_clauses(config: Dict) -> Dict[str, List[str]]:
    """从配置中提取必备条款映射，兜底使用硬编码。"""
    return config.get("required_clauses_by_type", {
        "general": ["当事人信息", "标的/服务内容", "价款/报酬", "履行期限", "违约责任", "争议解决"],
    })


def load_category_keys(config: Dict) -> Dict[str, List[str]]:
    """从配置中提取必备条款关键词映射。"""
    return config.get("category_keys_for_missing", {
        "当事人信息": ["甲方", "乙方", "当事人"],
        "标的/服务内容": ["标的", "服务内容", "商品"],
        "价款/报酬": ["价款", "报酬", "费用", "金额", "价格"],
        "履行期限": ["期限", "交付时间", "完成时间"],
        "违约责任": ["违约", "赔偿责任", "违约金"],
        "争议解决": ["争议", "仲裁", "诉讼", "管辖"],
    })


# ============================================================================
# 2. 合同文本拼接
# ============================================================================

def get_contract_full_text(clauses: List[Dict]) -> str:
    """将所有条款拼接为完整文本，用于选查法规关键词匹配。"""
    parts = []
    for c in clauses:
        parts.append(c.get("title", ""))
        parts.append(c.get("text", ""))
    return " ".join(parts)


# ============================================================================
# 3. 合同类型判断 & 必备条款
# ============================================================================

def detect_contract_type_from_metadata(metadata: Dict) -> str:
    """从元数据获取合同类型。"""
    return metadata.get("contract_type", "未知")


def get_required_clauses_for_type(contract_type: str,
                                   required_map: Dict[str, List[str]]) -> List[str]:
    """根据合同类型返回必备条款列表。"""
    ct = contract_type.lower()
    clauses = list(required_map.get("general", []))

    if "劳动" in ct or "labor" in ct or "employ" in ct:
        clauses.extend(required_map.get("劳动合同", []))
    if "买卖" in ct or "sale" in ct or "采购" in ct or "销售" in ct or "货物" in ct:
        clauses.extend(required_map.get("买卖合同", []))

    # 去重保序
    seen = set()
    result = []
    for c in clauses:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


# ============================================================================
# 4. 专项检查逻辑
# ============================================================================

def check_missing_clauses(clauses: List[Dict],
                          contract_type: str,
                          rule: Dict,
                          required_map: Dict[str, List[str]],
                          category_keys: Dict[str, List[str]]) -> List[Dict]:
    """检查必备条款是否缺失。"""
    required = get_required_clauses_for_type(contract_type, required_map)
    combined_text = " ".join(
        c.get("title", "") + " " + c.get("text", "")[:100]
        for c in clauses
    )

    findings = []
    for req in required:
        keywords = category_keys.get(req, [req])
        found = any(kw in combined_text for kw in keywords)
        if not found:
            findings.append({
                "clause_id": "",
                "clause_title": "",
                "status": "missing",
                "risk_level": rule.get("risk_level", "medium"),
                "category": rule.get("category", ""),
                "regulation": rule["regulation"],
                "rule_id": rule["rule_id"],
                "issue": f"合同缺少必要的「{req}」条款",
                "reason": f"根据{rule['regulation']}，合同应当包含「{req}」条款。缺失该条款可能导致合同权利义务不明确，在履行和争议解决时缺乏依据。",
                "source": f"{rule['regulation']}：{rule['issue']}",
                "recommendation": f"建议添加「{req}」相关条款，明确双方的{req}相关权利义务。",
            })
    return findings


def check_six_point_check(clauses: List[Dict], rule: Dict, contract_text: str) -> List[Dict]:
    """执行所内六项初审检查。"""
    six_points = [
        ("主体资格", ["营业执照", "统一社会信用代码", "法定代表人", "主体资格", "注册号"]),
        ("经营资质", ["许可证", "资质证书", "经营范围", "资质等级"]),
        ("履约能力", ["履约能力", "支付能力", "生产能力", "运输能力", "资金证明", "验资报告"]),
        ("履约信用", ["履约信用", "无违约", "经济纠纷", "经济犯罪", "信用"]),
        ("条款完备性", ["标的", "价款", "期限", "违约责任", "争议解决"]),
        ("委托代理", ["法定代表人", "授权委托书", "身份证明", "委托代理人"]),
    ]

    findings = []
    for point_name, keywords in six_points:
        found = any(kw in contract_text for kw in keywords)
        if not found:
            findings.append({
                "clause_id": "",
                "clause_title": "",
                "status": "needs_review",
                "risk_level": rule.get("risk_level", "high"),
                "category": rule.get("category", ""),
                "regulation": rule["regulation"],
                "rule_id": rule["rule_id"],
                "issue": f"合同未明确涉及「{point_name}」相关审查内容",
                "reason": f"根据{rule['regulation']}，合同管理主责部门初审须核查「{point_name}」。合同中未发现相关内容，建议补充或书面说明审核情况。",
                "source": f"{rule['regulation']}：{rule['issue'].split('(一)')[0].strip()}",
                "recommendation": f"建议在合同附件或审核记录中补充「{point_name}」的核查情况说明。",
            })
    return findings


def check_template_check(clauses: List[Dict], rule: Dict, contract_text: str) -> List[Dict]:
    """检查合同类型与标准格式文本。"""

    findings = []
    # 检查合同类型是否明确
    type_keywords = ["资金收入类", "资金支出类", "工程类", "货物类", "服务类",
                     "军品收入", "军贸收入", "民品收入"]
    has_type = any(kw in contract_text for kw in type_keywords)
    if not has_type:
        findings.append({
            "clause_id": "",
            "clause_title": "",
            "status": "needs_review",
            "risk_level": rule.get("risk_level", "medium"),
            "category": rule.get("category", ""),
            "regulation": rule["regulation"],
            "rule_id": rule["rule_id"],
            "issue": "合同未明确标注合同类型分类",
            "reason": f"根据{rule['regulation']}，合同应按资金收入类/支出类进行分类管理，支出类还需区分工程类、货物类和服务类。合同文本中未找到明确的类型标注，可能影响后续管理与归档。",
            "source": f"{rule['regulation']}：{rule['issue']}",
            "recommendation": "建议在合同标题或首部明确标注合同类型（如“工程类合同”、“服务类合同”等），并确认使用了对应的标准格式文本。",
        })
    return findings


# ============================================================================
# 5. 关键词扫描（通用）
# ============================================================================

def keyword_scan_clause(clause: Dict, rule: Dict) -> Optional[Dict]:
    """在单个条款中扫描规则关键词，命中则返回发现。"""
    clause_id = clause.get("id", "")
    title = clause.get("title", "")
    content = clause.get("text", "")
    combined = title + " " + content
    keywords = rule.get("keywords", [])

    if not keywords:
        return None

    for kw in keywords:
        if kw in combined:
            return {
                "clause_id": clause_id,
                "clause_title": title,
                "status": "non_compliant" if rule.get("risk_level") == "high" else "needs_review",
                "risk_level": rule.get("risk_level", "medium"),
                "category": rule.get("category", ""),
                "regulation": rule["regulation"],
                "rule_id": rule["rule_id"],
                "issue": rule["issue"],
                "reason": f"条款「{title}」中包含关键词「{kw}」，涉及{rule['regulation']}规定的合规风险。{rule['issue']}",
                "source": f"{rule['regulation']}：{rule['issue']}",
                "recommendation": f"建议根据{rule['regulation']}的要求，对条款「{title}」中的相关内容进行修改或补充。",
            }
    return None


# ============================================================================
# 6. 单条规则执行调度
# ============================================================================

def execute_rule(rule: Dict,
                 clauses: List[Dict],
                 contract_text: str,
                 contract_type: str,
                 required_map: Dict[str, List[str]],
                 category_keys: Dict[str, List[str]]) -> List[Dict]:
    """
    根据规则类型调度执行：
    - 有 check_type → 执行专项检查
    - 有关键词列表 → 逐条款扫描
    - 两者都有 → 先专项检查，再关键词扫描（去重）
    """
    findings = []
    check_type = rule.get("check_type", "")

    # 专项检查
    if check_type == "missing_clauses":
        findings.extend(
            check_missing_clauses(clauses, contract_type, rule, required_map, category_keys)
        )
    elif check_type == "six_point_check":
        findings.extend(check_six_point_check(clauses, rule, contract_text))
    elif check_type == "template_check":
        findings.extend(check_template_check(clauses, rule, contract_text))

    # 关键词扫描（有 keywords 且非纯专项规则时，同时扫描）
    keywords = rule.get("keywords", [])
    if keywords and check_type not in ("missing_clauses",):
        for clause in clauses:
            result = keyword_scan_clause(clause, rule)
            if result:
                findings.append(result)

    # 如果关键词列表为空且无 check_type，说明这个规则仅靠关键词扫描但 keywords 为空
    if not keywords and not check_type:
        logger.debug("规则 %s 既无 keywords 也无 check_type，跳过", rule.get("rule_id"))

    return findings


# ============================================================================
# 7. 选查规则匹配
# ============================================================================

def match_optional_rules(optional_rules: List[Dict],
                         contract_text: str) -> Tuple[List[Dict], List[Dict]]:
    """
    根据合同全文关键词匹配选查规则。
    返回：(匹配到的规则列表, 未匹配的规则列表)
    """
    matched = []
    skipped = []
    for rule in optional_rules:
        triggers = rule.get("trigger_keywords", [])
        if not triggers:
            matched.append(rule)
        elif any(kw in contract_text for kw in triggers):
            matched.append(rule)
        else:
            skipped.append(rule)

    logger.info("选查法规：匹配 %d 条，跳过 %d 条", len(matched), len(skipped))
    return matched, skipped


# ============================================================================
# 8. LLM 深度合规检查（可选）
# ============================================================================

def llm_compliance_check(clauses: List[Dict],
                         contract_type: str,
                         matched_rules: List[Dict],
                         law_context: str = "") -> List[Dict]:
    """
    调用 LLM 进行深度合规检查。

    Args:
        law_context: 从 laws/ 文件夹检索到的法规条文全文（可选）。若提供，优先作为审查依据。
    """
    try:
        import openai
    except ImportError:
        logger.warning("openai 库未安装，跳过 LLM 合规检查")
        return []

    import os
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY 未设置，跳过 LLM 合规检查")
        return []

    client = openai.OpenAI(api_key=api_key)

    # 构建条款文本
    clauses_text = "\n\n".join(
        f"[条款ID: {c.get('id', '')}] {c.get('title', '')}\n{c.get('text', '')}"
        for c in clauses
    )

    # 优先使用法典检索结果，其次使用规则摘要
    if law_context:
        regulations_context = f"\n\n## 以下是从法典中检索到的相关法规条文（你必须基于这些条文进行审查，不要引用未列出的法规）\n{law_context}"
    elif matched_rules:
        reg_lines = []
        for r in matched_rules:
            reg_lines.append(f"- {r['regulation']}：{r['issue'][:120]}")
        regulations_context = (
            "\n\n## 本合同相关的行业法规（请据此审查）\n" + "\n".join(reg_lines)
        )
    else:
        regulations_context = ""

    system_prompt = f"""你是一名专业的中国法律合规审查专家。请对以下合同条款进行全面的合规性审查。

## 审查依据

1. 《中华人民共和国民法典》合同编
2. 《中华人民共和国劳动合同法》（如适用）
3. 二十所/电科西北《合同管理办法》（所综〔2026〕231号）
4. 其他适用的行业法律法规
{regulations_context}

## 输出要求

请输出严格的JSON格式（不要输出Markdown代码块标记）：

{{
  "findings": [
    {{
      "clause_id": "条款ID（对应输入中的条款ID）",
      "status": "compliant / non_compliant / needs_review",
      "risk_level": "high / medium / low",
      "regulation": "所依据的法规条文出处（如：《民法典》第XX条）",
      "issue": "合规问题的具体描述（中文）",
      "reason": "为什么这构成合规风险的解释（中文）",
      "recommendation": "具体的修改建议（中文）"
    }}
  ],
  "overall_compliance": "compliant / non_compliant / needs_review"
}}

## 注意事项
- 所有输出必须使用中文
- 每条发现必须提供法规出处（regulation字段）
- risk_level 必须根据问题的严重程度合理判断：
  - high：违反法律法规强制性规定，可能导致合同无效或行政处罚
  - medium：存在潜在合规风险，可能导致争议
  - low：格式或表述不完善，建议优化"""

    user_prompt = f"合同类型：{contract_type}\n\n请审查以下条款的合规性：\n\n{clauses_text}"

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        content = response.choices[0].message.content.strip()
        # 清理可能的 Markdown 代码块
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
        result = json.loads(content)
        findings = []
        for item in result.get("findings", []):
            status = item.get("status", "needs_review")
            if status != "compliant":
                findings.append({
                    "clause_id": item.get("clause_id", ""),
                    "clause_title": item.get("clause_title", ""),
                    "status": status,
                    "risk_level": item.get("risk_level", "medium"),
                    "category": "LLM深度检查",
                    "regulation": item.get("regulation", ""),
                    "rule_id": "llm_deep_check",
                    "issue": item.get("issue", ""),
                    "reason": item.get("reason", ""),
                    "source": item.get("regulation", ""),
                    "recommendation": item.get("recommendation", ""),
                })
        logger.info("LLM 合规检查完成，发现 %d 条问题", len(findings))
        return findings
    except Exception as e:
        logger.error("LLM 合规检查失败: %s", e)
        return []


# ============================================================================
# 9. 去重
# ============================================================================

def deduplicate_findings(findings: List[Dict]) -> List[Dict]:
    """按 (clause_id, rule_id, issue) 去重。"""
    seen = set()
    unique = []
    for f in findings:
        key = (f.get("clause_id", ""), f.get("rule_id", ""), f.get("issue", "")[:60])
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


# ============================================================================
# 10. 整体合规状态
# ============================================================================

def determine_overall_compliance(findings: List[Dict]) -> str:
    """根据发现推断整体合规状态。"""
    has_non_compliant = any(f.get("status") == "non_compliant" for f in findings)
    has_missing = any(f.get("status") == "missing" for f in findings)
    has_needs_review = any(f.get("status") == "needs_review" for f in findings)

    if has_non_compliant or has_missing:
        return "non_compliant"
    if has_needs_review:
        return "needs_review"
    return "compliant"


# ============================================================================
# 11. 合并到 risk_register.json
# ============================================================================

def update_risk_register(risk_register_path: Optional[Path],
                         compliance_findings: List[Dict]) -> None:
    """将合规发现合并写入 risk_register.json。"""
    if not risk_register_path:
        logger.info("未指定 --risk-register 路径，跳过合并。")
        return

    # 加载已有
    if risk_register_path.exists():
        try:
            with open(risk_register_path, "r", encoding="utf-8") as f:
                risk_register = json.load(f)
        except Exception:
            risk_register = {"findings": []}
    else:
        risk_register = {"findings": []}

    if "findings" not in risk_register or not isinstance(risk_register["findings"], list):
        risk_register["findings"] = []

    existing_keys = {
        (r.get("clause_id"), r.get("rule_id", ""))
        for r in risk_register["findings"]
    }

    for f in compliance_findings:
        key = (f.get("clause_id", ""), f.get("rule_id", ""))
        if key not in existing_keys:
            risk_register["findings"].append({
                "clause_id": f.get("clause_id", ""),
                "risk_level": f.get("risk_level", "medium"),
                "risk_type": "合规风险",
                "description": f.get("issue", ""),
                "buyer_impact": "",
                "seller_impact": "",
                "rationale": f"{f.get('regulation', '')}：{f.get('reason', '')}",
                "recommendation": f.get("recommendation", ""),
                "source": "compliance_check",
                "rule_id": f.get("rule_id", ""),
            })
            existing_keys.add(key)

    risk_register_path.parent.mkdir(parents=True, exist_ok=True)
    with open(risk_register_path, "w", encoding="utf-8") as f:
        json.dump(risk_register, f, ensure_ascii=False, indent=2)
    logger.info("已将 %d 条合规发现合并到 %s", len(compliance_findings), risk_register_path)


# ============================================================================
# 12. 主函数
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="合规检查 — 双轨制（必查法规 + 行业法规选查），输出中文风险等级及出处。"
    )
    parser.add_argument("--input", required=True, help="extracted_clauses.json 路径")
    parser.add_argument("--output", required=True, help="compliance_report.json 输出路径")
    parser.add_argument("--risk-register", help="risk_register.json 路径（可选，用于合并合规发现）")
    parser.add_argument("--regulations", help="industry_regulations.json 路径（可选，默认 config/industry_regulations.json）")
    parser.add_argument("--laws-dir", help="法典文件夹路径（可选，默认 ./laws）")
    parser.add_argument("--law-index", help="law_index.json 路径（可选，默认 config/law_index.json）")
    parser.add_argument("--llm", action="store_true", help="启用 LLM 深度合规检查（需设置 OPENAI_API_KEY）")
    args = parser.parse_args()

    # 1. 加载法规配置
    reg_config = load_regulations(args.regulations)
    must_check_rules = reg_config.get("must_check", [])
    optional_check_rules = reg_config.get("optional_check", [])
    required_map = load_required_clauses(reg_config)
    category_keys = load_category_keys(reg_config)

    # 法典检索路径（默认值）
    laws_dir = args.laws_dir or DEFAULT_LAWS_DIR
    law_index = args.law_index or DEFAULT_LAW_INDEX_PATH

    # 2. 加载合同数据
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error("无法加载输入文件 %s: %s", args.input, e)
        return

    metadata = data.get("metadata", {})
    clauses = data.get("clauses", [])
    contract_type = detect_contract_type_from_metadata(metadata)
    contract_text = get_contract_full_text(clauses)

    logger.info("合同类型: %s，条款数: %d", contract_type, len(clauses))

    # 3. 执行必查规则
    all_findings = []
    for rule in must_check_rules:
        findings = execute_rule(rule, clauses, contract_text, contract_type,
                                required_map, category_keys)
        all_findings.extend(findings)

    # 4. 选查规则：根据关键词匹配
    matched_optional, skipped_optional = match_optional_rules(optional_check_rules, contract_text)
    for rule in matched_optional:
        findings = execute_rule(rule, clauses, contract_text, contract_type,
                                required_map, category_keys)
        all_findings.extend(findings)

    # 5. LLM 深度检查（可选）— 优先使用法典检索，其次使用规则引擎
    law_context = ""
    if args.llm:
        # 尝试从 laws/ 文件夹加载法典
        if Path(laws_dir).exists():
            try:
                from law_retriever import retrieve_for_llm
                law_result = retrieve_for_llm(
                    contract_text=contract_text,
                    laws_dir=str(laws_dir),
                    index_path=str(law_index),
                    max_tokens=3000,
                )
                law_context = law_result["context"]
                logger.info("法典检索完成：%d 部法规，%d 条被跳过",
                            len(law_result.get("checked", [])),
                            len(law_result.get("skipped", [])))
            except ImportError as e:
                logger.warning("law_retriever 模块不可用：%s，回退到规则引擎", e)
            except Exception as e:
                logger.warning("法典检索失败：%s，回退到规则引擎", e)

        llm_findings = llm_compliance_check(
            clauses, contract_type,
            must_check_rules + matched_optional,
            law_context=law_context,
        )
        all_findings.extend(llm_findings)

    # 6. 去重
    all_findings = deduplicate_findings(all_findings)

    # 7. 分离缺失条款发现
    missing = [f for f in all_findings if f.get("status") == "missing"]
    non_missing = [f for f in all_findings if f.get("status") != "missing"]
    all_findings = non_missing  # 后续 findings 中去掉 missing 类（它们在 missing_clauses 中单独列出）

    # 组装 missing_clauses（增强信息）
    missing_with_info = []
    for m in missing:
        missing_with_info.append({
            "name": m.get("issue", "").replace("合同缺少必要的「", "").replace("」条款", ""),
            "risk_level": m.get("risk_level", "medium"),
            "source": m.get("source", ""),
            "reason": m.get("reason", ""),
            "recommendation": m.get("recommendation", ""),
        })
    # 同时从 findings 中提取提单级别的缺失条款引用（兼容旧字段）
    simple_missing_list = [m["name"] for m in missing_with_info]

    # 8. 法规清单（按基础法规名分组）
    checked_regs = _build_checked_regulations(must_check_rules + matched_optional)

    skipped_regs = []
    for r in skipped_optional:
        reg_name = r.get("regulation", "")
        contract_kws = r.get("trigger_keywords", [])
        skipped_regs.append({
            "regulation": reg_name,
            "reason": f"合同内容未涉及相关关键词：{'、'.join(contract_kws[:5])}",
        })

    # 9. 组装输出
    overall = determine_overall_compliance(all_findings + missing)

    output = {
        "findings": all_findings,
        "missing_clauses": simple_missing_list,
        "missing_clauses_detail": missing_with_info,
        "overall_compliance": overall,
        "checked_regulations": checked_regs,
        "skipped_regulations": skipped_regs,
    }

    # 10. 写入 compliance_report.json
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info("合规报告已写入: %s", output_path)
    logger.info("整体合规状态: %s | 发现 %d 条问题 | 缺失 %d 条必备条款",
                overall, len(all_findings), len(missing))
    logger.info("已检查法规: %d 条 | 已跳过法规: %d 条",
                len(checked_regs), len(skipped_regs))

    # 11. 合并到 risk_register
    if args.risk_register:
        update_risk_register(Path(args.risk_register), all_findings + missing)


if __name__ == "__main__":
    main()
