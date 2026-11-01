# Contract Review Skill

A structured contract and legal agreement review skill.

## Quick Start

1. Place the contract file in the working directory.
2. Run the pipeline:

```bash
# Step 1: Extract clauses
python scripts/extract_clauses.py --input contract.pdf --output "./contract review/extracted_clauses.json"

# Step 2: Compliance check (dual-track: must-check + optional industry regulations)
python scripts/compliance_check.py --input "./contract review/extracted_clauses.json" --output "./contract review/compliance_report.json" --risk-register "./contract review/risk_register.json"

# Step 3: Risk analysis
python scripts/analyze_risks.py --clauses "./contract review/extracted_clauses.json" --output "./contract review/risk_register.json"

# Step 4: Modification suggestions
python scripts/suggestion.py ...

# Step 5: Generate DOCX report (recommended)
python scripts/generate_docx_report.py \
    --clauses "./contract review/extracted_clauses.json" \
    --risks "./contract review/risk_register.json" \
    --compliance "./contract review/compliance_report.json" \
    --suggestions "./contract review/suggestions.json" \
    --output "./合同审核报告.docx" \
    --annotate "原始合同.docx"   # optional: generate annotated contract

# Or: Generate Markdown report (fallback)
python scripts/generate_report.py \
    --clauses "./contract review/extracted_clauses.json" \
    --risks "./contract review/risk_register.json" \
    --compliance "./contract review/compliance_report.json" \
    --suggestions "./contract review/suggestions.json" \
    --output "./contract_review_report.md"
```

3. Review the DOCX report (or `contract_review_report.md`).

## Features

- **Dual-track compliance check**: All contracts checked against Civil Code, Labor Contract Law, and internal regulations; industry-specific regulations (Safety Production Law, Construction Law, Fire Law, etc.) triggered by contract keywords
- **Risk level + source citation**: Every finding includes risk level (high/medium/low), regulation source, reason explanation, and specific recommendation — all in Chinese
- **DOCX report output**: Structured report with cover → summary → clause-by-clause review (ordered by contract) → compliance → suggestions → appendix. Risk levels marked with color badges.
- **Annotated contract** (optional): Original contract DOCX with Word comments, highlights, and revision suggestions

## Files

- `SKILL.md` — Skill definition and execution order.
- `config/risk_checklist.json` — Risk dimensions and scoring rules.
- `config/industry_regulations.json` — Dual-track regulation configuration (must-check + optional).
- `scripts/` — Core scripts for extraction, analysis, compliance, reporting, and DOCX generation.
- `templates/` — Report template.

## License

See `LICENSE.txt`.