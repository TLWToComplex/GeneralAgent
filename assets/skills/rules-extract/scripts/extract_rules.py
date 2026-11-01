#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rules-extract: 制度文件结构化摘要工具

支持从文本、本地文件或网页 URL 读取制度内容，
调用大模型按「制度名称、核心目标、责任主体、关键执行步骤、关键阈值、
禁止事项、关键词」等维度生成表格化摘要。

若未配置大模型 API，则回退到本地规则提取。
"""

import os
import re
import sys
import json
import argparse
from collections import Counter

import urllib.request
import urllib.parse

# docx 用于导出 Word
try:
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:  # pragma: no cover
    DOCX_AVAILABLE = False

# 兼容 Windows 控制台输出中文
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    requests = None  # type: ignore
    BeautifulSoup = None  # type: ignore

# ---------------------------------------------------------------------------
# 停用词
# ---------------------------------------------------------------------------
STOPWORDS = {
    '的', '了', '和', '是', '在', '我', '有', '也', '都', '就', '要', '会',
    '可以', '这个', '这样', '非常', '因为', '所以', '但是', '而且', '规定',
    '制度', '办法', '细则', '章程', 'the', 'and', 'of', 'to', 'a', 'is', 'in',
    'for', 'on', 'with'
}

# 常见部门/角色词库
COMMON_PARTIES = [
    '人力资源部', '财务部', '行政部', '法务部', '董事会', '总经理', '各部门',
    '项目负责人', '直接上级', '纪检监察部', '安全管理部门', '信息中心',
    '员工', '公司', '部门负责人', '本部门', '财务资产部', '下属公司',
    '资金经办部门', '纪检部门', '纪监审计部', '审计委员会', '风险管理部',
    '合规部', '经营管理部', '办公室', '二级单位', '业务部门'
]

# 关键词库（领域短语在前，保证优先命中）
COMMON_KEYWORDS = [
    '资金归集', '银行账户', '资金计划', '融资担保', '票据池', '三重一大',
    '银企对账', '司库管理', '司库系统', '风险防控', '资金风险', '责任追究',
    '监督考核', '账户开立', '资金集中', '债务融资', '商业汇票', '应收款项',
    '应收款项清收', '资金结算', '内控监督', '清收', '分级监管', '归口管理',
    '合规性', '协同性', '效益性', '安全性',
    '考勤', '请假', '迟到', '早退', '旷工', '加班', '调休', '出差',
    '报销', '审批', '审核', '备案', '申请', '提交', '员工', '公司',
    '部门', '负责人', '管理', '制度', '规定', '绩效', '考核',
    '合同', '劳动', '解除', '终止', '保密', '竞业', '福利',
    '培训', '晋升', '薪酬', '打卡', '资金', '账户', '担保', '归集',
    '财务', '预算', '收支', '票据', '融资', '投资'
]

# ---------------------------------------------------------------------------
# 公共工具函数
# ---------------------------------------------------------------------------
def normalize_text(text: str) -> str:
    """归一化 PDF/网页 提取的文本：合并被换行打断的句子。"""
    lines = [line.rstrip() for line in text.splitlines()]
    merged = []
    for line in lines:
        if not line:
            continue
        if not merged:
            merged.append(line)
            continue
        last = merged[-1]
        if (last and not re.search(r'[。！？.!?；;]$', last)
                and re.match(r'[\u4e00-\u9fa5]', line[0])):
            merged[-1] = last + line
        else:
            merged.append(line)
    text = '\n'.join(merged)
    text = re.sub(r' +', ' ', text)
    return text


def clean_text(text: str) -> str:
    """预处理文本：去除 markdown 标记、章节编号、页码残片等噪音"""
    text = normalize_text(text)
    text = re.sub(r'\*\*', '', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'^[—\-–－\s]*\d{1,3}\s*[—\-–－]\s*$', '', text, flags=re.MULTILINE)  # 独立页码行（如"—7—"）
    text = re.sub(r'第[一二三四五六七八九十百千万]+章', '', text)
    text = re.sub(r'第[一二三四五六七八九十百千万]+条', '', text)
    text = re.sub(r'^\d+\.\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\|?[-:| ]+\|?$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{2,}', '\n', text)
    return text


def split_sentences(text: str) -> list:
    """按中文/英文标点分句，优先按行分割避免标题与正文合并"""
    lines = [line.strip() for line in re.split(r'[\n\r]+', text) if line.strip()]
    sentences = []
    for line in lines:
        parts = re.findall(r'([^。！？.!?]+[。！？.!?]*)', line)
        if parts:
            for s in parts:
                s = s.strip()
                if s:
                    sentences.append(s)
        else:
            sentences.append(line)
    return sentences


def safe_shorten(value: str, max_len: int = 200) -> str:
    """安全截断"""
    if not value:
        return value
    return value if len(value) <= max_len else value[:max_len] + '...'


# ---------------------------------------------------------------------------
# 内容获取
# ---------------------------------------------------------------------------
def get_file_content(file_path: str) -> str:
    """读取本地文件内容"""
    if not os.path.exists(file_path):
        print(f"[错误] 文件不存在: {file_path}", file=sys.stderr)
        sys.exit(1)

    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext in ['.txt', '.md', '.py', '.js', '.java', '.cpp', '.c', '.html', '.css', '.json']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        elif ext == '.docx':
            try:
                import docx
                doc = docx.Document(file_path)
                return '\n'.join([p.text for p in doc.paragraphs])
            except ImportError:
                print("[提示] 读取 docx 需要安装 python-docx: pip install python-docx", file=sys.stderr)
                sys.exit(1)
        elif ext == '.pdf':
            try:
                import pdfplumber
                text = ''
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + '\n'
                return text
            except ImportError:
                print("[提示] 读取 pdf 需要安装 pdfplumber: pip install pdfplumber", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"[错误] 不支持的文件格式: {ext}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"[错误] 读取文件失败: {e}", file=sys.stderr)
        sys.exit(1)


def get_url_content(url: str) -> str:
    """抓取网页正文内容"""
    if requests is None or BeautifulSoup is None:
        print("[错误] 抓取网页需要安装: pip install requests beautifulsoup4", file=sys.stderr)
        sys.exit(1)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=30)
        resp.encoding = resp.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'aside', 'header']):
            tag.decompose()
        text = soup.get_text(separator='\n', strip=True)
        text = re.sub(r'\n+', '\n', text)
        return text
    except Exception as e:
        print(f"[错误] 抓取网页失败: {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# 大模型调用
# ---------------------------------------------------------------------------
def load_config() -> dict:
    """加载配置文件"""
    config = {
        'api_key': os.environ.get('RULES_EXTRACT_API_KEY', ''),
        'base_url': os.environ.get('RULES_EXTRACT_BASE_URL', ''),
        'model': os.environ.get('RULES_EXTRACT_MODEL', ''),
    }
    config_path = os.path.expanduser('~/.rules-extract/config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config.update(json.load(f))
        except Exception:
            pass
    return config


def build_prompt(text: str, length: str = 'medium', keywords_count: int = 10) -> str:
    """构建给大模型的提取 Prompt（含长度配额与提取纪律）"""
    quota = {
        'short': (3, 5, 3),
        'medium': (8, 12, 10),
        'long': (16, 20, 14),
    }.get(length, (8, 12, 10))
    steps_n, thresh_n, forbid_n = quota
    return f"""你是一位专业的制度文件分析助手。请通读下面的制度文件全文，按七个维度逐一提取结构化信息，只输出 JSON（不要任何解释文字）。

