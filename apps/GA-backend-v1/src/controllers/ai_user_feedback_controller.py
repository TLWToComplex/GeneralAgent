"""
AI用户反馈控制器模块。
处理 /aiUserFeedback/* 相关HTTP请求，提供用户反馈与功能改进追溯记录的CRUD接口。
"""
import logging
from typing import Dict, Tuple

from flask import request, jsonify

from src.accessors.ai_user_feedback_accessor import AIUserFeedback

logger = logging.getLogger(__name__)


class AIUserFeedbackController:
    """处理 ai_user_feedback 表相关请求的控制器。"""

    @staticmethod
    async def add_feedback(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        新增一条用户反馈记录。

        期望JSON请求体字段：
            - feedback_content (str, 必填): 用户反馈内容
            - priority (str, 可选): 需求优先级（高/中/低）
            - improvement_plan (str, 可选): 改进措施/解决方案
            - source (str, 可选): 需求来源
            - status (str, 可选): 当前进度状态
            - progress (float, 可选): 完成进度（0~1）
            - start_time (str, 可选): 需求提出时间
            - finish_time (str, 可选): 完成时间
            - verify_result (str, 可选): 验证结果/用户反馈
            - remark (str, 可选): 备注
        """
        if not request.is_json:
            return jsonify({'code': 400, 'message': '请求体必须为JSON格式'}), 400

        data = request.json or {}
        if not data.get('feedback_content'):
            return jsonify({'code': 400, 'message': 'feedback_content 为必填字段'}), 400

        data.setdefault('create_by', current_user)
        data.setdefault('update_by', current_user)

        success, result = AIUserFeedback.add_feedback(data)
        if success:
            logger.info(f"Feedback added: uuid={result.get('uuid')} by={current_user}")
            return jsonify({'code': 200, 'message': '反馈添加成功', 'data': result}), 200
        logger.warning(f"Add feedback failed: {result}")
        return jsonify({'code': 400, 'message': result}), 400

    @staticmethod
    async def get_feedback(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        查询单条反馈记录。

        查询参数：
            - id (int): 反馈ID
            - uuid (str): 反馈UUID
        """
        feedback_id = request.args.get('id', type=int)
        feedback_uuid = request.args.get('uuid', type=str)

        if not any([feedback_id, feedback_uuid]):
            return jsonify({'code': 400, 'message': '必须提供 id 或 uuid'}), 400

        success, result = AIUserFeedback.get_feedback(feedback_id=feedback_id, feedback_uuid=feedback_uuid)
        if success:
            return jsonify({'code': 200, 'message': '获取成功', 'data': result}), 200
        return jsonify({'code': 404, 'message': result}), 404

    @staticmethod
    async def list_feedback(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        分页查询反馈列表。

        查询参数：
            - skip (int, 默认 0)
            - take (int, 默认 100，最大 1000)
        """
        skip = request.args.get('skip', default=0, type=int)
        take = request.args.get('take', default=100, type=int)
        if skip < 0 or take <= 0 or take > 1000:
            return jsonify({'code': 400, 'message': '分页参数无效'}), 400

        success, result = AIUserFeedback.list_feedback(skip=skip, take=take)
        if success:
            return jsonify({'code': 200, 'message': '获取成功', 'data': result}), 200
        return jsonify({'code': 500, 'message': '获取列表失败', 'error': result}), 500

    @staticmethod
    async def query_feedback(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        条件查询反馈。

        查询参数：
            - keyword (str): 关键字（同时匹配反馈内容/改进措施/验证结果/备注）
            - priority (str): 高/中/低
            - status (str): 进度状态
            - source (str): 需求来源
            - create_by (str): 创建人
            - skip / take: 分页
        """
        skip = request.args.get('skip', default=0, type=int)
        take = request.args.get('take', default=100, type=int)
        if skip < 0 or take <= 0 or take > 1000:
            return jsonify({'code': 400, 'message': '分页参数无效'}), 400

        success, result = AIUserFeedback.query_feedback(
            keyword=request.args.get('keyword', type=str),
            priority=request.args.get('priority', type=str),
            status=request.args.get('status', type=str),
            source=request.args.get('source', type=str),
            create_by=request.args.get('create_by', type=str),
            skip=skip, take=take,
        )
        if success:
            return jsonify({'code': 200, 'message': '查询成功', 'data': result}), 200
        return jsonify({'code': 500, 'message': '查询失败', 'error': result}), 500

    @staticmethod
    async def update_feedback(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        更新反馈记录。

        请求体：
            - uuid (str, 必填)
            - 其余可选字段同 add_feedback
        """
        if not request.is_json:
            return jsonify({'code': 400, 'message': '请求体必须为JSON格式'}), 400

        data = request.json or {}
        feedback_uuid = data.pop('uuid', None) or request.args.get('uuid', type=str)
        if not feedback_uuid:
            return jsonify({'code': 400, 'message': 'uuid 为必填字段'}), 400
        if not data:
            return jsonify({'code': 400, 'message': '更新数据不能为空'}), 400

        data['update_by'] = current_user

        success, result = AIUserFeedback.update_feedback(feedback_uuid, data)
        if success:
            logger.info(f"Feedback updated: uuid={feedback_uuid} by={current_user}")
            return jsonify({'code': 200, 'message': '反馈更新成功', 'data': result}), 200
        if '不存在' in str(result):
            return jsonify({'code': 404, 'message': result}), 404
        return jsonify({'code': 400, 'message': result}), 400

    @staticmethod
    async def delete_feedback(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        软删除反馈记录。

        请求体或查询参数：
            - uuid (str, 必填)
        """
        data = request.json if request.is_json else {}
        feedback_uuid = (data or {}).get('uuid') or request.args.get('uuid', type=str)
        if not feedback_uuid:
            return jsonify({'code': 400, 'message': 'uuid 为必填字段'}), 400

        success, result = AIUserFeedback.delete_feedback(feedback_uuid, delete_by=current_user)
        if success:
            logger.info(f"Feedback deleted: uuid={feedback_uuid} by={current_user}")
            return jsonify({'code': 200, 'message': '反馈删除成功'}), 200
        if '不存在' in str(result):
            return jsonify({'code': 404, 'message': result}), 404
        return jsonify({'code': 400, 'message': result}), 400
