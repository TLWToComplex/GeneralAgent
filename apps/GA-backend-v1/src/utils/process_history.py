"""
Conversation history processing module.
Provides functions for processing and formatting conversation history.
"""
from typing import List, Dict

def process_history(history: List[Dict[str, str]], k:int = 2) -> List[Dict[str, str]]:
    """
    处理历史消息列表，保留system消息，并只保留最近的2组user-assistant对话对

    Args:
        history: 历史消息列表
        k: 保留的对话对数量

    Returns:
        处理后的消息列表
    """
    # 获取system消息
    system_message = None
    if history and history[0]["role"] == "system":
        system_message = history[0]

    # 提取所有user-assistant对话对
    pairs = []
    i = 1  # 从第二条消息开始（跳过system消息）
    while i < len(history) - 1:
        if history[i]["role"] == "user" and history[i+1]["role"] == "assistant":
            pairs.append((history[i], history[i+1]))
        i += 2

    # 只保留最近的k组对话对
    recent_pairs = pairs[-k:] if len(pairs) > 2 else pairs

    # 构建新的历史消息列表
    new_history = []
    if system_message:
        new_history.append(system_message)

    # 添加最近的2组对话对
    for user_msg, assistant_msg in recent_pairs:
        new_history.append(user_msg)
        new_history.append(assistant_msg)

    return new_history

