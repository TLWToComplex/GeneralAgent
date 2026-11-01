"""
Extract clauses and metadata from a contract file.

Usage:
    python scripts/extract_clauses.py --input contract.pdf --output extracted_clauses.json
"""

import argparse
import json
import re
from pathlib import Path


def extract_text_from_pdf(path: str) -> str:
    """Extract text from a PDF file."""
    try:
        import pdfplumber
    except ImportError as exc:
        raise ImportError("pdfplumber is required to read PDF files") from exc

    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_docx(path: str) -> str:
    """Extract text from a DOCX file."""
    try:
        from docx import Document
    except ImportError as exc:
        raise ImportError("python-docx is required to read DOCX files") from exc

    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text_from_txt(path: str) -> str:
    """Extract text from a plain text file."""
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def extract_text(path: str) -> str:
    """Dispatch extraction based on file extension."""
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        return extract_text_from_pdf(path)
    if p.suffix.lower() == ".docx":
        return extract_text_from_docx(path)
    if p.suffix.lower() == ".txt":
        return extract_text_from_txt(path)
    raise ValueError(f"Unsupported file type: {p.suffix}")


def detect_contract_type(text: str) -> str:
    """Detect contract type from keywords in the text."""
    text_lower = text.lower()
    keywords = [
        ("NDA", ["non-disclosure", "confidentiality agreement", "保密协议"]),
        ("MSA", ["master service agreement", "msa", "主服务协议"]),
        ("SLA", ["service level agreement", "sla", "服务等级协议"]),
        ("Employment", ["employment agreement", "offer letter", "劳动合同"]),
        ("Vendor", ["vendor agreement", "supplier agreement", "采购合同"]),
        ("Partnership", ["partnership agreement", "joint venture", "合作协议"]),
        ("Sales", ["sales contract", "买卖合同", "购销合同"]),
    ]
    for contract_type, terms in keywords:
        if any(term in text_lower for term in terms):
            return contract_type
    return "Unknown"


def parse_raw_text_to_sections(text: str) -> list[dict]:
    """
    将原始合同文本按章节切分。
    识别常见的中文合同章节格式：
      - 第一条、第二条...
      - 一、二、三...
      - 1. 2. 3. / 1、2、3
      - 第1条 / 第2条
    """
    patterns = [
        r"(第[一二三四五六七八九十百]+条\s*.+)",
        r"(第\d+条\s*.+)",
        r"([一二三四五六七八九十]+、\s*.+)",
        r"(\d+[\.、]\s*.+)",
    ]

    combined = "|".join(patterns)
    sections: list[dict] = []
    last_pos = 0
    last_title = "前言"

    for match in re.finditer(combined, text):
        content = text[last_pos:match.start()].strip()
        if content:
            sections.append({"title": last_title, "content": content})

        last_title = match.group(0).strip()
        last_pos = match.end()

    remaining = text[last_pos:].strip()
    if remaining:
        sections.append({"title": last_title, "content": remaining})

    if not sections and text.strip():
        sections.append({"title": "全文", "content": text.strip()})

    return sections


def segment_clauses(text: str) -> list[dict]:
    """Segment contract text into clauses based on common heading patterns."""
    # First try Chinese-style section patterns
    sections = parse_raw_text_to_sections(text)
    if len(sections) > 1 or (len(sections) == 1 and sections[0]["title"] != "全文"):
        clauses = []
        for i, sec in enumerate(sections, start=1):
            clauses.append({
                "id": str(i),
                "title": sec["title"],
                "text": sec["content"],
                "start_pos": 0,
                "end_pos": 0,
            })
        return clauses

    # Fallback: English-style heading patterns
    pattern = re.compile(
        r"(?:^|\n)\s*(?:(?:Article|Section|Clause)\s*\d+[\.\:]?|\d+[\.\)]\s+[A-Z][^\n]{0,80})\s*\n",
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(text))

    clauses = []
    if not matches:
        return [{"id": "1", "title": "Full Text", "text": text.strip(), "start_pos": 0, "end_pos": len(text)}]

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        clause_text = text[start:end].strip()
        title = match.group(0).strip()
        clauses.append({
            "id": str(i + 1),
            "title": title,
            "text": clause_text,
            "start_pos": start,
            "end_pos": end,
        })
    return clauses


def extract_entities(text: str) -> list[dict]:
    """Extract common contract entities from the text."""
    entities: list[dict] = []

    # Party A / Party B (Chinese)
    party_patterns = [
        (r"甲方[：:]\s*([^\n]{2,40})", "party_a"),
        (r"乙方[：:]\s*([^\n]{2,40})", "party_b"),
        (r"买方[：:]\s*([^\n]{2,40})", "party_a"),
        (r"卖方[：:]\s*([^\n]{2,40})", "party_b"),
        (r"买方[:：]\s*([^\n]{2,40})", "party_a"),
        (r"卖方[:：]\s*([^\n]{2,40})", "party_b"),
    ]

    for pattern, entity_type in party_patterns:
        for match in re.finditer(pattern, text):
            value = match.group(1).strip()
            # Clean trailing punctuation
            value = re.sub(r"[，。；,;]\s*$", "", value)
            if value and not any(e["value"] == value for e in entities if e["entity_type"] == entity_type):
                entities.append({"entity_type": entity_type, "value": value})

    # Amounts
    amount_patterns = [
        r"(人民币\s*[\d,]+\s*(?:元|万元))?",
        r"([\d,]+\s*(?:元|美元|USD|RMB|CNY))",
    ]
    for pattern in amount_patterns:
        for match in re.finditer(pattern, text):
            value = match.group(0).strip()
            if value and not any(e["value"] == value for e in entities if e["entity_type"] == "amount"):
                entities.append({"entity_type": "amount", "value": value})

    # Dates
    date_patterns = [
        r"(\d{4}年\d{1,2}月\d{1,2}日)",
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{4}/\d{2}/\d{2})",
    ]
    for pattern in date_patterns:
        for match in re.finditer(pattern, text):
            value = match.group(0).strip()
            if value and not any(e["value"] == value for e in entities if e["entity_type"] == "date"):
                entities.append({"entity_type": "date", "value": value})

    return entities


def main():
    parser = argparse.ArgumentParser(description="Extract clauses and entities from a contract file.")
    parser.add_argument("--input", required=True, help="Path to contract file (pdf/docx/txt).")
    parser.add_argument("--output", required=True, help="Path to output JSON file.")
    args = parser.parse_args()

    text = extract_text(args.input)
    clauses = segment_clauses(text)
    contract_type = detect_contract_type(text)
    entities = extract_entities(text)

    output = {
        "metadata": {
            "filename": Path(args.input).name,
            "contract_type": contract_type,
            "parties": entities,
            "governing_law": None,
            "jurisdiction": None,
        },
        "clauses": clauses,
        "entities": entities,
    }

    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Extracted {len(clauses)} clauses and {len(entities)} entities to {args.output}")


if __name__ == "__main__":
    main()
