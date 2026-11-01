"""
AI聊天控制器模块。
处理AI大模型对话和智能体对话的API端点。
"""
from flask import request, jsonify, Response
from typing import Dict, List, Tuple

from langchain_openai import ChatOpenAI

from src.accessors.ai_agent_accessor import AIAgent
from src.accessors.ai_user_accessor import AIUser
from src.accessors.ai_user_group_accessor import ai_user_group_accessor
from src.accessors.ai_user_group_relation_accessor import ai_user_group_relation_accessor
from src.utils.langfuse_utils import get_langfuse_handler, langfuse_trace_context
from langchain_deepseek import ChatDeepSeek
import logging
import json
import re
import time
import threading
import urllib.parse
from src.services.agent_init_service import AgentInitService
from src.utils.chat_record_collector import ChatRecordCollector, extract_last_user_question, extract_last_user_images, extract_system_prompt
from src.utils.config_manager import config_manager
from src.utils.stream_hub import stream_hub, run_producer_sync
from src.utils.interrupt_utils import check_interrupt, clear_interrupt_flag

# 获取logger
logger = logging.getLogger(__name__)

# 匹配 markdown 链接: [filename](url)
_MD_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')


def _to_container_download_url(filename: str, session_thread_id: str) -> str:
    """将文件名转换为容器内下载链接（output 目录）。"""
    container_base = config_manager.get_file_container_path()
    file_path = f"{container_base}/{session_thread_id}/output/{filename}"
    return (
        f"http://<server_host>:<server_port>"
        f"/aiFileProcessor/download"
        f"?file_path={urllib.parse.quote(file_path)}"
    )


def _transform_download_links(line: str, session_thread_id: str) -> str:
    """将 injector 产出的下载链接行中的 URL 替换为容器内下载链接。"""
    try:
        if not line.startswith("0:"):
            return line
        text = json.loads(line[2:])
        if not isinstance(text, str):
            return line

        def _replace(match):
            fn = match.group(1)
            new_url = _to_container_download_url(fn, session_thread_id)
            return f"[{fn}]({new_url})"

        transformed = _MD_LINK_RE.sub(_replace, text)
        if transformed == text:
            return line
        return f"0:{json.dumps(transformed, ensure_ascii=False)}\n"
    except Exception:
        return line

