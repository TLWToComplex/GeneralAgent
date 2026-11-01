"""
网页截图控制器

提供 POST /api/screenshot 接口
"""

import os
import logging
from flask import request, jsonify, send_file
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class ScreenshotController:
    """截图接口控制器"""

    @staticmethod
    def take_screenshot() -> Tuple[Dict, int]:
        """
        网页截图接口

        JSON Payload:
            url         (必填)  目标网页地址
            width       (可选)  视口宽度，默认 1280
            height      (可选)  视口高度，默认 720
            isfullpage  (可选)  是否全页截图，默认 false
            timeout     (可选)  超时时间(ms)，默认 30000

        返回:
            成功: image/png 图片流
            失败: JSON 错误信息
        """
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"success": False, "error": "请求体必须为 JSON 格式"}), 400

        url = data.get("url", "").strip()
        if not url:
            return jsonify({"success": False, "error": "缺少必填字段: url"}), 400

        width = data.get("width")
        height = data.get("height")
        isfullpage = data.get("isfullpage", False)
        timeout = data.get("timeout")

        # 类型校验与转换，避免 JSON 字符串导致运行时异常
        try:
            width = int(width) if width is not None else None
            height = int(height) if height is not None else None
            timeout = int(timeout) if timeout is not None else None
        except (ValueError, TypeError) as e:
            return jsonify({"success": False, "error": f"参数类型错误: {e}"}), 400

        try:
            from src.utils.screenshot_utils import ScreenshotManager
            manager = ScreenshotManager.get_instance()

            output_path, filename = manager.take_screenshot(
                url=url,
                width=width,
                height=height,
                isfullpage=isfullpage,
                timeout=timeout,
            )

            return send_file(
                output_path,
                mimetype="image/png",
                as_attachment=False,
                download_name=filename,
            )

        except RuntimeError as e:
            logger.error(f"截图服务异常: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
        except Exception as e:
            logger.error(f"截图接口未知异常: [{type(e).__name__}] {e!r}", exc_info=True)
            return jsonify({"success": False, "error": f"截图失败: [{type(e).__name__}] {e}"}), 500

    @staticmethod
    def health() -> Tuple[Dict, int]:
        """截图服务健康检查"""
        try:
            from src.utils.screenshot_utils import ScreenshotManager
            manager = ScreenshotManager.get_instance()
            # 线程存活即视为健康
            alive = manager._thread is not None and manager._thread.is_alive()
            return jsonify({
                "status": "ok" if alive else "degraded",
                "worker_alive": alive,
            }), 200
        except Exception:
            return jsonify({"status": "not_initialized", "worker_alive": False}), 503
