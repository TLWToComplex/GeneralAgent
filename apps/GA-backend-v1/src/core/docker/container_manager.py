"""
Docker 容器管理器模块。
用于创建和管理 Docker 容器。
"""
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ContainerManager:
    """
    容器管理器，用于创建和管理Docker容器
    """

    def __init__(self):
        """
        初始化容器管理器
        """
        import docker
        self.client = docker.from_env()

    def create_container(
        self,
        image_name: str,
        container_name: str,
        command: str,
        volumes: Optional[Dict[str, Any]] = None,
        working_dir: Optional[str] = None,
        detach: bool = True,
        auto_remove: bool = False,
        environment: Optional[Dict[str, str]] = None,
    ):
        """
        创建或获取容器

        Args:
            image_name: 镜像名称
            container_name: 容器名称
            command: 启动命令
            volumes: 挂载卷
            working_dir: 工作目录
            detach: 是否后台运行
            auto_remove: 是否自动删除
            environment: 容器环境变量，键值对形式

        Returns:
            容器对象
        """
        try:
            # 尝试获取现有容器
            container = self.client.containers.get(container_name)
            logger.info(f"使用现有容器: {container_name}")

            # 检查容器状态
            if container.status != 'running':
                logger.info(f"启动容器: {container_name}")
                container.start()

            return container
        except Exception:
            # 容器不存在，创建新容器
            logger.info(f"创建新容器: {container_name}")

            # 准备参数
            kwargs = {
                'image': image_name,
                'name': container_name,
                'command': command,
                'detach': detach,
                'auto_remove': auto_remove
            }

            # 添加可选参数
            if volumes:
                kwargs['volumes'] = volumes
            if working_dir:
                kwargs['working_dir'] = working_dir
            if environment:
                kwargs['environment'] = environment

            # 创建容器
            container = self.client.containers.run(**kwargs)
            logger.info(f"容器创建成功: {container_name}")

            return container

    def stop_container(self, container_name: str):
        """
        停止容器

        Args:
            container_name: 容器名称
        """
        try:
            container = self.client.containers.get(container_name)
            if container.status == 'running':
                logger.info(f"停止容器: {container_name}")
                container.stop()
        except Exception as e:
            logger.warning(f"停止容器失败 {container_name}: {e}")

    def remove_container(self, container_name: str, force: bool = False):
        """
        删除容器

        Args:
            container_name: 容器名称
            force: 是否强制删除
        """
        try:
            container = self.client.containers.get(container_name)
            if container.status == 'running':
                self.stop_container(container_name)
            logger.info(f"删除容器: {container_name}")
            container.remove(force=force)
        except Exception as e:
            logger.warning(f"删除容器失败 {container_name}: {e}")


# 创建容器管理器实例
container_manager = ContainerManager()
