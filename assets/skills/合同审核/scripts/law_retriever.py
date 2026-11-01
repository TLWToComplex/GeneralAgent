#!/usr/bin/env python3
"""
法典检索引擎 — 从 laws/ 文件夹加载法典文件，按合同内容检索相关条文。

用法：
    from law_retriever import LawRetriever

    retriever = LawRetriever(laws_dir="./laws", index_path="./config/law_index.json")

    # 检索必查法典的相关条文
    must_articles = retriever.retrieve_must_check(contract_text)

    # 检索选查法典的相关条文（自动按 trigger_keywords 激活）
    optional_articles = retriever.retrieve_optional_check(contract_text)

    # 组装 LLM 上下文
    context = retriever.build_llm_context(contract_text, max_tokens=3000)
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# 法典文件格式：以 "## 第XXX条" 为段落分隔符
ARTICLE_PATTERN = re.compile(r'^##\s*(第[^条]+条)\s*\n', re.MULTILINE)

# 中文停用词（检索时忽略）
STOP_WORDS = {
    "的", "了", "在", "是", "有", "和", "与", "或", "及", "等",
    "不", "也", "都", "就", "而", "但", "且", "若", "则",
    "其", "此", "该", "本", "以", "将", "已", "被", "所",
    "可以", "应当", "必须", "不得", "没有", "根据", "按照",
    "第一", "第二", "第三", "第四", "第五", "第六", "一", "二", "三",
    "对", "由", "为", "向", "从", "到", "于", "之",
}


class Article:
    """单条法律条文。"""

    def __init__(self, law_name: str, article_id: str, text: str):
        self.law_name = law_name      # 所属法律名称
        self.article_id = article_id  # 条文号，如 "第497条"
        self.text = text              # 条文全文
        self._tokens: Set[str] = set()  # 分词后的 token 集合（用于匹配）

    def tokenize(self) -> Set[str]:
        """简单分词：提取所有非停用词的中文词和数字。"""
        if self._tokens:
            return self._tokens

        # 提取中文字符序列（2字及以上）、数字、英文字母
        words = set()
        text = self.text

        # 中文词（2-4字级别）
        for length in [4, 3, 2]:
            for i in range(len(text) - length + 1):
                chunk = text[i:i + length]
                # 纯中文字符组成的 chunk
                if all('\u4e00' <= c <= '\u9fff' for c in chunk):
                    if chunk not in STOP_WORDS:
                        words.add(chunk)

        # 数字（金额、百分比）
        for match in re.finditer(r'[\d,.]+%?', text):
            words.add(match.group())

        self._tokens = words
        return words

    def relevance_score(self, query_tokens: Set[str]) -> int:
        """计算与查询的匹配度 = 交集 token 数。"""
        self_tokens = self.tokenize()
        return len(self_tokens & query_tokens)


class LawFile:
    """一部法典文件。"""

    def __init__(self, path: Path, display_name: str):
        self.path = path
        self.display_name = display_name
        self.articles: List[Article] = []
        self._loaded = False

    def load(self):
        """解析法典文件（支持 .txt / .docx / .pdf），按条文号切分。"""
        if self._loaded:
            return

        if not self.path.exists():
            logger.warning("法典文件不存在: %s", self.path)
            self._loaded = True
            return

        # 根据文件类型提取文本
        suffix = self.path.suffix.lower()
        if suffix == ".docx":
            text = self._extract_docx_text()
        elif suffix == ".pdf":
            text = self._extract_pdf_text()
        else:
            text = self.path.read_text(encoding="utf-8")

        if not text:
            logger.warning("法典文件提取文本为空: %s", self.path)
            self._loaded = True
            return

        # 按条文号切分
        self._parse_articles(text)

        # 如果 Markdown 格式切不出来（DOCX/PDF 通常没有 ## 标记），
        # 尝试备选方案：按 "第X条" 正则直接扫全文切分
        if len(self.articles) <= 2:
            logger.info("Markdown 解析仅获 %d 条，尝试备选正则切分", len(self.articles))
            self.articles.clear()
            self._parse_articles_fallback(text)

        self._loaded = True
        logger.info("加载法典 %s: %d 条文", self.display_name, len(self.articles))

    def _extract_docx_text(self) -> str:
        """从 .docx 文件提取纯文本。"""
        try:
            from docx import Document
        except ImportError:
            logger.error("python-docx 未安装，无法读取 .docx: %s", self.path)
            return ""
        doc = Document(str(self.path))
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
        return "\n".join(paragraphs)

    def _extract_pdf_text(self) -> str:
        """从 .pdf 文件提取纯文本。"""
        try:
            import pdfplumber
        except ImportError:
            logger.error("pdfplumber 未安装，无法读取 .pdf: %s", self.path)
            return ""
        parts = []
        with pdfplumber.open(str(self.path)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    parts.append(page_text)
        return "\n".join(parts)

    def _parse_articles(self, text: str):
        """Markdown 格式切分：按 '## 第X条' 切分。"""
        parts = re.split(r'\n(?=##\s*第)', text)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            match = re.match(r'##\s*(第[^条]+条)\s*\n', part)
            if match:
                article_id = match.group(1).strip()
                article_text = part[match.end():].strip()
            else:
                if part.startswith("# ") and "##" not in part:
                    continue
                article_id = ""
                article_text = part
            if article_text:
                self.articles.append(Article(
                    law_name=self.display_name,
                    article_id=article_id,
                    text=article_text,
                ))

    def _parse_articles_fallback(self, text: str):
        """
        备选方案：按 '第X条' 正则直接在全文匹配切分。
        适用于无 Markdown 标记的 DOCX/PDF 法规原文。
        
        匹配模式：第XXX条（中文数字或阿拉伯数字）
        """
        # 清理前置内容（法律名称、目录等），找到第一个 "第X条"
        first = re.search(r'(第[一二三四五六七八九十百千\d]+条)', text)
        if not first:
            return
        body = text[first.start():]

        # 按 "第X条" 切分（保留分隔符）
        parts = re.split(r'(?=第[一二三四五六七八九十百千\d]+条)', body)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            match = re.match(r'(第[一二三四五六七八九十百千\d]+条)(.*)', part, re.DOTALL)
            if match:
                article_id = match.group(1).strip()
                article_text = match.group(2).strip()
                if article_text:
                    self.articles.append(Article(
                        law_name=self.display_name,
                        article_id=article_id,
                        text=article_text,
                    ))

    def retrieve(self, query_tokens: Set[str], top_k: int = 15) -> List[Article]:
        """检索 Top-K 最相关的条文。"""
        self.load()
        if not self.articles:
            return []

        scored = [(a, a.relevance_score(query_tokens)) for a in self.articles]
        # 按相关度降序排列
        scored.sort(key=lambda x: x[1], reverse=True)
        # 取 Top-K（至少 relevance_score > 0）
        return [a for a, score in scored if score > 0][:top_k]


class LawRetriever:
    """
    法典检索引擎。

    工作流程：
    1. 优先加载 laws/pre_parsed.json（上传前已预解析，毫秒级）
    2. 如不存在，回退到逐文件懒加载（首次较慢，建议先运行 pre_parse_laws.py）
    3. 从合同文本提取查询关键词（分词）
    4. 对必查法典 → 全部检索
    5. 对选查法典 → 先匹配 trigger_keywords 激活，再检索
    6. 返回相关条文列表
    """

    def __init__(self, laws_dir: str = "./laws", index_path: str = "./config/law_index.json"):
        self.laws_dir = Path(laws_dir)
        self.index = self._load_index(index_path)
        self._law_files: Dict[str, LawFile] = {}
        self._pre_parsed: Optional[Dict] = None
        self._load_pre_parsed()

    def _load_pre_parsed(self):
        """尝试加载预解析 JSON，如果存在则直接使用，跳过逐个文件解析。"""
        pre_path = self.laws_dir / "pre_parsed.json"
        if pre_path.exists():
            try:
                with open(pre_path, "r", encoding="utf-8") as f:
                    self._pre_parsed = json.load(f)
                logger.info("已加载预解析法典: %d 部法律, %d 条文 (预解析于 %s)",
                            self._pre_parsed.get("total_laws", 0),
                            self._pre_parsed.get("total_articles", 0),
                            self._pre_parsed.get("parsed_at", "未知"))
            except Exception as e:
                logger.warning("预解析 JSON 加载失败: %s，回退到逐文件解析", e)
                self._pre_parsed = None
        else:
            logger.info("未找到 pre_parsed.json，使用逐文件解析（建议运行 python scripts/pre_parse_laws.py 生成预解析文件以加速）")

    def _load_index(self, index_path: str) -> Dict:
        path = Path(index_path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        logger.warning("law_index.json 不存在: %s，使用空索引", index_path)
        return {"must_check": [], "optional_check": []}

    def _get_law(self, filename: str, display_name: str, folder: str) -> LawFile:
        """懒加载法典文件。"""
        key = f"{folder}/{filename}"
        if key not in self._law_files:
            self._law_files[key] = LawFile(
                path=self.laws_dir / folder / filename,
                display_name=display_name,
            )
        return self._law_files[key]

    @staticmethod
    def extract_query_tokens(text: str) -> Set[str]:
        """从合同文本中提取查询关键词。"""
        tokens = set()
        # 中文词（2-4字级别）
        for length in [4, 3, 2]:
            for i in range(len(text) - length + 1):
                chunk = text[i:i + length]
                if all('\u4e00' <= c <= '\u9fff' for c in chunk):
                    if chunk not in STOP_WORDS:
                        tokens.add(chunk)
        # 提取关键实体：金额、百分比、日期
        for match in re.finditer(r'[\d,.]+[元万元%‰]', text):
            tokens.add(match.group())
        return tokens

    def _retrieve_from_pre_parsed(self, folder: str, query_tokens: Set[str], top_k: int) -> List[Dict]:
        """从预解析 JSON 中检索条文。"""
        results = []
        for law in self._pre_parsed.get("laws", []):
            if law.get("source") != folder:
                continue
            articles = law.get("articles", [])
            if not articles:
                continue

            # 为每条条文计算与查询的相关度
            scored = []
            for a in articles:
                art = Article(
                    law_name=law["law_name"],
                    article_id=a.get("id", ""),
                    text=a.get("text", ""),
                )
                score = art.relevance_score(query_tokens)
                if score > 0:
                    scored.append((art, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            top = scored[:top_k]
            if top:
                results.append({
                    "law_name": law["law_name"],
                    "source": folder,
                    "articles": [
                        {"id": a[0].article_id, "text": a[0].text}
                        for a in top
                    ],
                })
        return results

    def retrieve_must_check(self, contract_text: str, top_k_per_law: int = 15) -> List[Dict]:
        """
        检索所有必查法典。
        """
        query_tokens = self.extract_query_tokens(contract_text)

        # 优先使用预解析数据
        if self._pre_parsed:
            return self._retrieve_from_pre_parsed("必查", query_tokens, top_k_per_law)

        # 回退：逐文件加载
        results = []
        for law_config in self.index.get("must_check", []):
            law = self._get_law(law_config["file"], law_config["display_name"], "必查")
            articles = law.retrieve(query_tokens, top_k=top_k_per_law)
            if articles:
                results.append({
                    "law_name": law.display_name,
                    "source": "必查",
                    "articles": [
                        {"id": a.article_id, "text": a.text}
                        for a in articles
                    ],
                })
        return results

    def retrieve_optional_check(self, contract_text: str, top_k_per_law: int = 10) -> List[Dict]:
        """
        按合同关键词激活并检索选查法典。
        """
        query_tokens = self.extract_query_tokens(contract_text)
        results = []
        activated = []
        skipped = []

        for law_config in self.index.get("optional_check", []):
            triggers = law_config.get("trigger_keywords", [])
            if not triggers:
                activated.append(law_config)
                continue
            if any(kw in contract_text for kw in triggers):
                activated.append(law_config)
            else:
                skipped.append(law_config)

        logger.info("选查法典: 激活 %d 部, 跳过 %d 部", len(activated), len(skipped))

        # 优先使用预解析数据
        if self._pre_parsed:
            activated_names = {c["display_name"] for c in activated}
            for law in self._pre_parsed.get("laws", []):
                if law.get("source") != "选查":
                    continue
                if law["law_name"] not in activated_names:
                    continue
                articles = law.get("articles", [])
                if not articles:
                    continue

                scored = []
                for a in articles:
                    art = Article(law_name=law["law_name"], article_id=a.get("id", ""), text=a.get("text", ""))
                    score = art.relevance_score(query_tokens)
                    if score > 0:
                        scored.append((art, score))

                scored.sort(key=lambda x: x[1], reverse=True)
                top = scored[:top_k_per_law]
                if top:
                    results.append({
                        "law_name": law["law_name"],
                        "source": "选查",
                        "articles": [{"id": a[0].article_id, "text": a[0].text} for a in top],
                    })
        else:
            # 回退：逐文件加载
            for law_config in activated:
                law = self._get_law(law_config["file"], law_config["display_name"], "选查")
                articles = law.retrieve(query_tokens, top_k=top_k_per_law)
                if articles:
                    results.append({
                        "law_name": law.display_name,
                        "source": "选查",
                        "articles": [{"id": a.article_id, "text": a.text} for a in articles],
                    })

        self._last_skipped = [
            {"regulation": c["display_name"],
             "reason": f"未触发关键词: {'、'.join(c.get('trigger_keywords', [])[:5])}"}
            for c in skipped
        ]

        return results

    def get_skipped_info(self) -> List[Dict]:
        """获取最近一次检索中被跳过的法规信息。"""
        return getattr(self, '_last_skipped', [])

    def build_llm_context(self, contract_text: str, max_tokens: int = 3000) -> str:
        """
        一站式：检索必查+选查法典 → 组装为 LLM system prompt 可注入的上下文字符串。

        Args:
            contract_text: 合同全文
            max_tokens: 最大 token 数（中文字符约 = token 数 × 1.5）

        Returns:
            格式化的法规上下文字符串
        """
        must = self.retrieve_must_check(contract_text)
        optional = self.retrieve_optional_check(contract_text)

        lines = []
        char_count = 0
        char_limit = max_tokens * 3  # 粗略估计 1 token ≈ 3 中文字符

        for group in must + optional:
            law_name = group["law_name"]
            articles = group["articles"]
            if not articles:
                continue

            lines.append(f"\n### {law_name}")
            for a in articles:
                article_block = f"\n**{a['id']}**\n{a['text']}"
                if char_count + len(article_block) > char_limit:
                    lines.append("\n（后续条文因长度限制已截断）")
                    break
                lines.append(article_block)
                char_count += len(article_block)

        return "\n".join(lines).strip()


# ============================================================
# 便捷函数：直接为 compliance_check.py 提供数据
# ============================================================

def retrieve_for_llm(
    contract_text: str,
    laws_dir: str = "./laws",
    index_path: str = "./config/law_index.json",
    max_tokens: int = 3000,
) -> Dict:
    """
    为 LLM 合规检查检索相关法典条文。

    Returns:
        {
            "context": "...",           # LLM 可注入的上下文字符串
            "checked": [...],           # 已检查的法规列表
            "skipped": [...],           # 跳过的法规列表
        }
    """
    retriever = LawRetriever(laws_dir=laws_dir, index_path=index_path)

    must = retriever.retrieve_must_check(contract_text)
    optional = retriever.retrieve_optional_check(contract_text)

    # 已检查法规
    checked = []
    for g in must + optional:
        articles_count = len(g.get("articles", []))
        if articles_count > 0:
            article_ids = [a["id"] for a in g["articles"]]
            checked.append({
                "regulation": g["law_name"],
                "articles": article_ids,
            })

    # 上下文
    context = retriever.build_llm_context(contract_text, max_tokens=max_tokens)

    return {
        "context": context,
        "checked": checked,
        "skipped": retriever.get_skipped_info(),
    }