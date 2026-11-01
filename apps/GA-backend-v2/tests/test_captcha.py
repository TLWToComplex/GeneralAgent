"""验证码接口测试（GET /captcha）。"""
from __future__ import annotations

import base64

from tests.support import ApiTestCase


class CaptchaApiTest(ApiTestCase):
    def test_captcha_response_contract(self) -> None:
        """响应结构与老项目一致：code/message/data.captchaId/captchaImage。"""
        response = self.client.get("/captcha")
        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(body["code"], 200)
        self.assertEqual(body["message"], "success")
        self.assertIn("captchaId", body["data"])
        self.assertTrue(body["data"]["captchaId"])
        self.assertTrue(body["data"]["captchaImage"].startswith("data:image/png;base64,"))

    def test_captcha_image_is_valid_png(self) -> None:
        """返回的 Base64 必须是可解码的 PNG 图片。"""
        body = self.client.get("/captcha").json()
        raw = base64.b64decode(body["data"]["captchaImage"].split(",", 1)[1])
        self.assertTrue(raw.startswith(b"\x89PNG\r\n\x1a\n"), "不是 PNG 数据")
        self.assertGreater(len(raw), 200)

    def test_captcha_id_is_unique(self) -> None:
        first = self.client.get("/captcha").json()["data"]["captchaId"]
        second = self.client.get("/captcha").json()["data"]["captchaId"]
        self.assertNotEqual(first, second)

    def test_captcha_answer_is_cached_with_configured_length(self) -> None:
        captcha_id, code = self.fetch_captcha()
        self.assertEqual(len(code), 4)
        self.assertEqual(self.app.state.captcha_cache.get(captcha_id), code)

    def test_unknown_captcha_id_is_rejected(self) -> None:
        """未申请过（或已被消费）的 captchaId 视为过期。"""
        response = self.login("nobody", "whatever", captcha_id="not-exist", captcha_code="ABCD")
        self.assert_error(self, response, 401, "验证码已过期，请重新获取")