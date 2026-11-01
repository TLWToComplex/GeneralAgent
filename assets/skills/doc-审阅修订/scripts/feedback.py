"""
feedback.py — 缺陷反馈回路管理

接收用户反馈，自动生成对应的缺陷检测模式并追加到 _defect_patterns.py。
"""
import re
import json
from pathlib import Path


PATTERNS_FILE = Path(__file__).parent / '_defect_patterns.py'


def add_pattern(name, severity, scope, description, detect_logic, fix_hint, source):
    """添加一条新缺陷模式到 _defect_patterns.py。

    Args:
        name: 缺陷名称（简短）
        severity: error / warning / info
        scope: heading / list / region / format
        description: 详细描述
        detect_logic: 检测逻辑的 Python 代码字符串（函数体）
        fix_hint: 修复建议
        source: 来源说明

    Returns:
        新模式的 ID (如 DP012)
    """
    if not PATTERNS_FILE.exists():
        raise FileNotFoundError(f"模式库文件不存在: {PATTERNS_FILE}")

    content = PATTERNS_FILE.read_text(encoding='utf-8')

    # 计算下一个 ID
    existing_ids = re.findall(r'DP(\d{3})', content)
    next_num = max(int(x) for x in existing_ids) + 1 if existing_ids else 1
    new_id = f'DP{next_num:03d}'

    # 生成注册代码
    register_code = f'''
_register({{
    "name": "{name}",
    "severity": "{severity}",
    "scope": "{scope}",
    "description": "{description}",
    "source": "{source}",
    "detect": lambda doc, spec: {detect_logic},
    "fix_hint": "{fix_hint}",
}})
'''

    # 在最后一个 _register 调用之后插入
    last_register = content.rfind('_register({')
    insert_pos = content.find(')', last_register) + 1
    new_content = content[:insert_pos] + register_code + content[insert_pos:]

    PATTERNS_FILE.write_text(new_content, encoding='utf-8')

    return new_id


def list_patterns():
    """列出所有已注册的缺陷模式。"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from _defect_patterns import PATTERNS

    result = []
    for p in PATTERNS:
        result.append({
            "id": p['id'],
            "name": p['name'],
            "severity": p['severity'],
            "scope": p['scope'],
            "description": p['description'],
            "source": p['source'],
        })
    return result
