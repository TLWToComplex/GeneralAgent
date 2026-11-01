---
name: 合同审核
description: "合同审核：用户上传合同、协议、法律文件时触发。触发词：合同、协议、审核、审查、审阅、风险、合规、法律、条款、NDA、保密协议、劳动合同、采购合同、买卖合同、技术开发合同、保密、违约、知识产权、争议解决。"
license: Proprietary. LICENSE.txt has complete terms
---

# 合同审核技能

## 用途

对合同和法律协议进行结构化、风险感知的审查。识别关键条款，标记不利条款，评估合规性与财务风险，生成可操作的审查报告。

## 绝对执行顺序（不可跳过）

收到合同或法律文件后，必须严格按照以下顺序执行。不得直接跳到结论，不得输出不含风险评级的通用摘要。

0. **源理解** —— 确认上传文件类型，提取文本，识别合同类型（NDA、MSA、SLA、劳动合同、供应商协议、合伙协议等）。
1. **预处理（LLM）** —— 使用大语言模型将合同文本解析为结构化条款、元数据与实体，输出 `extracted_clauses.json`。
2. **合规检查** —— 依据中国法律法规（民法典、劳动合同法等）进行合规性审查，输出 `compliance_report.json`，并将发现合并到 `risk_register.json`。
3. **风险分析** —— 对每条条款进行法律与财务风险评分（高/中/低），输出 `risk_register.json`。
4. **修改建议生成** —— 基于风险与合规结果，生成具体可操作的修改建议及版本差异对比，输出 `suggestions.json`。
5. **报告生成** —— 将所有中间结果汇总为审查报告。**每次运行必须产出三份文件**：
   - **DOCX 结构化报告** — `python scripts/generate_docx_report.py --clauses ... --risks ... --compliance ... --suggestions ... --output 合同审核报告.docx --annotate 原始合同.docx`
   - **原始合同批注版** — 自动生成，文件名 = `合同审核报告（批注版）.docx`。在原始合同上插入 Word 批注、高亮、修订建议标记
   - **Markdown 报告** — 自动生成，文件名 = `合同审核报告.md`。纯文本版本，作为兜底查阅
有效运行必须产出：
	
```text
合同审核报告.docx          ← 结构化报告（封面→摘要→按条款审查→合规→建议→附录）
合同审核报告（批注版）.docx  ← 原始合同 + Word批注 + 修订建议
合同审核报告.md            ← Markdown 纯文本版
extracted_clauses.json
risk_register.json
compliance_report.json
suggestions.json
```

> **输出目录约定（务必遵守）**：
> - **最终报告** `合同审核报告.docx` 输出到 **workspace 根目录**（推荐）；`contract_review_report.md` 同样输出到根目录（Markdown 备选）。
> - **中间产物**（`extracted_clauses.json`、`risk_register.json`、`compliance_report.json`、`suggestions.json`）统一输出到 **`./contract review/`** 子文件夹下，路径中的空格必须用引号包裹，例如 `--output "./contract review/extracted_clauses.json"`。
> - 除上述指定的 `contract review/` 子文件夹外，禁止创建其他子文件夹（如 `output/`、`reports/` 等）。

如果合同缺少关键信息（如无适用法律条款），应在发现中明确标注。

---

## 必要输入

- **合同文件**（PDF、DOCX、TXT 或图片）。使用平台提取的文本内容。
- **上下文**（可选）：对方名称、交易金额、业务目的、谈判立场。

---

## 第一步：源理解

目标：将原始合同文本转换为结构化的 JSON，包含元数据、条款和实体。

执行：python scripts/extract_clauses.py --input 合同文件 --output "./contract review/extracted_clauses.json"

LLM System Prompt:你是一个专业的法律合同条款提取专家。你的任务是从合同文本中提取结构化条款信息，并严格按照以下 JSON Schema 输出（不要输出任何其他内容）。

输出 JSON 必须遵循以下结构：

