from flask import request, jsonify
from typing import Dict, Tuple, List
from src.accessors.ai_chat_session_summary_accessor import ai_chat_session_summary_accessor
import logging

logger = logging.getLogger(__name__)


class AIChatSessionSummaryController:
    @staticmethod
    async def list_summaries(current_user: str = None) -> Tuple[Dict, int]:
        """查询当前用户所有会话的摘要

        Returns:
            ({'code': 200, 'message': 'success', 'data': [{'session_thread_id': ..., 'summary': ...}, ...]}, status_code)
        """
        try:
            success, result = ai_chat_session_summary_accessor.list_summary(create_by=current_user)
            if success:
                data = [
                    {'session_thread_id': s.get('session_thread_id', ''),
                     'summary': s.get('summary', ''),
                     'create_time': s.get('create_time', ''),
                     'update_time': s.get('update_time', '')
                     }
                    for s in result
                ]
                return jsonify({
                    'code': 200,
                    'message': 'success',
                    'data': data
                }), 200
            else:
                logger.error(f"查询会话摘要失败: {result}")
                return jsonify({
                    'code': 1,
                    'message': result
                }), 500
        except Exception as e:
            logger.error(f"查询会话摘要异常: {str(e)}", exc_info=True)
            return jsonify({
                'code': 1,
                'message': f'查询会话摘要失败: {str(e)}'
            }), 500

    @staticmethod
    async def check_summary(current_user: str = None) -> Tuple[Dict, int]:
        """ 检查对话摘要是否存在

        Returns:
            ({'code': 200, 'message': '检查会话摘要成功', 'exists': exists}, status_code)
        """

        session_thread_id = request.args.get('session_thread_id', type=str)
        try:
            exists, _ = ai_chat_session_summary_accessor.get_by_session_thread_id(session_thread_id)
            return jsonify({
                'code': 200,
                'message': '检查会话摘要成功',
                'exists': exists
            }), 200
        except Exception as e:
            logger.error(f"检查会话摘要异常: {str(e)}", exc_info=True)
            return jsonify({
                'code': 1,
                'message': f'检查会话摘要失败: {str(e)}',
                'exists': False
            }), 500

    @staticmethod
    async def edit_summary(current_user: str = None) -> Tuple[Dict, int]:
        """编辑会话摘要

        Body (JSON):
            session_thread_id: 会话线程ID（必填）
            summary: 新的摘要内容（必填）

        Returns:
            ({'code': 200, 'message': 'success'}, status_code)
        """
        data = request.json or {}
        session_thread_id = data.get('session_thread_id') or request.args.get('session_thread_id', type=str)
        summary = data.get('summary') or request.args.get('summary', type=str)

        if not session_thread_id:
            return jsonify({'code': 1, 'message': 'session_thread_id 不能为空'}), 400
        if not summary or not str(summary).strip():
            return jsonify({'code': 1, 'message': 'summary 不能为空'}), 400

        try:
            success, result = ai_chat_session_summary_accessor.update_summary(
                session_thread_id=session_thread_id,
                summary=str(summary),
                operator=current_user,
            )
            if success:
                return jsonify({'code': 200, 'message': result}), 200
            return jsonify({'code': 1, 'message': result}), 400
        except Exception as e:
            logger.error(f"编辑会话摘要异常: {str(e)}", exc_info=True)
            return jsonify({'code': 1, 'message': f'编辑会话摘要失败: {str(e)}'}), 500