JSON 结构：
{{
  "制度名称": "…",
  "核心目标": "…",
  "责任主体": ["…", "…"],
  "关键执行步骤": [{{"title": "…", "content": "…"}}],
  "关键阈值": [{{"title": "…", "content": "…"}}],
  "禁止事项": [{{"title": "…", "content": "…"}}],
  "关键词": ["…", "…"]
}}

提取纪律（违反视为不合格）：
1. 制度名称：原文件正式全称——发文主体 + 名称 + 文号（如"所财〔2026〕229号"）+ 印发/施行日期 + "自印发之日起执行"类施行表述，原文有的都要保留，不超过 110 字。
2. 核心目标：目的句（"为…""旨在…"）+ 制定依据（"依据…制定"）+ 原则句（"坚持/遵循…原则"）+ 适用范围（"适用于…"），1-4 句、合计不超过 200 字。
3. 责任主体：不超过 10 个，每个写成"名称：职责"（职责取自原文、尽量完整，每条不超过 300 字）。
4. 关键执行步骤：不超过 {steps_n} 条；title 不超过 12 字；content 为 1-4 句、不超过 300 字，把原文条款的关键细节（原则、范围、时限、审批层级等）都保留下来，不要过度压缩。
5. 关键阈值：不超过 {thresh_n} 条；content 写"数值+单位+适用事项语境"（如"总担保规模不得超过合并净资产的 40%"），不超过 100 字。
6. 禁止事项：不超过 {forbid_n} 条；同一句里出现多个"严禁/不得/禁止"时**逐项拆成独立的条目**，每条只含一个禁令动词及其完整表述，不超过 120 字。
7. 关键词：恰好 {keywords_count} 个 2-8 字的专业词语或名词短语（如"资金归集""银行账户管理"），不用动词、不用句子。
8. 全部内容必须出自原文，不得编造、扩写或改动任何数字；意思相近的条目合并为一条。
9. 某个维度在原文确无信息时，字符串维度填"未明确提取"；列表维度填 [{{"title": "未明确提取", "content": "未明确提取"}}]。

