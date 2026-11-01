"""验证码缓存与生成器单元测试（不经 HTTP）。"""
from __future__ import annotations

import base64
import unittest

from app.core.captcha import CaptchaGenerator
from app.core.captcha_cache import CaptchaCacheManager


class CaptchaCacheTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cache = CaptchaCacheManager(default_ttl=300, max_size=3)

    def test_set_get_delete(self) -> None:
        self.cache.set("id-1", "ABCD")
        self.assertEqual(self.cache.get("id-1"), "ABCD")
        self.cache.delete("id-1")
        self.assertIsNone(self.cache.get("id-1"))

    def test_ttl_expiry(self) -> None:
        self.cache.set("id-1", "ABCD", ttl=-1)
        self.assertIsNone(self.cache.get("id-1"), "过期验证码应读取不到")
        self.assertEqual(len(self.cache), 0, "过期项应被清除")

    def test_default_ttl_keeps_entry_alive(self) -> None:
        self.cache.set("id-1", "ABCD")
        self.assertEqual(self.cache.get("id-1"), "ABCD")

    def test_max_size_evicts_earliest_expiring_entry(self) -> None:
        self.cache.set("a", "AAAA", ttl=100)
        self.cache.set("b", "BBBB", ttl=200)
        self.cache.set("c", "CCCC", ttl=300)
        self.cache.set("d", "DDDD", ttl=400)  # 触发淘汰
        self.assertEqual(len(self.cache), 3)
        self.assertIsNone(self.cache.get("a"), "最早过期的条目应被淘汰")
        self.assertEqual(self.cache.get("d"), "DDDD")

    def test_cleanup_expired(self) -> None:
        self.cache.set("a", "AAAA", ttl=-1)
        self.cache.set("b", "BBBB", ttl=-1)
        self.cache.set("c", "CCCC", ttl=60)
        self.assertEqual(self.cache.cleanup_expired(), 2)
        self.assertEqual(len(self.cache), 1)


class CaptchaGeneratorTest(unittest.TestCase):
    def test_generate_returns_code_and_png(self) -> None:
        generator = CaptchaGenerator()
        code, image_base64 = generator.generate()
        self.assertEqual(len(code), 4)
        raw = base64.b64decode(image_base64)
        self.assertTrue(raw.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_generate_code_excludes_confusing_chars(self) -> None:
        generator = CaptchaGenerator(length=200)
        code = generator.generate_code()
        for confusing in "0OIl1":
            self.assertNotIn(confusing, code)

    def test_generate_codes_are_random(self) -> None:
        generator = CaptchaGenerator(length=10)
        codes = {generator.generate_code() for _ in range(20)}
        self.assertGreater(len(codes), 1)