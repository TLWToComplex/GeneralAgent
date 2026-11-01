"""
AI权限控制器模块。
处理AI权限管理的API端点。
"""
from flask import request, jsonify
from typing import Dict, List, Union, Tuple, Any
from src.accessors.ai_permissions_accessor import AIPermission
from src.utils.name_converter import convert_dict_keys_to_camel_case

class AIPermissionsController:

    @staticmethod
    async def update_permission(current_user: str = None) -> Tuple[Dict, int]:
        """批量更新AI权限信息，接收包含多个权限项的数组"""
        # 检查当前用户是否存在
        if not current_user:
            return jsonify({'error': '用户未认证'}), 401
        
        # 检查当前用户是否为管理员
        if current_user.lower() != 'admin':
            return jsonify({'error': '权限不足，只有管理员可以更新权限'}), 403
            
        request_data = request.json
        
        if not request_data:
            return jsonify({'error': '请求数据不能为空'}), 400
        
        # 验证请求体结构
        if 'group_id' not in request_data:
            return jsonify({'error': 'group_id为必填字段'}), 400
        
        if 'list' not in request_data or not isinstance(request_data['list'], list):
            return jsonify({'error': 'list必须是数组类型'}), 400
        
        group_id = request_data['group_id']
        permissions_list = request_data['list']
        
        if not permissions_list:
            return jsonify({'error': '权限列表不能为空'}), 400
        
        # 验证每个权限项
        for idx, perm_item in enumerate(permissions_list):
            # 验证必要字段
            required_fields = ['entity_id', 'entity_type', 'permission']
            for field in required_fields:
                if field not in perm_item:
                    return jsonify({'error': f'第{idx+1}个权限项中{field}为必填字段'}), 400
                # 对于数值类型的字段，允许0值
                if field in ['entity_type', 'permission'] and not isinstance(perm_item[field], int):
                    return jsonify({'error': f'第{idx+1}个权限项中{field}必须为整数类型'}), 400
            
            # 验证权限值的有效性（0：无权限 1：只读 2：读写）
            if perm_item['permission'] not in [0, 1, 2]:
                return jsonify({'error': f'第{idx+1}个权限项中的权限值必须为0、1或2'}), 400
        
        # 准备返回结果
        result_list = []
        errors = []
        
        # 遍历权限列表，逐个处理
        for idx, perm_item in enumerate(permissions_list):
            try:
                # 构造权限数据
                permission_data = {
                    'group_id': group_id,
                    'entity_id': perm_item['entity_id'],
                    'entity_type': perm_item['entity_type'],
                    'permission': perm_item['permission'],
                    'update_by': current_user,
                    'create_by': current_user
                }
                
                # 尝试通过group_id、entity_id和entity_type查找权限
                filters = {
                    'group_id': group_id,
                    'entity_id': perm_item['entity_id'],
                    'entity_type': perm_item['entity_type']
                }
                
                find_result, existing_permissions = AIPermission.list_permissions(
                    take=1, 
                    filters=filters
                )
                
                if find_result and existing_permissions.get('items'):
                    # 权限存在，执行更新操作
                    existing_perm = existing_permissions['items'][0]
                    update_result, updated_perm = AIPermission.update_permission(
                        permission_id=existing_perm.get('id'),
                        update_data=permission_data
                    )
                    
                    if update_result:
                        result_list.append(AIPermissionsController._flatten_additional_info(updated_perm))
                    else:
                        errors.append(f'第{idx+1}个权限项更新失败: {updated_perm}')
                else:
                    # 权限不存在，执行新增操作
                    add_result, new_perm = AIPermission.add_permission(permission_data)
                    
                    if add_result:
                        result_list.append(AIPermissionsController._flatten_additional_info(new_perm))
                    else:
                        errors.append(f'第{idx+1}个权限项创建失败: {new_perm}')
            except Exception as e:
                errors.append(f'第{idx+1}个权限项处理失败: {str(e)}')
        
        # 返回处理结果
        if errors:
            return jsonify({
                'success': False,
                'message': '部分权限处理失败',
                'errors': errors,
                'data': result_list
            }), 207
        else:
            return jsonify({
                'success': True,
                'message': '权限处理成功',
                'data': result_list
            }), 200

    @staticmethod
    def _flatten_additional_info(permission_data: Dict) -> Dict:
        """平铺permission_data中的additional_info字段，并将下划线命名转换为驼峰命名
        
        如果permission_data中存在additional_info字段且为字典类型，
        则将其中的所有键值对添加到permission_data的顶层，然后移除additional_info字段。
        同时将所有键名从下划线命名转换为驼峰命名（如create_time -> createTime）。
        
        参数:
            permission_data: 权限数据字典
            
        返回:
            处理后的权限数据字典
        """
        # 创建一个副本以避免修改原始数据
        result = permission_data.copy()
        
        # 检查是否存在additional_info字段且为字典类型
        if 'additional_info' in result and isinstance(result['additional_info'], dict):
            # 将additional_info中的键值对添加到顶层
            result.update(result['additional_info'])
            # 移除原始的additional_info字段
            del result['additional_info']
        
        # 从utils导入的函数转换所有键名为驼峰命名
        return convert_dict_keys_to_camel_case(result)