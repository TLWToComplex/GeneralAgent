"""
AI技能控制器模块。
处理AI技能管理的API端点。
"""
import os
import logging
from flask import request, jsonify
from typing import Dict, Tuple
from src.accessors.ai_skill_accessor import AISkill
from src.utils.name_converter import convert_dict_keys_to_camel_case
from src.controllers.deepagent_file_controller import deepagent_file_controller
from src.utils.config_manager import config_manager

logger = logging.getLogger(__name__)


class AISkillController:

    @staticmethod
    async def upload_skill(current_user: str = None) -> Tuple[Dict, int]:
        """上传技能压缩包，解压文件并写入数据库"""
        if not current_user:
            return jsonify({'error': '用户未认证'}), 401

        # 从表单获取字段
        name = request.form.get('name')
        description = request.form.get('description', '')
        visibility = request.form.get('visibility', 'private')
        additional_info_str = request.form.get('additional_info', '')

        if not name:
            return jsonify({'error': '技能名称为必填字段'}), 400

        # 获取上传文件
        if 'file' not in request.files:
            return jsonify({'error': '请上传技能压缩包'}), 400

        file = request.files['file']
        if not file.filename:
            return jsonify({'error': '文件名不能为空'}), 400

        # 检查同名技能是否已存在
        exists, existing_skill = AISkill.check_name_exists(name)
        if exists and existing_skill:
            if existing_skill['visibility'] == 'public':
                return jsonify({'error': '该技能名称已存在'}), 409
            elif existing_skill['create_by'] != current_user:
                return jsonify({'error': '该技能名称已存在，如需使用请联系管理员解决'}), 409
            else:
                return jsonify({'error': '您已上传同名技能，请修改名称或删除旧技能'}), 409

        # 读取文件内容
        file_content = file.read()

        # 调用文件控制器解压到 skills_repo
        try:
            deepagent_file_controller.upload_skill_package(
                file_content=file_content,
                filename=file.filename,
                skill_name=name
            )
        except Exception as e:
            return jsonify({'error': f'技能包解压失败: {str(e)}'}), 400

        # 解析 additional_info
        additional_info = {}
        if additional_info_str:
            try:
                import json
                additional_info = json.loads(additional_info_str)
            except (json.JSONDecodeError, TypeError):
                pass

        # 写入数据库
        skill_data = {
            'name': name,
            'description': description,
            'folder_name': name,
            'visibility': visibility,
            'create_by': current_user,
            'additional_info': additional_info,
        }
        result, skill_or_error = AISkill.add_skill(skill_data)
        if result:
            skill_data_camel = convert_dict_keys_to_camel_case(skill_or_error)
            return jsonify(skill_data_camel), 200
        else:
            # 数据库写入失败，清理已解压的文件
            try:
                skills_path = config_manager.get_skills_path()
                skill_dir = os.path.join(skills_path, name)
                if os.path.exists(skill_dir):
                    import shutil
                    shutil.rmtree(skill_dir, ignore_errors=True)
            except Exception:
                pass
            return jsonify({'error': f'技能保存失败: {skill_or_error}'}), 400

    @staticmethod
    async def list_skills(current_user: str = None, allowed_entity_ids: list = None) -> Tuple[Dict, int]:
        """获取技能列表（使用统一的权限过滤）"""
        from flask import g as request_g
        if not current_user:
            return jsonify({'error': '用户未认证'}), 401

        # 优先从 g 对象获取权限列表
        perm_list = getattr(request_g, 'allowed_entity_ids', None) or allowed_entity_ids
        result, skills_or_error = AISkill.list_skills(create_by=current_user, allowed_entity_ids=perm_list)
        if result:
            skills_camel = [convert_dict_keys_to_camel_case(s) for s in skills_or_error]
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': {
                    'skills': skills_camel
                }
            }), 200
        else:
            return jsonify({
                'code': 1,
                'message': skills_or_error
            }), 500

    @staticmethod
    async def get_skill(current_user: str = None, allowed_entity_ids: list = None) -> Tuple[Dict, int]:
        """获取单个技能详情（使用统一的权限过滤）"""
        from flask import g as request_g
        if not current_user:
            return jsonify({'error': '用户未认证'}), 401

        uuid = request.args.get('uuid', type=str)
        if not uuid:
            return jsonify({'error': '必须提供技能UUID'}), 400

        # 优先从 g 对象获取权限列表
        perm_list = getattr(request_g, 'allowed_entity_ids', None) or allowed_entity_ids
        
        create_by_filter = current_user
        if perm_list and uuid in perm_list:
            create_by_filter = None

        result, skill_or_error = AISkill.get_skill(uuid=uuid, create_by=create_by_filter)
        if result:
            skill_camel = convert_dict_keys_to_camel_case(skill_or_error)
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': skill_camel
            }), 200
        else:
            return jsonify({
                'code': 1,
                'message': skill_or_error
            }), 404

    @staticmethod
    async def get_skill_md(current_user: str = None) -> Tuple[Dict, int]:
        """查看 skills_repo 下某一文件夹内的 SKILL.md 文件内容"""
        if not current_user:
            return jsonify({'error': '用户未认证'}), 401

        skill_id = request.args.get('skill_id', type=str)
        if not skill_id:
            return jsonify({'error': '必须提供技能ID'}), 400

        success, skill_data = AISkill.get_skill(uuid=skill_id)
        if not success:
            return jsonify({'error': skill_data}), 404

        # 权限校验：技能存在数据库记录时，须为 public 或当前用户创建（admin 放行）
        if skill_data.get('visibility') != 'public' and skill_data.get('create_by') != current_user and current_user.lower() != 'admin':
            return jsonify({'error': '无权查看该技能'}), 403

        folder = skill_data.get('folder_name')
        if not folder:
            return jsonify({'error': '文件夹名称不存在'}), 400

        # 防止路径穿越：文件夹名中不允许包含路径分隔符或 ..
        if '..' in folder or '/' in folder or '\\' in folder:
            return jsonify({'error': '非法的文件夹名称'}), 400

        skill_name = skill_data.get('name', '')

        skills_path = config_manager.get_skills_path()
        real_base = os.path.realpath(skills_path)
        skill_dir = os.path.realpath(os.path.join(skills_path, folder))
        if not skill_dir.startswith(real_base + os.sep):
            return jsonify({'error': '非法的文件夹名称'}), 400

        readme_path = os.path.join(skill_dir, 'SKILL.md')
        if not os.path.isfile(readme_path):
            return jsonify({'error': 'SKILL.md 文件不存在'}), 404

        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read SKILL.md for folder '{folder}': {e}")
            return jsonify({'error': f'读取 SKILL.md 失败: {str(e)}'}), 500

        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'skill_name': skill_name,
                'content': content
            }
        }), 200

    @staticmethod
    async def delete_skill(current_user: str = None) -> Tuple[Dict, int]:
        """删除技能：同时删除数据库记录和文件系统目录"""
        if not current_user:
            return jsonify({'error': '用户未认证'}), 401

        request_data = request.json or {}
        uuid = request_data.get('uuid')
        if not uuid:
            uuid = request.args.get('uuid', type=str)
        if not uuid:
            return jsonify({'error': '删除操作需要提供技能UUID'}), 400

        result, message = AISkill.delete_skill(uuid=uuid)
        if result:
            return jsonify({'success': True, 'message': message}), 200
        else:
            return jsonify({'error': message}), 404

    @staticmethod
    async def update_skill(current_user: str = None) -> Tuple[Dict, int]:
        """编辑技能信息"""
        if not current_user:
            return jsonify({'error': '用户未认证'}), 401

        update_data = request.json
        if not update_data:
            return jsonify({'error': '更新数据不能为空'}), 400

        uuid = update_data.pop('uuid', None)
        if not uuid:
            uuid = request.args.get('uuid', type=str)
        if not uuid:
            return jsonify({'error': '必须提供技能UUID'}), 400

        result, skill_or_message = AISkill.update_skill(uuid=uuid, update_data=update_data, current_user=current_user)
        if result:
            skill_camel = convert_dict_keys_to_camel_case(skill_or_message)
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': skill_camel
            }), 200
        else:
            return jsonify({
                'code': 1,
                'message': skill_or_message
            }), 400
