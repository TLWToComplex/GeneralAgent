#!/usr/bin/env python3
"""
法典预解析脚本 — 一次性运行：将 laws/ 文件夹中所有法典文件（txt/docx/pdf）解析为
laws/pre_parsed.json，供运行时直接加载，消除每次调用的重复解析开销。

用法：
    python scripts/pre_parse_laws.py [--laws-dir ./laws] [--index ./config/law_index.json]

输出：
    laws/pre_parsed.json — 包含所有法典的全部条文，按 law_name 分组
"""

import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ARTICLE_RE = re.compile(r'第[一二三四五六七八九十百千\d]+条')


def extract_docx_text(path: str) -> str:
    """从 .docx 提取文本。"""
    try:
        from docx import Document
    except ImportError:
        logger.error("python-docx 未安装")
        return ""
    doc = Document(path)
    return "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())


def extract_pdf_text(path: str) -> str:
    """从 .pdf 提取文本（优先 pdftotext，其次 pdfplumber）。"""
    # 方案1: pdftotext（速度快，通常已安装）
    try:
        result = subprocess.run(
            ["pdftotext", "-enc", "UTF-8", path, "-"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and len(result.stdout.strip()) > 100:
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # 方案2: pdfplumber
    try:
        import pdfplumber
        parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    parts.append(text)
        return "\n".join(parts)
    except ImportError:
        logger.error("pdfplumber 未安装，且 pdftotext 不可用")
        return ""
    except Exception as e:
        logger.error("pdfplumber 解析失败: %s", e)
        return ""


def extract_text(path: str) -> str:
    """根据文件后缀提取文本。"""
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(path)
    elif suffix == ".docx":
        return extract_docx_text(path)
    else:
        return Path(path).read_text(encoding="utf-8", errors="ignore")


def parse_articles(text: str) -> List[Dict]:
    """
    从文本中拆分条文。先尝试 Markdown 格式（## 第X条），
    失败则回退到正则直接扫 "第X条"。
    """
    articles = []

    # 第一阶段：Markdown 格式
    parts = re.split(r'\n(?=##\s*第)', text)
    if len(parts) > 2:
        for part in parts:
            part = part.strip()
            if not part:
                continue
            m = re.match(r'##\s*(第[^条]+条)\s*\n', part)
            if m:
                aid = m.group(1).strip()
                atext = part[m.end():].strip()
            else:
                if part.startswith("# ") and "##" not in part:
                    continue
                aid = ""
                atext = part
            if atext and len(atext) > 5:
                articles.append({"id": aid, "text": atext})

    # 第二阶段：正则回退
    if len(articles) <= 2:
        articles.clear()
        first = re.search(r'(第[一二三四五六七八九十百千\d]+条)', text)
        if first:
            body = text[first.start():]
            parts = re.split(r'(?=第[一二三四五六七八九十百千\d]+条)', body)
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                m = re.match(r'(第[一二三四五六七八九十百千\d]+条)(.*)', part, re.DOTALL)
                if m:
                    aid = m.group(1).strip()
                    atext = m.group(2).strip()
                    if atext and len(atext) > 5:
                        articles.append({"id": aid, "text": atext})

    return articles


def pre_parse_all(laws_dir: str = "./laws", index_path: str = "./config/law_index.json") -> Dict:
    """
    解析 laws/ 下所有法典，输出结构化 JSON。
    """
    laws_dir = Path(laws_dir)
    index = {}
    index_file = Path(index_path)
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            index = json.load(f)

    all_laws = []
    total_articles = 0
    failed = []

    for category, folder in [("must_check", "必查"), ("optional_check", "选查")]:
        for law_config in index.get(category, []):
            filename = law_config.get("file", "")
            display_name = law_config.get("display_name", filename)
            file_path = laws_dir / folder / filename

            if not file_path.exists():
                logger.warning("文件不存在: %s", file_path)
                failed.append({"file": filename, "error": "文件不存在"})
                continue

            logger.info("解析: %s (%s)", display_name, filename)

            text = extract_text(str(file_path))
            if not text or len(text.strip()) < 50:
                logger.warning("提取文本为空或过短: %s (%d 字节)", filename, len(text) if text else 0)
                failed.append({"file": filename, "error": "文本提取失败或内容过短"})
                continue

            articles = parse_articles(text)

            if articles:
                all_laws.append({
                    "law_name": display_name,
                    "source": folder,
                    "file": filename,
                    "article_count": len(articles),
                    "articles": articles,
                })
                total_articles += len(articles)
                logger.info("  → %d 条文", len(articles))
            else:
                logger.warning("  → 未能解析出条文")
                failed.append({"file": filename, "error": "未能解析出条文"})

    result = {
        "version": "1.0.0",
        "parsed_at": subprocess.run(
            ["date", "+%Y-%m-%dT%H:%M:%S"], capture_output=True, text=True
        ).stdout.strip(),
        "total_laws": len(all_laws),
        "total_articles": total_articles,
        "laws": all_laws,
        "failed": failed,
    }

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="预解析 laws/ 文件夹中所有法典")
    parser.add_argument("--laws-dir", default="./laws", help="法典文件夹路径")
    parser.add_argument("--index", default="./config/law_index.json", help="law_index.json 路径")
    parser.add_argument("--output", default=None, help="输出路径（默认 laws/pre_parsed.json）")
    args = parser.parse_args()

    output_path = args.output or str(Path(args.laws_dir) / "pre_parsed.json")

    logger.info("开始预解析...")
    result = pre_parse_all(laws_dir=args.laws_dir, index_path=args.index)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info("预解析完成: %d 部法律, %d 条文 → %s",
                result["total_laws"], result["total_articles"], output_path)

    if result["failed"]:
        logger.warning("以下文件解析失败:")
        for f in result["failed"]:
            logger.warning("  - %s: %s", f["file"], f["error"])

    return 0 if not result["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())