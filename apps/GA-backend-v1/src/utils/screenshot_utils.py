"""
Playwright 网页截图工具

提供浏览器单例管理 + 截图功能，避免每次请求冷启动 Chromium。
Playwright 运行在独立专属线程中，通过队列接收任务，解决 Flask 多线程下的线程安全问题。
"""

import os
import logging
import threading
from datetime import datetime
from queue import Queue, Empty
from urllib.parse import urlparse
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class ScreenshotManager:
    """Playwright 浏览器管理器，在专属线程中运行，通过队列通信"""

    _instance: Optional["ScreenshotManager"] = None
    _lock = threading.Lock()

    # 类级别保存配置，启动时注入，首次使用时才启动线程
    _config = None

    def __init__(self, save_dir: str, default_width: int = 1280,
                 default_height: int = 720, default_timeout: int = 30000):
        self._save_dir = save_dir
        self._default_width = default_width
        self._default_height = default_height
        self._default_timeout = default_timeout
        self._task_queue: Queue = Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        # 初始化信号：用 Event 代替队列传递，避免工作线程自己消费掉 init 消息
        self._init_event = threading.Event()
        self._init_error: Optional[str] = None
        os.makedirs(save_dir, exist_ok=True)

    @classmethod
    def save_config(cls, save_dir: str, default_width: int = 1280,
                    default_height: int = 720, default_timeout: int = 30000):
        """保存配置（启动时调用），不创建浏览器实例"""
        cls._config = {
            "save_dir": save_dir,
            "default_width": default_width,
            "default_height": default_height,
            "default_timeout": default_timeout,
        }

    @classmethod
    def get_instance(cls) -> "ScreenshotManager":
        """获取单例实例，首次调用时用保存的配置初始化并启动专属线程"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    if cls._config is None:
                        raise RuntimeError("ScreenshotManager 未配置，请先调用 save_config()")
                    cfg = cls._config
                    instance = cls(cfg["save_dir"], cfg["default_width"],
                                   cfg["default_height"], cfg["default_timeout"])
                    instance._start_thread()
                    cls._instance = instance
        return cls._instance

    def _start_thread(self):
        """启动专属线程，在其中初始化并运行 Playwright"""
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        # 等待浏览器初始化完成（用 Event，避免队列竞态）
        if not self._init_event.wait(timeout=30):
            raise RuntimeError("浏览器初始化超时（30秒内未完成）")
        if self._init_error:
            raise RuntimeError(f"浏览器初始化失败: {self._init_error}")

    def _run_loop(self):
        """专属线程主循环：初始化浏览器 → 循环处理截图任务"""
        playwright = None
        browser = None
        try:
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            playwright = pw
            browser = pw.chromium.launch(headless=True)
            logger.info("Playwright Chromium 浏览器启动成功")
        except Exception as e:
            logger.error(f"Playwright 浏览器启动失败: {e}")
            self._init_error = str(e)
            self._init_event.set()
            return

        # 通知主线程初始化完成
        self._init_event.set()

        # 任务循环
        while not self._stop_event.is_set():
            try:
                task: Dict[str, Any] = self._task_queue.get(timeout=1)
            except Empty:
                continue

            if task.get("type") == "shutdown":
                break

            if task.get("type") == "screenshot":
                try:
                    result = self._do_screenshot(browser, task)
                    task["result_queue"].put(result)
                except Exception as e:
                    task["result_queue"].put({"success": False, "error": str(e)})

        # 清理
        try:
            if browser:
                browser.close()
            if playwright:
                playwright.stop()
            logger.info("Playwright 浏览器已关闭")
        except Exception as e:
            logger.error(f"Playwright 浏览器关闭异常: {e}")

    def _do_screenshot(self, browser, task: Dict[str, Any]) -> Dict[str, Any]:
        """在专属线程中执行截图"""
        url = task["url"]
        width = task["width"] or self._default_width
        height = task["height"] or self._default_height
        timeout = task["timeout"] or self._default_timeout
        isfullpage = task["isfullpage"]

        # 自动补全协议前缀
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        filename = self._generate_filename(url)
        output_path = os.path.join(self._save_dir, filename)

        context = None
        try:
            context = browser.new_context(
                viewport={"width": width, "height": height},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            # 等待页面基本渲染（网络空闲短窗口），兼顾速度与内容完整性
            page.wait_for_timeout(2000)
            page.screenshot(path=output_path, full_page=isfullpage)

            file_size = os.path.getsize(output_path)
            logger.info(f"截图成功: {url} | fullpage={isfullpage} | {file_size / 1024:.1f} KB -> {output_path}")
            return {"success": True, "output_path": output_path, "filename": filename}

        except Exception as e:
            logger.error(f"截图失败: {url} | {e}")
            return {"success": False, "error": str(e)}

        finally:
            if context:
                try:
                    context.close()
                except Exception:
                    pass

    def shutdown(self):
        """关闭浏览器，释放资源"""
        with self._lock:
            try:
                if self._thread and self._thread.is_alive():
                    self._task_queue.put({"type": "shutdown"})
                    self._thread.join(timeout=10)
                logger.info("ScreenshotManager 已关闭")
            except Exception as e:
                logger.error(f"ScreenshotManager 关闭异常: {e}")
            finally:
                ScreenshotManager._instance = None

    @staticmethod
    def _generate_filename(url: str) -> str:
        """根据 URL 和时间戳生成文件名"""
        parsed = urlparse(url)
        domain = parsed.netloc.replace(":", "_").replace(".", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"screenshot_{domain}_{timestamp}.png"

    def take_screenshot(
        self,
        url: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        isfullpage: bool = False,
        timeout: Optional[int] = None,
    ) -> Tuple[str, str]:
        """
        对指定 URL 截图（通过队列提交任务到专属线程执行）

        Args:
            url: 目标网页地址
            width: 视口宽度，默认使用配置值
            height: 视口高度，默认使用配置值
            isfullpage: 是否全页截图
            timeout: 超时时间(ms)

        Returns:
            (文件绝对路径, 文件名)

        Raises:
            RuntimeError: 截图失败
        """
        result_queue: Queue = Queue()
        task = {
            "type": "screenshot",
            "url": url,
            "width": width,
            "height": height,
            "isfullpage": isfullpage,
            "timeout": timeout,
            "result_queue": result_queue,
        }
        self._task_queue.put(task)

        # 等待结果，超时略大于截图 timeout
        wait_timeout = (timeout or self._default_timeout) / 1000 + 10
        try:
            result = result_queue.get(timeout=wait_timeout)
        except Empty:
            raise RuntimeError(f"截图超时: {url}")

        if result.get("success"):
            return result["output_path"], result["filename"]
        else:
            raise RuntimeError(f"截图失败: {result.get('error')}")