"""
敏感数据脱敏工具
用于在流式输出时对思考过程和工具调用的敏感信息进行脱敏处理。
"""
import json
import re
from typing import Any


# 敏感字段名（出现在 dict key 中时直接脱敏）
SENSITIVE_KEYS = {
    "password", "passwd", "secret", "token", "authorization", "Authorization",
    "api_key", "apiKey", "apikey", "access_key", "accessKey",
    "access_token", "accessToken", "refresh_token", "refreshToken",
}

# 敏感值正则：匹配常见的凭据格式（用户名、密码、token 等）
SENSITIVE_VALUE_PATTERN = re.compile(
    r'(?:admin|Aa@123456|sk-[a-zA-Z0-9]{20,}|Bearer\s+[a-zA-Z0-9_\-\.]+)', re.IGNORECASE
)


def mask_value(value: Any) -> Any:
    """对字符串值进行脱敏，匹配到的敏感词替换为 ***。

    如果字符串是有效 JSON，会递归解析并脱敏后重新序列化。
    """
    if not isinstance(value, str):
        return value

    # 尝试解析 JSON 字符串，递归脱敏后重新序列化
    try:
        parsed = json.loads(value)
        masked = mask_sensitive_fields(parsed)
        if masked != parsed:
            return json.dumps(masked, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        pass

    # 非 JSON 字符串，用正则匹配敏感词替换
    if SENSITIVE_VALUE_PATTERN.search(value):
        return SENSITIVE_VALUE_PATTERN.sub("***", value)
    return value


def mask_sensitive_fields(data: Any) -> Any:
    """递归遍历数据结构，脱敏敏感字段名对应的值以及匹配凭据模式的字符串。"""
    if isinstance(data, dict):
        return {
            k: "***" if k in SENSITIVE_KEYS else mask_sensitive_fields(v)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [mask_sensitive_fields(item) for item in data]
    return mask_value(data)
