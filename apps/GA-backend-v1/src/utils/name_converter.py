"""命名转换工具模块

提供各种命名风格转换功能，如下划线命名转换为驼峰命名等。
"""
from typing import Dict

def convert_to_camel_case(text: str) -> str:
    """将下划线命名转换为驼峰命名
    
    Args:
        text: 下划线命名的字符串
        
    Returns:
        驼峰命名的字符串
    """
    parts = text.split('_')
    if len(parts) <= 1:
        return text
    # 第一个单词保持小写，后面的单词首字母大写
    return parts[0] + ''.join(part.capitalize() for part in parts[1:])

def convert_dict_keys_to_camel_case(data: Dict) -> Dict:
    """将字典中的所有键从下划线命名转换为驼峰命名
    
    Args:
        data: 包含下划线命名键的字典
        
    Returns:
        键为驼峰命名的字典
    """
    # 不需要递归转换 key 的字段（值为原始保留的字典）
    _skip_keys = {"env_vars"}

    result = {}
    for key, value in data.items():
        # env_vars 整个字段（含 key 本身及内部内容）保持原样，不做任何转换
        if key in _skip_keys:
            result[key] = value
            continue
        # 转换键名
        camel_case_key = convert_to_camel_case(key)
        # 如果值是字典，递归转换
        if isinstance(value, dict):
            result[camel_case_key] = convert_dict_keys_to_camel_case(value)
        else:
            result[camel_case_key] = value
    return result