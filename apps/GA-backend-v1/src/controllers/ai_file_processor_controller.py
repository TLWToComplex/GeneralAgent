"""
AI文件处理控制器模块。
处理文件上传和LangChain文件读取的API端点。
"""
import logging
import asyncio
import os
import json
import urllib.parse
from flask import request, jsonify
from typing import Dict, Tuple
from src.config import _config_loader
from src.utils.config_manager import config_manager
import aiohttp

logger = logging.getLogger(__name__)

# 文件处理服务地址（从配置文件读取）
FILE_PROCESSOR_URL = _config_loader.get("file_processing.service_url", "http://localhost:8200/api/process")
# 文件处理服务超时时间（从配置文件读取，默认10分钟=600秒）
FILE_PROCESSOR_TIMEOUT = _config_loader.get("file_processing.timeout", 600)


class AIFileProcessorController:
    """
    文件处理器控制器类，用于处理文件上传和LangChain文件读取的API请求
    """

    @staticmethod
    async def upload_and_process_files(current_user: str = None) -> Tuple[Dict, int]:
        """
        上传并处理文件，转发至文件处理服务进行文档分割

        参数:
            current_user: 当前用户

        返回:
            Tuple[Dict, int]: 响应数据和状态码
        """
        # 验证当前用户
        if not current_user:
            return jsonify({'error': '用户未认证'}), 401

        # 获取对话ID
        conversation_id = request.form.get('conversation_id')
        if not conversation_id:
            return jsonify({'error': '对话ID为必填字段'}), 400

        session_thread_id = request.form.get('session_thread_id')
        turn_id = request.form.get('turn_id')

        # 获取处理类型，默认为 langchain
        process_type = request.form.get('process_type', 'langchain')

        # 获取上传的文件
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': '请至少上传一个文件'}), 400

        # 一次性读取所有文件内容（流只能读取一次，读取后复用内存内容）
        file_contents = []
        for f in files:
            file_contents.append((f.filename, f.stream.read(), f.content_type))

        # 构建转发给文件处理服务的文件数据（复用已读取的内存内容）
        file_data = {}
        for idx, (filename, content, content_type) in enumerate(file_contents):
            file_data[f'files_{idx}'] = (
                filename,
                content,
                content_type
            )

        # 异步调用文件处理服务
        try:
            async with aiohttp.ClientSession() as session:
                # 创建 multipart/form-data 表单
                form_data = aiohttp.FormData()
                form_data.add_field('conversation_id', conversation_id)
                form_data.add_field('process_type', process_type)
                
                for key, (filename, content, content_type) in file_data.items():
                    form_data.add_field(
                        'files',
                        content,
                        filename=filename,
                        content_type=content_type
                    )
                
                # 发送异步请求
                async with session.post(
                    FILE_PROCESSOR_URL,
                    data=form_data,
                    timeout=aiohttp.ClientTimeout(total=FILE_PROCESSOR_TIMEOUT)
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"文件处理服务返回错误: {resp.status}, {error_text}")
                        return jsonify({'error': f'文件处理服务返回错误: {resp.status}'}), 502
                    
                    result = await resp.json()

                    # 保存文件到本地存储
                    base_dir = config_manager.get_file_container_path()
                    input_dir = os.path.join(base_dir, str(session_thread_id), "input")
                    os.makedirs(input_dir, exist_ok=True)

                    saved_file_paths = []
                    for filename, content, content_type in file_contents:
                        # 若同名文件已存在，则在文件名后追加序号，避免覆盖已有文件
                        save_name = filename
                        stem, ext = os.path.splitext(filename)
                        counter = 1
                        while os.path.exists(os.path.join(input_dir, save_name)):
                            save_name = f"{stem}({counter}){ext}"
                            counter += 1

                        file_path = os.path.join(input_dir, save_name)
                        with open(file_path, 'wb') as f_out:
                            f_out.write(content)
                        download_url = (
                            f"http://<server_host>:<server_port>"
                            f"/aiFileProcessor/download"
                            f"?file_path={urllib.parse.quote(file_path)}"
                        )
                        saved_file_paths.append({"name": save_name, "path": download_url})

                    # 更新上传记录 JSON 文件
                    json_path = os.path.join(base_dir, str(session_thread_id), "upload_records.json")
                    upload_records = {}
                    if os.path.exists(json_path):
                        with open(json_path, 'r', encoding='utf-8') as jf:
                            upload_records = json.load(jf)

                    turn_key = str(turn_id)
                    if turn_key in upload_records:
                        upload_records[turn_key].extend(saved_file_paths)
                    else:
                        upload_records[turn_key] = saved_file_paths

                    with open(json_path, 'w', encoding='utf-8') as jf:
                        json.dump(upload_records, jf, ensure_ascii=False, indent=4)

        except asyncio.TimeoutError:
            logger.error("文件处理服务请求超时")
            return jsonify({'error': '文件处理服务请求超时'}), 504
        except aiohttp.ClientConnectionError:
            logger.error("文件处理服务连接失败")
            return jsonify({'error': '文件处理服务不可用'}), 503
        except aiohttp.ClientError as e:
            logger.error(f"文件处理服务调用异常: {e}")
            return jsonify({'error': f'文件处理服务调用异常: {str(e)}'}), 500

        return jsonify(result), 200