制度文件全文：
{text}
"""


def call_llm(prompt: str, config: dict) -> dict:
    """调用大模型 API，返回解析后的 JSON"""
    api_key = config.get('api_key')
    base_url = config.get('base_url')
    model = config.get('model')

    if not all([api_key, base_url, model]):
        raise ValueError("未配置大模型 API，请设置 api_key、base_url、model")

    headers = {
        'Authorization': f"Bearer {api_key}",
        'Content-Type': 'application/json'
    }
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': 'You are a helpful assistant that extracts structured information from Chinese regulation documents and returns valid JSON.'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.3
    }

    try:
        resp = requests.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        content = data['choices'][0]['message']['content']
        # 尝试从 markdown 代码块中提取 JSON
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if match:
            content = match.group(1)
        return json.loads(content.strip())
    except json.JSONDecodeError as e:
        print(f"[错误] 大模型返回内容无法解析为 JSON: {e}\n返回内容：{content}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[错误] 调用大模型失败: {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# 本地规则提取（作为大模型不可用时的 fallback）
# ---------------------------------------------------------------------------
def _norm_str(v, max_len=None):
    """字符串维度归一化：列表转句、去空、限长、缺失占位。"""
    if isinstance(v, list):
        v = '；'.join(str(x) for x in v)
    if v is None or str(v).strip() == '':
        return '未明确提取'
    s = str(v).strip()
    if max_len and len(s) > max_len:
        s = s[:max_len] + '…'
    return s


def _norm_list(v):
    """列表维度归一化为 [(title, content), ...]；为空时给"未明确提取"占位。"""
    items = []
    for x in v or []:
        if isinstance(x, dict):
            t, c = x.get('title'), x.get('content')
        elif isinstance(x, (list, tuple)) and len(x) == 2:
            t, c = x[0], x[1]
        else:
            t, c = '', str(x)
        t = re.sub(r'^[\d.、\s]+', '', str(t or '')).strip()[:16] or '要点'
        c = str(c or '').strip()[:300] or t
        items.append((t, c))
    return items or [('未明确提取', '未明确提取')]


# 禁令动词（"不得"后接 超过/少于/低于/高于/多于 时属于阈值表述，不算禁令）
BAN_PATTERN = r'(?:(?:严禁|禁止|不许|不准)|不得(?!超过|少于|低于|高于|多于|少于等于))'


def _split_prohibitions(items):
    """把含多个禁令动词的条目按分号/禁令词边界拆成独立条目（每条只含一个禁令）。"""
    ban_re = re.compile(BAN_PATTERN)
    out, seen = [], set()
    for t, c in items:
        if not ban_re.search(c):
            out.append((t, c))
            continue
        pieces = [p.strip('，,。；;、 ') for p in re.split(r'[；;]', c) if ban_re.search(p)]
        if len(pieces) <= 1:
            pieces = [p.strip('，,。；;、 ')
                      for p in re.split(rf'(?={BAN_PATTERN})', c)
                      if ban_re.search(p) and len(p.strip('，,。；;、 ')) >= 6]
        for p in pieces:
            title = t if t and t != '要点' else p[:12]
            key = (title, p)
            if key not in seen:
                seen.add(key)
                out.append((title, p))
    return out


def normalize_llm_result(llm_result: dict, length: str, keywords_count: int) -> dict:
    """把大模型返回结果规整为与本地提取一致的内部格式，并强制长度配额。"""
    quota = {'short': (3, 5, 3), 'medium': (8, 12, 10), 'long': (16, 20, 14)}.get(length, (8, 12, 10))
    # 责任主体：字符串列表（可含"名称：职责"）或字符串
    parties = llm_result.get('责任主体', [])
    if isinstance(parties, str):
        parties = re.split(r'[；;]', parties)
    seen, body = set(), []
    for p in parties:
        p = str(p).strip().rstrip('，,；;。')
        if not p or p in seen:
            continue
        seen.add(p)
        if '：' in p or ':' in p:
            name, duty = re.split(r'[：:]', p, maxsplit=1)
            body.append((name.strip()[:20], duty.strip()[:300]))
        else:
            body.append((p[:20], ''))
    keywords = []
    for kw in llm_result.get('关键词', []):
        kw = str(kw).strip()
        if kw and kw not in keywords and len(kw) <= 12:
            keywords.append(kw)
    return {
        '制度名称': _norm_str(llm_result.get('制度名称'), 110),
        '核心目标': _norm_str(llm_result.get('核心目标'), 220),
        '责任主体': body[:10] or [('未明确提取', '未明确提取')],
        '关键执行步骤': _norm_list(llm_result.get('关键执行步骤'))[:quota[0]],
        '关键阈值': _norm_list(llm_result.get('关键阈值'))[:quota[1]],
        '禁止事项': _split_prohibitions(_norm_list(llm_result.get('禁止事项')))[:quota[2]],
        '关键词': keywords[:keywords_count] or ['未明确提取'],
    }


def extract_rule_name(text: str, file_path: str = None) -> str:
    """提取制度名称（含发文文号，如"所财〔2026〕229号"）"""
    flat_text = re.sub(r'[\n\r]+', '', text)
    name = None
    match = re.search(r'《([^》]{2,40})》', flat_text)
    if match:
        name = match.group(1).strip()

    if name is None:
        match = re.search(r'([^\n。，,;；]{2,20}(?:制度|办法|规定|细则|章程))', flat_text)
        if match:
            name = re.sub(r'^#+\s*', '', match.group(1)).strip()

    if name:
        parts = []
        # 发文主体（原文出现的机构全称）
        orgs = [x for x in ('中国电子科技集团公司第二十研究所', '中电科西北集团有限公司') if x in flat_text]
        if orgs:
            parts.append('、'.join(orgs))
        # 文号（对行距/空格/有无括号均鲁棒）
        doc_no = re.search(r'〔\s*\d{4}\s*〕\s*\d{1,4}\s*号', flat_text)
        if doc_no and re.search(r'〔\s*\d{4}\s*〕', name) is None:
            head = flat_text[max(0, doc_no.start() - 6):doc_no.start()]
            head = re.sub(r'^.*文件', '', head)
            head = re.sub(r'\s+', '', head)
            head = re.sub(r'^[^A-Za-z\u4e00-\u9fa5]+', '', head)
            fragment = head[-4:] + re.sub(r'\s+', '', doc_no.group(0))
            if fragment:
                parts.append(fragment)
        # 印发日期
        m = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', flat_text)
        if m:
            parts.append(f"{m.group(1)}年{int(m.group(2))}月{int(m.group(3))}日印发")
        # 施行表述
        m2 = re.search(r'(自印发之日(?:起)?执行|自发布之日(?:起)?(?:施行|执行))', flat_text)
        if m2:
            parts.append(m2.group(1))
        return f"《{name}》（{'，'.join(parts)}）"[:110] if parts else name[:50]

    if file_path:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        if base_name and base_name not in ('test', 'test_rule', 'rule', 'index', '新建文件'):
            return base_name
    return "未知"


def extract_core_objective(text: str) -> str:
    """提取核心目标：目的句 + 原则句（如有"坚持/遵循…原则"）"""
    flat_text = re.sub(r'[\n\r]+', '', text)
    objective = None
    patterns = [
        r'为(?:了)?((?:进一步)?(?:规范|加强|完善|明确|落实|强化|保障|提升|做好|切实|有效)(?:进一步)?[^。，]{2,200}?)(?:[，；;。]|$)',
        r'(?:为|旨在)(?:了)?[\s，,]*([^。，]{3,120}?)(?:[，；;。]|\n)',
        r'(?:目的|目标)(?:是|在于)?[:\s，,]*([^。，]{3,120}?)(?:[，；;。]|\n)',
        r'本制度旨在([^。，]{3,120}?)(?:[，；;。]|\n)',
        r'本(?:制度|办法|规定)旨在([^。，]{3,120}?)(?:[，；;。]|\n)',
    ]
    for pat in patterns:
        match = re.search(pat, flat_text)
        if match:
            g = ''.join(match.groups()) if match.groups() else match.group(0)
            g = re.sub(r'^[的地得]+', '', g.strip())
            g = re.sub(r'[的地得]+$', '', g)
            if len(g) >= 3:
                objective = g[:120]
                break
    if not objective:
        return "未明确提取"

    # 制定依据（"依据…《…》…制定"）
    m = re.search(r'依据([^，。\n]{2,60}?)(?=，)', flat_text)
    if m and '依据' not in objective:
        basis = f"依据{m.group(1)}"
        basis += "并结合工作实际制定" if '结合工作实际' in flat_text else "制定"
        objective = f"{objective}；{basis}"
    # 原则句：坚持/遵循/应当按照…原则
    m = re.search(r'(?:坚持|遵循|应当.{0,6}(?:按照|坚持)|按照).{0,40}?原则', flat_text)
    if m and m.group(0)[:40] not in objective:
        objective = f"{objective}；{m.group(0)[:60]}"
    # 适用范围
    m = re.search(r'适用于([^。\n；;]{2,60}?)(?:。|；|$)', flat_text)
    if m and '适用' not in objective:
        objective = f"{objective}；适用于{m.group(1)}"
    return objective[:220]


def extract_party_duties(text: str) -> list:
    """提取责任主体及其职责，返回 [(主体, 职责描述), ...]，有职责的排在前面。

    - 机构类主体（部/处/科/室/中心/组/会/院结尾）优先；
    - 名称互为子串时保留长名称（避免"财务部"命中"财务资产部"内部）；
    - 职责 = 主体名称之后出现"负责/组织/归口/统筹…"等动词的那个小句。
    """
    duty_verbs = '负责|组织|建立|制定|统筹|统一|归口|指导|监控|监督|检查|考核|承担|审批|备案|办理|管理|归集|编制'
    flat = re.sub(r'[\n\r]+', '', text)
    flat = re.sub(r'[—\-–－]{1,2}\s*\d{1,3}\s*[—\-–－]{1,2}|\d{1,3}\s*[—\-–－]{1,2}\s*[—\-–－]', '', flat)  # 页码残片

    institutions, generics = [], []
    for party in COMMON_PARTIES:
        if party not in flat:
            continue
        if re.search(r'(?:部|处|科|室|中心|组|会|院|公司)$', party):
            if party not in institutions:
                institutions.append(party)
        elif party not in generics:
            generics.append(party)
    for m in re.finditer(r'(?<![\u4e00-\u9fa5])([\u4e00-\u9fa5]{2,8}(?:部|处|科|室|中心|组|会|院))(?![\u4e00-\u9fa5])', flat):
        n = m.group(1)
        n = re.sub(r'^(?:二十所|电科西北|集团公司|二十所、电科西北|电科西北、二十所)', '', n)
        if n and n not in institutions:
            institutions.append(n)

    def drop_substrings(items):
        """互为子串或词干前缀的名称保留较长者，避免"财务部"与"财务资产部"并列。"""
        def related(m, n):
            if (n in m) or m.startswith(n):
                return True
            # 均以"部"结尾时比词干（财务资产部 vs 财务部 → 财务资产 vs 财务）
            if m.endswith('部') and n.endswith('部'):
                return m[:-1].startswith(n[:-1])
            return False

        out = []
        for n in sorted(items, key=len, reverse=True):
            if any(related(m, n) for m in out):
                continue
            out.append(n)
        return out

    name_seq = drop_substrings(institutions) + [g for g in generics
                                                if not any(g in m for m in institutions)]

    # 通用主体（非机构名）需要严格的主语位置校验
    GENERIC_PARTIES = {'各部门', '本部门', '部门', '公司', '员工', '部门负责人',
                       '项目负责人', '直接上级', '总经理'}

    def valid_occurrences(n):
        """过滤"长机构名的片段"出现位置：名字后紧跟"门/资产/机构"等续字时视为更长名称的一部分。"""
        out = []
        for m in re.finditer(re.escape(n), flat):
            end = m.end()
            if flat[end:end + 1] == '门' or flat[end:end + 2] in ('资产', '机构'):
                continue
            out.append(m)
        return out

    NOT_FOUND = object()

    def find_duty(n, strict_subject=False):
        occs = valid_occurrences(n)
        if not occs:
            return NOT_FOUND
        for m in occs:
            start = m.start()
            if strict_subject:
                prev = flat[max(0, start - 1):start]
                if prev and prev not in '。；;，,、:：（(':
                    continue
            window = flat[start + len(n): start + len(n) + 30]
            if '制度' in window[:10]:
                continue  # 命中标题/适用范围类句子（如"员工考勤管理制度 总则…"），跳过
            vm = re.search(duty_verbs, window)
            if not vm or vm.start() > 22:
                continue
            # 取包含主体的小句：从最近一个句读到下一个句号/分号
            head = flat.rfind('。', 0, start) + 1
            tail = flat.find('。', start + len(n))
            semi = flat.find('；', start + len(n))
            if tail != -1 and semi != -1:
                tail = min(tail, semi)
            elif tail == -1:
                tail = semi
            end = tail if tail != -1 else min(len(flat), start + len(n) + 140)
            clause = flat[head:end + 1].strip('，,；;。 ')
            clause = re.sub(r'^[—\-–－\d\s]+', '', clause)
            clause = re.sub(r'^第[一二三四五六七八九十百千万0-9]+章.*?第[一二三四五六七八九十百千万0-9]+条\s*', '', clause)
            if 6 <= len(clause) <= 140:
                return clause
        return ''

    with_duty, without_duty = [], []
    for n in name_seq:
        duty = find_duty(n, strict_subject=(n in GENERIC_PARTIES))
        if duty is NOT_FOUND:
            continue  # 名称只是更长机构名的片段，整体剔除
        if duty:
            with_duty.append((n, duty))
        else:
            without_duty.append((n, ''))
    return (with_duty + without_duty)[:8]


def clean_title(title: str) -> str:
    """清理小标题"""
    title = re.sub(r'^(?:员工|各部门负责人|部门负责人|公司|本部门|部门|各级|各)\s*', '', title)
    title = re.sub(r'^[的地得]+', '', title)
    title = re.sub(r'[的地得]+$', '', title)
    return title.strip()


def trim_step_title(title: str) -> str:
    """去除执行步骤标题中的常见冗余前缀，并修复贪婪回溯残留的孤立前缀字。"""
    title = re.sub(r'^(?:每日|每|各|当日|次日|本部门|部门|公司|员工|各部门负责人|部门负责人|各级|负责人)\s*', '', title)
    # 贪婪匹配窗口可能把"每/当"吞掉只留下"日/时"（如"日上下班按时打卡"）；非日期类词时去掉
    if len(title) >= 4 and title[0] in '日时' and title[1] not in '期程报志常历间刻段':
        title = title[1:]
    # 窗口可能从"员工考勤…"的"工"字切起，补回语义
    title = re.sub(r'^工(?=考勤|作|时|单)', '', title)
    # "集团"被斩掉"集"时补回（如"团公司相关管理政策"→"集团公司相关管理政策"）
    if title.startswith('团公司'):
        title = '集' + title
    while title and len(title) > 1 and not re.search(r'[\u4e00-\u9fa5]', title[1:2]):
        title = title[1:]
    return title.strip()


def extract_step_title(sentence: str) -> str:
    """从执行步骤句子中提取核心动作短语作为小标题"""
    match = re.search(r'(?:应当|必须|应|需|须|应该|需要)\s*([^。！？.!?]+)', sentence)
    if match:
        action_part = match.group(1).strip()
    else:
        action_part = sentence

    action_keywords = '归集|上报|报送|开立|执行|组织|搭建|留存|集中|调整|编制|打卡|请假|出勤|加班|调休|出差|审批|备案|申请|报销|审核|监督管理|管理|报告|记录|考核|核对'
    # 按标点切段，取含动作词的段尾作为标题（锚定段尾，避免截断/前缀残片）
    for seg in re.split(r'[，,；;、]', action_part):
        seg = seg.strip().strip('（(）)')
        seg = re.sub(r'^[^：:]{0,12}职责[：:]', '', seg)   # 去掉"主要履行以下职责："类引导
        seg = re.sub(r'^[（(][一二三四五六七八九十\d]+[）)]\s*', '', seg)
        seg = re.sub(r'^[—\-–－\d\s]+', '', seg)
        if not seg:
            continue
        # 关键词可能离段尾较远，按 10/12/14/16 字窗口切段重试，保证锚定成功
        for cut in (10, 12, 14, 16):
            t = seg[-cut:].rstrip('。．;；，,、 ')
            if not t:
                continue
            m = re.search(r'([\u4e00-\u9fa5]{0,6}(?:' + action_keywords + r')[\u4e00-\u9fa5]{0,4})$', t)
            if m:
                title = clean_title(trim_step_title(m.group(1)))
                if 2 <= len(title) <= 10:
                    return title

    title = clean_title(trim_step_title(action_part[:8]))
    return title if action_part else clean_title(sentence[:8])


def extract_short_title(text: str) -> str:
    """从句子中自动提炼简短小标题"""
    text = text.strip().rstrip('。')
    match = re.search(r'《([^》]{2,8})》', text)
    if match:
        return match.group(1)

    match = re.search(r'(严禁|禁止|不得|不许|不准|不允许)\s*([^，。：；\s]{2,8})', text)
    if match:
        title = match.group(1) + match.group(2)
        if 2 <= len(title) <= 10:
            return title

    match = re.search(r'(\d+(?:\.\d+)?)\s*(天|小时|分钟|分|次|个|元|%)', text)
    if match:
        return f"{match.group(1)}{match.group(2)}标准"

    action_keywords = '打卡|请假|出勤|加班|调休|出差|审批|备案|申请|报销|审核|管理|监督管理|报告|记录|考核|核对'
    segments = re.split(r'[，,；;。]', text)
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        match = re.search(r'([\u4e00-\u9fa5]{0,6}(?:' + action_keywords + r'))', seg)
        if match:
            title = clean_title(match.group(1))
            if 2 <= len(title) <= 10:
                return title

    t = clean_title(text[:8] if len(text) > 8 else text)
    return t if t else text[:6]


def extract_key_steps(text: str, length: str = 'medium') -> list:
    """提取关键执行步骤，返回 (标题, 内容) 元组列表"""
    step_keywords = ['应当', '必须', '应', '需', '按照', '根据', '执行', '履行',
                     '办理', '提交', '审批', '审核', '申请', '报送', '备案']
    noise_patterns = [
        r'现予[以]?印发',
        r'请遵照执行',
        r'关于发布',
        r'制定了《',
        r'结合工作实际',
        r'主要履行以下职责',
        r'是资金归口管理部门',
        r'是本单位资金归口管理部门',
        r'是资金的具体使用部门',
    ]
    sentences = split_sentences(text)
    steps = []
    seen_content = set()
    for s in sentences:
        s = s.strip()
        if len(s) <= 30 and not re.search(r'[应须需]', s):
            continue
        if s in seen_content:
            continue
        if any(k in s for k in step_keywords) and 20 <= len(s) <= 250:
            if any(re.search(p, s) for p in noise_patterns):
                continue
            title = extract_step_title(s)
            if len(title) < 2 or re.search(r'^(职责|分工|管理|规定|制度)$', title):
                continue
            seen_content.add(s)
            steps.append((title, s))

    limit = {'short': 3, 'medium': 8, 'long': 16}.get(length, 8)
    return steps[:limit]


def extract_prohibitions(text: str, length: str = 'medium') -> list:
    """提取禁止事项：同一句内多个禁令动词按分号/动词边界拆成独立条目。"""
    ban_re = re.compile(BAN_PATTERN)
    prohibitions = []
    for s in split_sentences(text):
        s = s.strip()
        if not ban_re.search(s):
            continue
        pieces = [p.strip('，,。；;、 ') for p in re.split(r'[；;]', s) if ban_re.search(p)]
        if len(pieces) <= 1:
            pieces = [p.strip('，,。；;、 ') for p in re.split(rf'(?={BAN_PATTERN})', s)
                      if ban_re.search(p) and len(p.strip('，,。；;、 ')) >= 6]
        for p in pieces:
            if any(p == old[1] for old in prohibitions):
                continue
            prohibitions.append((extract_short_title(p), p))
    limit = {'short': 3, 'medium': 10, 'long': 14}.get(length, 10)
    return prohibitions[:limit]


def extract_key_thresholds(text: str, length: str = 'medium') -> list:
    """提取关键阈值：在整篇平铺文本上用 ±14 字窗口取标题语境（对 PDF 换行鲁棒）。"""
    unit_pat = re.compile(r'(\d+(?:\.\d+)?)\s*(天|小时|分钟|分|次|个|元|%|％)')
    vague_pat = re.compile(r'(超过|少于|连续|累计|达到|不超过|不少于|不高于|低于|高于)\s*(\d+(?:\.\d+)?)')

    def title_of_flat(start, num_text):
        head = flat_text[max(0, start - 14):start]
        frag = re.split(r'[，,；;。：:（(]', head)[-1]
        frag = re.sub(r'\s+', '', frag)  # PDF 提取常插入空格，先归并
        frag = re.sub(r'^[-\s*·•#▲△>]+', '', frag)
        frag = re.sub(r'^(不得超过|不超过|不高于|不得少于|少于|不低于|低于|超过|达到|至少|累计)', '', frag)
        frag = re.sub(r'[的地得达为至]$', '', frag.strip())
        if len(frag) > 8:  # 超长时取尾部语境（如"…总担保规模不得超过合并净资产的40%"）
            frag = frag[-8:]
            frag = re.sub(r'^[\u4e00-\u9fa5]{0,5}?(?:不得超过|不超过|不高于|不得少于|不低于|低于|高于|超过|少于|达到|累计|至少)', '', frag)
            frag = re.sub(r'[的地得达为至]$', '', frag.strip())
        frag = frag.strip('，,；;。、（）() ')
        return frag if 2 <= len(frag) <= 8 else f"{num_text}标准"

    flat_text = re.sub(r'[\n\r]+', '', text)
    result, seen = [], set()
    covered_numbers = set()
    for m in unit_pat.finditer(flat_text):
        unit = m.group(2)
        detail = f"{m.group(1)}{unit}" if unit in '%％' else f"{m.group(1)} {unit}"
        covered_numbers.add(m.group(1))
        if detail in seen:
            continue
        seen.add(detail)
        result.append((title_of_flat(m.start(), m.group(1)), detail))
    for m in vague_pat.finditer(flat_text):
        if m.group(2) in covered_numbers:
            continue  # 同一数字已被"数值+单位"表达覆盖，跳过模糊重复
        detail = f"{m.group(1)} {m.group(2)}"
        if detail in seen:
            continue
        seen.add(detail)
        result.append((title_of_flat(m.start(), m.group(2)), detail))
    # 频率类阈值（按日归集/每月底上报/每周调整/按月对账等）
    freq_titles = {'按日': '归集频率', '按月': '银企对账频率', '每月底前': '资金计划上报时限', '每周': '资金计划调整频率'}
    for m in re.finditer(r'(按日|按月|按周|每月底前|每周|每月|每天|每季|每年度|工作日)', flat_text):
        detail = m.group(1)
        if detail in seen:
            continue
        seen.add(detail)
        title = freq_titles.get(detail) or title_of_flat(m.start(), detail)
        result.append((title, detail))
    limit = {'short': 5, 'medium': 12, 'long': 20}.get(length, 12)
    return result[:limit]


def extract_keywords(text: str, count: int = 8) -> list:
    """提取关键词：优先匹配领域词库，再按全文词频补足（2-8 字词语）"""
    flat_text = re.sub(r'[\n\r]+', '', text)
    words = []
    for kw in COMMON_KEYWORDS:
        if kw in flat_text:
            words.append(kw)

    for seg in re.findall(r'[\u4e00-\u9fa5]{2,8}', flat_text):
        if seg not in STOPWORDS and seg not in words:
            words.append(seg)

    counter = Counter(words)
    candidates = [w for w, _ in counter.most_common(count * 8)]

    bad_substrings = (
        '各业务单元', '集团公司第', '中国电子科技', '十研究所', '电科西北财务',
        '主要履行', '以下职责', '规章制度和', '资金管理基本',
        '为进一步', '依据中国'
    )
    noise_words = {'以下', '主要', '履行', '职责', '工作', '规定', '管理', '制度'}
    seen = set()
    result = []
    for w in candidates:
        if w in seen or w in noise_words:
            continue
        if any(bs in w for bs in bad_substrings):
            continue
        if '应' in w and len(w) <= 4:
            continue
        if len(w) < 2:
            continue
        seen.add(w)
        result.append(w)
        if len(result) >= count:
            break
    return result


def summarize_rules_fallback(text: str, file_path: str = None, length: str = 'medium', keywords_count: int = 8) -> dict:
    """本地规则提取 fallback"""
    cleaned_text = clean_text(text)

    key_steps = extract_key_steps(cleaned_text, length)
    prohibitions = extract_prohibitions(cleaned_text, length)
    party_duties = extract_party_duties(cleaned_text)
    thresholds = extract_key_thresholds(cleaned_text, length)

    return {
        '制度名称': extract_rule_name(text, file_path),
        '核心目标': extract_core_objective(text),
        '责任主体': party_duties if party_duties else [('未明确提取', '未明确提取')],
        '关键执行步骤': key_steps,
        '关键阈值': thresholds if thresholds else [('未明确提取', '未明确提取')],
        '禁止事项': prohibitions if prohibitions else [('未明确提取', '未明确提取')],
        '关键词': extract_keywords(text, keywords_count)
    }


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def _format_list_value(value: list, is_markdown: bool = True) -> str:
    """格式化列表值：带 (标题, 内容) 的条目按编号逐条列出；平铺列表（如关键词）用顿号连接。"""
    if value and all(not isinstance(v, (list, tuple, dict)) for v in value):
        return '、'.join(str(v) for v in value)
    items = []
    for i, v in enumerate(value):
        if isinstance(v, (list, tuple)) and len(v) == 2:
            title, detail = v
            item = f"{i+1}. {title}：{detail}" if detail and detail != title else f"{i+1}. {title}"
            items.append(item)
        elif isinstance(v, dict) and 'title' in v and 'content' in v:
            item = f"{i+1}. {v['title']}：{v['content']}" if v['content'] and v['content'] != v['title'] else f"{i+1}. {v['title']}"
            items.append(item)
        else:
            items.append(str(v))
    sep = '<br>' if is_markdown else '\n'
    return sep.join(items)


def format_as_markdown_table(result: dict) -> str:
    """输出为 Markdown 表格"""
    lines = [
        '## 制度摘要',
        '',
        '| 信息类别 | 内容 |',
        '|----------|------|'
    ]
    for key, value in result.items():
        if isinstance(value, list):
            value_str = _format_list_value(value, is_markdown=True)
        else:
            value_str = str(value)
        lines.append(f"| **{key}** | {value_str} |")
    return '\n'.join(lines)


def format_as_text(result: dict) -> str:
    """输出为纯文本"""
    lines = ['===== 制度摘要 =====']
    for key, value in result.items():
        if isinstance(value, list):
            value_str = _format_list_value(value, is_markdown=False)
        else:
            value_str = str(value)
        lines.append(f"{key}: {value_str}")
    return '\n'.join(lines)


def result_to_json_serializable(result: dict) -> dict:
    """将结果中的元组转成列表，便于 JSON 序列化"""
    new_result = {}
    for key, value in result.items():
        if isinstance(value, list):
            new_result[key] = [
                {'title': v[0], 'content': v[1]} if isinstance(v, (list, tuple)) and len(v) == 2 else v
                for v in value
            ]
        else:
            new_result[key] = value
    return new_result


# Word 输出样式常量（与 SKILL.md「输出格式规范」保持一致）
_W_TITLE_FONT = '黑体'
_W_BODY_FONT = '宋体'
_W_PRIMARY = (0x1F, 0x4E, 0x79)   # 深蓝
_W_HEADER_BG = '1F4E79'
_W_CATEGORY_BG = 'F2F7FC'
_W_ZEBRA_BG = 'EDF3FA'
_W_OUTER_BORDER = '8496B0'
_W_INNER_BORDER = 'C9D4E0'
_W_MUTED = (0x80, 0x80, 0x80)     # 灰


def _set_run_font(run, name, size, bold=False, color=None):
    """设置 run 的字体（含中文 eastAsia）"""
    from docx.oxml.ns import qn
    run.font.name = name
    run._element.rPr.rFonts.set(qn('w:eastAsia'), name)
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)


def _cell_bg(cell, hex_color):
    """设置单元格底纹"""
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    cell._tc.get_or_add_tcPr().append(
        parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}" w:val="clear"/>'))


def _cell_margins(cell, top=140, bottom=140, left=120, right=120):
    """设置单元格内边距（单位 twips）"""
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_pr.append(parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        '</w:tcMar>'))


def save_markdown_to_word(markdown_text: str, output_path: str, meta: dict = None):
    """将 Markdown 表格保存为样式规范的 Word 文档（.docx）。

    meta 可选字段：制度名称（用于生成标题/副题）、章节数、条数（用于"说明"段）。
    """
    if not DOCX_AVAILABLE:
        print("[错误] 导出 Word 需要安装 python-docx: pip install python-docx", file=sys.stderr)
        sys.exit(1)

    meta = meta or {}
    doc_name = str(meta.get('制度名称', '')).strip()
    bare_name = re.split(r'[（(〔]', doc_name)[0].strip('《》') if doc_name else ''
    chapters = meta.get('章节数')
    articles = meta.get('条数')

    from docx.shared import Cm
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls

    doc = Document()

    # ── 页面设置：A4，上下 2.2cm、左右 2.4cm ──
    section = doc.sections[0]
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.4)
    section.right_margin = Cm(2.4)

    # ── 全局默认字体 ──
    from docx.oxml.ns import qn
    style = doc.styles['Normal']
    style.font.name = _W_BODY_FONT
    style._element.rPr.rFonts.set(qn('w:eastAsia'), _W_BODY_FONT)
    style.font.size = Pt(10.5)
    style.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    # ── 标题、副题与说明段 ──
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(4)
    title.paragraph_format.space_after = Pt(2)
    title_text = f"《{bare_name}》要点摘要" if bare_name else '制度摘要'
    _set_run_font(title.add_run(title_text), _W_TITLE_FONT, 18, bold=True, color=_W_PRIMARY)

    if doc_name and (not bare_name or doc_name != bare_name):
        subtitle = doc.add_paragraph()
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle.paragraph_format.space_after = Pt(2)
        _set_run_font(subtitle.add_run(doc_name), _W_BODY_FONT, 10.5)
    else:
        subtitle = doc.add_paragraph()
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle.paragraph_format.space_after = Pt(2)
        _set_run_font(subtitle.add_run('制度文件结构化摘要'), _W_BODY_FONT, 9, color=_W_MUTED)

    note = doc.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    note.paragraph_format.space_after = Pt(10)
    scope = ''
    if chapters and articles:
        scope = f"，共{chapters}章{articles}条"
        chapter_names = meta.get('章节名') or []
        if chapter_names:
            scope += f"（{'、'.join(chapter_names)}）"
    trans = meta.get('衔接条款') or ''
    trans_text = f"。{trans}" if trans else ''
    _set_run_font(note.add_run(
        f"说明：本摘要依据原文件全文整理{scope}，由 rules-extract 自动生成，供快速查阅，具体执行以原文为准{trans_text}。"),
        _W_BODY_FONT, 9, color=_W_MUTED)

    # ── 解析 Markdown 表格 ──
    lines = markdown_text.strip().splitlines()
    table_lines = [ln for ln in lines if ln.strip().startswith('|')]
    if not table_lines:
        doc.add_paragraph(markdown_text)
        doc.save(output_path)
        return

    header_cells = [c.strip() for c in table_lines[0].split('|')[1:-1]]
    rows = []
    for ln in table_lines[2:]:
        cells = [c.strip() for c in ln.split('|')[1:-1]]
        if cells and any(cells):
            rows.append(cells)

    # ── 建表：固定列宽、整表居中、细边框 ──
    col_widths = [Cm(4.2), Cm(12.0)]
    table = doc.add_table(rows=1 + len(rows), cols=2)
    table.autofit = False
    table.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tbl_pr = table._tbl.tblPr
    tbl_pr.append(parse_xml(f'<w:tblW {nsdecls("w")} w:w="9185" w:type="dxa"/>'))
    tbl_pr.append(parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="8" w:space="0" w:color="{_W_OUTER_BORDER}"/>'
        f'<w:left w:val="single" w:sz="8" w:space="0" w:color="{_W_OUTER_BORDER}"/>'
        f'<w:bottom w:val="single" w:sz="8" w:space="0" w:color="{_W_OUTER_BORDER}"/>'
        f'<w:right w:val="single" w:sz="8" w:space="0" w:color="{_W_OUTER_BORDER}"/>'
        f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{_W_INNER_BORDER}"/>'
        f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="{_W_INNER_BORDER}"/>'
        '</w:tblBorders>'))
    tbl_pr.append(parse_xml(f'<w:tblLayout {nsdecls("w")} w:type="fixed"/>'))

    # ── 表头：深蓝底、白色加粗黑体、居中 ──
    for i, text in enumerate(header_cells[:2]):
        cell = table.rows[0].cells[i]
        cell.width = col_widths[i]
        _cell_bg(cell, _W_HEADER_BG)
        _cell_margins(cell)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_run_font(p.add_run(re.sub(r'\*\*', '', text)), _W_TITLE_FONT, 10.5,
                      bold=True, color=(0xFF, 0xFF, 0xFF))

    # ── 数据行：维度列浅蓝底加粗，内容列隔行着色、每条一段 ──
    for r_idx, cells in enumerate(rows):
        if len(cells) < 2:
            continue
        cat = re.sub(r'\*\*', '', cells[0])
        content = cells[1].replace('<br>', '\n')
        cat_cell, cont_cell = table.rows[r_idx + 1].cells
        cat_cell.width, cont_cell.width = col_widths
        _cell_margins(cat_cell)
        _cell_margins(cont_cell)
        _cell_bg(cat_cell, _W_CATEGORY_BG)
        if r_idx % 2 == 0:
            _cell_bg(cont_cell, _W_ZEBRA_BG)
        p = cat_cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_run_font(p.add_run(cat), _W_TITLE_FONT, 10.5, bold=True, color=_W_PRIMARY)
        first = True
        for seg in content.split('\n'):
            seg = seg.strip()
            if not seg:
                continue
            p = cont_cell.paragraphs[0] if first else cont_cell.add_paragraph()
            first = False
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.25
            m = re.match(r'^(\d+\.\s*.{1,12}?)[：:](.*)$', seg)
            if m:
                _set_run_font(p.add_run(m.group(1) + '：'), _W_TITLE_FONT, 10.5,
                              bold=True, color=_W_PRIMARY)
                _set_run_font(p.add_run(m.group(2)), _W_BODY_FONT, 10.5)
            else:
                _set_run_font(p.add_run(seg), _W_BODY_FONT, 10.5)

    doc.save(output_path)


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='制度文件结构化摘要工具')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--text', help='需要摘要的文本内容')
    group.add_argument('--file', help='本地文件路径')
    group.add_argument('--url', help='网页 URL 地址')

    parser.add_argument('--length', choices=['short', 'medium', 'long'], default='medium', help='摘要长度')
    parser.add_argument('--output', choices=['text', 'markdown', 'json', 'word'], default='markdown', help='输出格式')
    parser.add_argument('--output-file', help='指定输出文件路径（word 输出时必须）')
    parser.add_argument('--keywords-count', type=int, default=10, help='提取关键词数量')
    parser.add_argument('--use-llm', action='store_true', help='强制使用大模型提取（需配置 API）')

    args = parser.parse_args()

    # 获取内容
    if args.text:
        text = args.text
        file_path = None
    elif args.file:
        text = get_file_content(args.file)
        file_path = args.file
    elif args.url:
        text = get_url_content(args.url)
        file_path = None
    else:
        parser.print_help()
        sys.exit(1)

    config = load_config()

    # 判断是否使用大模型
    use_llm = args.use_llm or all(config.get(k) for k in ['api_key', 'base_url', 'model'])
    if use_llm:
        prompt = build_prompt(text, args.length, args.keywords_count)
        try:
            llm_result = call_llm(prompt, config)
        except ValueError:
            print("[提示] 未配置大模型 API，已回退到本地规则提取。", file=sys.stderr)
            llm_result = None
        if llm_result:
            # 将 LLM 结果归一化为统一格式（强制配额、去重、补全）
            result = normalize_llm_result(llm_result, args.length, args.keywords_count)
        else:
            result = summarize_rules_fallback(text, file_path, args.length, args.keywords_count)
    else:
        result = summarize_rules_fallback(text, file_path, args.length, args.keywords_count)

    # 输出
    if args.output == 'json':
        print(json.dumps(result_to_json_serializable(result), ensure_ascii=False, indent=2))
    elif args.output == 'text':
        print(format_as_text(result))
    elif args.output == 'word':
        markdown_table = format_as_markdown_table(result)
        if args.output_file:
            output_path = args.output_file
        else:
            import tempfile
            output_dir = os.path.dirname(file_path) if file_path else tempfile.gettempdir()
            base_name = os.path.splitext(os.path.basename(file_path))[0] if file_path else '制度摘要'
            output_path = os.path.join(output_dir, f"{base_name}_摘要.docx")
        # 统计章节/条款数量与章节名，用于 Word 的"说明"段
        flat_text = re.sub(r'[\n\r]+', '', text)
        chapters = len(set(re.findall(r'第[一二三四五六七八九十百千万0-9]+\s*章', flat_text)))
        articles = len(set(re.findall(r'第[一二三四五六七八九十百千万0-9]+\s*条', flat_text)))
        chapter_names = re.findall(r'第[一二三四五六七八九十百千万0-9]+\s*章\s*([^第\s]{2,12})', flat_text)
        trans_text = ''
        for s in re.split(r'[。\n]', flat_text):
            if '新发布' in s and '执行' in s:
                s = re.sub(r'^第[一二三四五六七八九十百千万0-9]+\s*条\s*', '', s)
                m = re.search(r'((?:若|如).{0,120}?(?:执行|为准))', s)
                if m:
                    trans_text = m.group(1)
                    break
        meta = {
            '制度名称': result.get('制度名称'),
            '章节数': chapters,
            '条数': articles,
            '章节名': chapter_names,
            '衔接条款': trans_text,
        }
        save_markdown_to_word(markdown_table, output_path, meta=meta)
        print(f"Word 文档已保存至: {output_path}")
    else:
        print(format_as_markdown_table(result))


if __name__ == '__main__':
    main()
