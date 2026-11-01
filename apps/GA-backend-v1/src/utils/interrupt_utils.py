"""
会话中断管理工具
用于管理对话过程中的中断标志
"""
import threading
from typing import Dict

_lock = threading.RLock()
_interrupt_flags: Dict[str, bool] = {}


def set_interrupt_flag(session_id: str):
    """
    设置中断标志
    
    Args:
        session_id: 会话ID
    """
    with _lock:
        _interrupt_flags[session_id] = True


def clear_interrupt_flag(session_id: str):
    """
    清除中断标志
    
    Args:
        session_id: 会话ID
    """
    with _lock:
        _interrupt_flags.pop(session_id, None)


def check_interrupt(session_id: str) -> bool:
    """
    检查是否有中断请求
    
    Args:
        session_id: 会话ID
        
    Returns:
        True 如果有中断请求，否则 False
    """
    with _lock:
        return _interrupt_flags.get(session_id, False)
