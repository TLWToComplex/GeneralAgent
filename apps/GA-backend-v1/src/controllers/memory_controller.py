"""
记忆管理 API 控制器。
为 UI 提供 per-user 记忆文件的 list/get/update/clear/download 能力。

所有方法依赖 @jwt_required 提供的 current_user（username），通过数据库查询得到 user.uuid，
再定位到 {memory_container_path}/{agent_uuid}/{user_uuid}/ 目录（主容器内视角）。
"""
import io
import logging
import os
import zipfile
from datetime import datetime
from typing import Optional, Tuple

from flask import jsonify, request, send_file

from src.accessors.ai_user_accessor import AIUser
from src.core.memory.memory_seeder import (
    get_user_memory_dir,
    reset_memories,
    seed_initial_memories,
)
from src.utils.config_manager import config_manager

logger = logging.getLogger(__name__)


class MemoryController:
    """记忆管理控制器"""

    @staticmethod
    def _resolve_user_uuid(current_user: str) -> Tuple[Optional[str], Optional[str]]:
        """从 username 查询 user.uuid。

        Returns:
            (user_uuid, error_message)。error_message 为 None 表示成功。
        """
        if not current_user:
            return None, '未识别到当前用户'
        user = AIUser.query.filter_by(username=current_user, is_del=0).first()
        if not user:
            return None, f'用户不存在: {current_user}'
        return user.uuid, None

    @staticmethod
    def _read_file_safe(filepath: str) -> str:
        """读取文件内容，文件不存在返回空字符串。"""
        if not os.path.isfile(filepath):
            return ''
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取记忆文件失败 {filepath}: {e}")
            return ''

    @staticmethod
    def _file_meta(filepath: str, filename: str, agent_uuid: str, user_uuid: str) -> dict:
        """构建单个记忆文件的元数据。"""
        sandbox_base = config_manager.get_memory_sandbox_path().rstrip('/')
        sandbox_path = f"{sandbox_base}/{filename}"
        content = MemoryController._read_file_safe(filepath)
        size = 0
        updated_at = None
        if os.path.isfile(filepath):
            try:
                stat = os.stat(filepath)
                size = stat.st_size
                updated_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
            except Exception:
                pass
        return {
            'name': filename,
            'sandboxPath': sandbox_path,
            'containerPath': filepath,
            'content': content,
            'size': size,
            'updatedAt': updated_at,
        }

    @staticmethod
    def list(current_user: str):
        """GET /aiMemory/list?agentUuid=xxx — 列出当前用户在某 agent 的记忆文件。"""
        agent_uuid = request.args.get('agentUuid') or request.args.get('agent_uuid')
        if not agent_uuid:
            return jsonify({'code': 400, 'message': '缺少 agentUuid 参数'}), 400

        user_uuid, err = MemoryController._resolve_user_uuid(current_user)
        if err:
            return jsonify({'code': 401, 'message': err}), 401

        try:
            agent_memory_dir = get_user_memory_dir(agent_uuid, user_uuid)
            # 若目录不存在则按种子初始化（首次访问也能列出文件）
            if not os.path.isdir(agent_memory_dir):
                seed_initial_memories(agent_uuid, user_uuid)

            files_meta = []
            for filename in config_manager.get_memory_files():
                filepath = os.path.join(agent_memory_dir, filename)
                files_meta.append(
                    MemoryController._file_meta(filepath, filename, agent_uuid, user_uuid)
                )

            return jsonify({
                'code': 0,
                'message': 'success',
                'data': {
                    'agent_uuid': agent_uuid,
                    'user_uuid': user_uuid,
                    'enabled': config_manager.get_memory_enabled(agent_uuid),
                    'files': files_meta,
                }
            }), 200
        except Exception as e:
            logger.error(f"列出记忆失败: {e}", exc_info=True)
            return jsonify({'code': 500, 'message': f'列出记忆失败: {e}'}), 500

    @staticmethod
    def get(current_user: str):
        """GET /aiMemory/get?agentUuid=xxx&fileName=xxx — 获取单个文件或全部文件合并内容。"""
        agent_uuid = request.args.get('agentUuid') or request.args.get('agent_uuid')
        file_name = request.args.get('fileName') or request.args.get('file_name')
        if not agent_uuid:
            return jsonify({'code': 400, 'message': '缺少 agentUuid 参数'}), 400

        user_uuid, err = MemoryController._resolve_user_uuid(current_user)
        if err:
            return jsonify({'code': 401, 'message': err}), 401

        try:
            agent_memory_dir = get_user_memory_dir(agent_uuid, user_uuid)
            if not os.path.isdir(agent_memory_dir):
                seed_initial_memories(agent_uuid, user_uuid)

            allowed_files = set(config_manager.get_memory_files())

            if file_name:
                if file_name not in allowed_files:
                    return jsonify({'code': 400, 'message': f'非法文件名: {file_name}'}), 400
                filepath = os.path.join(agent_memory_dir, file_name)
                meta = MemoryController._file_meta(filepath, file_name, agent_uuid, user_uuid)
                return jsonify({'code': 0, 'message': 'success', 'data': meta}), 200

            # 无 fileName: 返回所有文件的合并内容
            sections = []
            for filename in config_manager.get_memory_files():
                filepath = os.path.join(agent_memory_dir, filename)
                content = MemoryController._read_file_safe(filepath)
                sections.append(f"# {filename}\n\n{content}")
            merged = "\n\n---\n\n".join(sections)
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': {
                    'agent_uuid': agent_uuid,
                    'user_uuid': user_uuid,
                    'memory': merged,
                }
            }), 200
        except Exception as e:
            logger.error(f"获取记忆失败: {e}", exc_info=True)
            return jsonify({'code': 500, 'message': f'获取记忆失败: {e}'}), 500

    @staticmethod
    def update(current_user: str):
        """POST /aiMemory/update — 更新单个文件内容。"""
        data = request.json or {}
        agent_uuid = data.get('agentUuid') or data.get('agent_uuid')
        file_name = data.get('fileName') or data.get('file_name') or 'AGENTS.md'
        content = data.get('content', '')

        if not agent_uuid:
            return jsonify({'code': 400, 'message': '缺少 agentUuid 参数'}), 400
        if not isinstance(content, str):
            return jsonify({'code': 400, 'message': 'content 必须是字符串'}), 400

        allowed_files = set(config_manager.get_memory_files())
        if file_name not in allowed_files:
            return jsonify({'code': 400, 'message': f'非法文件名: {file_name}'}), 400

        user_uuid, err = MemoryController._resolve_user_uuid(current_user)
        if err:
            return jsonify({'code': 401, 'message': err}), 401

        try:
            agent_memory_dir = get_user_memory_dir(agent_uuid, user_uuid)
            os.makedirs(agent_memory_dir, exist_ok=True)
            filepath = os.path.join(agent_memory_dir, file_name)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"用户 {current_user} 更新记忆文件: {filepath}")
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': MemoryController._file_meta(filepath, file_name, agent_uuid, user_uuid)
            }), 200
        except Exception as e:
            logger.error(f"更新记忆失败: {e}", exc_info=True)
            return jsonify({'code': 500, 'message': f'更新记忆失败: {e}'}), 500

    @staticmethod
    def reset(current_user: str):
        """POST /aiMemory/reset — 重置当前用户在指定 agent 的记忆为初始种子。"""
        data = request.json or {}
        agent_uuid = data.get('agentUuid') or data.get('agent_uuid')
        if not agent_uuid:
            return jsonify({'code': 400, 'message': '缺少 agentUuid 参数'}), 400

        user_uuid, err = MemoryController._resolve_user_uuid(current_user)
        if err:
            return jsonify({'code': 401, 'message': err}), 401

        try:
            agent_memory_dir = reset_memories(agent_uuid, user_uuid)
            logger.info(f"用户 {current_user} 重置记忆: {agent_memory_dir}")
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': {
                    'agent_uuid': agent_uuid,
                    'user_uuid': user_uuid,
                    'containerPath': agent_memory_dir,
                }
            }), 200
        except Exception as e:
            logger.error(f"重置记忆失败: {e}", exc_info=True)
            return jsonify({'code': 500, 'message': f'重置记忆失败: {e}'}), 500

    @staticmethod
    def download(current_user: str):
        """GET /aiMemory/download?agentUuid=xxx — 打包当前用户的记忆为 zip。"""
        agent_uuid = request.args.get('agentUuid') or request.args.get('agent_uuid')
        if not agent_uuid:
            return jsonify({'code': 400, 'message': '缺少 agentUuid 参数'}), 400

        user_uuid, err = MemoryController._resolve_user_uuid(current_user)
        if err:
            return jsonify({'code': 401, 'message': err}), 401

        try:
            agent_memory_dir = get_user_memory_dir(agent_uuid, user_uuid)
            if not os.path.isdir(agent_memory_dir):
                seed_initial_memories(agent_uuid, user_uuid)

            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for filename in config_manager.get_memory_files():
                    filepath = os.path.join(agent_memory_dir, filename)
                    if os.path.isfile(filepath):
                        zf.write(filepath, filename)
            buffer.seek(0)

            return send_file(
                buffer,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f"agent-{agent_uuid}-memory.zip",
            )
        except Exception as e:
            logger.error(f"下载记忆失败: {e}", exc_info=True)
            return jsonify({'code': 500, 'message': f'下载记忆失败: {e}'}), 500


memory_controller = MemoryController()
