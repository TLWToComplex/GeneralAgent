"""密码强度策略单元测试（老项目 PasswordValidator 的迁移校验）。"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app.core.password_policy import PasswordValidator
from app.core.security import hash_password


class PasswordPolicyTest(unittest.TestCase):
    def test_valid_password(self) -> None:
        result = PasswordValidator.validate_password("Kp!3RzT7Vm")
        self.assertTrue(result["valid"], result["message"])

    def test_empty(self) -> None:
        self.assertEqual(PasswordValidator.validate_password("")["message"], "密码不能为空")

    def test_too_short(self) -> None:
        self.assertEqual(
            PasswordValidator.validate_password("Kp!3RzT7V")["message"], "密码长度不能少于10位"
        )

    def test_too_long(self) -> None:
        message = PasswordValidator.validate_password("Kp!3" + "a" * 200)["message"]
        self.assertEqual(message, "密码长度不能超过128位")

    def test_contains_username(self) -> None:
        message = PasswordValidator.validate_password("Kp!3Zhangsan1", "zhangsan")["message"]
        self.assertEqual(message, "密码不能包含用户名")

    def test_requires_uppercase(self) -> None:
        self.assertEqual(
            PasswordValidator.validate_password("kp!3rzt7vm")["message"],
            "密码必须包含至少一个大写字母",
        )

    def test_requires_lowercase(self) -> None:
        self.assertEqual(
            PasswordValidator.validate_password("KP!3RZT7VM")["message"],
            "密码必须包含至少一个小写字母",
        )

    def test_requires_digit(self) -> None:
        self.assertEqual(
            PasswordValidator.validate_password("Kp!xRzTvVm")["message"],
            "密码必须包含至少一个数字",
        )

    def test_requires_special_char(self) -> None:
        self.assertEqual(
            PasswordValidator.validate_password("Kp13RzT7Vm")["message"],
            "密码必须包含至少一个特殊符号（如 !@# 等）",
        )

    def test_blacklisted_simple_password_is_rejected(self) -> None:
        """注意：老项目把复杂度校验排在黑名单之前，所以 'admin123456' 先报缺大写字母。"""
        result = PasswordValidator.validate_password("admin123456")
        self.assertFalse(result["valid"])
        self.assertEqual(result["message"], "密码必须包含至少一个大写字母")

    def test_common_password_blacklist_branch(self) -> None:
        """黑名单分支本身（用一个复杂度合格的密码验证该规则仍然生效）。

        注意：老项目是「密码转小写后比对黑名单集合」，所以集合里带大写字母的条目
        （如 'Aa123456'、'Password1'）永远匹配不到，迁移时保持原样。
        """
        with patch.object(PasswordValidator, "COMMON_PASSWORDS", {"kp!3rzt7vm"}):
            result = PasswordValidator.validate_password("Kp!3RzT7Vm")
        self.assertFalse(result["valid"])
        self.assertEqual(result["message"], "该密码过于常见，请使用更复杂的密码")

    def test_keyboard_sequence(self) -> None:
        self.assertEqual(
            PasswordValidator.validate_password("Kp!3qwertyZ")["message"],
            "密码不能包含键盘连续字符（如 qwerty）",
        )

    def test_repeated_characters(self) -> None:
        self.assertEqual(
            PasswordValidator.validate_password("Kp!3RzzzT7V")["message"],
            "密码不能包含连续3个及以上相同字符",
        )

    def test_alphabet_sequence(self) -> None:
        self.assertEqual(
            PasswordValidator.validate_password("Kp!3RabcT7V")["message"],
            "密码不能包含连续字母序列（如 abc、cba）",
        )

    def test_digit_sequence(self) -> None:
        self.assertEqual(
            PasswordValidator.validate_password("Kp!3RzT123")["message"],
            "密码不能包含连续数字序列（如 123、321）",
        )

    def test_history_reuse_rejected(self) -> None:
        history = [hash_password("Kp!3RzT7Vm")]
        result = PasswordValidator.validate_password(
            "Kp!3RzT7Vm", "someone", password_history_hashes=history
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["message"], "密码不能与近5次历史密码相同")

    def test_history_of_other_password_passes(self) -> None:
        history = [hash_password("Kp!9ZzQ2Wn")]
        result = PasswordValidator.validate_password(
            "Kp!3RzT7Vm", "someone", password_history_hashes=history
        )
        self.assertTrue(result["valid"], result["message"])