{
  "metadata": {
    "filename": "文件名（由系统提供，无需推断）",
    "contract_type": "合同类型（如：买卖合同、劳动合同、租赁合同、NDA、MSA、SLA 等）",
    "parties": [
      { "entity_type": "party_a", "value": "甲方名称" },
      { "entity_type": "party_b", "value": "乙方名称" }
    ],
    "governing_law": "适用法律（如 'People's Republic of China'，若无则 null）",
    "jurisdiction": "管辖地（如 'Shanghai'，若无则 null）"
  },
  "clauses": [
    {
      "id": "1",                     // 自增编号，保持顺序
      "title": "条款标题",
      "text": "条款完整内容",
      "category": "payment",         // 必须为下方预定义类别之一
      "section_number": "第一条",    // 原始章节编号（如 "第一条"、"Article 1"、"1.1" 等），若无则 null
      "start_pos": 0,               // 在原始文本中的起始字符位置（可填 0）
      "end_pos": 450
    }
  ],
  "entities": [
    { "entity_type": "party_a", "value": "甲方公司", "location": "第一条" },
    { "entity_type": "amount",  "value": "人民币500,000元", "location": "第三条" },
    { "entity_type": "date",    "value": "2026年3月1日", "location": "第九条" },
    { "entity_type": "subject", "value": "软件开发服务", "location": "第二条" },
    { "entity_type": "duration", "value": "12个月", "location": "第五条" }
  ]
}

条款类别（category）必须从以下列表中选取其一：
- payment: 付款条款
- liability: 责任条款
- confidentiality: 保密条款
- termination: 终止/解除条款
- intellectual_property: 知识产权条款
- dispute_resolution: 争议解决条款
- force_majeure: 不可抗力条款
- warranty: 保证/担保条款
- indemnification: 赔偿条款
- governing_law: 适用法律条款
- other: 其他（无法归入上述类别时使用）

实体类型（entity_type）包括但不限于：
- party_a, party_b（若合同中有明确区分）
- amount（金额）
- date（日期）
- subject（标的物/服务内容）
- duration（期限）
- address（地址）
- governing_law（法律）
- jurisdiction（管辖地）

对于 entities 中的每个实体，请尽量提供 `location` 字段（例如，该实体出现在哪个条款或章节中），以方便后续追溯。

重要约束：
1. 所有条款必须按合同中的原始顺序排列。
2. 如果合同没有明确的章节编号，`section_number` 可填写序号或 null。
3. 必须将每条条款归入最合适的 category，若无法判断则使用 "other"。
4. 仅输出 JSON，不添加解释或注释。

---

## 第二步：合规检查（双轨制）

目标：依据中国法律法规及所内规章制度识别合规问题，提供风险等级、原因解释和法规出处。

执行：`python scripts/compliance_check.py --input "./contract review/extracted_clauses.json" --output "./contract review/compliance_report.json" --risk-register "./contract review/risk_register.json" [--llm]`

### 检查机制：双轨制

#### 必查法规（must_check）— 所有合同均须检查
- **《中华人民共和国民法典》合同编**：格式条款无效（第497条）、口头变更风险（第490条）、过高违约金（第585条）、合同必备条款（第470条）
- **《中华人民共和国劳动合同法》**（劳动合同适用）：试用期限制（第19条）、劳动者违约金限制（第22/25条）、竞业限制范围（第24条）
- **二十所/电科西北《合同管理办法》（所综〔2026〕231号）**：六项初审核查（第38条）、禁止以部门名义签约（第3条）、合同分类与文本要求（第6条）

#### 选查法规（optional_check）— 根据合同内容关键词自动匹配触发

| 行业法规 | 触发关键词（示例） |
|----------|-------------------|
| 《安全生产法》（2021年修订） | 工程、施工、建设、生产、安装、装修 |
| 《建筑法》（2019年修订） | 建设工程、土建、装修工程、总承包 |
| 《特种设备安全法》 | 电梯、锅炉、压力容器、起重机械 |
| 《食品安全法》 | 食品、餐饮、食堂、食材、供餐 |
| 《消防法》（2021年修订） | 消防、防火、灭火、消防设施、消防工程 |
| 《城市房地产管理法》 | 房屋租赁、场地租赁、厂房租赁、办公楼 |
| 《机动车维修管理规定》（2023年修订） | 机动车维修、汽车维修、车辆保养 |
| 《机动车运行安全技术条件》GB7258-2017 | 机动车辆、客车、货车、车辆采购 |
| 《非科研生产类工程及保障服务采购实施细则》（所后〔2026〕163号） | 后勤、物业、保洁、保安、绿化、维修 |

法规配置位于 `config/industry_regulations.json`，可随时扩展。

### 输出格式

每条合规发现包含：风险等级（高/中/低）、法规出处原文引用、违规原因解释、具体修改建议。

