"""
验证码缓存管理器
用于存储和校验图形验证码，独立于 Agent 缓存。
"""
import threading
import time
import logging
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


class CaptchaCacheManager:
    """
    验证码缓存管理器
    基于内存存储验证码，支持 TTL 过期自动清理。
    """
    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """
        初始化验证码缓存管理器
        
        :param default_ttl: 默认过期时间（秒），默认 5 分钟
        :param max_size: 缓存最大容量，默认 1000
        """
        self._pool: Dict[str, Tuple[str, float]] = {}  # {captcha_id: (code, expire_time)}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._lock = threading.Lock()

    def set(self, captcha_id: str, code: str, ttl: int = None) -> None:
        """
        存储验证码
        
        :param captcha_id: 验证码唯一标识
        :param code: 验证码答案
        :param ttl: 过期时间（秒），默认使用初始化时的 default_ttl
        """
        expire_time = time.time() + (ttl if ttl is not None else self._default_ttl)
        with self._lock:
            # 容量控制：超过上限时删除最早过期（或最早创建）的验证码
            if len(self._pool) >= self._max_size:
                oldest_key = min(self._pool, key=lambda k: self._pool[k][1])
                self._pool.pop(oldest_key, None)
                logger.info(f"Captcha pool full, evicted oldest: {oldest_key}")
            
            self._pool[captcha_id] = (code, expire_time)
        logger.debug(f"Captcha stored: id={captcha_id}, ttl={ttl or self._default_ttl}")

    def get(self, captcha_id: str) -> Optional[str]:
        """
        获取验证码，不存在或已过期返回 None
        
        :param captcha_id: 验证码唯一标识
        :return: 验证码答案，或 None
        """
        with self._lock:
            if captcha_id not in self._pool:
                return None
            code, expire_time = self._pool[captcha_id]
            if time.time() > expire_time:
                del self._pool[captcha_id]
                return None
            return code

    def delete(self, captcha_id: str) -> None:
        """
        删除验证码
        
        :param captcha_id: 验证码唯一标识
        """
        with self._lock:
            self._pool.pop(captcha_id, None)

    def _cleanup_expired(self) -> None:
        """清理所有过期验证码（内部方法，按需调用）"""
        now = time.time()
        with self._lock:
            expired = [cid for cid, (_, et) in self._pool.items() if now > et]
            for cid in expired:
                self._pool.pop(cid, None)


# 全局验证码缓存实例
captcha_cache = CaptchaCacheManager()
