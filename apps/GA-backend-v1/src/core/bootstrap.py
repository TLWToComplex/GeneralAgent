"""系统启动初始化编排

负责在应用启动时执行所有一次性初始化操作，如：
- 确保默认管理员账号存在
- 确保默认用户组存在
- 初始化截图服务配置
"""
import logging
import os
import atexit

logger = logging.getLogger(__name__)


def ensure_default_data():
    """确保系统默认数据存在（管理员账号、默认用户组等）"""
    from src.services.ai_user_service import AIUserService
    AIUserService.ensure_default_admin()
    AIUserService.ensure_default_group()


def init_screenshot():
    """初始化截图服务配置"""
    try:
        from src.config import ScreenshotConfig
        from src.utils.screenshot_utils import ScreenshotManager
        ScreenshotManager.save_config(
            save_dir=os.path.abspath(ScreenshotConfig.SAVE_DIR),
            default_width=ScreenshotConfig.DEFAULT_WIDTH,
            default_height=ScreenshotConfig.DEFAULT_HEIGHT,
            default_timeout=ScreenshotConfig.DEFAULT_TIMEOUT,
        )
        logger.info(f"截图服务配置已加载，保存目录: {os.path.abspath(ScreenshotConfig.SAVE_DIR)}")
    except Exception as e:
        logger.warning(f"截图服务配置加载失败: {e}")


def shutdown_screenshot():
    """关闭时清理 Playwright 浏览器"""
    try:
        from src.utils.screenshot_utils import ScreenshotManager
        if ScreenshotManager._instance:
            ScreenshotManager.get_instance().shutdown()
    except Exception:
        pass


def register_shutdown_hooks():
    """注册进程退出时的清理回调"""
    atexit.register(shutdown_screenshot)
