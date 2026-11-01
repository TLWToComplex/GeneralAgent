"""密码强度校验器。

从老项目 ``src/utils/password_validator.py`` 原样迁移，规则顺序与提示语保持一致，
避免前端提示文案发生变化。
"""
from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class PasswordValidator:
    """密码强度校验器。"""

    COMMON_PASSWORDS = {
        "123456", "password", "12345678", "qwerty", "123456789",
        "12345", "1234", "111111", "1234567", "sunshine",
        "qwerty123", "0", "admin", "admin123", "Aa123456",
        "Password1", "123123", "abc123", "iloveyou", "admin123456",
        "welcome", "monkey", "dragon", "master", "passw0rd",
        "letmein", "shadow", "666666", "888888", "654321",
        "1234567890", "a123456", "123qwe", "qwe123", "1q2w3e4r",
        "zxcvbnm", "1qaz2wsx", "pass", "p@ssw0rd", "password123",
        "admin2024", "admin2025", "test123", "test", "guest",
        "default", "system", "root", "sa", "changeme",
        "000000", "147258", "159357", "112233", "121212",
        "qwertyuiop", "asdfghjkl", "zxcvbnm,", "qwerty1",
        "pass123", "pwd123", "admin1234", "abc123456",
    }

    KEYBOARD_PATTERNS = [
        "qwertyuiop", "asdfghjkl", "zxcvbnm",
        "qwerty", "asdfgh", "zxcvbn",
        "1qaz2wsx", "3edc4rfv", "zaq1xsw2",
        "!qaz@wsx", "qwe", "asd", "zxc",
        "qweasd", "qwerasdf", "qwertyasdf",
        "qazwsx", "wsxedc", "edcrfv",
        "rfvtgb", "tgbzhn", "yhnujm",
        "qscwdv", "wsxzaq",
    ]

    @classmethod
    def validate_password(
        cls,
        password: str,
        username: Optional[str] = None,
        password_history_hashes: Optional[list] = None,
    ) -> dict:
        """校验密码强度。

        Returns:
            dict: ``{"valid": bool, "message": str}``
        """
        if not password or not isinstance(password, str):
            return {"valid": False, "message": "密码不能为空"}

        if len(password) < 10:
            return {"valid": False, "message": "密码长度不能少于10位"}
        if len(password) > 128:
            return {"valid": False, "message": "密码长度不能超过128位"}

        if username and username.lower() in password.lower():
            return {"valid": False, "message": "密码不能包含用户名"}

        if not re.search(r"[A-Z]", password):
            return {"valid": False, "message": "密码必须包含至少一个大写字母"}
        if not re.search(r"[a-z]", password):
            return {"valid": False, "message": "密码必须包含至少一个小写字母"}
        if not re.search(r"[0-9]", password):
            return {"valid": False, "message": "密码必须包含至少一个数字"}
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:'\",.<>?/~`]", password):
            return {"valid": False, "message": "密码必须包含至少一个特殊符号（如 !@# 等）"}

        if password.lower() in cls.COMMON_PASSWORDS:
            return {"valid": False, "message": "该密码过于常见，请使用更复杂的密码"}

        password_lower = password.lower()
        for pattern in cls.KEYBOARD_PATTERNS:
            if pattern in password_lower:
                return {"valid": False, "message": "密码不能包含键盘连续字符（如 qwerty）"}

        if re.search(r"(.)\1{2,}", password):
            return {"valid": False, "message": "密码不能包含连续3个及以上相同字符"}

        for i in range(len(password) - 2):
            segment = password[i:i + 3]
            if segment.isalpha():
                c0, c1, c2 = (ord(ch.lower()) for ch in segment)
                if (c1 - c0 == 1 and c2 - c1 == 1) or (c1 - c0 == -1 and c2 - c1 == -1):
                    return {"valid": False, "message": "密码不能包含连续字母序列（如 abc、cba）"}

        for i in range(len(password) - 2):
            segment = password[i:i + 3]
            if segment.isdigit():
                d0, d1, d2 = (int(ch) for ch in segment)
                if (d1 - d0 == 1 and d2 - d1 == 1) or (d1 - d0 == -1 and d2 - d1 == -1):
                    return {"valid": False, "message": "密码不能包含连续数字序列（如 123、321）"}

        if password_history_hashes:
            from app.core.security import verify_password_hash

            for stored_hash in password_history_hashes:
                if verify_password_hash(stored_hash, password):
                    return {"valid": False, "message": "密码不能与近5次历史密码相同"}

        logger.debug("密码校验通过")
        return {"valid": True, "message": "密码强度合格"}