"""
沙盒控制器模块。
处理沙盒创建、释放、管理等API端点。
"""
import logging
import time
import threading
from contextlib import contextmanager
from typing import Dict, Any, Optional
from flask import jsonify
from src.utils.config_manager import config_manager
from src.core.docker.sandbox_backend import DockerSandboxBackend

# 获取logger
logger = logging.getLogger(__name__)


class SandboxController:
    """沙盒控制器"""

    # 沙盒最大存活时间：24小时（秒）
    SANDBOX_MAX_LIFETIME = 24 * 3600

    def __init__(self):
        """
        初始化沙盒控制器
        """
        # 内存存储沙盒信息
        self.sandboxes: Dict[str, Dict[str, Any]] = {}
        # 全局锁：仅用于保护 sandboxes / _session_locks 字典的快速读写，
        # 严禁在持有全局锁期间执行创建/关闭容器等慢操作，
        # 否则一个会话的慢操作会阻塞所有其它请求
        self._lock = threading.RLock()
        # 每个会话独立的锁（带引用计数）：用于串行化同一会话的沙盒创建/释放，
        # 不同会话之间互不阻塞。
        # 值为 [RLock, refcount]：refcount 记录"正在使用或等待该锁"的线程数，
        # 归零时才从字典中删除，避免直接 pop 导致的竞态
        # （若某线程正阻塞等待旧锁对象，此时 pop 后新线程会创建新锁进入临界区，
        #  两个线程将同时操作同一会话，可能并发创建两个同名容器）。
        # 引用计数也保证长期运行时 _session_locks 不会随会话数无限增长。
        self._session_locks: Dict[str, list] = {}
        # 清理调度器
        self._cleanup_scheduler = None
        self._cleanup_interval = config_manager.get_sandbox_cleanup_interval()
        self._sandbox_timeout = config_manager.get_sandbox_timeout()
        self._sandbox_max_lifetime = self.SANDBOX_MAX_LIFETIME

    @contextmanager
    def _session_lock(self, session_thread_id: str):
        """获取指定会话的独立锁（上下文管理器，带引用计数自动清理）。

        进入时对引用计数 +1（在全局锁保护下），退出时 -1，
        归零说明没有任何线程持有或等待该锁，此时安全地从字典中删除。
        全局锁只在计数操作期间短暂持有，慢操作（创建/关闭容器）
        只持有会话锁，避免跨会话互相阻塞。
        """
        # 1. 引用计数 +1，拿到锁对象
        with self._lock:
            entry = self._session_locks.get(session_thread_id)
            if entry is None:
                entry = [threading.RLock(), 0]
                self._session_locks[session_thread_id] = entry
            entry[1] += 1
            lock = entry[0]

        try:
            # 2. 持锁执行业务（慢操作期间不占用全局锁）
            with lock:
                yield
        finally:
            # 3. 引用计数 -1，归零则删除（此时必然无人持有/等待该锁）
            with self._lock:
                entry = self._session_locks.get(session_thread_id)
                if entry is not None and entry[0] is lock:
                    entry[1] -= 1
                    if entry[1] <= 0:
                        del self._session_locks[session_thread_id]

    def create_sandbox_backend(self, session_thread_id: str,
                                agent_uuid: str = None,
                                user_uuid: str = None,
                                skill_replacements: dict = None,
                                user_token: str = None) -> Dict[str, Any]:
        """
        创建沙盒后端（内部方法）

        Args:
            session_thread_id: 会话线程ID
            agent_uuid: 智能体 UUID（用于记忆 per-user 挂载，可选）
            user_uuid: 用户 UUID（来自 JWT 解析，用于记忆 per-user 挂载，可选）
            skill_replacements: skill folder_name -> additional_info 映射，用于 skill.md 占位符替换
            user_token: 用户 token

        Returns:
            沙盒信息字典
        """
        # 只持有会话级锁：同一会话的并发创建被串行化，
        # 但不会阻塞其它会话或只读接口（status/list 等）
        with self._session_lock(session_thread_id):
            # 检查沙盒是否已存在（全局锁只保护字典快速读取）
            with self._lock:
                existing = self.sandboxes.get(session_thread_id)
            if existing is not None:
                logger.info(f"沙盒已存在: {session_thread_id}")
                # 更新最后使用时间
                existing['last_used'] = time.time()
                return existing

            # 创建新沙盒（Docker 容器创建/启动是慢操作，在全局锁之外执行）
            try:
                # 生成容器名称
                container_name = f"skill-agent-sandbox-{session_thread_id}"

                # 创建Docker沙盒后端
                backend = DockerSandboxBackend(
                    image=config_manager.get_docker_image(),
                    container_name=container_name,
                    work_dir=config_manager.get_work_dir(),
                    mount_skills=config_manager.get_mount_skills(),
                    agent_uuid=agent_uuid,
                    user_uuid=user_uuid,
                    skill_replacements=skill_replacements,
                    user_token=user_token,
                    session_thread_id=session_thread_id
                )

                # 存储沙盒信息
                sandbox_info = {
                    'session_thread_id': session_thread_id,
                    'container_name': container_name,
                    'backend': backend,
                    'agent_uuid': agent_uuid,
                    'user_uuid': user_uuid,
                    'created_at': time.time(),
                    'last_used': time.time(),
                    'status': 'idle'  # 状态：idle(空闲) / running(运行中)
                }

                with self._lock:
                    self.sandboxes[session_thread_id] = sandbox_info
                logger.info(f"创建沙盒成功: {session_thread_id}, 容器: {container_name}")

                return sandbox_info
            except Exception as e:
                logger.error(f"创建沙盒失败: {e}")
                raise

    def create_sandbox(self, session_thread_id: str) -> tuple[Dict[str, Any], int]:
        """
        创建沙盒（API接口方法）

        Args:
            session_thread_id: 会话线程ID

        Returns:
            (response_dict, status_code)
        """
        try:
            if not session_thread_id:
                return jsonify({'code': 400, 'message': '缺少 session_thread_id 参数'}), 400

            sandbox_info = self.create_sandbox_backend(session_thread_id)

            # 只返回可序列化的数据，不包含backend对象
            serializable_sandbox_info = {
                'session_thread_id': sandbox_info['session_thread_id'],
                'container_name': sandbox_info['container_name'],
                'created_at': sandbox_info['created_at'],
                'last_used': sandbox_info['last_used']
            }

            logger.info(f"创建沙盒成功: {serializable_sandbox_info}")
            return jsonify({
                "code": 0,
                "message": "success",
                "data": serializable_sandbox_info
            }), 200
        except Exception as e:
            logger.error(f"创建沙盒失败: {str(e)}")
            return jsonify({
                "code": 500,
                "message": f"创建沙盒失败: {str(e)}"
            }), 500

    def release_sandbox_backend(self, session_thread_id: str):
        """
        释放沙盒后端（内部方法）

        Args:
            session_thread_id: 会话线程ID
        """
        with self._session_lock(session_thread_id):
            # 先在全局锁保护下从字典中移除（快速操作），
            # 避免其它请求再拿到即将关闭的 backend
            with self._lock:
                sandbox_info = self.sandboxes.pop(session_thread_id, None)

            # 检查沙盒是否存在
            if sandbox_info is None:
                logger.warning(f"沙盒不存在: {session_thread_id}")
                return

            try:
                # 关闭后端（container.stop/remove 是慢操作，在全局锁之外执行）
                if sandbox_info.get('backend'):
                    sandbox_info['backend'].close()
                    logger.info(f"关闭沙盒后端: {session_thread_id}")
            except Exception as e:
                logger.error(f"关闭沙盒后端失败: {e}")
            finally:
                logger.info(f"释放沙盒成功: {session_thread_id}")

    def release_sandbox(self, session_thread_id: str) -> tuple[Dict[str, Any], int]:
        """
        释放沙盒（API接口方法）

        Args:
            session_thread_id: 会话线程ID

        Returns:
            (response_dict, status_code)
        """
        try:
            if not session_thread_id:
                return jsonify({'code': 400, 'message': '缺少 session_thread_id 参数'}), 400

            # 调用 release_sandbox 方法释放沙盒
            # 即使沙盒信息不存在于内存中，也会尝试通过会话线程 ID 生成容器名称并释放
            self.release_sandbox_backend(session_thread_id)

            # 无论是否成功，都返回成功响应
            # 因为即使沙盒不存在，我们也已经尝试释放它了
            return jsonify({
                "code": 0,
                "message": "success"
            }), 200
        except Exception as e:
            logger.error(f"释放沙盒失败: {str(e)}")
            return jsonify({
                "code": 500,
                "message": f"释放沙盒失败: {str(e)}"
            }), 500

    def get_sandbox_backend(self, session_thread_id: str,
                             agent_uuid: str = None,
                             user_uuid: str = None,
                             skill_replacements: dict = None,
                             user_token: str = None) -> Optional[DockerSandboxBackend]:
        """
        获取沙盒后端，如果不存在则自动创建（内部方法）

        Args:
            session_thread_id: 会话线程ID
            agent_uuid: 智能体 UUID（仅在沙盒尚未创建时用于记忆挂载）
            user_uuid: 用户 UUID（仅在沙盒尚未创建时用于记忆挂载）
            skill_replacements: skill folder_name -> additional_info 映射
            user_token: 用户 token

        Returns:
            DockerSandboxBackend 实例
        """
        # 会话级锁：同一会话的"检查+自动创建"保持原子，
        # 但不阻塞其它会话和其它接口
        with self._session_lock(session_thread_id):
            with self._lock:
                exists = session_thread_id in self.sandboxes

            # 检查沙盒是否存在，不存在则创建（慢操作在全局锁之外）
            if not exists:
                logger.info(f"沙盒不存在，自动创建: {session_thread_id}")
                self.create_sandbox_backend(session_thread_id, agent_uuid=agent_uuid,
                                            user_uuid=user_uuid, skill_replacements=skill_replacements, user_token=user_token)
            elif skill_replacements:
                with self._lock:
                    self.sandboxes[session_thread_id]['backend']._skill_replacements = skill_replacements

            # 更新最后使用时间和状态
            with self._lock:
                sandbox_info = self.sandboxes[session_thread_id]
                sandbox_info['last_used'] = time.time()
                sandbox_info['status'] = 'running'
                return sandbox_info['backend']

    def get_sandbox_backend_if_exists(self, session_thread_id: str) -> Optional[DockerSandboxBackend]:
        """获取已存在的沙箱后端，不存在时返回 None（不自动创建）。

        用于流结束后的兜底文件扫描，避免意外启动新容器。
        """
        with self._lock:
            sandbox_info = self.sandboxes.get(session_thread_id)
            if sandbox_info is None:
                return None
            return sandbox_info.get('backend')

    def set_sandbox_idle(self, session_thread_id: str):
        """
        设置沙盒为空闲状态

        Args:
            session_thread_id: 会话线程ID
        """
        with self._lock:
            if session_thread_id in self.sandboxes:
                self.sandboxes[session_thread_id]['status'] = 'idle'
                self.sandboxes[session_thread_id]['last_used'] = time.time()
                logger.debug(f"沙盒设置为空闲状态: {session_thread_id}")

    def get_sandbox_status(self, session_thread_id: str) -> tuple[Dict[str, Any], int]:
        """
        获取沙盒状态（API接口方法）

        Args:
            session_thread_id: 会话线程ID

        Returns:
            (response_dict, status_code)
        """
        try:
            if not session_thread_id:
                return jsonify({'code': 400, 'message': '缺少 session_thread_id 参数'}), 400

            # 检查沙盒是否存在
            with self._lock:
                exists = session_thread_id in self.sandboxes
                backend_exists = exists and 'backend' in self.sandboxes[session_thread_id]

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "session_thread_id": session_thread_id,
                    "status": "running" if exists else "not_found",
                    "sandbox_exists": exists,
                    "backend_exists": backend_exists
                }
            }), 200
        except Exception as e:
            logger.error(f"获取沙盒状态失败: {str(e)}")
            return jsonify({
                "code": 500,
                "message": f"获取沙盒状态失败: {str(e)}"
            }), 500

    def list_sandboxes(self) -> tuple[Dict[str, Any], int]:
        """
        列出所有活跃的沙盒（API接口方法）

        Returns:
            (response_dict, status_code)
        """
        try:
            # 获取内部存储的沙盒信息
            sandboxes = []
            with self._lock:
                for session_thread_id, sandbox_info in self.sandboxes.items():
                    sandboxes.append({
                        'session_thread_id': sandbox_info['session_thread_id'],
                        'container_name': sandbox_info['container_name'],
                        'created_at': sandbox_info['created_at'],
                        'last_used': sandbox_info['last_used']
                    })

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "count": len(sandboxes),
                    "sandboxes": sandboxes
                }
            }), 200
        except Exception as e:
            logger.error(f"列出沙盒失败: {str(e)}")
            return jsonify({
                "code": 500,
                "message": f"列出沙盒失败: {str(e)}"
            }), 500

    def cleanup_expired_sandboxes(self):
        """
        清理过期的沙盒（内部方法）
        清理条件：
        1. 沙盒处于空闲状态且空闲时间超过配置的超时时间
        2. 沙盒存在时间超过24小时（无论状态如何）
        """
        with self._lock:
            current_time = time.time()
            expired_session_ids = []

            # 找出需要清理的沙盒
            for session_thread_id, sandbox_info in self.sandboxes.items():
                created_at = sandbox_info.get('created_at', 0)
                last_used = sandbox_info.get('last_used', 0)
                status = sandbox_info.get('status', 'idle')
                
                # 条件1：沙盒空闲且空闲时间超过超时时间
                is_idle_timeout = (status == 'idle') and (current_time - last_used > self._sandbox_timeout)
                
                # 条件2：沙盒存在时间超过24小时
                is_max_lifetime_exceeded = (current_time - created_at > self._sandbox_max_lifetime)
                
                if is_idle_timeout or is_max_lifetime_exceeded:
                    reason = "空闲超时" if is_idle_timeout else "达到最大存活时间"
                    logger.info(f"沙盒 {session_thread_id} 满足清理条件: {reason}")
                    expired_session_ids.append(session_thread_id)

        # 释放过期的沙盒（必须在全局锁之外执行：
        # release_sandbox_backend 会获取会话锁并执行慢速的容器关闭操作，
        # 若在持有全局锁时调用，会与"持有会话锁等待全局锁"的线程交叉死锁）
        for session_thread_id in expired_session_ids:
            logger.info(f"清理过期沙盒: {session_thread_id}")
            self.release_sandbox_backend(session_thread_id)

    def start_scheduler(self):
        """
        启动清理调度器（内部方法）
        """
        if self._cleanup_scheduler is not None and self._cleanup_scheduler.is_alive():
            logger.info("清理调度器已经启动")
            return

        def cleanup_task():
            while True:
                try:
                    self.cleanup_expired_sandboxes()
                except Exception as e:
                    logger.error(f"清理沙盒失败: {e}")
                time.sleep(self._cleanup_interval)

        # 启动后台线程
        self._cleanup_scheduler = threading.Thread(target=cleanup_task, daemon=True)
        self._cleanup_scheduler.start()
        logger.info(f"清理调度器启动成功，间隔: {self._cleanup_interval}秒")

    def stop_scheduler(self):
        """
        停止清理调度器（内部方法）
        """
        if self._cleanup_scheduler is not None:
            # 由于使用了daemon线程，当主线程退出时会自动停止
            self._cleanup_scheduler = None
            logger.info("清理调度器停止成功")


# 全局沙盒控制器实例
sandbox_controller = SandboxController()
