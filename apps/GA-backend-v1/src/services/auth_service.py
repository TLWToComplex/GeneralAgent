"""
认证业务逻辑服务模块。
处理用户登录、密码修改等认证相关的核心业务逻辑。
"""
import logging
import time
from typing import Any, Tuple
from datetime import datetime, timedelta
from flask_jwt_extended import create_access_token
from src.accessors.ai_user_accessor import AIUser
from src.accessors.ai_password_history_accessor import ai_password_history_accessor
from src.utils.password_validator import PasswordValidator
from src.core.cache.captcha_cache import captcha_cache
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

# 密码历史记录保留数量
PASSWORD_HISTORY_KEEP_COUNT = 5


class AuthService:
    """
    认证业务逻辑服务类。
    提供用户认证相关的纯业务逻辑，不依赖 HTTP 请求/响应对象。
    """

    @staticmethod
    def find_user(username_or_email: str, for_update: bool = False):
        """根据用户名或邮箱查找用户

        Args:
            username_or_email: 用户名或邮箱
            for_update: 是否加行锁（SELECT ... FOR UPDATE），用于防止并发竞态
        """
        is_email = '@' in username_or_email
        query = AIUser.query.filter_by(is_del=0)
        if is_email:
            query = query.filter_by(email=username_or_email)
        else:
            query = query.filter_by(username=username_or_email)

        if for_update:
            query = query.with_for_update()

        user = query.first()

        if not user:
            return None, None

        username = user.username if is_email else username_or_email
        return user, username

    @staticmethod
    def validate_captcha(captcha_id: str, captcha_code: str) -> tuple:
        """验证码校验"""
        stored_code = captcha_cache.get(captcha_id)
        captcha_cache.delete(captcha_id)

        if not stored_code:
            return False, '验证码已过期，请重新获取'
        if stored_code.upper() != captcha_code.upper():
            return False, '验证码错误'
        return True, None

    @staticmethod
    def check_account_locked(additional_info: dict) -> tuple:
        """检查账号锁定状态，返回 (is_locked, message, updated_info)

        注意：此方法仅修改内存中的 additional_info dict，实际的数据库写入
        由调用方在行锁保护下统一提交，避免并发竞态和字段丢失。
        """
        locked_until_str = additional_info.get('locked_until')
        if locked_until_str:
            locked_until = datetime.fromisoformat(locked_until_str)
            if datetime.now() < locked_until:
                remaining = int((locked_until - datetime.now()).total_seconds() / 60)
                return True, f"账号已锁定，请{remaining}分钟后重试", additional_info
            else:
                # 锁定已过期，清除锁定状态及失败记录（仅修改内存）
                additional_info.pop("locked_until", None)
                additional_info.pop("login_failed_count", None)
        return False, "", additional_info

    @staticmethod
    def check_inactive_account(additional_info: dict, username: str) -> tuple:
        """检查账号是否因超过30天未登录而处于不活跃锁定状态，返回 (is_locked, message, updated_info)

        注意：此方法仅修改内存中的 additional_info dict，实际的数据库写入
        由调用方在行锁保护下统一提交，避免并发竞态和字段丢失。
        """
        if username == 'admin':
            return False, "", additional_info

        if 'inactive_locked' in additional_info:
            # inactive_locked 存在即标记为不活跃锁定，保持锁定状态
            return True, "账号因超过30天未登录已被锁定，请联系管理员解锁", additional_info

        last_login_str = additional_info.get('last_login_time')
        if last_login_str:
            try:
                last_login = datetime.fromisoformat(last_login_str)
                days_inactive = (datetime.now() - last_login).days
                if days_inactive >= 30:
                    additional_info['inactive_locked'] = '1'
                    logger.warning(f"账号因超过30天未登录被锁定，最后登录时间: {last_login_str}")
                    return True, f"账号已超过30天未登录，已被自动锁定，请联系管理员解锁", additional_info
            except Exception as e:
                logger.warning(f"解析 last_login_time 失败: {str(e)}")
        return False, "", additional_info

    @staticmethod
    def record_login_failure(additional_info: dict) -> tuple:
        """记录登录失败，返回 (error_message, status_code)

        注意：此方法仅修改内存中的 additional_info dict，实际的数据库写入
        由调用方在行锁保护下统一提交，避免并发竞态和字段丢失。
        """
        failed_count = additional_info.get("login_failed_count", 0) + 1
        additional_info["login_failed_count"] = failed_count

        if failed_count >= 5:
            locked_until = datetime.now() + timedelta(minutes=5)
            additional_info["locked_until"] = locked_until.isoformat()
            return '连续5次密码错误，账号已锁定5分钟', 401
        remaining = 5 - failed_count
        return f'密码错误，还剩{remaining}次机会', 401

    @staticmethod
    def clear_login_failure(additional_info: dict):
        """登录成功清除失败记录（仅修改内存，由调用方统一写库）"""
        if any(key in additional_info for key in ("login_failed_count", "locked_until")):
            additional_info.pop("login_failed_count", None)
            additional_info.pop("locked_until", None)

    @staticmethod
    def unlock_account(user_uuid: str, current_user: str) -> tuple:
        """管理员解锁因超过30天未登录而被锁定的账号

        Args:
            user_uuid: 用户UUID
            current_user: 当前操作人（管理员）

        Returns:
            Tuple[bool, Any]:
                (True, {'status': 'success', 'message': '账号已解锁'})
                (False, {'error': str, 'status_code': int})
        """
        try:
            # 查询用户
            success, user_result = AIUser.get_user(uuid=user_uuid)
            if not success:
                logger.warning(f"解锁失败，用户不存在: {user_uuid}")
                return False, {'error': '用户不存在', 'status_code': 404}

            additional_info = user_result.get('additional_info', {}) or {}
            if not isinstance(additional_info, dict):
                additional_info = {}

            # 检查是否确实被不活跃锁定
            if 'inactive_locked' not in additional_info:
                logger.info(f"用户 {user_result['username']} (uuid: {user_uuid}) 未被锁定，无需解锁")
                return True, {'status': 'success', 'message': '该账号未被锁定，无需解锁'}

            # 解锁：移除锁定标记，并刷新最后登录时间
            additional_info.pop('inactive_locked', None)
            additional_info['last_login_time'] = datetime.now().isoformat()

            # 更新数据库
            user_id = user_result['id']
            update_success, update_result = AIUser.update_user(
                user_id=user_id,
                update_data={
                    'additional_info': additional_info,
                    'update_by': current_user
                }
            )

            if not update_success:
                logger.error(f"解锁失败，数据库更新错误: {update_result}")
                return False, {'error': '系统错误，请稍后重试', 'status_code': 500}

            logger.info(f"管理员 {current_user} 已解锁用户 {user_result['username']} (uuid: {user_uuid})")
            return True, {'status': 'success', 'message': '账号已解锁，用户可以正常登录'}

        except Exception as e:
            logger.error(f"解锁账号异常 (uuid: {user_uuid}): {str(e)}")
            return False, {'error': '服务器内部错误', 'status_code': 500}

    @staticmethod
    def check_password_expired(additional_info: dict, username: str) -> bool:
        """检查密码是否超过90天未更新, admin60天

        Args:
            additional_info: 用户附加信息字典

        Returns:
            bool: 密码是否过期（超过90天未更新）
        """
        last_change_str = additional_info.get('last_password_change')
        if last_change_str:
            try:
                last_change = datetime.fromisoformat(last_change_str)
                days_since_change = (datetime.now() - last_change).days
                if days_since_change >= 90 or (username == 'admin' and days_since_change >= 60):
                    return True
            except Exception as e:
                logger.warning(f"解析 last_password_change 失败: {str(e)}")
        return False

    @staticmethod
    def authenticate(username_or_email: str, password: str,
                     captcha_id: str, captcha_code: str) -> Tuple[bool, Any]:
        """
        执行登录认证业务逻辑。

        包含：验证码校验 → 用户查找 → 账号锁定检查 → 不活跃检查 → 密码验证
        → 成功则清除失败记录、更新登录时间、生成token；失败则记录失败次数。

        Args:
            username_or_email: 用户名或邮箱
            password: 明文密码
            captcha_id: 验证码ID
            captcha_code: 验证码值

        Returns:
            Tuple[bool, Any]:
                (True, {
                    'user_details': dict,        # 已脱敏、已平铺的用户信息
                    'username': str,             # 登录用户名
                    'is_email': bool,            # 是否邮箱登录
                    'token': str,                # JWT token
                    'password_expired_warning': bool  # 密码是否超过90天未更新
                })
                (False, {
                    'error': str,                # 错误信息
                    'status_code': int           # 建议HTTP状态码
                })
        """
        # 验证码校验
        captcha_ok, captcha_error = AuthService.validate_captcha(captcha_id, captcha_code)
        if not captcha_ok:
            logger.warning(f"Captcha validation failed: {captcha_error}")
            return False, {'error': captcha_error, 'status_code': 401}

        # 查找用户（加行锁，防止并发竞态）
        user, username = AuthService.find_user(username_or_email, for_update=True)
        if not user:
            logger.warning(f"Invalid login attempt: {username_or_email}")
            return False, {'error': '用户名或邮箱无效', 'status_code': 401}

        # 检查账号锁定状态（登录失败锁定）
        additional_info = user.additional_info or {}
        is_locked, lock_message, additional_info = AuthService.check_account_locked(additional_info)
        if is_locked:
            logger.warning(f"Account locked for user: {username_or_email}")
            return False, {'error': lock_message, 'status_code': 403}

        # 检查账号是否因超过30天未登录被锁定
        is_inactive, inactive_message, additional_info = AuthService.check_inactive_account(additional_info, username)
        if is_inactive:
            # 将 inactive_locked 标记持久化到数据库（check_inactive_account 仅修改了内存中的 dict）
            if not AIUser.update_user_additional_info_in_transaction(user, additional_info):
                logger.error(f"Failed to save inactive_locked flag for {username}")
            logger.warning(f"Inactive account for user: {username_or_email}")
            return False, {'error': inactive_message, 'status_code': 403}

        # 验证密码
        is_valid = AIUser.verify_password(username, password)

        if is_valid:
            # 登录成功 - 清除失败记录（仅修改内存）
            AuthService.clear_login_failure(additional_info)

            # 清除不活跃锁定标记（登录成功说明账号已激活）
            additional_info.pop("inactive_locked", None)

            # 记录最后登录时间（用于30天未登录锁定检测）
            additional_info['last_login_time'] = datetime.now().isoformat()

            # 检查密码是否超过90天未更新（仅提醒，不阻断登录）
            password_expired = AuthService.check_password_expired(additional_info, username)

            # 在行锁保护下通过 accessor 统一写回并提交
            if not AIUser.update_user_additional_info_in_transaction(user, additional_info):
                logger.error(f"Failed to update additional_info for {username}")
                return False, {'error': '系统错误，请稍后重试', 'status_code': 500}

            success, user_details = AIUser.get_user(username=username)
            if not success:
                logger.error(f"Failed to retrieve user details for {username}")
                return False, {'error': '获取用户信息失败', 'status_code': 500}

            is_email = '@' in username_or_email

            # 脱敏：移除密码
            user_details.pop('password', None)

            # 平铺 additional_info 到顶层
            if isinstance(user_details, dict) and 'additional_info' in user_details:
                add_info = user_details.pop('additional_info', {})
                if isinstance(add_info, dict):
                    user_details.update(add_info)

            # 设置 needUpdateMsg
            user_details['needUpdateMsg'] = False if user_details.get('realname') else True

            # 生成 JWT Token
            identity_data = {
                'username': username,
                'user_id': user_details.get('id'),
                'timestamp': time.time()
            }
            access_token = create_access_token(identity=identity_data)

            logger.info(f"User logged in successfully: {username} (via {'email' if is_email else 'username'})")

            return True, {
                'user_details': user_details,
                'username': username,
                'is_email': is_email,
                'token': access_token,
                'password_expired_warning': password_expired
            }
        else:
            # 密码错误 - 记录失败（仅修改内存）
            failure_message, status_code = AuthService.record_login_failure(additional_info)

            # 在行锁保护下通过 accessor 统一写回并提交
            if not AIUser.update_user_additional_info_in_transaction(user, additional_info):
                logger.error(f"Failed to update additional_info for {username_or_email}")
                return False, {'error': '系统错误，请稍后重试', 'status_code': 500}

            logger.warning(f"Invalid login attempt for {username_or_email}")
            return False, {'error': failure_message, 'status_code': status_code}

    @staticmethod
    def change_password(user_uuid: str, old_password: str,
                        new_password: str, current_user: str) -> Tuple[bool, Any]:
        """
        修改用户密码业务逻辑。

        Args:
            user_uuid: 用户UUID
            old_password: 旧密码
            new_password: 新密码
            current_user: 当前操作人

        Returns:
            Tuple[bool, Any]:
                (True, {'status': 'success', 'message': '密码更新成功'})
                (False, {'error': str, 'status_code': int})
        """
        try:
            # 先通过uuid查询用户信息
            user_success, user_result = AIUser.get_user(uuid=user_uuid)
            if not user_success:
                logger.error(f"Failed to find user by uuid {user_uuid}: {user_result}")
                return False, {'error': '用户不存在', 'status_code': 404}

            # 获取用户名用于密码验证
            username = user_result['username']

            # 验证旧密码是否正确
            is_valid = AIUser.verify_password(username, old_password)
            if not is_valid:
                logger.warning(f"Invalid old password for user {username} (uuid: {user_uuid})")
                return False, {'error': '旧密码不正确', 'status_code': 401}

            # 获取近5次历史密码哈希列表
            recent_hashes = ai_password_history_accessor.get_recent_hashes(user_uuid, n=PASSWORD_HISTORY_KEEP_COUNT)

            # 密码禁用规则校验（含历史密码检查）
            password_validation = PasswordValidator.validate_password(
                new_password, username, password_history_hashes=recent_hashes
            )
            if not password_validation['valid']:
                logger.warning(f"Password validation failed for user {username}: {password_validation['message']}")
                return False, {'error': password_validation['message'], 'status_code': 400}

            # 准备更新数据，只包含新密码和更新时间
            update_data = {
                'password': new_password,
                'update_by': current_user  # 使用当前登录用户作为更新人
            }

            # 使用用户ID调用update_user方法更新密码
            user_id = user_result['id']
            success, result = AIUser.update_user(user_id=user_id, update_data=update_data)

            if success:
                logger.info(f"Password updated successfully for user {username} (uuid: {user_uuid})")

                # 记录新密码到历史记录表（update_user内部已哈希，此处重新哈希记录以便未来比对）
                try:
                    new_password_hash = generate_password_hash(new_password)
                    ai_password_history_accessor.add_record(user_uuid, new_password_hash)
                    ai_password_history_accessor.cleanup_old_records(user_uuid, keep=PASSWORD_HISTORY_KEEP_COUNT)
                    logger.info(f"Password history recorded for user {username} (uuid: {user_uuid})")
                except Exception as hist_err:
                    # 密码历史记录失败不影响主流程，仅记录日志
                    logger.error(f"Failed to record password history for user {user_uuid}: {str(hist_err)}")

                # 记录密码变更时间到 additional_info.last_password_change
                try:
                    current_user_info, _ = AIUser.get_user(uuid=user_uuid)
                    if current_user_info:
                        additional = current_user_info.get('additional_info', {}) or {}
                        additional['last_password_change'] = datetime.now().isoformat()
                        current_id = current_user_info['id']
                        AIUser.update_user(user_id=current_id, update_data={'additional_info': additional})
                        logger.info(f"last_password_change updated for user {username} (uuid: {user_uuid})")
                except Exception as lpc_err:
                    logger.error(f"Failed to update last_password_change for user {user_uuid}: {str(lpc_err)}")

                return True, {'status': 'success', 'message': '密码更新成功'}
            else:
                logger.error(f"Failed to update password for user {user_uuid}: {result}")
                return False, {'error': result, 'status_code': 400}

        except Exception as e:
            logger.error(f"Error in change_password for user {user_uuid}: {str(e)}")
            return False, {'error': '服务器内部错误', 'status_code': 500}
