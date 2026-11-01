"""
Agent 初始化服务模块。
专门负责 MCP、KB Chat 和 Agent 实例的初始化和缓存管理。
"""
import asyncio
import logging
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple, Any

from langchain_deepseek import ChatDeepSeek

from src.config import DeepAgentConfig
from src.core.cache.agent_cache import agent_cache_manager
from src.core.middlware.summary_middleware import AutoSummaryMiddleware
from src.core.tools.kb_chat_tools import search_docs_tool_prompt, build_kb_chat_tools
from src.core.prompts.deepagent_prompt import system_role_prompt
from src.utils.config_manager import config_manager
from src.accessors.ai_agent_accessor import AIAgent
from src.accessors.ai_skill_accessor import AISkill
from src.accessors.ai_mcp_server_accessor import AIMCPServer

logger = logging.getLogger(__name__)


class AgentInitService:
    """Agent 资源初始化服务"""

    @staticmethod
    async def initialize_all(agent_uuid: str, session_thread_id: str = None, user_uuid: str = None, user_token: str= None) -> Dict:
        """
        初始化所有 Agent 相关资源（MCP、KB、Agent 实例）

        Args:
            agent_uuid: Agent UUID
            session_thread_id: 会话线程 ID（用于 Agent 缓存）
            user_uuid: 用户 UUID
            user_token: 用户 Token

        Returns:
            初始化结果字典
        """
        # 1. 从数据库获取 Agent 数据
        success, agent_data = AIAgent.get_agent(uuid=agent_uuid)
        if not success or not agent_data:
            return {
                'agentUuid': agent_uuid,
                'success': False,
                'error': '智能体未找到或无访问权限'
            }
        
        # 2. 验证配置
        success, config_or_error = AgentInitService._validate_agent_config(agent_data)
        if not success:
            return {
                'agentUuid': agent_uuid,
                'success': False,
                'error': config_or_error.get('error', '配置验证失败')
            }
        
        config = config_or_error
        
        result = {
            'agentUuid': agent_uuid,
            'mcpInitialized': False,
            'kbInitialized': False,
            'agentInitialized': False,
            'deepagentInitialized': False,
            'success': False,
            'description': config['additional_info'].get('description', '')
        }
        
        try:
            # 2. 获取 MCP 服务器数据
            mcp_server_data = AgentInitService._fetch_mcp_server_data(agent_data)
            
            # 3. 初始化 MCP 工具（会缓存到 agent_cache_manager._mcp_pool）
            all_mcp_tools, mcp_success = await AgentInitService._init_mcp_tools(mcp_server_data)
            result['mcpInitialized'] = mcp_success
            
            # 4. 初始化 KB Chat 工具（会缓存到 agent_cache_manager._kb_pool）
            kb_chat_tools, kb_names, kb_success = await AgentInitService._init_kb_tools(
                config.get('kb_info', {})
            )
            result['kbInitialized'] = kb_success
            
            # 5. 初始化并缓存 Agent 实例（必须使用传入的 session_thread_id）
            if not session_thread_id:
                logger.error(f"缺少 session_thread_id，无法初始化 Agent: {agent_uuid}")
                result['success'] = False
                result['error'] = '缺少必要参数：sessionThreadId'
                return result
            
            agent_type = config.get('agent_type', 'agent')
            cache_key = f"{agent_uuid}:{session_thread_id}"
            
            if agent_type == 'deepagent':
                deepagent_instance = await AgentInitService._init_deepagent_instance(
                    config, session_thread_id, mcp_server_data, user_uuid=user_uuid, user_token=user_token
                )
                result['deepagentInitialized'] = deepagent_instance is not None
                # 如果初始化成功，缓存 Agent（使用元组格式：instance, timestamp）
                if deepagent_instance:
                    agent_cache_manager._agent_pool[cache_key] = (deepagent_instance, time.time())
                    logger.info(f"DeepAgent 已缓存: {cache_key}")
            else:
                agent_instance = await AgentInitService._init_agent_instance(config, session_thread_id, mcp_server_data)
                result['agentInitialized'] = agent_instance is not None
                # 如果初始化成功，缓存 Agent（使用元组格式：instance, timestamp）
                if agent_instance:
                    agent_cache_manager._agent_pool[cache_key] = (agent_instance, time.time())
                    logger.info(f"Agent 已缓存: {cache_key}")
            
            # 6. 判断总体是否成功
            result['success'] = result['agentInitialized'] or result['deepagentInitialized']
            return result
            
        except Exception as e:
            logger.error(f"初始化 Agent 资源失败: {e}", exc_info=True)
            result['success'] = False
            result['error'] = str(e)
            return result

    @staticmethod
    async def _init_mcp_tools(mcp_servers_data: Dict = None) -> Tuple[List, bool]:
        """
        初始化 MCP 工具
        
        Args:
            mcp_server_data: MCP 服务器数据字典（由 Controller 层传入），格式：{server_id: server_record}
        Returns:
            (工具列表, 是否成功)
        """
        all_mcp_tools = []
        try:
            from src.utils.mcp_client_utils import get_mcp_tools
            
            for server_uid, server_record in mcp_servers_data.items():
                sid_str = str(server_uid)
                # 检查缓存（现在缓存是元组格式：(tools, timestamp)）
                if sid_str in agent_cache_manager._mcp_pool:
                    tools, timestamp = agent_cache_manager._mcp_pool[sid_str]
                    logger.info(f"MCP 服务 {sid_str} 命中缓存，共{len(tools)} 个工具")
                else:
                    # 连接 MCP 服务
                    tools = await get_mcp_tools(
                        server_name=server_record.get('name', sid_str),
                        url=server_record.get('url', ''),
                        transport=server_record.get('transport', 'sse'),
                        timeout=10.0,
                        headers=server_record.get('headers', None),
                    )
                    
                    # 只在连接成功时才缓存（使用元组格式）
                    if tools and len(tools) > 0:
                        agent_cache_manager._mcp_pool[sid_str] = (tools, time.time())
                        logger.info(f"MCP 服务 {sid_str} 连接成功，已缓存 {len(tools)} 个工具")
                    else:
                        logger.warning(f"MCP 服务 {sid_str} 连接失败或未获取到工具，不缓存")
                
                all_mcp_tools.extend(tools)
            
            success = len(all_mcp_tools) > 0
            logger.info(f"初始化 MCP 工具: {len(all_mcp_tools)} 个工具")
            return all_mcp_tools, success
            
        except Exception as e:
            logger.warning(f"初始化 MCP 工具失败: {e}")
            return [], False

    @staticmethod
    async def _init_kb_tools(kb_info: Dict) -> Tuple[List, List[str], bool]:
        """
        初始化 KB Chat 工具
        
        Args:
            kb_info: 知识库配置信息
            
        Returns:
            (工具列表, 知识库名称列表, 是否成功)
        """
        if not kb_info or not kb_info.get('enabled'):
            return [], [], True  # 没有 KB 也算成功
        
        try:
            kb_names = kb_info.get('selectedKnowledge', [])
            
            if not kb_names:
                return [], [], True
            
            # 按 kb_name 组合缓存
            kb_key = "_".join(sorted(kb_names)) if kb_names else "empty"
            
            # 检查缓存（现在缓存是元组格式：(tools, timestamp)）
            if kb_key in agent_cache_manager._kb_pool:
                kb_chat_tools, timestamp = agent_cache_manager._kb_pool[kb_key]
            else:
                kb_chat_tools = await build_kb_chat_tools(kb_names=kb_names)
                agent_cache_manager._kb_pool[kb_key] = (kb_chat_tools, time.time())
            
            success = len(kb_chat_tools) > 0
            logger.info(f"初始化 KB Chat 工具: {len(kb_chat_tools)} 个工具")
            return kb_chat_tools, kb_names, success
            
        except Exception as e:
            logger.warning(f"初始化 KB Chat 工具失败: {e}")
            return [], [], False

    @staticmethod
    async def _init_deepagent_instance(config: Dict, session_thread_id: str,
                                        mcp_server_data: Dict = None,
                                        user_uuid: str = None,
                                        user_token: str = None) -> Any:
        """
        初始化 DeepAgent 实例

        Args:
            config: Agent 配置
            session_thread_id: 会话线程 ID
            mcp_server_data: MCP 服务器数据字典
            user_uuid: 用户 UUID（用于 per-user 记忆隔离）
            user_token: 用户 token

        Returns:
            DeepAgent 实例，失败返回 None
        """
        try:
            from deepagents import create_deep_agent
            from src.controllers.sandbox_controller import sandbox_controller
            from src.core.prompts.deepagent_prompt import build_deepagent_system_prompt
            from langchain_openai import ChatOpenAI
            
            # 获取 MCP 和 KB 工具
            all_mcp_tools, mcp_success = await AgentInitService._init_mcp_tools(mcp_server_data)
            kb_chat_tools, kb_names, kb_success = await AgentInitService._init_kb_tools(
                config['kb_info']
            )
            
            # 创建 LLM 实例
            llm = AgentInitService._create_llm_from_config(
                config['model_config'],
                config['api_url'],
                config['api_key'],
                config['model_name'],
                agent_type='deepagent'
            )

            # 计算记忆启用条件：仅 deepagent 启用 per-user 记忆
            agent_uuid = config.get('agent_uuid')
            visibility = config.get('visibility', 'private')
            agent_type_in_config = config.get('agent_type', 'agent')
            memory_enabled = (
                config_manager.get_memory_enabled(agent_uuid)
                and bool(agent_uuid)
                and bool(user_uuid)
                and agent_type_in_config == 'deepagent'
            )
            logger.info(
                f"[Memory] enabled={memory_enabled}, agent_uuid={agent_uuid}, "
                f"user_uuid={user_uuid}, visibility={visibility}, agent_type={agent_type_in_config}"
            )

            def _prepare_sandbox_backend_sync():
                """同步阻塞部分：skill 数据查询 + 沙盒容器创建。

                Docker 容器的创建/启动可能耗时数秒甚至更久，
                必须放到线程池中执行（asyncio.to_thread），
                否则会阻塞整个事件循环，导致后端其它接口全部卡住。
                """
                # 加载 skill 的 additional_info，构建 skill.md 占位符替换映射
                skill_replacements = {}
                skill_uuids = config.get('skills', []) or []
                if skill_uuids:
                    for skill_uuid in skill_uuids:
                        s_ok, s_data = AISkill.get_skill(uuid=skill_uuid)
                        if s_ok and s_data:
                            info = s_data.get('additional_info') or {}
                            if isinstance(info, str):
                                try:
                                    info = json.loads(info)
                                except (json.JSONDecodeError, TypeError):
                                    info = {}
                            folder = s_data.get('folder_name')
                            if info and folder:
                                skill_replacements[folder] = info
                # 获取沙盒 backend（带 agent_uuid + user_uuid，用于 per-user 记忆挂载）
                # 注意：asyncio.to_thread 会传播 contextvars，
                # Flask 的 app_context 在工作线程中依然有效
                return sandbox_controller.get_sandbox_backend(
                    session_thread_id,
                    agent_uuid=agent_uuid,
                    user_uuid=user_uuid,
                    skill_replacements=skill_replacements,
                    user_token=user_token,
                )

            backend = await asyncio.to_thread(_prepare_sandbox_backend_sync)

            if not backend:
                logger.warning(f"无法获取沙盒 backend，跳过 DeepAgent 初始化")
                return False

            # 构建系统提示词（不追加任何记忆相关文本，记忆指令由 MemoryMiddleware 自动注入）
            server_host = config_manager.get_public_host()
            server_port = config_manager.get_public_port()
            final_system_prompt = build_deepagent_system_prompt(
                server_host=server_host,
                server_port=server_port,
                session_thread_id=session_thread_id
            )

            if config['system_prompt']:
                final_system_prompt += "\n\n" + config['system_prompt']
            if all_mcp_tools or kb_chat_tools:
                final_system_prompt += "\n\n" + search_docs_tool_prompt

            final_system_prompt += "\n\n" + system_role_prompt

            # 获取 checkpointer
            from src.core.memory.checkpointer import get_checkpointer
            checkpointer = await get_checkpointer(DeepAgentConfig.CheckpointConfig.PATH_LOCAL)

            # 解析技能路径（用于日志 & 判断是否有配置 skill）
            skills_paths = AgentInitService._resolve_skill_folder_names(config.get('skills', []))
            logger.info(f"注入技能路径: {skills_paths}")

            # SkillsMiddleware 的 sources 需要是"容器目录"——列出其下的子目录作为 skill。
            # 传入单个父目录，而不是各个 skill 子目录路径，否则 middleware
            # 对每个 source 做 ls 时找不到子目录，导致 Available Skills 为空。
            sandbox_skills_path = config_manager.get_skills_sandbox_path()
            skills_source = [f"{sandbox_skills_path.rstrip('/')}/"] if skills_paths else None

            # 计算 memory_paths：仅在 memory_enabled 时传入
            memory_paths = None
            if memory_enabled:
                memory_sandbox_path = config_manager.get_memory_sandbox_path()
                memory_files = config_manager.get_memory_files()
                memory_paths = [f"{memory_sandbox_path.rstrip('/')}/{f}" for f in memory_files]
                logger.info(f"[Memory] memory_paths={memory_paths}")

            # 创建 DeepAgent 实例
            return create_deep_agent(
                model=llm,
                skills=skills_source,
                tools=all_mcp_tools + kb_chat_tools,
                backend=backend,
                system_prompt=final_system_prompt,
                checkpointer=checkpointer,
                memory=memory_paths,
            )

        except Exception as e:
            logger.warning(f"初始化 DeepAgent 实例失败: {e}")
            return None

    @staticmethod
    async def _init_agent_instance(config: Dict, session_thread_id: str, mcp_server_data: Dict = None):
        """
        初始化普通 Agent 实例
        
        Args:
            config: Agent 配置
            session_thread_id: 会话线程 ID
            mcp_server_data: MCP 服务器数据字典
            
        Returns:
            Agent 实例，失败返回 None
        """
        try:
            from src.langgraph_agent.travel_planner.agents.itinerary_planner_agent import create_agent
            
            # 获取 MCP 和 KB 工具
            all_mcp_tools, mcp_success = await AgentInitService._init_mcp_tools(mcp_server_data)
            kb_chat_tools, kb_names, kb_success = await AgentInitService._init_kb_tools(config['kb_info'])
            
            # 创建 LLM 实例
            llm = AgentInitService._create_llm_from_config(
                config['model_config'],
                config['api_url'],
                config['api_key'],
                config['model_name'],
                agent_type='agent'
            )
            
            # 构建系统提示词
            system_prompt = config['system_prompt']
            if kb_names:
                system_prompt += "\n\n" + search_docs_tool_prompt

            system_prompt += "\n\n" + system_role_prompt
            
            # 获取 checkpointer
            from src.core.memory.checkpointer import get_checkpointer
            checkpointer = await get_checkpointer(DeepAgentConfig.CheckpointConfig.PATH_LOCAL)

            # 创建 Agent 实例
            return create_agent(
                model=llm,
                tools=all_mcp_tools + kb_chat_tools,
                system_prompt=system_prompt,
                middleware=[AutoSummaryMiddleware(llm, max_turns=20, keep_recent_turns=5)],
                checkpointer=checkpointer
            )
                
        except Exception as e:
            logger.warning(f"初始化 Agent 实例失败: {e}")
            return None

    @staticmethod
    async def get_or_create_agent(agent_uuid: str, config: Dict, session_thread_id: str,
                                   mcp_server_data: Dict = None, user_uuid: str = None, user_token: str =None) -> Any:
        """
        获取或创建 Agent 实例（按 session_thread_id 缓存）

        Args:
            agent_uuid: Agent UUID
            config: Agent 配置
            session_thread_id: 会话线程 ID
            mcp_server_data: MCP 服务器数据字典
            user_uuid: 用户 UUID（用于 per-user 记忆隔离）
            user_token: 用户 token

        Returns:
            Agent 实例，失败返回 None
        """
        agent_type = config.get('agent_type', '')

        # 使用 session_thread_id 作为缓存 key
        cache_key = f"{agent_uuid}:{session_thread_id}"

        # 定义工厂函数
        async def create_agent_instance():
            logger.info(f"{agent_type} Agent 未命中缓存，创建新实例: {cache_key}")
            if agent_type == 'deepagent':
                return await AgentInitService._init_deepagent_instance(
                    config, session_thread_id, mcp_server_data, user_uuid=user_uuid, user_token=user_token
                )
            else:
                return await AgentInitService._init_agent_instance(config, session_thread_id, mcp_server_data)

        # 从缓存获取或创建
        try:
            agent = await agent_cache_manager.get_or_create_async(
                pool_name='agent',
                entity_id=cache_key,
                factory_func=create_agent_instance
            )
            logger.info(f"{agent_type} Agent 已缓存: {cache_key}")
            return agent
        except Exception as e:
            logger.error(f"Agent 缓存获取失败: {e}", exc_info=True)
            # 降级：直接创建
            if agent_type == 'deepagent':
                return await AgentInitService._init_deepagent_instance(
                    config, session_thread_id, mcp_server_data, user_uuid=user_uuid, user_token=user_token
                )
            else:
                return await AgentInitService._init_agent_instance(config, session_thread_id, mcp_server_data)

    @staticmethod
    def _validate_agent_config(agent_data: Dict) -> Tuple[bool, Dict]:
        """
        验证 Agent 配置并构建配置字典
        
        Args:
            agent_data: Agent 数据字典（从数据库查询得到）
            
        Returns:
            (是否成功, 配置字典或错误信息)
        """
        # 获取 agent 配置
        agent_config = agent_data.get('config', {})
        
        # 验证模型配置
        model_config = agent_config.get('model', {})
        model_name = model_config.get('name')
        api_key = model_config.get('apiKey')
        api_url = model_config.get('apiUrl', '')
        
        if not model_name or not api_key or not api_url:
            return False, {'error': '智能体模型配置不完整'}
        
        # 处理 API URL，移除 /chat/completions 后缀
        if api_url.endswith('/chat/completions'):
            api_url = api_url[:-17]

        if not api_url.endswith('/v1'):
            api_url = api_url.rstrip('/') + '/v1'

        # 构建返回的配置字典
        config_dict = {
            'agent_uuid': agent_data.get('uuid'),
            'visibility': agent_data.get('visibility', 'private'),
            'agent_config': agent_config,
            'model_config': model_config,
            'model_name': model_name,
            'api_key': api_key,
            'api_url': api_url,
            'system_prompt': AgentInitService._resolve_config_vars(agent_config.get('prompt', {}).get('systemPrompt', '')),
            'mcp_servers': agent_config.get('mcp', {}).get('enabledServerIdentifiers', []),
            'skills': agent_data.get('skills', []),
            'kb_info': agent_config.get('knowledge') or {},
            'agent_type': agent_data.get('agent_type', 'assistant'),
            "top_p": model_config.get('top_p', 1),
            "memory": agent_config.get('memory') or {},
            "additional_info": agent_data.get('additional_info', {})
        }
        model_context_size = AgentInitService._get_model_context_size(model_name)
        if model_context_size:
            config_dict["model_config"]["model_context_size"] = model_context_size
        return True, config_dict

    @staticmethod
    def _get_model_context_size(model_name: str):
        from src.accessors.ai_platform_model_accessor import ai_platform_model_accessor
        ok, model_result = ai_platform_model_accessor.get_model_by_model_name(model_name)
        return model_result.get('context_size') if ok and model_result else None

    @staticmethod
    def _create_llm_from_config(model_config: Dict, api_url: str, api_key: str, 
                                 model_name: str, agent_type: str = 'agent'):
        """根据配置创建 LLM 实例
        
        Args:
            model_config: 模型配置字典
            api_url: API 基础 URL
            api_key: API 密钥
            model_name: 模型名称
            agent_type: Agent 类型 ('agent' 或 'deepagent')
            
        Returns:
            ChatOpenAI 实例
        """
        from langchain_openai import ChatOpenAI
        
        # 打印详细的 LLM 配置信息用于调试
        masked_key = api_key[:8] + '****' if api_key else 'None'
        logger.info(f"[LLM Config] model={model_name}, api_base={api_url}, api_key={masked_key}, agent_type={agent_type}")
        llm_params = {
            'model': model_name,
            'api_key': api_key,
            'api_base': api_url,
            'streaming': True,
            # 直接传递 extra_body 以支持 reasoning/thinking 输出
            'extra_body': {
                'enable_thinking': True,  # 开启思考逻辑
                'include_thought': True,  # 确保返回体包含 thought 字段
                'stop': None
            },
            'temperature': model_config.get('temperature', 0.6),
            'top_p': model_config.get('top_p', 0.95),
        }

        logger.info(f"[LLM Config] 完整参数: {llm_params}")
        llm = ChatDeepSeek(**llm_params)
        if model_config.get("model_context_size"):
            ratio = DeepAgentConfig.LLMConfig.MODEL_CONTEXT_SIZE_RATIO
            # DB 的 context_size 已是原始 token 数（schema 注释/前端存储均如此），勿再乘 1024
            llm.profile.update({"max_input_tokens": int(model_config.get("model_context_size") * ratio)})
        return llm
        # # 基础参数（所有 Agent 类型共用）
        # llm_params = {
        #     'model': model_name,
        #     'api_key': api_key,
        #     'base_url': api_url,
        #     'streaming': True,
        # }
        #
        # # 根据 Agent 类型添加特定参数
        # if agent_type == 'deepagent':
        #     # DeepAgent 使用固定配置，启用 reasoning 支持
        #     llm_params.update({
        #         'temperature': 0,
        #         'timeout': 300,
        #         'max_retries': 2,
        #         'max_tokens': model_config.get('maxTokens', 4000),
        #     })
        # else:
        #     # 普通 Agent 使用可配置参数
        #     llm_params.update({
        #         'temperature': model_config.get('temperature', 0.7),
        #         'max_tokens': model_config.get('maxTokens', 4000),
        #         'timeout': model_config.get('timeout', 30.0),
        #     })
        #
        # logger.info(f"[LLM Config] 完整参数: {llm_params}")
        # return ChatOpenAI(**llm_params)

    @staticmethod
    def _fetch_mcp_server_data(agent_data: Dict) -> Dict:
        """
        获取 Agent 关联的 MCP 服务器数据（批量查询，避免 N+1 问题）
        
        Args:
            agent_data: Agent 数据字典
            
        Returns:
            MCP 服务器数据字典，格式：{server_uuid: server_record}
        """
        mcp_server_ids = agent_data.get('config', {}).get('mcp', {}).get('enabledServerIdentifiers', [])
        mcp_server_data = {}
        
        if not mcp_server_ids:
            return mcp_server_data
        
        # 批量查询 MCP 服务器（使用 uuid 字段）
        for server in AIMCPServer.query.filter(AIMCPServer.id.in_(mcp_server_ids)).all():
            mcp_server_data[server.uuid] = server.to_dict()
        
        return mcp_server_data

    @staticmethod
    async def prepare_agent_for_chat(agent_uuid: str, session_thread_id: str = None,
                                       user_uuid: str = None, user_token: str = None) -> Any:
        """
        为对话准备 Agent（初始化所有资源并返回）

        Args:
            agent_uuid: Agent UUID
            session_thread_id: 会话线程 ID（用于对话记忆和沙盒管理）
            user_uuid: 用户 UUID（用于 per-user 记忆隔离）
            user_token: 用户 token

        Returns:
            Agent 实例，失败返回 None
        """
        try:
            # 1. 从数据库获取 Agent 数据
            success, agent_data = AIAgent.get_agent(uuid=agent_uuid)
            if not success or not agent_data:
                logger.error(f"Agent 未找到或无访问权限: {agent_uuid}")
                return None

            # 2. 验证配置
            config_success, config_or_error = AgentInitService._validate_agent_config(agent_data)
            if not config_success:
                logger.error(f"Agent 配置验证失败: {config_or_error.get('error')}")
                return None

            config = config_or_error

            # 3. 获取 MCP 服务器数据
            mcp_server_data = AgentInitService._fetch_mcp_server_data(agent_data)

            # 必须传入 session_thread_id
            if not session_thread_id:
                logger.error(f"缺少 session_thread_id，无法准备 Agent: {agent_uuid}")
                return None

            # 4. 获取或创建 Agent 实例（传入 session_thread_id、mcp_server_data、user_uuid）
            agent = await AgentInitService.get_or_create_agent(
                agent_uuid, config, session_thread_id, mcp_server_data, user_uuid=user_uuid, user_token=user_token,
            )
            if not agent:
                logger.error(f"Agent 实例创建失败: {agent_uuid}")
                return None

            # 5. 返回 Agent 实例
            return agent

        except Exception as e:
            logger.error(f"准备 Agent 失败: {e}", exc_info=True)
            return None

    @staticmethod
    def _resolve_skill_folder_names(skill_uuids: List) -> List[str]:
        """将 skill uuid 列表转换为沙盒中的技能路径列表
        
        如果 skill_uuids 为空，返回空列表；
        否则根据每个 uuid 查询 folder_name，拼接为 sandbox_skills_path/folder_name。
        """
        import posixpath

        sandbox_skills_path = config_manager.get_skills_sandbox_path()

        if not skill_uuids:
            return []

        folder_names = []
        # 批量查询技能记录，避免 N+1 查询问题
        for skill_record in AISkill.query.filter(AISkill.uuid.in_(skill_uuids)).all():
            if skill_record.folder_name:
                folder_names.append(skill_record.folder_name)

        if not folder_names:
            return []

        return [posixpath.join(sandbox_skills_path, f"{name}/") for name in folder_names]

    @staticmethod
    def _resolve_config_vars(system_prompt: str) -> str:
        import re

        now = datetime.now()
        var_map = {
            'date': now.strftime('%Y-%m-%d'),
            'time': now.strftime('%H:%M:%S'),
            'datetime': now.strftime('%Y-%m-%d %H:%M:%S'),
            'timestamp': str(int(now.timestamp())),
            'year': str(now.year),
            'month': f'{now.month:02d}',
            'day': f'{now.day:02d}',
        }

        def replace(m):
            return var_map.get(m.group(1), m.group(0))

        return re.sub(r'\$\{(\w+)\}', replace, system_prompt)
