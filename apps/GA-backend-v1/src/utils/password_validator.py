"""
密码验证工具模块。
提供密码强度验证、弱密码黑名单检查等功能。
"""
import re
import logging

logger = logging.getLogger(__name__)


class PasswordValidator:
    """
    密码验证器。
    提供密码强度验证和弱密码检查功能。
    """

    # 常见弱密码黑名单（不区分大小写匹配）
    COMMON_PASSWORDS = {
        '123456', 'password', '12345678', 'qwerty', '123456789',
        '12345', '1234', '111111', '1234567', 'sunshine',
        'qwerty123', '0', 'admin', 'admin123', 'Aa123456',
        'Password1', '123123', 'abc123', 'iloveyou', 'admin123456',
        'welcome', 'monkey', 'dragon', 'master', 'passw0rd',
        'letmein', 'shadow', '666666', '888888', '654321',
        '1234567890', 'a123456', '123qwe', 'qwe123', '1q2w3e4r',
        'zxcvbnm', '1qaz2wsx', 'pass', 'p@ssw0rd', 'password123',
        'admin2024', 'admin2025', 'test123', 'test', 'guest',
        'default', 'system', 'root', 'sa', 'changeme',
        '000000', '147258', '159357', '112233', '121212',
        'qwertyuiop', 'asdfghjkl', 'zxcvbnm,', 'qwerty1',
        'pass123', 'pwd123', 'admin1234', 'abc123456',
    }

    # 键盘连续序列（不区分大小写匹配）
    KEYBOARD_PATTERNS = [
        'qwertyuiop', 'asdfghjkl', 'zxcvbnm',
        'qwerty', 'asdfgh', 'zxcvbn',
        '1qaz2wsx', '3edc4rfv', 'zaq1xsw2',
        '!qaz@wsx', 'qwe', 'asd', 'zxc',
        'qweasd', 'qwerasdf', 'qwertyasdf',
        'qazwsx', 'wsxedc', 'edcrfv',
        'rfvtgb', 'tgbzhn', 'yhnujm',
        'qscwdv', 'wsxzaq',
    ]

    @classmethod
    def validate_password(cls, password: str, username: str = None, password_history_hashes: list = None) -> dict:
        """
        验证密码强度。

        Args:
            password: 待验证的密码
            username: 用户名（可选，用于检查密码是否包含用户名）
            password_history_hashes: 近N次历史密码哈希列表（可选，用于检查是否与历史密码重复）

        Returns:
            dict: {
                'valid': bool,   # 是否通过验证
                'message': str   # 验证失败时的提示信息
            }
        """
        if not password or not isinstance(password, str):
            return {'valid': False, 'message': '密码不能为空'}

        # 1. 检查长度
        if len(password) < 10:
            return {'valid': False, 'message': '密码长度不能少于10位'}

        if len(password) > 128:
            return {'valid': False, 'message': '密码长度不能超过128位'}

        # 2. 检查是否包含用户名（不区分大小写）—— 优先于字符类型检查
        if username and username.lower() in password.lower():
            return {'valid': False, 'message': '密码不能包含用户名'}

        # 3. 检查复杂性 - 必须包含大写字母
        if not re.search(r'[A-Z]', password):
            return {'valid': False, 'message': '密码必须包含至少一个大写字母'}

        # 4. 检查复杂性 - 必须包含小写字母
        if not re.search(r'[a-z]', password):
            return {'valid': False, 'message': '密码必须包含至少一个小写字母'}

        # 5. 检查复杂性 - 必须包含数字
        if not re.search(r'[0-9]', password):
            return {'valid': False, 'message': '密码必须包含至少一个数字'}

        # 6. 检查复杂性 - 必须包含特殊符号
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:\'",.<>?/~`]', password):
            return {'valid': False, 'message': '密码必须包含至少一个特殊符号（如 !@# 等）'}

        # 7. 检查弱密码黑名单
        if password.lower() in cls.COMMON_PASSWORDS:
            return {'valid': False, 'message': '该密码过于常见，请使用更复杂的密码'}

        # 8. 检查键盘连续序列
        password_lower = password.lower()
        for pattern in cls.KEYBOARD_PATTERNS:
            if pattern in password_lower:
                return {'valid': False, 'message': '密码不能包含键盘连续字符（如 qwerty）'}

        # 9. 检查连续重复字符（3个及以上相同字符）
        if re.search(r'(.)\1{2,}', password):
            return {'valid': False, 'message': '密码不能包含连续3个及以上相同字符'}

        # 10. 检查连续字母序列（3位及以上升序/降序，如 abc、cba）
        for i in range(len(password) - 2):
            segment = password[i:i + 3]
            if segment.isalpha():
                c0, c1, c2 = ord(segment[0].lower()), ord(segment[1].lower()), ord(segment[2].lower())
                if (c1 - c0 == 1 and c2 - c1 == 1) or (c1 - c0 == -1 and c2 - c1 == -1):
                    return {'valid': False, 'message': '密码不能包含连续字母序列（如 abc、cba）'}

        # 11. 检查连续数字序列（3位及以上升序/降序）
        for i in range(len(password) - 2):
            segment = password[i:i + 3]
            if segment.isdigit():
                d0, d1, d2 = int(segment[0]), int(segment[1]), int(segment[2])
                if (d1 - d0 == 1 and d2 - d1 == 1) or (d1 - d0 == -1 and d2 - d1 == -1):
                    return {'valid': False, 'message': '密码不能包含连续数字序列（如 123、321）'}

        # 12. 检查是否与近5次历史密码相同
        if password_history_hashes:
            from werkzeug.security import check_password_hash
            for stored_hash in password_history_hashes:
                if check_password_hash(stored_hash, password):
                    return {'valid': False, 'message': '密码不能与近5次历史密码相同'}

        logger.debug(f"Password validation passed")
        return {'valid': True, 'message': '密码强度合格'}
