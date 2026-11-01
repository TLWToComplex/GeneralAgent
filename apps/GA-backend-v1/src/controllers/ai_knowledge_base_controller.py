import os
import json
from flask import Response, request, jsonify
import requests
from src.config import KBChatConfig
from src.utils.config_manager import config_manager
import logging
from src.accessors.ai_kb_chat_accessor import AIKBChat

logger = logging.getLogger(__name__)

class AIKnowledgeBaseController:
    
    # 获取请求中的知识库名称
    @staticmethod
    def get_knowledge_base_name():
        # 尝试从JSON请求体中获取
        if request.is_json:
            data = request.get_json(silent=True)
            # 对于delete_knowledge_base接口，直接返回data
            if request.path and '/knowledge_base/delete_knowledge_base' in request.path:
                return data['payload']['knowledge_base_name']
            if data and 'knowledge_base_name' in data:
                return data['knowledge_base_name']
        # 尝试从form data中获取
        form_data = request.form.to_dict()
        if 'knowledge_base_name' in form_data:
            return form_data['knowledge_base_name']
        
        # 尝试从查询参数中获取
        query_params = request.args.to_dict()
        if 'knowledge_base_name' in query_params:
            return query_params['knowledge_base_name']
        
        return None
    """知识库代理控制器"""
    """
    代理转发请求到知识库服务
    支持两种路径格式:
    1. /kb_chat - 根路径访问
    2. /kb_chat/{api_path} - 带子路径访问
    例如: /kb_chat/knowledge_base/list_knowledge_bases 会转发到配置的知识库服务地址
    """
    # 调用控制器处理代理转发逻辑
    @staticmethod
    async def proxy_kb_request(api_path: str, current_user: str = 'admin') -> Response:
        """
        代理转发请求到知识库服务
        
        参数:
            api_path: API路径
            
        返回:
            Response: 转发的响应
        """
        try:
            # 构建完整的目标URL
            base_url = KBChatConfig.BASE_URL
            if api_path:
                full_url = f"{base_url}/{api_path}"
            else:
                full_url = f"{base_url}"
            
            logger.info(f"Proxying request to: {full_url}, current_user: {current_user}")
            
            # 特殊处理知识库创建接口 - 允许所有用户创建，但会记录创建者
            if api_path == 'knowledge_base/create_knowledge_base' or api_path == '/knowledge_base/create_knowledge_base':
                # 获取知识库名称
                kb_name = AIKnowledgeBaseController.get_knowledge_base_name()
                if not kb_name:
                    # 从请求体中再次尝试获取（可能在不同的字段中）
                    if request.is_json:
                        data = request.get_json(silent=True)
                        if data:
                            kb_name = data.get('kb_name')
                
                # 记录要创建的知识库名称，用于后续数据库插入
                if kb_name:
                    request.kb_name_to_create = kb_name
                    logger.info(f"准备创建知识库: {kb_name}")
            
            # 特殊处理知识库列表接口 - 不需要权限检查，会在返回时过滤数据
            elif api_path == 'knowledge_base/list_knowledge_bases' or api_path == '/knowledge_base/list_knowledge_bases':
                logger.info(f"获取知识库列表，将过滤为用户 {current_user} 创建的数据和有权限访问的数据")

            # 特殊处理自动抽取实体类型和关系类型接口 - 不需要权限检查
            elif api_path == 'knowledge_base/auto_nodes_and_relationships' or api_path == '/knowledge_base/auto_nodes_and_relationships':
                logger.info(f"从文本中自动抽取实体类型和关系类型，不进行权限验证")

            # 其他所有接口都需要进行权限验证
            else:
                from flask import g as request_g
                # 获取知识库名称
                kb_name = AIKnowledgeBaseController.get_knowledge_base_name()
                if not kb_name:
                    # 尝试从请求体中的kb_name获取
                    if request.is_json:
                        data = request.get_json(silent=True)
                        if data and 'kb_name' in data:
                            kb_name = data['kb_name']
                
                if kb_name:
                    # 优先从 g 对象获取权限列表
                    perm_list = getattr(request_g, 'allowed_entity_ids', None)

                    # 统一处理字符串和列表两种形式，一次查询所有知识库
                    kb_name_list = kb_name if isinstance(kb_name, list) else [kb_name]
                    kb_records = {
                        kb.name: kb.to_dict()
                        for kb in AIKBChat.query.filter(AIKBChat.name.in_(kb_name_list)).all()
                    }

                    for single_kb_name in kb_name_list:
                        kb_info = kb_records.get(single_kb_name)
                        if not kb_info:
                            logger.warning(f"用户 {current_user} 对知识库 {single_kb_name} 没有访问权限或知识库不存在")
                            return jsonify({'code': 403, 'message': f'无权限访问知识库: {single_kb_name}'}), 403

                        is_creator = (kb_info.get('create_by') == current_user)
                        has_group_perm = perm_list and kb_info.get('uuid') in perm_list

                        if not is_creator and not has_group_perm and current_user.lower() != 'admin':
                            return jsonify({'code': 403, 'message': f'无权限访问知识库: {single_kb_name}'}), 403
                else:
                    # 对于POST请求，如果无法获取知识库名称，则拒绝访问
                    if request.method == 'POST':
                        logger.error(f"无法获取知识库名称，拒绝POST请求")
                        return jsonify({'code': 403, 'message': '无法获取知识库名称，拒绝操作'}), 403
                    logger.warning(f"无法获取知识库名称，跳过GET请求权限验证")
            
            # 获取原始请求的参数、数据和头部
            params = request.args.to_dict()
            headers = {key: value for key, value in request.headers if key.lower() != 'host'}
            form_headers = {
                k: v for k, v in request.headers.items()
                if k.lower() not in ['host', 'content-type', 'content-length']
            }
            request_method = request.method
            # 特殊处理文件下载接口：流式透传二进制响应，避免被当 JSON/文本解码导致文件损坏
            if api_path in ('knowledge_base/download_doc', '/knowledge_base/download_doc'):
                import asyncio
                loop = asyncio.get_event_loop()

                def make_download_request():
                    return requests.get(
                        full_url, params=params, headers=headers,
                        proxies={"http": None, "https": None},
                        timeout=3000, stream=True
                    )

                download_response = await loop.run_in_executor(None, make_download_request)

                # 过滤掉由 requests/Flask 自行处理的逐跳响应头
                excluded_headers = {'transfer-encoding', 'content-encoding', 'connection', 'content-length'}
                forward_headers = {
                    k: v for k, v in download_response.headers.items()
                    if k.lower() not in excluded_headers
                }

                def generate():
                    try:
                        for chunk in download_response.iter_content(chunk_size=8192):
                            if chunk:
                                yield chunk
                    finally:
                        download_response.close()

                return Response(generate(), status=download_response.status_code, headers=forward_headers)

            # 提前准备请求数据，避免在线程池中访问request对象
            request_data = None
            is_json = request.is_json
            form_data = request.form.to_dict() if not is_json else None
            files_payload = []
            if api_path == "knowledge_base/upload_docs":
                if request.files:
                    for key, file_storage in request.files.lists():
                        for file in file_storage:
                            # 格式: (表单Key, (文件名, 文件流, MimeType))
                            files_payload.append((key, (file.filename, file.stream, file.mimetype)))

            # 如果是JSON请求，提前获取数据
            if is_json:
                try:
                    request_data = request.json
                except:
                    request_data = None
            
            # 使用线程池执行同步的requests调用，避免阻塞事件循环
            import asyncio
            loop = asyncio.get_event_loop()
            
            # 定义同步函数用于在线程池中执行
            def make_request():
                if request_method == 'GET':
                    return requests.get(full_url, params=params, headers=headers, 
                                      proxies={"http": None, "https": None}, timeout=3000)
                elif request_method == 'POST':
                    if is_json and request_data:
                        return requests.post(full_url, json=request_data, params=params, headers=headers, 
                                           proxies={"http": None, "https": None}, timeout=3000)
                    else:
                        return requests.post(full_url, data=form_data, files=files_payload, params=params, headers=form_headers,
                                           proxies={"http": None, "https": None}, timeout=3000)
                elif request_method == 'PUT':
                    if is_json and request_data:
                        return requests.put(full_url, json=request_data, params=params, headers=headers, 
                                          proxies={"http": None, "https": None}, timeout=3000)
                    else:
                        return requests.put(full_url, data=form_data, params=params, headers=headers, 
                                          proxies={"http": None, "https": None}, timeout=3000)
                elif request_method == 'DELETE':
                    if is_json and request_data:
                        return requests.delete(full_url, json=request_data, params=params, headers=headers, 
                                          proxies={"http": None, "https": None}, timeout=3000)
                    else:
                        return requests.delete(full_url, params=params, headers=headers, 
                                          proxies={"http": None, "https": None}, timeout=3000)
                else:
                    return None
            
            # 如果请求方法不支持，直接返回错误
            if request_method not in ['GET', 'POST', 'PUT', 'DELETE']:
                return jsonify({'code': 1, 'message': f'不支持的方法: {request_method}'}), 405
            
            # 在线程池中执行同步请求
            response = await loop.run_in_executor(None, make_request)
            
            # 转发响应状态码和内容
            response_headers = {
                'Content-Type': response.headers.get('Content-Type', 'application/json')
            }
            
            # 尝试解析JSON响应
            try:
                response_data = response.json()
                
                # 处理知识库创建成功的情况
                if api_path == 'knowledge_base/create_knowledge_base' and response_data.get('code') == 200:
                    kb_name = getattr(request, 'kb_name_to_create', None)
                    if kb_name:
                        try:
                            # # 使用 accessor 创建知识库记录
                            kb_data = {
                                'name': kb_name,
                                'create_by': current_user,
                                'visibility': request_data.get('permission_code')
                            }
                            result, kb_or_error = AIKBChat.add_kb_chat(kb_data)
                            if result:
                                response_data['uuid'] = kb_or_error['uuid']
                                logger.info(f"知识库 {kb_name} 创建成功并记录到数据库")
                            else:
                                logger.error(f"将知识库 {kb_name} 记录到数据库失败: {kb_or_error}")
                        except Exception as e:
                            logger.error(f"将知识库 {kb_name} 记录到数据库失败: {str(e)}")
                
                # 处理知识库删除成功的情况
                elif (api_path == 'knowledge_base/delete_knowledge_base' or api_path == '/knowledge_base/delete_knowledge_base') and response_data.get('code') == 200:
                    # 获取知识库名称
                    kb_name = AIKnowledgeBaseController.get_knowledge_base_name()
                    if kb_name:
                        try:
                            # 使用 accessor 删除知识库记录
                            result, message = AIKBChat.delete_kb_chat(name=kb_name, create_by=current_user)
                            if result:
                                logger.info(f"知识库 {kb_name} 删除成功并从数据库中移除")
                            else:
                                logger.warning(f"从数据库中删除知识库 {kb_name} 失败: {message}")
                        except Exception as e:
                            logger.error(f"从数据库中删除知识库 {kb_name} 失败: {str(e)}")
                
                # 处理知识库列表响应
                elif (api_path == 'knowledge_base/list_knowledge_bases' or api_path == '/knowledge_base/list_knowledge_bases') and 'data' in response_data:
                    # 使用 accessor 获取当前用户可访问的知识库列表
                    try:
                        from flask import g as request_g
                        perm_list = getattr(request_g, 'allowed_entity_ids', None)
                        result, kb_list_or_error = AIKBChat.list_kb_chats(create_by=current_user,
                                                                          allowed_entity_ids=perm_list,
                                                                          permission_code=params.get('permission_code'))
                        
                        if result:
                            # 提取可访问的知识库名称列表
                            accessible_kb_info = {kb['name']: kb for kb in kb_list_or_error}
                            # 过滤响应数据，保留用户可访问的知识库
                            if isinstance(response_data['data'], list):
                                filtered_data = []
                                for item in response_data['data']:
                                    kb_name = item.get('kb_name', '')
                                    if kb_name in accessible_kb_info:
                                        item['kb_uuid'] = accessible_kb_info[kb_name]['uuid']
                                        filtered_data.append(item)
                                response_data['data'] = filtered_data
                        else:
                            # 如果没有权限限制（如admin或无用户组），保留原始数据
                            logger.info(f"用户 {current_user} 没有权限限制，返回所有知识库")
                            # 不做任何修改，保留 response_data['data'] 的原始值
                    except Exception as e:
                        logger.error(f"过滤知识库列表失败: {str(e)}")
                # 处理知识库更新信息（重命名）成功的情况
                elif (api_path == 'knowledge_base/update_info' or api_path == '/knowledge_base/update_info') and response_data.get('code') == 200:
                    new_kb_name = request_data.get('new_kb_name', "")
                    new_permission_code = request_data.get('new_permission_code', "")
                    if new_kb_name or new_permission_code:
                        old_kb_name = request_data.get('knowledge_base_name', "")
                        try:
                            # 使用 accessor 更新知识库名称
                            update_data = {'name': new_kb_name}
                            if new_permission_code:
                                update_data['visibility'] = new_permission_code
                            result, kb_or_error = AIKBChat.update_kb_chat(
                                name=old_kb_name,
                                update_data=update_data,
                                current_user=current_user
                            )
                            if result:
                                logger.info(f"知识库 {old_kb_name} 已重命名为 {new_kb_name}")
                            else:
                                logger.error(f"知识库 {old_kb_name} 重命名为 {new_kb_name} 失败: {kb_or_error}")
                        except Exception as e:
                            logger.error(f"知识库 {old_kb_name} 重命名为 {new_kb_name} 失败: {str(e)}")
                # 处理知识库搜索文档结果：将 file_path 中的 kb_chat.base_url 替换为本服务地址
                elif api_path == 'knowledge_base/search_docs' or api_path == '/knowledge_base/search_docs':
                    server_host = config_manager.get_public_host()
                    server_port = config_manager.get_public_port()
                    kb_base_url = KBChatConfig.BASE_URL.rstrip('/')
                    proxy_base_url_record = f'http://<server_host>:<server_port>/kb_chat'
                    proxy_base_url = f'http://{server_host}:{server_port}/kb_chat'
                    def replace_url(obj, url_old, url_new):
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                if k == 'file_path' and isinstance(v, str) and v.startswith(url_old):
                                    obj[k] = v.replace(url_old, url_new, 1)
                                else:
                                    replace_url(v, url_old, url_new)
                        elif isinstance(obj, list):
                            for item in obj:
                                replace_url(item, url_old, url_new)
                    replace_url(response_data, kb_base_url, proxy_base_url_record)

                    session_thread_id = request_data.get('session_thread_id') or ''
                    turn_id = request_data.get('turn_id') or ''
                    if session_thread_id and turn_id:
                        base_dir = config_manager.get_file_container_path()
                        os.makedirs(os.path.join(base_dir, str(session_thread_id)), exist_ok=True)
                        # 更新记录检索 kb 结果的 JSON 文件
                        json_path = os.path.join(base_dir, str(session_thread_id), "kb_citations.json")
                        kb_citations = {}
                        if os.path.exists(json_path):
                            with open(json_path, 'r', encoding='utf-8') as jf:
                                kb_citations = json.load(jf)

                        turn_key = str(turn_id)
                        kb_citations[turn_key] = response_data

                        with open(json_path, 'w', encoding='utf-8') as jf:
                            json.dump(kb_citations, jf, ensure_ascii=False, indent=4)

                    replace_url(response_data, proxy_base_url_record, proxy_base_url)

                return jsonify(response_data), response.status_code
            except ValueError:
                # 如果不是JSON格式，返回原始文本
                return Response(response.text, status=response.status_code, headers=response_headers)
        
        except requests.RequestException as e:
            logger.error(f"Proxy request failed with HTTP error: {str(e)}")
            return jsonify({'code': 1, 'message': f'代理请求失败: {str(e)}'}), 500
        except Exception as e:
            logger.error(f"Proxy request failed with error: {str(e)}")
            return jsonify({'code': 1, 'message': f'代理请求失败: {str(e)}'}), 500