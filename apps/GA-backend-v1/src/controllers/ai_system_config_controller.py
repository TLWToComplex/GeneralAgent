"""系统配置控制器模块"""
import logging
from typing import Dict, Tuple
from flask import request, jsonify
from src.accessors.ai_system_config_accessor import AISystemConfig

logger = logging.getLogger(__name__)


class AISystemConfigController:

    @staticmethod
    async def get_configs(current_user: str = 'admin') -> Tuple[Dict, int]:
        """获取系统配置列表（仅 admin 可访问）"""
        if current_user.lower() != 'admin':
            return jsonify({'code': 403, 'message': '权限不足，仅管理员可访问'}), 403

        success, result = AISystemConfig.get_configs_list()
        if success:
            return jsonify({'code': 0, 'data': result, 'message': '成功'}), 200
        return jsonify({'code': 500, 'message': result}), 500

    @staticmethod
    async def add_config(current_user: str = 'admin') -> Tuple[Dict, int]:
        """新增系统配置（仅 admin 可访问）"""
        if current_user.lower() != 'admin':
            return jsonify({'code': 403, 'message': '权限不足，仅管理员可访问'}), 403

        if not request.is_json:
            return jsonify({'code': 400, 'message': '请求体必须为JSON格式'}), 400

        data = request.json
        config_key = data.get('config_key')
        config_value = data.get('config_value')

        if not config_key or config_value is None:
            return jsonify({'code': 400, 'message': 'config_key 和 config_value 为必填字段'}), 400

        success, result = AISystemConfig.add_config(config_key, config_value, current_user)
        if success:
            return jsonify({'code': 0, 'data': result, 'message': '成功'}), 200
        return jsonify({'code': 400, 'message': result}), 400

    @staticmethod
    async def update_configs(current_user: str = 'admin') -> Tuple[Dict, int]:
        """更新系统配置（仅 admin 可访问）"""
        if current_user.lower() != 'admin':
            return jsonify({'code': 403, 'message': '权限不足，仅管理员可访问'}), 403

        if not request.is_json:
            return jsonify({'code': 400, 'message': '请求体必须为JSON格式'}), 400

        configs = request.json

        if not isinstance(configs, dict) or not configs:
            return jsonify({'code': 400, 'message': 'configs 必须是非空字典'}), 400

        success, result = AISystemConfig.update_configs(configs, current_user)
        if success:
            return jsonify({'code': 0, 'data': result, 'message': '成功'}), 200
        return jsonify({'code': 500, 'message': result}), 500