"""
Agent 资源缓存管理器
用于缓存 MCP 客户端、KB 工具和编译好的 Agent 实例，避免重复初始化带来的性能损耗。
"""
import hashlib
import json
import logging
import threading
import time
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class AgentCacheManager:
    """
    Agent 资源缓存管理器
    基于实体 ID 统一管理 MCP、KB 和 Agent 实例的缓存。
    """
    def __init__(self, cache_ttl: int = 7200):  # 默认 2 小时
        # --- 缓存池定义 (Key 均为实体 ID) ---
        self._mcp_pool: Dict[str, Tuple[Any, float]] = {}           # MCP 客户端连接池 (instance, timestamp)
        self._kb_pool: Dict[str, Tuple[Any, float]] = {}            # KB 工具缓存池 (instance, timestamp)
        self._agent_pool: Dict[str, Tuple[Any, float]] = {}         # Agent 实例缓存池 (instance, timestamp)
        
        # --- 线程安全与配置 ---
        self._lock = threading.Lock()
        self.MAX_CACHE_SIZE = 50
        self.CACHE_TTL = cache_ttl  # 统一缓存过期时间（秒），默认 2 小时

    async def get_or_create_async(self, pool_name: str, entity_id: str, factory_func) -> Any:
        """
        异步版本的获取或创建方法（用于 Agent）
        :param pool_name: 缓存池名称 ('mcp', 'kb', 'agent')
        :param entity_id: 实体 ID(agent_id + session_thread_id)
        :param factory_func: 异步初始化回调函数
        """
        pool_map = {
            'mcp': self._mcp_pool,
            'kb': self._kb_pool,
            'agent': self._agent_pool
        }
        
        if pool_name not in pool_map:
            raise ValueError(f"Unknown pool name: {pool_name}")
            
        target_pool = pool_map[pool_name]
        
        with self._lock:
            # 检查缓存是否存在且未过期（所有缓存类型都使用统一的 TTL）
            if entity_id in target_pool:
                instance, timestamp = target_pool[entity_id]
                if time.time() - timestamp < self.CACHE_TTL:
                    logger.info(f"[{pool_name}] 缓存命中: {entity_id} (已缓存 {int(time.time() - timestamp)} 秒)")
                    return instance
                else:
                    logger.info(f"[{pool_name}] 缓存过期: {entity_id} (已存在 {int(time.time() - timestamp)} 秒，超过 TTL {self.CACHE_TTL} 秒)")
                    del target_pool[entity_id]
            
            logger.info(f"[{pool_name}] 缓存未命中，开始创建新实例: {entity_id}")
            
            # 调用异步工厂函数（所有工厂函数都是异步的）
            import asyncio
            instance = await factory_func()
            
            # 容量控制
            if len(target_pool) >= self.MAX_CACHE_SIZE:
                # LRU: 删除最旧的（所有缓存都使用时间戳）
                oldest_key = min(target_pool, key=lambda k: target_pool[k][1])
                target_pool.pop(oldest_key)
                logger.info(f"缓存已满，删除最旧项: {oldest_key}")
            
            # 所有缓存都记录时间戳 (instance, timestamp)
            target_pool[entity_id] = (instance, time.time())
            
            return instance

    def invalidate(self, pool_name: str, entity_id: str = None):
        """清除指定缓存"""
        pool_map = {
            'mcp': self._mcp_pool,
            'kb': self._kb_pool,
            'agent': self._agent_pool
        }
        with self._lock:
            if entity_id:
                pool_map.get(pool_name, {}).pop(entity_id, None)
            else:
                pool_map.get(pool_name, {}).clear()
            logger.info(f"已清除 [{pool_name}] 缓存")

# 全局单例
agent_cache_manager = AgentCacheManager()