```json
{
  "findings": [
    {
      "clause_id": "1",
      "clause_title": "免责条款",
      "status": "non_compliant",
      "risk_level": "high",
      "category": "民法典",
      "regulation": "《中华人民共和国民法典》第497条",
      "rule_id": "civil_code_497",
      "issue": "提供格式条款一方不合理地免除或者减轻其责任...",
      "reason": "该条款声称'甲方不承担任何责任'，完全排除了甲方的基本责任义务...",
      "source": "依据《民法典》第497条第(二)项...",
      "recommendation": "建议修改为'甲方仅在因故意或重大过失造成损失时承担相应责任...'"
    }
  ],
  "missing_clauses": ["违约责任"],
  "missing_clauses_detail": [
    {
      "name": "违约责任",
      "risk_level": "high",
      "source": "《民法典》第470条、所内《合同管理办法》第38条",
      "reason": "合同缺少违约责任条款。违约责任是合同必备要素...",
      "recommendation": "建议添加违约责任相关条款..."
    }
  ],
  "overall_compliance": "non_compliant",
  "checked_regulations": [
    "《中华人民共和国民法典》",
    "所内《合同管理办法》（所综〔2026〕231号）",
    "《中华人民共和国安全生产法》（2021年修订）"
  ],
  "skipped_regulations": [
    {
      "regulation": "《中华人民共和国建筑法》",
      "reason": "合同内容未涉及相关关键词：建设工程、土建..."
    }
  ]
}
```

### 可选项：LLM 深度检查

使用 `--llm` 参数启用，需设置环境变量 `OPENAI_API_KEY`。LLM 会将匹配到的行业法规上下文注入 system prompt 进行深度语义合规分析。
---


## 第三步：风险分析

目标：采用 规则引擎 + 大语言模型（LLM）双引擎 架构，对每条条款进行法律和财务风险评分。

规则引擎：基于关键词快速扫描，识别确定性风险（如“无限责任”、“单方解除”、“自动续约”等），保证 100% 命中且无延迟。

LLM 深度分析：对每条条款进行语义理解，识别更隐蔽的风险（如知识产权归属模糊、管辖权不利、赔偿范围过宽等），并给出买卖双方的影响评估。

执行 scripts/analyze_risks.py（或直接使用 Agent 逻辑）读取 extracted_clauses.json，输出 risk_register.json。

你是一名资深的法律风险评估专家。你的任务是分析合同条款中的潜在风险。

请对每个条款进行风险评估，输出严格的JSON格式（不要输出其他内容）：

{
  "findings": [
    {
      "clause_id": "条款ID",
      "risk_level": "high/medium/low/none",
      "risk_type": "风险类型",
      "description": "风险描述",
      "buyer_impact": "对买方/甲方的影响",
      "seller_impact": "对卖方/乙方的影响",
      "rationale": "判断依据"
    }
  ],
  "overall_risk_level": "high/medium/low/none",
  "risk_summary": "风险总结（50字以内）"
}

常见风险类型包括：
- unlimited_liability: 无限责任
- unilateral_termination: 单方解除权
- unfair_penalty: 不合理违约金
- vague_terms: 模糊条款
- missing_protection: 缺少保护条款
- ip_risk: 知识产权风险
- payment_risk: 付款风险
- confidentiality_risk: 保密风险
- jurisdiction_risk: 管辖权风险
- auto_renewal_risk: 自动续约风险

风险等级判断标准：
- high: 可能导致重大经济损失或法律纠纷
- medium: 存在潜在风险，建议修改
- low: 轻微风险，建议关注
- none: 无明显风险

输出：`risk_register.json`，引用回条款 ID。

---
## 第四步：修改建议生成
目标：基于风险发现和合规问题，生成具体、可操作的修改建议，并提供条款级别的语义版本差异（diff）。

输入：extracted_clauses.json、risk_register.json、compliance_report.json
输出：suggestions.json（可选同时更新 risk_register.json 中的建议引用）
执行：python scripts/suggest_modifications.py \
    --input "./contract review/extracted_clauses.json" \
    --risks "./contract review/risk_register.json" \
    --compliance "./contract review/compliance_report.json" \
    --output "./contract review/suggestions.json" \
    --risk-register "./contract review/risk_register.json"