class AIChatController:

    @staticmethod
    async def chat_with_model(current_user: str = None) -> Tuple[Dict, int]:
        """大模型对话接口（纯转发）
        接收前端传来的完整消息，原样转发给大模型API。
        """
        data = request.json

        if not data:
            return jsonify({'error': '请求数据不能为空'}), 400

        model = data.get('model')
        messages = data.get('messages')
        api_key = data.get('apiKey', 'None')
        base_url = data.get('baseUrl')
        user_uuid = data.get('user_id')
        session_thread_id = data.get('session_thread_id')
        turn_id = data.get('turn_id')
        chat_type = data.get('chat_type') or 'model'

        if not model or not messages or not base_url:
            return jsonify({'error': '缺少必要参数'}), 400

        # 会话ID提前计算：StreamHub 以 session_id 为流 key。
        # 注意：前端未传 session_thread_id 时 key 为服务端生成的 chatcmpl-*，
        # 前端无从得知 → 无法 resume，建议前端总是传 session_thread_id
        session_id = session_thread_id if session_thread_id else f'chatcmpl-{int(time.time())}'

        # StreamHub 占坑：已有活跃流（starting/running）时不重复调用 LLM，直接 attach 订阅
        stream, is_new = stream_hub.claim(session_id, turn_id or "")
        if not is_new:
            logger.info(f"[hub] session={session_id} 已有活跃流(turn={stream.turn_id})，"
                        f"本次请求(turn={turn_id})直接 attach")
            return Response(
                stream_hub.subscribe_sync(session_id),
                mimetype='text/event-stream',
                headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

        clear_interrupt_flag(session_id)
        try:
            # 处理base_url，确保格式正确
            processed_base_url = base_url.strip()
            if processed_base_url.endswith('/chat'):
                processed_base_url = processed_base_url[:-5]
            elif processed_base_url.endswith('/chat/completions'):
                processed_base_url = processed_base_url[:-17]
            if not processed_base_url.endswith('/v1'):
                processed_base_url = processed_base_url.rstrip('/') + '/v1'

            llm_params = {
                'model': model,
                'api_key': api_key,
                'api_base': processed_base_url,
                'streaming': True,
                'extra_body': {
                    'enable_thinking': True,
                    'include_thought': True,
                    'stop': None
                },
                'temperature': 0.7,
            }
            llm = ChatDeepSeek(**llm_params)

            user_success, user_result = AIUser.get_user(uuid=user_uuid)

            real_name = user_result.get('realname') if user_success else ''
            user_group_success, user_group_ids = ai_user_group_relation_accessor.get_user_groups_by_user_id(user_id=user_uuid)
            user_groups = []
            for user_group_id in user_group_ids:
                success, group_info = ai_user_group_accessor.get_user_group(group_uuid=user_group_id)
                if success:
                    user_groups.append(str(group_info.get('name', '')))
            user_groups = ', '.join(user_groups)
            user_info = {'user_name': current_user, 'real_name': real_name, 'user_groups': user_groups}

            # ---------- Langfuse 追踪 ----------
            langfuse_handler = get_langfuse_handler()
            stream_config = {}
            if langfuse_handler is not None:
                stream_config = {"callbacks": [langfuse_handler]}

            # session_id 已在函数体前部计算（StreamHub claim 需要），此处直接复用

            # ---------- 对话记录采集器（model 类型） ----------
            record_collector = ChatRecordCollector(
                chat_type=chat_type,
                user_id=user_uuid,
                user_name=current_user or '',
                session_thread_id=session_id,
                agent_id='',
                turn_id=turn_id,
                llm_config={'model': model, 'api_key': api_key, 'base_url': processed_base_url},
                user_question=extract_last_user_question(messages),
                user_images=extract_last_user_images(messages),
            )
            record_collector.set_system_prompt(extract_system_prompt(messages))

            threading.Thread(target=record_collector.summarize_first_question, daemon=True).start()

            # ---------- 流式输出生成器 ----------
            def generate():
                with langfuse_trace_context(
                    name=f"chat-with-model-{session_id}" if chat_type == 'model' else f"chat-with-kb-{session_id}",
                    user_id=user_uuid or current_user or "",
                    session_id=session_id,
                    metadata=user_info
                ):
                    try:
                        for chunk in llm.stream(messages, config=stream_config):
                            if check_interrupt(session_id):
                                break
                            reasoning = getattr(chunk, "reasoning_content", None)
                            if not reasoning:
                                reasoning = chunk.additional_kwargs.get("reasoning_content")
                            # 累积对话记录（回复内容 + 思考内容）
                            record_collector.feed_chunk(
                                content=chunk.content or '',
                                reasoning=reasoning or '',
                            )
                            created_time = int(time.time())
                            response_chunk = {
                                'id': f'{session_id}-{created_time}',
                                'object': 'chat.completion.chunk',
                                'created': created_time,
                                'model': model,
                                'choices': [
                                    {
                                        'index': 0,
                                        'delta': {
                                            'role': 'assistant' if chunk.content else None,
                                            'content': chunk.content or '',
                                            'reasoning': reasoning or '',
                                        },
                                        'finish_reason': None
                                    }
                                ]
                            }
                            yield f'data: {json.dumps(response_chunk)}\n\n'
                    except Exception as e:
                        logger.error(f"流式输出异常: {e}")
                    finally:
                        # 本轮对话结束，实时落库对话记录
                        record_collector.finalize()
                        clear_interrupt_flag(session_id)
                        end_chunk = {
                            'id': session_id,
                            'object': 'chat.completion.chunk',
                            'created': int(time.time()),
                            'model': model,
                            'choices': [{
                                'index': 0,
                                'delta': {},
                                'finish_reason': 'stop'
                            }]
                        }
                        yield f'data: {json.dumps(end_chunk)}\n\n'
                        yield 'data: [DONE]\n\n'

            # 后台线程生产 + 本请求作为第一个订阅者：
            # 客户端断开 SSE 不影响 llm.stream 消费与 record_collector.finalize 落库。
            # generate() 只引用闭包变量（不触碰 Flask request），线程中执行安全；
            # ChatRecordCollector._persist 自带 app_context 检查。
            producer = threading.Thread(
                target=run_producer_sync,
                args=(stream_hub, session_id, generate()),
                name=f"model-turn-{session_id}",
                daemon=True)
            producer.start()
            stream_hub.attach_thread(session_id, producer)
            return Response(
                stream_hub.subscribe_sync(session_id),
                mimetype='text/event-stream',
                headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})
        except Exception as e:
            stream_hub.abort(session_id)  # 准备失败必须清坑，避免后续请求 attach 到死流
            logger.error("大模型对话失败: %s" % str(e))
            return jsonify({'error': '大模型对话失败: %s' % str(e)}), 500

    @staticmethod
    async def chat_with_deepagent(agent_uuid: str, messages: List[Dict], session_thread_id: str = None,
                                  user_uuid: str = None, token: str = None, turn_id: str = None):
        """Deepagent 对话接口（FastAPI 异步版本）
        Args:
            agent_uuid: 智能体 UUID
            messages: 对话消息列表
            session_thread_id: 会话线程 ID
            user_uuid: 用户 UUID
            token: 用户 token（可选，非空时注入到消息中告知大模型）
            turn_id: 本轮对话 ID（用于对话记录落库）

        Returns:
            异步生成器
        """
        try:
            
            # 调用 Service 层准备 DeepAgent（Service 层负责查询数据库）
            deepagent = await AgentInitService.prepare_agent_for_chat(
                agent_uuid, session_thread_id, user_uuid=user_uuid, user_token=token,
            )
            if not deepagent:
                return AIChatController._create_error_response('DeepAgent 准备失败')

            success, agent_data = AIAgent.get_agent(uuid=agent_uuid)
            config_success, config = AgentInitService._validate_agent_config(agent_data)
            llm_config = {
                'model': config['model_name'],
                'api_key': config['api_key'],
                'base_url': config['api_url'],
            }


            # # 如果 token 非空，在最后一条 user 消息中注入 token 信息
            # if token:
            #     for i in range(len(messages)):
            #         if messages[i].get('role') == 'user':
            #             messages[i]['content'] = f"[系统token（仅供内部API使用，调用MCP工具前必须先通过MCP的认证工具获取MCP专用token，禁止直接使用此token调用MCP工具）: {token}]\n\n" + \
            #                              messages[i]['content']
            #
            #             break

            # 转换消息格式（使用通用方法）
            input_messages = AIChatController._convert_messages_to_langchain(messages)

            logger.info(f"Starting deepagent with {len(input_messages)} messages, thread_id={session_thread_id}")

            # 使用通用方法创建异步流生成器
            thread_id = session_thread_id or f"session-{time.time()}"
            stream_config = {"recursion_limit": 1000}
            
            # 定义完成回调：将沙盒设置为空闲状态并清除中断标志
            def on_stream_complete():
                from src.controllers.sandbox_controller import sandbox_controller
                from src.utils.interrupt_utils import clear_interrupt_flag
                
                sandbox_controller.set_sandbox_idle(session_thread_id)
                clear_interrupt_flag(session_thread_id)
                logger.debug(f"DeepAgent 流式输出完成，沙盒 {session_thread_id} 已设置为空闲")

            # 获取文件下载服务地址
            from src.utils.config_manager import config_manager
            server_host = config_manager.get_public_host()
            server_port = config_manager.get_public_port()

            user_success, user_result = AIUser.get_user(uuid=user_uuid)
            user_name = user_result.get('username') if user_success else ''

            real_name = user_result.get('realname') if user_success else ''
            user_group_success, user_group_ids = ai_user_group_relation_accessor.get_user_groups_by_user_id(user_id=user_uuid)
            user_groups = []
            for user_group_id in user_group_ids:
                success, group_info = ai_user_group_accessor.get_user_group(group_uuid=user_group_id)
                if success:
                    user_groups.append(str(group_info.get('name', '')))
            user_groups = ', '.join(user_groups)
            user_info = {'user_name': user_name, 'real_name': real_name, 'user_groups': user_groups}
            # 调用生成器函数，返回生成器对象（不是函数本身）
            stream_generator = AIChatController._create_async_stream_generator(
                agent=deepagent,
                input_data={"messages": input_messages},
                thread_id=thread_id,
                stream_config=stream_config,
                wrap_sse=True,
                on_completion_callback=on_stream_complete,
                trace_name=f"DeepAgent-{agent_uuid}",
                server_host=server_host,
                server_port=server_port,
                user_id=user_uuid if user_uuid else "",
                session_id=thread_id,
                user_name=user_name,
                chat_type='deepagent',
                agent_id=agent_uuid,
                turn_id=turn_id,
                user_question=extract_last_user_question(messages),
                user_images=extract_last_user_images(messages),
                llm_config=llm_config,
                user_info=user_info
            )
            return stream_generator()
        except Exception as e:
            logger.error(f"Deepagent 执行失败: {e}", exc_info=True)
            return AIChatController._create_error_response(f'智能体执行失败: {str(e)}')

    @staticmethod
    async def chat_with_agent_async(agent_uuid: str, messages: List[Dict], session_thread_id: str = None, user_uuid: str = None, turn_id: str = None):
        """普通 Agent 对话接口（FastAPI 异步版本）
        Args:
            agent_uuid: 智能体 UUID
            messages: 对话消息列表
            session_thread_id: 会话线程 ID
            user_uuid: 用户 ID
            turn_id: 对话轮次 ID

        Returns:
            异步生成器
        """
        try:
            
            # 调用 Service 层准备 Agent（Service 层负责查询数据库）
            logger.info(f"[chat_with_agent_async] 准备 Agent, session_thread_id={session_thread_id}")
            agent = await AgentInitService.prepare_agent_for_chat(
                agent_uuid, session_thread_id
            )
            if not agent:
                return AIChatController._create_error_response('Agent 准备失败')

            success, agent_data = AIAgent.get_agent(uuid=agent_uuid)
            config_success, config = AgentInitService._validate_agent_config(agent_data)
            llm_config = {
                'model': config['model_name'],
                'api_key': config['api_key'],
                'base_url': config['api_url'],
            }

            agent_messages = AIChatController._convert_messages_to_dict(messages)

            logger.info("Agent %s 开始执行，消息数: %d", agent_uuid, len(agent_messages))

            thread_id = session_thread_id or f"session-{time.time()}"
            logger.info(f"[chat_with_agent_async] 使用 thread_id={thread_id} (原始 session_thread_id={session_thread_id})")
            
            # 定义完成回调：清除中断标志
            def on_stream_complete():
                from src.utils.interrupt_utils import clear_interrupt_flag
                
                clear_interrupt_flag(session_thread_id)
                logger.debug(f"Agent 流式输出完成，清除中断标志: {session_thread_id}")


            user_success, user_result = AIUser.get_user(uuid=user_uuid)
            user_name = user_result.get('username') if user_success else ''
            real_name = user_result.get('realname') if user_success else ''
            user_group_success, user_group_ids = ai_user_group_relation_accessor.get_user_groups_by_user_id(user_id=user_uuid)
            user_groups = []
            for user_group_id in user_group_ids:
                success, group_info = ai_user_group_accessor.get_user_group(group_uuid=user_group_id)
                if success:
                    user_groups.append(str(group_info.get('name', '')))
            user_groups = ', '.join(user_groups)
            user_info = {'user_name': user_name, 'real_name': real_name, 'user_groups': user_groups}

            # 调用生成器函数，返回生成器对象（不是函数本身）
            stream_generator = AIChatController._create_async_stream_generator(
                agent=agent,
                input_data={"messages": agent_messages},
                thread_id=thread_id,
                stream_config={},
                wrap_sse=True,
                on_completion_callback=on_stream_complete,
                trace_name=f"Agent-{agent_uuid}",
                user_id=user_uuid if user_uuid else "",
                session_id=thread_id,
                user_name=user_name,
                chat_type='agent',
                agent_id=agent_uuid,
                turn_id=turn_id,
                user_question=extract_last_user_question(messages),
                user_images=extract_last_user_images(messages),
                llm_config=llm_config,
                user_info=user_info
            )
            return stream_generator()
        except Exception as e:
            logger.error(f"Agent 执行失败: {e}", exc_info=True)
            return AIChatController._create_error_response(f'智能体执行失败: {str(e)}')


    @staticmethod
    async def chat_with_search_response(current_user: str = None) -> tuple[Response, int] | Response:
        """大模型根据检索结果生成答案
        接收前端传递的 search_response 信息、对话历史、用户query，调用大模型API并返回结果
        """

        # 暂时移除认证检查，以便前端能够正常调用接口
        # if not current_user:
        #     return jsonify({'error': '用户未认证'}), 401

        data = request.json

        # 验证必要参数
        if not data:
            return jsonify({'error': '请求数据不能为空'}), 400

        # 获取输入参数
        # TODO: 后面可能要改成从后端获取model、apiKey、baseUrl、maxTokens，前端只传递query、messages和search_response
        model = data.get('model')
        api_key = data.get('apiKey')
        base_url = data.get('baseUrl')
        max_tokens = data.get('maxTokens') or 1024

        query = data.get('query') or ''
        messages = data.get('messages')
        search_response = data.get('search_response') or []


        if not model or not messages or not api_key or not base_url:
            return jsonify({'error': '缺少必要参数'}), 400

        try:
            # 处理base_url，确保格式正确
            processed_base_url = base_url.strip()
            # 移除可能存在的 /chat 或 /chat/completions 路径
            if processed_base_url.endswith('/chat'):
                processed_base_url = processed_base_url[:-5]
            elif processed_base_url.endswith('/chat/completions'):
                processed_base_url = processed_base_url[:-17]
            # 确保URL以 /v1 结尾
            if not processed_base_url.endswith('/v1'):
                processed_base_url = processed_base_url.rstrip('/') + '/v1'

            # 创建ChatOpenAI实例，启用流式输出
            llm = ChatOpenAI(
                model=model,
                api_key=api_key,
                base_url=processed_base_url,
                temperature=0.7,
                max_tokens=max_tokens,
                timeout=30.0,
                streaming=True
            )
            context = "\n\n".join([doc.get("page_content", "") for doc in search_response])
            if messages and messages[-1]["content"] == query:
                messages.pop()
            messages = messages + [
                {
                    "role": "user",
                    "content": f"【指令】根据已知信息，使用简短和专业的语言回答问题。如果无法从中得到确定答案或问题与已知信息不相关，请说 \"知识库无相关信息\", 并忽略已知信息直接回答用户问题, 要符合逻辑不能编造事实。答案请使用中文。\n\n【已知信息】{context}\n\n【问题】{query}\n"
                }
            ]

            # 定义流式输出生成器
            def _generate_stream_response():
                # 调用大模型API进行流式输出
                for chunk in llm.stream(messages):
                    # 构建流式响应格式
                    response_chunk = {
                        'id': f'chatcmpl-{int(time.time())}',
                        'object': 'chat.completion.chunk',
                        'created': int(time.time()),
                        'model': model,
                        'choices': [
                            {
                                'index': 0,
                                'delta': {
                                    'role': 'assistant' if chunk.content else None,
                                    'content': chunk.content or ''
                                },
                                'finish_reason': None
                            }
                        ]
                    }
                    # 发送chunk
                    yield f'data: {json.dumps(response_chunk)}\n\n'

                # 发送结束标志
                end_chunk = {
                    'id': f'chatcmpl-{int(time.time())}',
                    'object': 'chat.completion.chunk',
                    'created': int(time.time()),
                    'model': model,
                    'choices': [
                        {
                            'index': 0,
                            'delta': {},
                            'finish_reason': 'stop'
                        }
                    ]
                }
                yield f'data: {json.dumps(end_chunk)}\n\n'
                yield 'data: [DONE]\n\n'

            # 返回流式响应
            return Response(_generate_stream_response(), mimetype='text/event-stream')
        except Exception as e:
            logger.error("大模型对话失败: %s" % str(e))
            return jsonify({'error': '大模型对话失败: %s' % str(e)}), 500

    @staticmethod
    def _create_error_response(message: str):
        """创建错误响应的异步生成器
        
        Args:
            message: 错误消息
            
        Returns:
            异步生成器，yield SSE 格式的错误消息
        """
        async def error_generator():
            yield f'data: {{"error": "{message}"}}\n\n'
        return error_generator()

    @staticmethod
    def _convert_messages_to_dict(messages: List[Dict]) -> List[Dict]:
        """将前端消息转换为字典格式（用于普通 Agent）
        
        Args:
            messages: 前端消息列表
            
        Returns:
            转换后的消息列表
        """
        agent_messages = []
        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content', '')
            
            if role == 'user':
                agent_messages.append({"role": "user", "content": content})
            elif role == 'assistant':
                agent_messages.append({"role": "assistant", "content": content})
            elif role == 'tool':
                agent_messages.append({
                    "role": "tool", 
                    "content": content, 
                    "tool_call_id": msg.get('tool_call_id', '')
                })
        
        return agent_messages

    @staticmethod
    def _convert_messages_to_langchain(messages: List[Dict]):
        """将前端消息转换为 LangChain 消息对象（用于 DeepAgent）
        
        Args:
            messages: 前端消息列表
            
        Returns:
            LangChain 消息对象列表
        """
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        
        input_messages = []
        for msg in messages:
            if msg['role'] == 'user':
                input_messages.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant':
                input_messages.append(AIMessage(content=msg['content']))
            elif msg['role'] == 'system':
                input_messages.append(SystemMessage(content=msg['content']))
        
        return input_messages

    @staticmethod
    def _create_async_stream_generator(agent, input_data, thread_id,
                                        node_stage_by_name=None,
                                        last_todos_fingerprint=None,
                                        last_stage=None,
                                        wrap_sse=True,
                                        stream_config=None,
                                        on_completion_callback=None,
                                        trace_name=None,
                                        server_host: str = None,
                                        server_port: str | int = None,
                                        user_id=None,
                                        session_id=None,
                                        user_name=None,
                                        chat_type: str = None,
                                        agent_id: str = '',
                                        turn_id: str = '',
                                        user_question: str = '',
                                        user_images: list = None,
                                        llm_config: dict = None,
                                        user_info: dict = None):
        """创建通用的异步流生成器

        Args:
            agent: LangGraph/DeepAgent 实例
            input_data: 输入数据字典，如 {"messages": ...}
            thread_id: 线程 ID
            node_stage_by_name: 节点阶段映射（可选）
            last_todos_fingerprint: todos 指纹（可选）
            last_stage: 最后阶段（可选）
            wrap_sse: 是否包装为 SSE 格式（默认 True）
            stream_config: 流式配置字典，如 {"recursion_limit": 1000}（可选）
            on_completion_callback: 完成回调函数（可选）
            trace_name: Langfuse trace 名称（可选）
            server_host: 文件下载地址 host（可选，提供则自动注入下载链接）
            server_port: 文件下载地址 port（可选，提供则自动注入下载链接）
            user_id:
            session_id:
            user_name:
            chat_type: 对话类型（提供则启用对话记录落库：deepagent / agent）
            agent_id: 智能体 UUID（用于对话记录）
            turn_id: 本轮对话 ID（用于对话记录）
            user_question: 本轮用户问题（用于对话记录）
            user_images: 本轮用户上传图片列表（用于对话记录）
            llm_config: 大模型配置
            user_info: 用户信息

        Returns:
            异步生成器函数
        """
        from src.langgraph_agent.common.utils.astream_events_tools import process_event
        from src.utils.reasoning_buffer import ReasoningBuffer
        
        # 设置默认值
        if node_stage_by_name is None:
            node_stage_by_name = {}
        if last_todos_fingerprint is None:
            last_todos_fingerprint = {"value": None}
        if last_stage is None:
            last_stage = {"value": None}
        if stream_config is None:
            stream_config = {}

        # 对话记录采集器（仅在提供 chat_type 时启用，不影响其他调用方）
        record_collector = (
            ChatRecordCollector(
                chat_type=chat_type,
                user_id=user_id,
                user_name=user_name,
                session_thread_id=session_id or thread_id,
                agent_id=agent_id,
                turn_id=turn_id,
                user_question=user_question,
                user_images=user_images,
                llm_config=llm_config
            )
            if chat_type
            else None
        )
        if record_collector:
            threading.Thread(target=record_collector.summarize_first_question, daemon=True).start()

        
        async def stream_generator():
            """异步流生成器"""

            buf = ReasoningBuffer()
            try:
                from src.utils.interrupt_utils import check_interrupt

                # 构建 astream_events 的配置参数
                config = {"configurable": {"thread_id": thread_id}}
                config.update(stream_config)
                # 指定 trace 名称（Langfuse 会用它作为 trace name）
                if trace_name:
                    config["run_name"] = trace_name

                # 注入 Langfuse callback（若启用且 SDK 可用）
                langfuse_handler = get_langfuse_handler()
                if langfuse_handler is not None:
                    existing_callbacks = config.get("callbacks") or []
                    config["callbacks"] = existing_callbacks + [langfuse_handler]

                # 通过外层 root span 把 user_id / session_id 写到 trace 上，
                # CallbackHandler 会自动复用当前 OTel context 挂到该 span 下
                with langfuse_trace_context(
                        name=trace_name,
                        user_id=user_id,
                        session_id=session_id,
                        metadata=user_info
                ):
                    async for event in agent.astream_events(input_data, config=config, version="v2"):
                        # 检查是否有中断请求
                        if check_interrupt(thread_id):
                            break

                        run_id = event.get("run_id", "") or ""

                        async for output in process_event(event, thread_id, node_stage_by_name, last_todos_fingerprint,
                                                          last_stage):
                            # 累积对话记录（喂原始标签行，避免与 buf 聚合行重复统计）
                            if record_collector:
                                record_collector.feed_line(output)
                            line = buf.feed(run_id, output)
                            if line is not None:
                                yield f"data: {line}\n\n" if wrap_sse else line

            except Exception as e:
                error_msg_json = json.dumps({"error": f"流式输出失败: {str(e)}"})
                if wrap_sse:
                    yield f'data: {error_msg_json}\n\n'
                else:
                    yield error_msg_json
            finally:
                # 循环结束后 flush 所有残余缓冲，确保异常时也不会丢失思考内容
                # 嵌套 try/finally：生成器被强行关闭/取消（客户端断开、服务 shutdown）时，
                # 下方的 yield 可能抛出异常，仍须保证文件状态持久化、对话记录落库与完成回调执行
                try:
                    for line in buf.flush_all():
                        yield f"data: {line}\n\n" if wrap_sse else line
                finally:

                    # 本轮对话结束，实时落库对话记录（幂等，失败不阻断完成回调）
                    if record_collector:
                        try:
                            record_collector.finalize()
                        except Exception as finalize_error:
                            logger.error(f"对话记录落库失败: {finalize_error}")

                    # 流完成时调用回调函数（沙盒置闲 / 清除中断标志）
                    if on_completion_callback:
                        try:
                            on_completion_callback()
                        except Exception as callback_error:
                            logger.error(f"Completion callback failed: {callback_error}")

        return stream_generator
