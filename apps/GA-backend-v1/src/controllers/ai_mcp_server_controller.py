"""
AI MCP服务器控制器模块。
处理AI MCP服务器管理操作的HTTP请求。
"""
import logging
from typing import Dict, Tuple
from flask import request, jsonify
from src.accessors.ai_mcp_server_accessor import ai_mcp_server_accessor
from src.utils.async_route import async_route

logger = logging.getLogger(__name__)


class AIMCPServerController:
    """
    处理AI MCP服务器相关HTTP请求的控制器类。
    提供AI MCP服务器的CRUD操作。
    """

    @staticmethod
    def create_mcp_server(current_user: str = 'admin') -> Tuple[Dict, int]:
        """创建MCP服务的内部方法"""
        # 实际实现逻辑保持不变
        """
        创建MCP服务

        期望输入包含MCP服务器详情的JSON数据。

        返回:
            包含创建的服务器数据或错误信息的JSON响应
        """
        if not request.is_json:
            logger.warning("Received non-JSON request for create_mcp_server")
            return jsonify({
                'code': 1,
                'message': '请求体必须为JSON格式'
            }), 400

        request_data = request.json

        # 验证必填字段
        if 'name' not in request_data:
            logger.warning("Missing required field: name")
            return jsonify({
                'code': 1,
                'message': 'MCP服务名称为必填字段'
            }), 400

        if 'url' not in request_data:
            logger.warning("Missing required field: url")
            return jsonify({
                'code': 1,
                'message': 'MCP服务地址为必填字段'
            }), 400

        if 'type' not in request_data:
            logger.warning("Missing required field: type")
            return jsonify({
                'code': 1,
                'message': 'MCP服务类型为必填字段'
            }), 400

        # 调用访问器创建服务
        success, result = ai_mcp_server_accessor.create_mcp_server(
            request_data, create_by=current_user
        )

        if success:
            logger.info(f"MCP server created successfully: {request_data['name']}")

            # 获取创建的完整服务信息
            success, server_info = ai_mcp_server_accessor.get_mcp_server(result['uuid'])
            if success:
                return jsonify({
                    'code': 0,
                    'message': 'success',
                    'data': server_info
                }), 200
            else:
                return jsonify({
                    'code': 1,
                    'message': '创建成功但获取详情失败'
                }), 500
        else:
            logger.error(f"Failed to create MCP server: {result}")
            return jsonify({
                'code': 1,
                'message': result
            }), 400
    
    # 以下是路由中使用的方法名，作为上面方法的别名
    @staticmethod
    async def add_mcp_server(current_user: str = 'admin') -> Tuple[Dict, int]:
        """创建MCP服务（路由方法）"""
        # 虽然accessor方法是同步的，但为了支持异步路由，这里使用异步方法包装
        return AIMCPServerController.create_mcp_server(current_user)
    
    @staticmethod
    async def list_mcp_servers_basic(current_user: str = 'admin') -> Tuple[Dict, int]:
        """获取MCP服务基本列表（路由方法）"""
        # 这里可以根据需要返回简化版本的列表
        return AIMCPServerController.list_mcp_servers(current_user)
    
    @staticmethod
    async def get_mcp_server_async(current_user: str = 'admin') -> Tuple[Dict, int]:
        """获取MCP服务详情（异步路由方法）"""
        return AIMCPServerController.get_mcp_server(current_user)
    
    @staticmethod
    async def list_mcp_servers_async(current_user: str = 'admin') -> Tuple[Dict, int]:
        """获取MCP服务列表（异步路由方法）"""
        return AIMCPServerController.list_mcp_servers(current_user)
    
    @staticmethod
    async def update_mcp_server_async(current_user: str = 'admin') -> Tuple[Dict, int]:
        """更新MCP服务（异步路由方法）"""
        return AIMCPServerController.update_mcp_server(current_user)
    
    @staticmethod
    async def delete_mcp_server_async(current_user: str = 'admin') -> Tuple[Dict, int]:
        """删除MCP服务（异步路由方法）"""
        return AIMCPServerController.delete_mcp_server(current_user)

    @staticmethod
    async def test_mcp_connection(current_user: str = 'admin') -> Tuple[Dict, int]:
        """测试MCP服务连接（异步路由方法）"""
        from src.utils.mcp_client_utils import test_mcp_connection as mcp_test
        
        if not request.is_json:
            logger.warning("Received non-JSON request for test_mcp_connection")
            return jsonify({
                'code': 1,
                'message': '请求体必须为JSON格式'
            }), 400

        request_data = request.json
        
        # 验证必填字段
        server_name = request_data.get('server_name')
        url = request_data.get('url')
        transport = request_data.get('transport') or request_data.get('type')
        headers = request_data.get('headers')  # 可选的认证头
        
        if not server_name or not url:
            logger.warning("Missing required fields: server_name or url")
            return jsonify({
                'code': 1,
                'message': 'server_name和url为必填字段'
            }), 400
        
        try:
            # 调用公共测试方法
            result = await mcp_test(
                server_name=server_name,
                url=url,
                transport=transport,
                timeout=5.0,
                headers=headers
            )
            
            return jsonify({
                'code': 0 if result['success'] else 1,
                'message': result['message'],
                'data': result
            }), 200 if result['success'] else (408 if result.get('error_type') == 'timeout' else 500)
            
        except Exception as e:
            logger.error(f"Error in test_mcp_connection: {str(e)}", exc_info=True)
            return jsonify({
                'code': 1,
                'message': f'测试失败: {str(e)}'
            }), 500

    @staticmethod
    def get_mcp_server(current_user: str = 'admin', allowed_entity_ids: list = None) -> Tuple[Dict, int]:
        """获取MCP服务详情的内部方法"""
        from flask import g as request_g
        server_uuid = request.args.get('uuid', type=str)

        if not server_uuid:
            logger.warning("MCP server UUID is required")
            return jsonify({
                'code': 1,
                'message': 'MCP服务UUID为必填参数'
            }), 400

        # 优先从 g 对象获取权限列表
        perm_list = getattr(request_g, 'allowed_entity_ids', None) or allowed_entity_ids

        # 只有在没有权限过滤（即查询列表或Admin操作）或者用户是创建者时才传入 create_by
        create_by_filter = current_user
        if perm_list and server_uuid in perm_list:
            # 用户在允许访问的列表中，不限制创建者
            create_by_filter = None

        # 调用访问器获取服务信息，传递当前用户参数以过滤create_by字段
        success, result = ai_mcp_server_accessor.get_mcp_server(server_uuid, create_by=create_by_filter)

        if success:
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': result
            }), 200
        else:
            logger.error(f"Failed to get MCP server: {result}")
            return jsonify({
                'code': 1,
                'message': result
            }), 404

    @staticmethod
    def list_mcp_servers(current_user: str = 'admin', allowed_entity_ids: list = None) -> Tuple[Dict, int]:
        """获取MCP服务列表的内部方法"""
        # 移除分页功能，直接获取所有MCP服务器数据
        """
        获取MCP服务列表

        返回:
            包含服务器列表的JSON响应（无需分页）
        """
        try:
            # 获取所有服务列表，传递当前用户参数以过滤create_by字段
            # 使用较大的take值确保获取所有数据
            from flask import g as request_g
            perm_list = getattr(request_g, 'allowed_entity_ids', None) or allowed_entity_ids
            success, result = ai_mcp_server_accessor.list_mcp_servers(0, 9999, create_by=current_user, allowed_entity_ids=perm_list)

            if success:
                return jsonify({
                    'code': 0,
                    'message': 'success',
                    'data': result['items']
                }), 200
            else:
                logger.error(f"Failed to list MCP servers: {result}")
                return jsonify({
                    'code': 1,
                    'message': result
                }), 500
        except Exception as e:
            logger.error(f"Error in list_mcp_servers: {str(e)}")
            return jsonify({
                'code': 1,
                'message': str(e)
            }), 500

    @staticmethod
    def update_mcp_server(current_user: str = 'admin') -> Tuple[Dict, int]:
        """更新MCP服务的内部方法"""
        # 实际实现逻辑保持不变
        """
        更新MCP服务

        请求体:
            - uuid: MCP服务UUID (必需)
            - 其他需要更新的字段

        返回:
            包含更新后的服务器数据或错误信息的JSON响应
        """
        if not request.is_json:
            logger.warning("Received non-JSON request for update_mcp_server")
            return jsonify({
                'code': 1,
                'message': '请求体必须为JSON格式'
            }), 400

        request_data = request.json

        # 从请求体或URL参数获取服务UUID
        server_uuid = request_data.pop('uuid', None)
        if not server_uuid:
            server_uuid = request.args.get('uuid', type=str)
            if not server_uuid:
                logger.warning("MCP server UUID is required for update")
                return jsonify({
                    'code': 1,
                    'message': 'MCP服务UUID为必填参数'
                }), 400

        # 调用访问器更新服务
        success, result = ai_mcp_server_accessor.update_mcp_server(
            server_uuid, request_data, update_by=current_user
        )

        if success:
            logger.info(f"MCP server updated successfully: {server_uuid}")
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': result
            }), 200
        else:
            logger.error(f"Failed to update MCP server {server_uuid}: {result}")
            return jsonify({
                'code': 1,
                'message': result
            }), 400

    @staticmethod
    def delete_mcp_server(current_user: str = 'admin') -> Tuple[Dict, int]:
        """删除MCP服务的内部方法"""
        # 实际实现逻辑保持不变
        """
        删除MCP服务

        请求体或查询参数:
            - uuid: MCP服务UUID (必需)

        返回:
            包含成功消息或错误信息的JSON响应
        """
        # 优先从请求体获取uuid
        if request.is_json:
            request_data = request.json
            server_uuid = request_data.get('uuid')
        else:
            server_uuid = None

        # 如果请求体中没有，从查询参数获取
        if not server_uuid:
            server_uuid = request.args.get('uuid', type=str)

        if not server_uuid:
            logger.warning("MCP server UUID is required for deletion")
            return jsonify({
                'code': 1,
                'message': 'MCP服务UUID为必填参数'
            }), 400

        # 调用访问器删除服务，传递当前用户参数
        success, result = ai_mcp_server_accessor.delete_mcp_server(server_uuid, delete_by=current_user)

        if success:
            logger.info(f"MCP server deleted successfully: {server_uuid}")
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': {'message': result}
            }), 200
        else:
            logger.error(f"Failed to delete MCP server {server_uuid}: {result}")
            return jsonify({
                'code': 1,
                'message': result
            }), 400