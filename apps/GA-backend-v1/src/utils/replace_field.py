"""
Field replacement utility module.
Provides functions for replacing fields in data structures.
"""
from typing import Dict, Any, List, Union

def transform_json(item: Dict[str, Any], replace_mapping: Dict[str, str], value_mapping: Dict[str, Dict[str, str]],
                   ignore_fields: List[str]) -> Dict[str, Any]:
    """
    转换JSON数据，替换键名和指定的值
    :param item: 原始数据字典
    :param replace_mapping: 键名替换映射
    :param value_mapping: 值替换映射，格式为 {'字段名': {'原值': '新值'}}
    :param ignore_fields: 需要忽略的字段列表
    :return: 转换后的字典
    """
    result = {}
    for key, value in item.items():
        if key not in ignore_fields:
            new_key = replace_mapping.get(key, key)
            # 检查是否需要替换值
            if key in value_mapping:

                str_value = str(value)
                if str_value in value_mapping[key]:
                    new_value = value_mapping[key][str_value]
                else:
                    new_value = value
            else:
                new_value = value
            result[new_key] = new_value
    return result

