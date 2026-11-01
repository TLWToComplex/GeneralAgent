"""图形验证码生成器。

逻辑与老项目 ``src/utils/captcha_utils.py`` 一致：4 位字符（剔除易混淆字符），
带干扰线与噪点，输出 PNG 的 Base64 编码。
"""
from __future__ import annotations

import base64
import io
import logging
import random
import string
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class CaptchaGenerator:
    """图形验证码生成器。"""

    #: 字符集（排除易混淆字符：0, O, I, l, 1）
    CAPTCHA_CHARS = "".join(set(string.ascii_uppercase + string.digits) - {"0", "O", "I", "l", "1"})

    def __init__(self, length: int = 4, width: int = 140, height: int = 40) -> None:
        self.length = length
        self.width = width
        self.height = height
        self._font: ImageFont.ImageFont | None = None

    def generate_code(self) -> str:
        """生成随机验证码字符串。"""
        return "".join(random.choices(self.CAPTCHA_CHARS, k=self.length))

    def _get_random_color(self, min_val: int = 50, max_val: int = 200) -> tuple[int, int, int]:
        return (
            random.randint(min_val, max_val),
            random.randint(min_val, max_val),
            random.randint(min_val, max_val),
        )

    def _load_font(self) -> ImageFont.ImageFont:
        """加载字体，Windows/Linux 均失败时退回 Pillow 内置字体。"""
        if self._font is not None:
            return self._font
        for name in ("arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
            try:
                self._font = ImageFont.truetype(name, 24)
                return self._font
            except Exception:
                continue
        self._font = ImageFont.load_default()
        return self._font

    def _draw_interference_lines(self, draw: ImageDraw.ImageDraw) -> None:
        for _ in range(random.randint(2, 4)):
            start_point = (random.randint(0, self.width // 3), random.randint(0, self.height))
            end_point = (random.randint(self.width * 2 // 3, self.width), random.randint(0, self.height))
            draw.line([start_point, end_point], fill=self._get_random_color(100, 200), width=1)

    def _draw_noise_points(self, draw: ImageDraw.ImageDraw) -> None:
        for _ in range(random.randint(30, 50)):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            draw.point((x, y), fill=self._get_random_color(100, 200))

    def generate_image(self, code: str) -> Image.Image:
        """生成验证码图片。"""
        image = Image.new("RGB", (self.width, self.height), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        self._draw_interference_lines(draw)
        self._draw_noise_points(draw)

        font_size = 24
        font = self._load_font()
        char_width = self.width // (self.length + 1)

        for index, char in enumerate(code):
            x = char_width * (index + 1) - font_size // 4
            y = (self.height - font_size) // 2 + random.randint(-3, 3)
            color = (random.randint(20, 80), random.randint(20, 80), random.randint(20, 80))
            draw.text((x, y), char, font=font, fill=color)

        return image

    def generate(self) -> Tuple[str, str]:
        """生成验证码，返回 ``(答案, PNG Base64)``。"""
        code = self.generate_code()
        image = self.generate_image(code)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        logger.debug("验证码已生成: %s", code)
        return code, image_base64