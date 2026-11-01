"""
验证码生成工具类
使用 Pillow 生成图形验证码图片
"""
import random
import string
import base64
import io
import logging
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class CaptchaGenerator:
    """
    验证码生成器
    生成带干扰线的图形验证码图片
    """
    
    # 验证码字符集（排除易混淆字符：0, O, I, l, 1）
    CAPTCHA_CHARS = ''.join(set(string.ascii_uppercase + string.digits) - {'0', 'O', 'I', 'l', '1'})
    
    def __init__(self, length: int = 4, width: int = 140, height: int = 40):
        """
        初始化验证码生成器
        
        :param length: 验证码字符长度，默认4位
        :param width: 图片宽度，默认140
        :param height: 图片高度，默认40
        """
        self.length = length
        self.width = width
        self.height = height
    
    def generate_code(self) -> str:
        """
        生成随机验证码字符串
        
        :return: 随机验证码字符串
        """
        return ''.join(random.choices(self.CAPTCHA_CHARS, k=self.length))
    
    def _get_random_color(self, min_val: int = 50, max_val: int = 200) -> tuple:
        """
        生成随机颜色
        
        :param min_val: 最小值
        :param max_val: 最大值
        :return: RGB颜色元组
        """
        return (random.randint(min_val, max_val),
                random.randint(min_val, max_val),
                random.randint(min_val, max_val))
    
    def _draw_interference_lines(self, draw: ImageDraw.Draw) -> None:
        """
        绘制干扰线
        
        :param draw: ImageDraw 对象
        """
        for _ in range(random.randint(2, 4)):
            start_point = (random.randint(0, self.width // 3), random.randint(0, self.height))
            end_point = (random.randint(self.width * 2 // 3, self.width), random.randint(0, self.height))
            draw.line([start_point, end_point], fill=self._get_random_color(100, 200), width=1)
    
    def _draw_noise_points(self, draw: ImageDraw.Draw) -> None:
        """
        绘制噪点
        
        :param draw: ImageDraw 对象
        """
        for _ in range(random.randint(30, 50)):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            draw.point((x, y), fill=self._get_random_color(100, 200))
    
    def generate_image(self, code: str) -> Image.Image:
        """
        生成验证码图片
        
        :param code: 验证码字符串
        :return: PIL Image 对象
        """
        # 创建白色背景图片
        image = Image.new('RGB', (self.width, self.height), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # 绘制干扰线
        self._draw_interference_lines(draw)
        
        # 绘制噪点
        self._draw_noise_points(draw)
        
        # 计算字符间距和起始位置
        char_width = self.width // (self.length + 1)
        
        # 尝试加载字体，如果失败则使用默认字体
        try:
            # 尝试使用系统字体
            font_size = 24
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            except Exception:
                font = ImageFont.load_default()
        
        # 绘制验证码字符
        for i, char in enumerate(code):
            x = char_width * (i + 1) - font_size // 4
            y = (self.height - font_size) // 2 + random.randint(-3, 3)
            
            # 随机颜色（较深的颜色，确保可读性）
            color = (random.randint(20, 80), random.randint(20, 80), random.randint(20, 80))
            
            # 绘制字符
            draw.text((x, y), char, font=font, fill=color)
        
        return image
    
    def generate(self) -> tuple[str, str]:
        """
        生成验证码图片并返回 Base64 编码
        
        :return: (验证码答案, Base64编码的图片字符串)
        """
        # 生成验证码
        code = self.generate_code()
        
        # 生成图片
        image = self.generate_image(code)
        
        # 转换为 Base64
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        logger.debug(f"Captcha generated: {code}")
        
        return code, image_base64


# 全局验证码生成器实例
captcha_generator = CaptchaGenerator()