输出 JSON Schema:
{
  "suggestions": [
    {
      "clause_id": "1",
      "original_text": "甲方不承担任何责任",
      "suggested_text": "甲方仅在故意或重大过失情况下承担责任",
      "reason": "原条款可能构成格式条款无效情形（民法典第497条）",
      "priority": "high"
    }
  ],
  "version_diff": "--- 第一条 (原始)\n+++ 第一条 (建议)\n-甲方不承担任何责任\n+甲方仅在故意或重大过失情况下承担责任",
  "total_suggestions": 3
}

## 第五步：报告生成
目标：将所有中间结果汇总为一份综合性的、人类可读的 Markdown 报告。
执行 scripts/generate_report.py（或直接使用 LLM 生成）根据前述步骤产出的文件：

extracted_clauses.json

risk_register.json

compliance_report.json

suggestions.json（由修改建议步骤产生，如已实现）

生成一份人类可读的 contract_review_report.md 报告。
报告应包含以下章节：
1. 执行摘要
- 整体风险等级（高/中/低）
- 前三大风险点（按风险等级排序）
- 整体合规状态（合规/不合规/待审查）
2. 主要发现
- 列表形式展示高风险、中风险项，附带条款引用（章节编号和标题）
- 每个发现包含：风险类型、描述、对买卖双方的影响、建议
3. 合规缺口
- 列出缺失的必要条款（如“当事人信息”、“违约责任”等）
- 对不合规条款引用具体法规（如《民法典》第497条）并说明问题
4. 商业观察
- 付款条款、期限、责任限制、知识产权、保密等商业方面的专项评估
- 关注对己方不利的条款（如自动续约、单方解约）
5. 建议行动
- 按优先级（高/中/低）排序的修改建议
- 每条建议包含：条款ID、原始文本（或摘要）、建议修改文本、修改理由
6. 附录
- 完整风险登记表（risk_register.json 的内容表格化）
- 完整的合规检查结果（compliance_report.json 的内容表格化）

生成方式：
可使用 LLM 直接根据上述 JSON 数据生成 Markdown 报告，亦可将数据填充到预置模板（templates/review_report_template.md）中。若使用脚本，需确保脚本能读取所有中间 JSON 文件并合并内容。

最终输出：contract_review_report.md
---

## 输出产物

> 每次运行必须产出以下 **3 份用户可见报告 + 4 份中间 JSON**：

| 文件 | 类型 | 用途 |
|------|------|------|
| `合同审核报告.docx` | **强制** | 结构化 DOCX 审查报告（封面→按条款审查→合规→建议→附录），风险等级色标 |
| `合同审核报告（批注版）.docx` | **强制** | 原始合同 + Word 批注 + 高亮 + 修订建议标记（如合同非 DOCX 则跳过） |
| `合同审核报告.md` | **强制** | Markdown 纯文本报告，便于快速查阅和版本对比 |
| `extracted_clauses.json` | 中间 | 合同条款分段与元数据 |
| `risk_register.json` | 中间 | 逐条风险评分与说明 |
| `compliance_report.json` | 中间 | 合规发现与法规引用 |
| `suggestions.json` | 中间 | 修改建议与版本差异 |

---

## 质量检查（必须）

交付报告前请确认：

1. 每条高风险发现都有直接引用或条款引用。
2. 适用法律/管辖地已正确识别。
3. "缺失条款"发现是真实存在的（非 OCR/标题提取导致的假阴性）。
4. 建议具体、可操作且比例适当。
5. 如果输入是图片或扫描版 PDF，提醒用户 OCR 精度可能存在局限。

---

## 依赖

```bash
pip install python-docx PyPDF2 pdfplumber openpyxl markitdown
```

Optional:

```bash
pip install spacy zhconv  # for Chinese clause segmentation
```

---

## 目录结构

```
contract_skills/
├── SKILL.md
├── LICENSE.txt
├── README.md
├── config/
│   ├── risk_checklist.json
│   └── industry_regulations.json   ← 法规配置（必查+选查双轨制）
├── scripts/
│   ├── __init__.py
│   ├── extract_clauses.py
│   ├── analyze_risks.py
│   ├── compliance_check.py         ← 合规检查（双轨制）
│   ├── suggestion.py
│   ├── generate_report.py          ← MD 报告生成（兜底）
│   ├── generate_docx_report.py     ← DOCX 报告生成（推荐）
│   └── content_tracker.py          ← Word 批注/修订追踪
├── templates/
│   └── review_report_template.md
└── tests/
    └── sample_contracts/
```
