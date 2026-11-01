"""
AI技能访问器模块。
管理AI技能的数据库操作。
"""
import uuid
import shutil
import logging
from datetime import datetime
from src.utils.database import db
from typing import Dict, Any, Tuple, List, Union

logger = logging.getLogger(__name__)


class AISkill(db.Model):
    __tablename__ = 'ai_skill'
    __table_args__ = (
        db.UniqueConstraint('folder_name', 'create_by', name='uq_skill_folder_name_create_by'),
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    folder_name = db.Column(db.String(100), nullable=False)
    visibility = db.Column(db.String(10), default='private')
    create_time = db.Column(db.DateTime, nullable=False, default=datetime.now)
    create_by = db.Column(db.String(50), nullable=False)
    additional_info = db.Column(db.JSON)

    @classmethod
    def add_skill(cls, skill_data: dict) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """添加技能记录"""
        try:
            if 'uuid' not in skill_data:
                skill_data['uuid'] = str(uuid.uuid4())
            if 'create_time' not in skill_data:
                skill_data['create_time'] = datetime.now()

            new_skill = cls(**skill_data)
            db.session.add(new_skill)
            db.session.commit()
            return True, cls._to_dict(new_skill)
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def list_skills(cls, create_by: str = None, allowed_entity_ids: list = None) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """查询技能列表，支持权限过滤"""
        try:

            # 基础查询：自己创建的技能（无论 visibility 状态）
            if create_by == 'admin':
                query = cls.query
            else:
                query = cls.query.filter_by(create_by=create_by)
                # 如果有授权的实体ID列表，则通过 OR 条件合并查询
                # 注意：这里我们只允许访问 visibility='public' 或 'global' 或者自己创建的 private 技能
                if allowed_entity_ids:
                    authorized_query = cls.query.filter(
                        cls.uuid.in_(allowed_entity_ids),
                        cls.visibility.in_(['public', 'global'])
                    )
                    query = query.union(authorized_query)
            # 排序并返回所有数据
            skills = query.order_by(cls.id).all()
            return True, [cls._to_dict(skill) for skill in skills] if skills else []
        except Exception as e:
            return False, str(e)

    @classmethod
    def get_skill(cls, uuid: str = None, create_by: str = None) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """获取单个技能详情"""
        try:
            if not uuid:
                return False, '技能UUID不能为空'
            
            # 构建查询
            query = cls.query.filter_by(uuid=uuid)
            
            skill = query.first()
            if skill:
                return True, cls._to_dict(skill)
            else:
                return False, '技能不存在或无访问权限'
            
        except Exception as e:
            return False, str(e)

    @classmethod
    def delete_skill(cls, uuid: str = None, current_user: str = None) -> Tuple[bool, str]:
        """删除技能记录及文件系统目录"""
        try:
            skill = cls.query.filter_by(uuid=uuid).first()
            if not skill:
                return False, '技能不存在'

            # 只有创建者可以删除
            if current_user and skill.create_by != current_user:
                return False, '无权删除该技能'

            # 保存目录信息用于删除文件
            folder_name = skill.folder_name

            # 物理删除数据库记录
            db.session.delete(skill)
            db.session.commit()

            # 删除文件系统目录
            try:
                from src.utils.config_manager import config_manager
                skills_path = config_manager.get_skills_path()
                import os
                skill_dir = os.path.join(skills_path, folder_name)
                if os.path.exists(skill_dir):
                    shutil.rmtree(skill_dir, ignore_errors=True)
                    logger.info(f"Deleted skill directory: {skill_dir}")
            except Exception as e:
                logger.warning(f"Failed to delete skill directory: {e}")

            return True, '技能删除成功'
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def check_name_exists(cls, folder_name: str) -> Tuple[bool, Union[Dict[str, Any], None]]:
        """检查同名技能是否已存在"""
        try:
            skill = cls.query.filter_by(folder_name=folder_name).first()
            if skill:
                return True, cls._to_dict(skill)
            return False, None
        except Exception as e:
            return False, None

    @classmethod
    def update_skill(cls, uuid: str = None, update_data: dict = None, current_user: str = None) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """更新技能信息"""
        try:
            skill = cls.query.filter_by(uuid=uuid).first()
            if not skill:
                return False, '技能不存在'

            # 只有创建者或admin可以修改
            if current_user and skill.create_by != current_user and current_user.lower() != 'admin':
                return False, '无权修改该技能'

            # 不允许更新的字段
            update_data.pop('id', None)
            update_data.pop('uuid', None)
            update_data.pop('create_time', None)
            update_data.pop('create_by', None)
            update_data.pop('folder_name', None)

            # 如果修改了 name，需要同步重命名文件夹
            new_name = update_data.get('name')
            if new_name and new_name != skill.folder_name:
                # 检查新名称是否已存在
                exists, _ = cls.check_name_exists(new_name)
                if exists:
                    return False, '该技能名称已存在'

                # 重命名文件系统目录
                try:
                    from src.utils.config_manager import config_manager
                    import os
                    skills_path = config_manager.get_skills_path()
                    old_dir = os.path.join(skills_path, skill.folder_name)
                    new_dir = os.path.join(skills_path, new_name)
                    if os.path.exists(old_dir) and not os.path.exists(new_dir):
                        os.rename(old_dir, new_dir)
                        update_data['folder_name'] = new_name
                except Exception as e:
                    logger.warning(f"Failed to rename skill directory: {e}")
                    return False, f'重命名技能目录失败: {str(e)}'

            for key, value in update_data.items():
                setattr(skill, key, value)

            db.session.commit()
            return True, cls._to_dict(skill)
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def _to_dict(skill) -> Dict[str, Any]:
        """将模型实例转换为字典"""
        return {
            'id': skill.id,
            'uuid': skill.uuid,
            'name': skill.name,
            'description': skill.description,
            'folder_name': skill.folder_name,
            'visibility': skill.visibility,
            'create_time': skill.create_time,
            'create_by': skill.create_by,
            'additional_info': skill.additional_info,
        }
