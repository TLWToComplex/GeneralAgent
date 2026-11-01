"""
AI 用户组关联控制器模块。
处理AI用户组关联管理操作的HTTP请求。
"""
import logging
from typing import Dict, Tuple
from flask import request, jsonify
from src.accessors.ai_user_group_relation_accessor import ai_user_group_relation_accessor
from src.utils.async_route import async_route

logger = logging.getLogger(__name__)


class AIUserGroupRelationController:
    """
    处理AI用户组关联相关HTTP请求的控制器类。
    提供AI用户组关联的CRUD操作。
    """


    @staticmethod
    def get_user_group_relation(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        获取用户组关联详情的内部方法
        
        参数:
            - current_user (str): 当前登录的用户名
            
        查询参数:
            - uuid: 用户组关联UUID (与group_id二选一)
            - group_id: 群组ID (与uuid二选一)
            - user_id: 用户ID (可选)
        
        返回:
            包含用户组关联详情或错误信息的JSON响应
        """
        relation_uuid = request.args.get('uuid', type=str)
        group_id = request.args.get('group_id', type=str)

        # 验证参数，uuid和group_id必须提供其中一个
        if not relation_uuid and not group_id:
            logger.warning("Either user group relation UUID or group_id is required")
            return jsonify({
                'code': 1,
                'message': '必须提供用户组关联UUID或群组ID'
            }), 400

        # 如果提供了uuid，按uuid查询单个关联
        if relation_uuid:
            # 调用访问器获取用户组关联信息
            success, result = ai_user_group_relation_accessor.get_user_group_relation(relation_uuid)

            if success:
                return jsonify({
                    'code': 0,
                    'message': 'success',
                    'data': result
                }), 200
            else:
                logger.error(f"Failed to get user group relation by UUID: {result}")
                return jsonify({
                    'code': 1,
                    'message': result
                }), 404
        
        # 如果提供了group_id，查询该群组下的所有用户关联
        if group_id:
            # 调用访问器查询该群组的所有用户关联
            success, results = ai_user_group_relation_accessor.list_user_group_relations(
                skip=0, 
                take=1000,  # 设置一个较大的值以获取所有关联
                filters={'group_id': group_id}
            )

            if success:
                # 从返回的字典中提取items列表
                relations_list = results.get('items', [])
                total = results.get('total', 0)
                
                # 提取所有user_id并汇总到一个数组
                user_ids = []
                combined_data = None
                
                for result in relations_list:
                    # 收集所有user_id
                    if isinstance(result, dict) and 'user_id' in result:
                        user_ids.append(result['user_id'])
                    # 获取第一条记录作为基础数据
                    if not combined_data and isinstance(result, dict):
                        combined_data = result.copy()
                
                # 如果有数据，构建响应格式
                if combined_data:
                    # 用汇总的user_id数组替换单个user_id
                    combined_data['user_id'] = user_ids
                    
                    # 构建完整响应体
                    response_body = {
                        "code": 0,
                        "data": combined_data,
                        "message": "success"
                    }
                    
                    return jsonify(response_body), 200
                else:
                    # 如果没有找到数据，返回空结果
                    return jsonify({
                        "code": 0,
                        "data": {},
                        "message": "success"
                    }), 200
            else:
                logger.error(f"Failed to get user group relations by group_id: {results}")
                return jsonify({
                    'code': 1,
                    'message': results
                }), 500

    @staticmethod
    async def get_user_group_relation_async(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        获取用户组关联关系（异步路由方法）
        虽然accessor方法是同步的，但为了支持异步路由，这里使用异步方法包装
        """
        return AIUserGroupRelationController.get_user_group_relation(current_user)
    

    @staticmethod
    async def sync_user_group_relations_async(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        同步用户组关联关系（异步路由方法）
        虽然accessor方法是同步的，但为了支持异步路由，这里使用异步方法包装
        """
        return AIUserGroupRelationController.sync_user_group_relations(current_user)
    
    @staticmethod
    def sync_user_group_relations(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        同步用户组关联关系（批量处理）
        
        需求：以全量user_id数组为基准，确保数据库中user_id和group_id的关联与输入一致
        1. 保持已存在的关联
        2. 新增需要关联的用户
        3. 删除取消关联的用户
        
        参数:
            - current_user (str): 当前登录的用户名
            
        请求体：
            - user_id: 字符串数组，包含全量的用户ID（已绑定和未绑定）
            - group_id: 字符串，用户组ID
            - additional_info: 可选，扩展字段
            
        返回:
            包含同步结果的JSON响应
        """
        if not request.is_json:
            logger.warning("Received non-JSON request for sync_user_group_relations")
            return jsonify({
                'code': 1,
                'message': '请求体必须为JSON格式'
            }), 400

        request_data = request.json

        # 验证必填字段
        if 'user_id' not in request_data:
            logger.warning("Missing required field: user_id")
            return jsonify({
                'code': 1,
                'message': '用户ID为必填字段'
            }), 400

        if 'group_id' not in request_data:
            logger.warning("Missing required field: group_id")
            return jsonify({
                'code': 1,
                'message': '用户组ID为必填字段'
            }), 400

        # 获取请求参数
        input_user_ids = request_data['user_id']
        group_id = request_data['group_id']
        additional_info = request_data.get('additional_info', {})
        
        # 验证user_id必须是数组
        if not isinstance(input_user_ids, list):
            return jsonify({
                'code': 1,
                'message': 'user_id必须为字符串数组'
            }), 400
        
        # 验证数组中的每个元素都是字符串
        for uid in input_user_ids:
            if not isinstance(uid, str):
                return jsonify({
                    'code': 1,
                    'message': f'用户ID必须为字符串格式，发现非字符串值: {uid}'
                }), 400
        
        try:
            # 获取数据库中该group_id下已有的所有用户关联
            success, db_results = ai_user_group_relation_accessor.list_user_group_relations(
                skip=0, 
                take=1000,  # 设置一个较大的值以获取所有关联
                filters={'group_id': group_id}
            )
            
            if not success:
                logger.error(f"Failed to get existing user group relations: {db_results}")
                return jsonify({
                    'code': 1,
                    'message': f'获取现有关联失败: {db_results}'
                }), 500
            
            # 提取数据库中已存在的user_id和对应的关联UUID
            existing_relations = db_results.get('items', [])
            existing_user_ids = set()
            user_id_to_uuid = {}
            
            for relation in existing_relations:
                if 'user_id' in relation and 'uuid' in relation:
                    existing_user_ids.add(relation['user_id'])
                    user_id_to_uuid[relation['user_id']] = relation['uuid']
            
            # 计算需要操作的用户ID集合
            input_user_ids_set = set(input_user_ids)
            
            # 需要新增的用户ID（在输入中但不在数据库中）
            to_add_user_ids = input_user_ids_set - existing_user_ids
            
            # 需要删除的用户ID（在数据库中但不在输入中）
            to_delete_user_ids = existing_user_ids - input_user_ids_set
            
            # 执行删除操作
            deleted_count = 0
            delete_failures = []
            for uid in to_delete_user_ids:
                relation_uuid = user_id_to_uuid.get(uid)
                if relation_uuid:
                    success, result = ai_user_group_relation_accessor.delete_user_group_relation(
                        relation_uuid, delete_by=current_user
                    )
                    if success:
                        deleted_count += 1
                        logger.info(f"Deleted user group relation: user_id={uid}, group_id={group_id}")
                    else:
                        delete_failures.append({
                            'user_id': uid,
                            'message': result
                        })
            
            # 执行新增操作
            added_count = 0
            add_failures = []
            for uid in to_add_user_ids:
                single_data = {
                    'user_id': uid,
                    'group_id': group_id,
                    'additional_info': additional_info
                }
                
                success, result = ai_user_group_relation_accessor.create_user_group_relation(
                    single_data, create_by=current_user
                )
                
                if success:
                    added_count += 1
                    logger.info(f"Added user group relation: user_id={uid}, group_id={group_id}")
                else:
                    add_failures.append({
                        'user_id': uid,
                        'message': result
                    })
            
            # 构建响应数据
            response_data = {
                'added_count': added_count,
                'deleted_count': deleted_count,
                'total_requested': len(input_user_ids),
                'total_remaining': len(input_user_ids_set) - len(add_failures)
            }
            
            # 添加失败信息（如果有）
            has_failures = len(add_failures) > 0 or len(delete_failures) > 0
            if has_failures:
                response_data['add_failures'] = add_failures
                response_data['delete_failures'] = delete_failures
                
                # 部分成功的情况
                return jsonify({
                    'code': 2,
                    'message': '部分用户组关联操作失败',
                    'data': response_data
                }), 207
            
            # 全部成功的情况
            logger.info(f"Successfully synced user group relations: group_id={group_id}, added={added_count}, deleted={deleted_count}")
            return jsonify({
                'code': 0,
                'message': '用户组关联同步成功',
                'data': response_data
            }), 200
        except Exception as e:
            logger.error(f"Exception during sync_user_group_relations: {str(e)}")
            return jsonify({
                'code': 1,
                'message': f'同步用户组关联时发生错误: {str(e)}'
            }), 500