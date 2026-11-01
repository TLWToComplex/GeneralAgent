"""
AI用户服务层模块。
整合用户、用户组、用户组关联的业务逻辑。
"""
import logging
from typing import Dict, Any, Tuple, List
from src.accessors.ai_user_accessor import AIUser
from src.accessors.ai_user_group_relation_accessor import AIUserGroupRelation, ai_user_group_relation_accessor
from src.accessors.ai_user_group_accessor import AIUserGroup

logger = logging.getLogger(__name__)


class AIUserService:
    """
    AI用户服务类。
    提供涉及多表的复杂业务逻辑操作。
    """
    
    @staticmethod
    def get_user_with_groups(user_id: int = None, uuid: str = None, username: str = None) -> Tuple[bool, Any]:
        """
        获取单个用户信息及其所属用户组

        Returns:
            Tuple[bool, Any]: (是否成功, 成功返回用户字典（含groups字段），失败返回错误信息)
        """
        try:
            success, result = AIUser.get_user(user_id, uuid, username)
            if not success:
                return False, result

            user_uuid = result.get('uuid')

            relations = AIUserGroupRelation.query.filter(
                AIUserGroupRelation.user_id == user_uuid
            ).all()

            groups = []
            if relations:
                group_ids = [r.group_id for r in relations]
                group_records = AIUserGroup.query.filter(AIUserGroup.uuid.in_(group_ids)).all()
                groups = [{'group_id': g.uuid, 'group_name': g.name} for g in group_records]

            result['groups'] = groups
            return True, result

        except Exception as e:
            logger.error(f"Error in get_user_with_groups service: {str(e)}")
            return False, str(e)

    @staticmethod
    def list_users_with_groups(skip: int = 0, take: int = 100) -> Tuple[bool, Any]:
        """
        获取用户列表及其所属的用户组信息
        
        Args:
            skip: 跳过记录数
            take: 返回记录数
            
        Returns:
            Tuple[bool, Any]: (是否成功, 成功返回用户列表及分页信息，失败返回错误信息)
        """
        try:
            # 第1步：查询所有用户（支持分页）
            users_query = AIUser.query.filter_by(is_del=0).order_by(AIUser.id)
            total = users_query.count()
            users = users_query.offset(skip).limit(take).all()
            
            if not users:
                return True, {
                    'items': [],
                    'total': 0,
                    'skip': skip,
                    'take': take
                }
            
            # 提取所有用户的UUID
            user_uuids = [user.uuid for user in users]
            
            # 第2步：批量查询这些用户的用户组关联关系
            relations = AIUserGroupRelation.query.filter(
                AIUserGroupRelation.user_id.in_(user_uuids)
            ).all()
            
            # 建立 user_id -> [group_id] 的映射
            user_groups_map = {}
            all_group_ids = set()
            
            for relation in relations:
                user_id = relation.user_id
                group_id = relation.group_id
                
                if user_id not in user_groups_map:
                    user_groups_map[user_id] = []
                user_groups_map[user_id].append(group_id)
                all_group_ids.add(group_id)
            
            # 第3步：批量查询所有涉及的用户组信息
            groups = []
            if all_group_ids:
                groups = AIUserGroup.query.filter(
                    AIUserGroup.uuid.in_(list(all_group_ids))
                ).all()
            
            # 建立 group_id -> group_info 的映射
            group_map = {}
            for group in groups:
                group_map[group.uuid] = {
                    'group_id': group.uuid,
                    'group_name': group.name,
                    'description': group.additional_info.get('description', '') if group.additional_info else ''
                }
            
            # 第4步：组装数据（只返回必要字段）
            items = []
            for user in users:
                # 获取该用户的用户组列表
                user_group_ids = user_groups_map.get(user.uuid, [])
                user_groups = [
                    {
                        'group_id': group_map[gid]['group_id'],
                        'group_name': group_map[gid]['group_name']
                    }
                    for gid in user_group_ids
                    if gid in group_map
                ]

                # 只返回必要的用户字段
                user_data = {
                    'user_id': user.uuid,
                    'id': user.id,
                    'username': user.username,
                    'realname': user.realname,
                    'email': user.email,
                    'groups': user_groups,
                    'is_locked': bool(user.additional_info and 'inactive_locked' in user.additional_info),
                }
                
                items.append(user_data)
            
            return True, {
                'items': items,
                'total': total,
                'skip': skip,
                'take': take
            }
            
        except Exception as e:
            logger.error(f"Error in list_users_with_groups service: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def sync_user_groups_for_users(user_group_map: Dict[str, List[str]], current_user: str = 'admin') -> Tuple[bool, Any]:
        """
        批量同步用户与用户组的关联关系（以用户为中心）
        
        对于每个用户，确保其用户组关联与输入一致：
        1. 保留已存在的关联
        2. 新增需要关联的用户组
        3. 删除取消关联的用户组
        
        Args:
            user_group_map: 字典，key为用户ID(uuid)，value为用户组ID(uuid)列表
                           例如: {"user_uuid_1": ["group_uuid_a", "group_uuid_b"]}
            current_user: 当前操作人
            
        Returns:
            Tuple[bool, Any]: (是否成功, 同步结果统计信息)
        """
        try:
            total_added = 0
            total_deleted = 0
            user_results = []
            failures = []
            
            # 遍历每个用户
            for user_id, target_group_ids in user_group_map.items():
                try:
                    # 验证 user_id 格式
                    if not isinstance(user_id, str) or not user_id.strip():
                        failures.append({
                            'user_id': user_id,
                            'error': '用户ID格式无效'
                        })
                        continue
                    
                    # 验证 group_ids 格式
                    if not isinstance(target_group_ids, list):
                        failures.append({
                            'user_id': user_id,
                            'error': '用户组ID必须为数组'
                        })
                        continue
                    
                    # 过滤空字符串
                    target_group_ids = [gid for gid in target_group_ids if isinstance(gid, str) and gid.strip()]
                    
                    # 第1步：查询该用户现有的所有用户组关联
                    success, existing_relations = ai_user_group_relation_accessor.list_user_group_relations(
                        skip=0,
                        take=1000,
                        filters={'user_id': user_id}
                    )
                    
                    if not success:
                        failures.append({
                            'user_id': user_id,
                            'error': f'查询现有关联失败: {existing_relations}'
                        })
                        continue
                    
                    # 提取现有的 group_id 和对应的 relation_uuid
                    existing_group_ids = set()
                    group_id_to_uuid = {}
                    
                    for relation in existing_relations.get('items', []):
                        if 'group_id' in relation and 'uuid' in relation:
                            existing_group_ids.add(relation['group_id'])
                            group_id_to_uuid[relation['group_id']] = relation['uuid']
                    
                    # 第2步：计算差异
                    target_group_set = set(target_group_ids)
                    to_add = target_group_set - existing_group_ids  # 需要新增的
                    to_delete = existing_group_ids - target_group_set  # 需要删除的
                    
                    user_added = 0
                    user_deleted = 0
                    user_errors = []
                    
                    # 第3步：执行删除操作
                    for group_id in to_delete:
                        relation_uuid = group_id_to_uuid.get(group_id)
                        if relation_uuid:
                            success, result = ai_user_group_relation_accessor.delete_user_group_relation(
                                relation_uuid, delete_by=current_user
                            )
                            if success:
                                user_deleted += 1
                                logger.info(f"Deleted relation: user_id={user_id}, group_id={group_id}")
                            else:
                                user_errors.append({
                                    'action': 'delete',
                                    'group_id': group_id,
                                    'error': result
                                })
                    
                    # 第4步：执行新增操作
                    for group_id in to_add:
                        relation_data = {
                            'user_id': user_id,
                            'group_id': group_id
                        }
                        success, result = ai_user_group_relation_accessor.create_user_group_relation(
                            relation_data, create_by=current_user
                        )
                        if success:
                            user_added += 1
                            logger.info(f"Added relation: user_id={user_id}, group_id={group_id}")
                        else:
                            user_errors.append({
                                'action': 'add',
                                'group_id': group_id,
                                'error': result
                            })
                    
                    total_added += user_added
                    total_deleted += user_deleted
                    
                    # 记录用户级别的結果
                    user_results.append({
                        'user_id': user_id,
                        'added_count': user_added,
                        'deleted_count': user_deleted,
                        'final_group_count': len(target_group_set) - len([e for e in user_errors if e['action'] == 'add'])
                    })
                    
                    # 如果有错误，记录到 failures
                    if user_errors:
                        failures.append({
                            'user_id': user_id,
                            'errors': user_errors
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing user {user_id}: {str(e)}")
                    failures.append({
                        'user_id': user_id,
                        'error': f'处理异常: {str(e)}'
                    })
            
            # 构建返回结果
            result_data = {
                'total_users_processed': len(user_group_map),
                'total_added': total_added,
                'total_deleted': total_deleted,
                'user_results': user_results
            }
            
            if failures:
                result_data['failures'] = failures
                return True, result_data  # 部分成功也返回 True，但包含失败信息
            
            return True, result_data
            
        except Exception as e:
            logger.error(f"Error in sync_user_groups_for_users service: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def delete_user_with_relations(user_uuid: str) -> Tuple[bool, Any]:
        """
        删除用户及其相关的用户组关联记录
        
        Args:
            user_uuid: 用户UUID
            
        Returns:
            Tuple[bool, Any]: (是否成功, 成功返回消息，失败返回错误信息)
        """
        try:
            # 第1步：调用 Accessor 层删除该用户的所有用户组关联记录
            success, result = ai_user_group_relation_accessor.delete_user_group_relations_by_user(
                user_id=user_uuid,
                delete_by='system'
            )
            
            if not success:
                logger.error(f"Failed to delete user group relations: {result}")
                return False, f"删除用户组关联失败: {result}"
            
            logger.info(f"Deleted group relations for user: {user_uuid}")
            
            # 第2步：调用 accessor 的 delete_user 方法（软删除）
            from src.accessors.ai_user_accessor import AIUser
            success, result = AIUser.delete_user(user_uuid)
            
            if success:
                logger.info(f"User deleted successfully: {user_uuid}")
                return True, result
            else:
                logger.error(f"Failed to delete user: {result}")
                return False, result
                
        except Exception as e:
            logger.error(f"Error in delete_user_with_relations service: {str(e)}")
            return False, str(e)

    @staticmethod
    def ensure_default_admin():
        """系统启动时确保 admin 用户存在，不存在则自动创建"""
        from src.config import DefaultAdminConfig
        try:
            existing = AIUser.query.filter_by(username=DefaultAdminConfig.USERNAME, is_del=0).first()
            if existing:
                logger.info(f"默认管理员账号已存在: {DefaultAdminConfig.USERNAME}")
                return True
            user_data = {
                'username': DefaultAdminConfig.USERNAME,
                'password': DefaultAdminConfig.PASSWORD,
                'realname': DefaultAdminConfig.REALNAME,
                'email': DefaultAdminConfig.EMAIL,
                'additional_info': {},
                'platform_sort': [],
                'preferences': {},
                'create_by': 'system',
            }
            success, result = AIUser.add_user(user_data)
            if success:
                logger.info(f"默认管理员账号创建成功: {DefaultAdminConfig.USERNAME}")
            else:
                logger.error(f"默认管理员账号创建失败: {result}")
            return success
        except Exception as e:
            logger.error(f"初始化默认管理员账号异常: {e}")
            return False

    @staticmethod
    def ensure_default_group():
        """系统启动时确保存在默认用户组，不存在则自动创建"""
        from src.accessors.ai_user_group_accessor import ai_user_group_accessor
        try:
            default_group = AIUserGroup.query.filter(
                AIUserGroup.additional_info['is_default'].as_boolean() == True  # noqa: E712
            ).first()
            if default_group:
                logger.info(f"默认用户组已存在: {default_group.name}")
                return True
            group_data = {
                'name': '默认组',
                'additional_info': {'is_default': True},
            }
            success, result = ai_user_group_accessor.create_user_group(group_data, create_by='system')
            if success:
                logger.info("默认用户组创建成功: 默认组")
            else:
                logger.error(f"默认用户组创建失败: {result}")
            return success
        except Exception as e:
            logger.error(f"初始化默认用户组异常: {e}")
            return False

    @staticmethod
    def flatten_additional_info(user_data: dict) -> dict:
        """
        平铺用户信息中的 additional_info 字段。
        将 additional_info 中的键值对提取到用户对象的顶层，并移除 additional_info 键本身。

        Args:
            user_data: 包含 additional_info 字段的用户字典

        Returns:
            平铺后的用户字典
        """
        if isinstance(user_data, dict) and 'additional_info' in user_data:
            additional_info = user_data.pop('additional_info', {})
            if isinstance(additional_info, dict):
                user_data.update(additional_info)
        return user_data

    @staticmethod
    def delete_group_with_relations(group_uuid: str) -> Tuple[bool, Any]:
        """
        删除用户组及其关联的权限记录和用户组关联记录

        Args:
            group_uuid: 用户组UUID

        Returns:
            Tuple[bool, Any]: (是否成功, 成功返回消息，失败返回错误信息)
        """
        try:
            from src.accessors.ai_permissions_accessor import AIPermission

            # 1. 删除 ai_permissions 中该用户组的所有权限记录
            success, result = AIPermission.delete_permissions_by_group(group_uuid)
            if not success:
                logger.error(f"Failed to delete permissions for group {group_uuid}: {result}")
                return False, f"删除权限记录失败: {result}"
            logger.info(f"Deleted permissions for group: {group_uuid}")

            # 2. 删除 ai_user_group_relation 中该用户组的所有关联记录
            success, result = ai_user_group_relation_accessor.delete_user_group_relations_by_group(
                group_id=group_uuid, delete_by='system'
            )
            if not success:
                logger.error(f"Failed to delete user group relations for group {group_uuid}: {result}")
                return False, f"删除用户组关联失败: {result}"
            logger.info(f"Deleted user group relations for group: {group_uuid}")

            # 3. 删除用户组本身
            group = AIUserGroup.query.filter_by(uuid=group_uuid).first()
            if not group:
                return False, "用户组不存在"
            from src.utils.database import db
            db.session.delete(group)
            db.session.commit()
            logger.info(f"User group deleted successfully: {group_uuid}")
            return True, "用户组删除成功"

        except Exception as e:
            logger.error(f"Error in delete_group_with_relations service: {str(e)}")
            return False, str(e)
