"""
树结构控制器模块。
提供查询MCP、Platform、Agent树结构的接口。
"""
import logging
from typing import Dict, List, Tuple
from flask import jsonify, request
from src.accessors.ai_mcp_server_accessor import AIMCPServerAccessor
from src.accessors.ai_platform_model_accessor import AIPlatform
from src.accessors.ai_agent_accessor import AIAgent
from src.accessors.ai_permissions_accessor import AIPermission
from src.utils.database import db
from sqlalchemy import text

logger = logging.getLogger(__name__)


class TreeController:
    """
    处理树结构查询请求的控制器类。
    提供获取MCP、Platform、Agent树结构数据的方法。
    """

    @staticmethod
    async def get_tree_structure(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        获取MCP、Platform、Agent的树结构数据，包含权限信息
        
        返回:
            包含树结构数据和权限信息的JSON响应
        """
        try:
            # 获取group_id参数
            group_id = request.args.get('group_id')
            if not group_id:
                return jsonify({
                    'code': 1,
                    'message': 'group_id参数不能为空'
                }), 400
            
            # 初始化访问器
            mcp_accessor = AIMCPServerAccessor()
            
            # 构建树结构数据
            tree_data = []
            
            # 查询该group_id的所有权限
            permissions_map = {}
            if group_id:
                perm_success, permissions_result = AIPermission.list_permissions(
                    take=1000,
                    filters={'group_id': group_id}
                )
                if perm_success:
                    # 创建权限映射 {entity_type_entity_id: permission_value}
                    for perm in permissions_result.get('items', []):
                        key = f"{perm.get('entity_type')}_{perm.get('entity_id')}"
                        permissions_map[key] = perm.get('permission', 0)
            
            # 1. 获取MCP服务器数据
            mcp_success, mcp_result = mcp_accessor.list_mcp_servers_basic(current_user)
            if mcp_success:
                mcp_children = []
                for mcp in mcp_result.get('items', []):
                    mcp_uuid = mcp.get('uuid', '')
                    # 获取权限，如果没有则默认为0
                    permission_key = f"0_{mcp_uuid}"
                    permission = permissions_map.get(permission_key, 0)
                    
                    mcp_children.append({
                        'title': mcp.get('name', 'Unknown MCP'),
                        'key': mcp_uuid,
                        'entity_id': mcp_uuid,
                        'entity_type': 0,
                        'permission': permission
                    })
                
                if mcp_children:
                    tree_data.append({
                        'title': 'mcp',
                        'key': 'mcp',
                        'children': mcp_children
                    })
            
            # 2. 获取Platform数据
            from src.accessors.ai_platform_model_accessor import AIPlatform
            platform_success, platforms = AIPlatform.list_platforms(create_by=current_user)
            platform_children = []
            if platform_success:
                for platform in platforms:
                    platform_uuid = platform.uuid
                    # 获取权限，如果没有则默认为0
                    permission_key = f"1_{platform_uuid}"
                    permission = permissions_map.get(permission_key, 0)
                    
                    platform_children.append({
                        'title': platform.name,
                        'key': platform_uuid,
                        'entity_id': platform_uuid,
                        'entity_type': 1,
                        'permission': permission
                    })

            if platform_children:
                tree_data.append({
                    'title': 'platform',
                    'key': 'platform',
                    'children': platform_children
                })
            
            # 3. 获取Agent数据
            logger.info("开始查询Agent数据")
            agent_success, agents = AIAgent.list_agents(create_by=current_user)
            logger.info(f"Agent查询结果: success={agent_success}, agents={agents}")
            agent_children = []
            if agent_success:
                logger.info(f"成功获取到{len(agents)}个Agent")
                for agent in agents:
                    agent_uuid = agent.get('uuid', '')
                    agent_id = agent.get('id', '')
                    agent_config = agent.get('config', {})
                    # 获取权限，如果没有则默认为0
                    permission_key = f"3_{agent_uuid}"
                    permission = permissions_map.get(permission_key, 0)
                    
                    # 从config.basic中获取agent名称，如果没有则使用默认名称
                    if isinstance(agent_config, dict) and 'basic' in agent_config and isinstance(agent_config['basic'], dict):
                        agent_name = agent_config['basic'].get('name', f'Agent {agent_id}')
                    else:
                        agent_name = f'Agent {agent_id}'
                    logger.info(f"处理Agent: id={agent_id}, uuid={agent_uuid}, name={agent_name}, config_structure={list(agent_config.keys())}")
                    agent_children.append({
                        'title': agent_name,
                        'key': agent_uuid,
                        'entity_id': agent_uuid,
                        'entity_type': 3,
                        'permission': permission
                    })
            else:
                logger.error(f"获取Agent失败: {agents}")
            
            if agent_children:
                tree_data.append({
                    'title': 'agent',
                    'key': 'agent',
                    'children': agent_children
                })
            else:
                logger.warning("没有找到任何Agent数据")
            
            # 4. 获取知识库(kb_chat)数据
            logger.info("开始查询知识库(kb_chat)数据")
            try:
                # 使用 accessor 查询知识库
                from src.accessors.ai_kb_chat_accessor import AIKBChat
                kb_success, kb_result = AIKBChat.list_kb_chats(create_by=current_user)
                
                kb_chat_children = []
                if kb_success and kb_result:
                    for kb in kb_result:
                        kb_uuid = kb.get('uuid', '')
                        kb_name = kb.get('name', '')
                        # 获取权限，如果没有则默认为0，entity_type为4表示知识库
                        permission_key = f"4_{kb_uuid}"
                        permission = permissions_map.get(permission_key, 0)
                        
                        kb_chat_children.append({
                            'title': kb_name,
                            'key': kb_uuid,
                            'entity_id': kb_uuid,
                            'entity_type': 4,
                            'permission': permission
                        })
                
                if kb_chat_children:
                    tree_data.append({
                        'title': 'kb_chat',
                        'key': 'kb_chat',
                        'children': kb_chat_children
                    })
                else:
                    logger.warning("没有找到任何知识库数据")
            except Exception as e:
                logger.error(f"获取知识库数据失败: {str(e)}")
            
            # 5. 获取Skill数据
            logger.info("开始查询Skill数据")
            try:
                from src.accessors.ai_skill_accessor import AISkill
                skill_success, skill_result = AISkill.list_skills(create_by=current_user)
                
                skill_children = []
                if skill_success and skill_result:
                    for skill in skill_result:
                        skill_uuid = skill.get('uuid', '')
                        skill_name = skill.get('name', '')
                        # 获取权限，如果没有则默认为0，entity_type为5表示Skill
                        permission_key = f"5_{skill_uuid}"
                        permission = permissions_map.get(permission_key, 0)
                        
                        skill_children.append({
                            'title': skill_name,
                            'key': skill_uuid,
                            'entity_id': skill_uuid,
                            'entity_type': 5,
                            'permission': permission
                        })
                
                if skill_children:
                    tree_data.append({
                        'title': 'skill',
                        'key': 'skill',
                        'children': skill_children
                    })
                else:
                    logger.warning("没有找到任何Skill数据")
            except Exception as e:
                logger.error(f"获取Skill数据失败: {str(e)}")
            
            # 返回树结构数据
            return jsonify({
                'code': 0,
                'message': 'Success',
                'data': tree_data
            }), 200
        except Exception as e:
            logger.error(f"Failed to get tree structure: {str(e)}")
            return jsonify({
                'code': 1,
                'message': f'获取树结构失败: {str(e)}'
            }), 500