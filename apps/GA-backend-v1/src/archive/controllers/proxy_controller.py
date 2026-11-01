"""
Proxy controller module.
Handles API proxying to external services like LLM providers and TTS services.
"""
import os
import json
import logging
import requests
import uuid
from flask import Response, request, jsonify
import time
from typing import Dict, List, Union, Tuple, Any, Generator

# 使用环境变量获取KB聊天URL
kb_chat_url = os.getenv('KB_CHAT_URL', '')
class ProxyController:

    # Configure logging
    # logging.basicConfig(
    #     level=logging.INFO,
    #     format='%(asctime)s [%(levelname)s] %(message)s',
    #     handlers=[
    #         logging.StreamHandler(),
    #         logging.FileHandler('proxy.log')
    #     ]
    # )
    logger = logging.getLogger('proxy')

    @staticmethod
    def format_json(data) -> str:
        """Format JSON data for pretty printing in logs"""
        if not data:
            return "None"
        try:
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            return str(data)

    @staticmethod
    def get_model_mapping() -> Dict:
        """获取模型映射关系，包含各类型模型的配置信息"""
        logger = ProxyController.logger
        logger.info("Loading model configurations...")

        # 1. 获取LLM（大语言模型）配置
        llm_ids = os.getenv('LLM_IDS', '').split(',')
        llm_urls = os.getenv('LLM_URLS', '').split(',')
        llm_api_keys = os.getenv('LLM_API_KEYS', '').split(',')
        llm_max_tokens = os.getenv('LLM_MAX_TOKENS', '').split(',')

        logger.info(f"Found {len(llm_ids)} LLM configurations")

        # 1.1  获取AWC配置
        awc_ids = os.getenv('AWC_IDS', '').split(',')
        awc_urls = os.getenv('AWC_URLS', '').split(',')
        awc_api_keys = os.getenv('AWC_API_KEYS', '').split(',')
        awc_max_tokens = os.getenv('AWC_MAX_TOKENS', '').split(',')

        # 2. 获取VLM（视觉语言模型）配置
        vlm_ids = os.getenv('VLM_IDS', '').split(',')
        vlm_urls = os.getenv('VLM_URLS', '').split(',')
        vlm_api_keys = os.getenv('VLM_API_KEYS', '').split(',')
        vlm_max_tokens = os.getenv('VLM_MAX_TOKENS', '').split(',')

        # 3. 获取Embedding模型配置（不需要max_tokens）
        embedding_ids = os.getenv('EMBEDDING_IDS', '').split(',')
        embedding_urls = os.getenv('EMBEDDING_URLS', '').split(',')
        embedding_api_keys = os.getenv('EMBEDDING_API_KEYS', '').split(',')

        # 4. 获取Rerank模型配置（不需要max_tokens）
        rerank_ids = os.getenv('RERANK_IDS', '').split(',')
        rerank_urls = os.getenv('RERANK_URLS', '').split(',')
        rerank_api_keys = os.getenv('RERANK_API_KEYS', '').split(',')

        # 5. 获取ASR（语音识别）模型配置（不需要max_tokens）
        asr_ids = os.getenv('ASR_IDS', '').split(',')
        asr_urls = os.getenv('ASR_URLS', '').split(',')
        asr_api_keys = os.getenv('ASR_API_KEYS', '').split(',')

        # 6. 获取TTS（文本转语音）模型配置（不需要max_tokens）
        tts_ids = os.getenv('TTS_IDS', '').split(',')
        tts_urls = os.getenv('TTS_URLS', '').split(',')
        tts_api_keys = os.getenv('TTS_API_KEYS', '').split(',')

        model_mapping = {}

        # 处理LLM模型
        for i in range(min(len(llm_ids), len(llm_urls))):
            model_id = llm_ids[i].strip()
            model_url = llm_urls[i].strip()

            # 处理API密钥
            api_key = ""
            if i < len(llm_api_keys):
                api_key = llm_api_keys[i].strip()

            # 处理max_tokens配置
            max_tokens = None
            if i < len(llm_max_tokens):
                try:
                    max_tokens = int(llm_max_tokens[i].strip())
                except (ValueError, AttributeError):
                    logger.warning(f"Invalid max_tokens value for LLM {model_id}: {llm_max_tokens[i]}")
                    max_tokens = None

            if model_id and model_url:
                model_mapping[model_id] = {
                    "url": model_url,
                    "api_key": api_key,
                    "type": "LLM",
                    "max_tokens": max_tokens
                }
                logger.info(f"Configured LLM model: {model_id} -> {model_url} -> {max_tokens}")
            else:
                logger.warning(f"Skipping invalid LLM configuration at index {i}")

        # 处理AWC模型
        for i in range(min(len(awc_ids), len(awc_urls))):
            model_id = awc_ids[i].strip()
            model_url = awc_urls[i].strip()

            api_key = ""
            if i < len(awc_api_keys):
                api_key = awc_api_keys[i].strip()

            max_tokens = None
            if i < len(awc_max_tokens):
                try:
                    max_tokens = int(awc_max_tokens[i].strip())
                except (ValueError, AttributeError):
                    max_tokens = None

            if model_id and model_url:
                model_mapping[model_id] = {
                    "url": model_url,
                    "api_key": api_key,
                    "type": "AWC",
                    "max_tokens": max_tokens
                }

        # 处理VLM模型
        for i in range(min(len(vlm_ids), len(vlm_urls))):
            model_id = vlm_ids[i].strip()
            model_url = vlm_urls[i].strip()

            api_key = ""
            if i < len(vlm_api_keys):
                api_key = vlm_api_keys[i].strip()

            max_tokens = None
            if i < len(vlm_max_tokens):
                try:
                    max_tokens = int(vlm_max_tokens[i].strip())
                except (ValueError, AttributeError):
                    max_tokens = None

            if model_id and model_url:
                model_mapping[model_id] = {
                    "url": model_url,
                    "api_key": api_key,
                    "type": "VLM",
                    "max_tokens": max_tokens
                }

        # 处理Embedding模型（没有max_tokens）
        for i in range(min(len(embedding_ids), len(embedding_urls))):
            model_id = embedding_ids[i].strip()
            model_url = embedding_urls[i].strip()

            api_key = ""
            if i < len(embedding_api_keys):
                api_key = embedding_api_keys[i].strip()

            if model_id and model_url:
                model_mapping[model_id] = {
                    "url": model_url,
                    "api_key": api_key,
                    "type": "EMBEDDING"
                }

        # 处理Rerank模型（没有max_tokens）
        for i in range(min(len(rerank_ids), len(rerank_urls))):
            model_id = rerank_ids[i].strip()
            model_url = rerank_urls[i].strip()

            api_key = ""
            if i < len(rerank_api_keys):
                api_key = rerank_api_keys[i].strip()

            if model_id and model_url:
                model_mapping[model_id] = {
                    "url": model_url,
                    "api_key": api_key,
                    "type": "RERANK"
                }

        # 处理ASR模型（没有max_tokens）
        for i in range(min(len(asr_ids), len(asr_urls))):
            model_id = asr_ids[i].strip()
            model_url = asr_urls[i].strip()

            api_key = ""
            if i < len(asr_api_keys):
                api_key = asr_api_keys[i].strip()

            if model_id and model_url:
                model_mapping[model_id] = {
                    "url": model_url,
                    "api_key": api_key,
                    "type": "ASR"
                }

        # 处理TTS模型（没有max_tokens）
        for i in range(min(len(tts_ids), len(tts_urls))):
            model_id = tts_ids[i].strip()
            model_url = tts_urls[i].strip()

            api_key = ""
            if i < len(tts_api_keys):
                api_key = tts_api_keys[i].strip()

            if model_id and model_url:
                model_mapping[model_id] = {
                    "url": model_url,
                    "api_key": api_key,
                    "type": "TTS"
                }

        logger.info(f"Total models configured: {len(model_mapping)}")
        return model_mapping

    @staticmethod
    def get_model_list() -> Tuple[Dict, int]:
        model_mapping = ProxyController.get_model_mapping()
        return jsonify({
            "models": [
                {
                    "id": model_id,
                    "type": info["type"],
                    "url": info["url"],
                    "max_tokens": info.get("max_tokens")
                }
                for model_id, info in model_mapping.items()
            ]
        })

    @staticmethod
    def get_model_list_tts() -> Dict:
        model_mapping = ProxyController.get_model_mapping()
        return {
            "models": [
                {
                    "id": model_id,
                    "type": info["type"],
                    "url": info["url"],
                    "max_tokens": info.get("max_tokens")
                }
                for model_id, info in model_mapping.items()
            ]
        }

    @staticmethod
    def proxy_llm(llm_payload=None) -> Union[Response, Tuple[Dict, int]]:
        logger = ProxyController.logger
        logger.info("-" * 100)

        # Log request details
        client_ip = request.remote_addr
        data = llm_payload if llm_payload is not None else request.get_json()
        model = data.get('model')
        messages = data.get('messages')
        stream = data.get('stream', True)

        # Log basic request info
        logger.info(f"Request IP: {client_ip} | Model: {model} | Stream: {stream}")

        # Log the full request payload with clear marker
        logger.info(">>> REQUEST PAYLOAD >>>")
        logger.info(ProxyController.format_json(data))
        logger.info("<<< REQUEST PAYLOAD <<<")

        # Get model mapping
        model_mapping = ProxyController.get_model_mapping()
        model_info = model_mapping.get(model, {})
        default_max_tokens = model_info.get("max_tokens", 1024) 

        if model in model_mapping:
            provider_info = model_mapping[model]
            api_url = provider_info["url"]
            api_key = provider_info["api_key"]
            model_type = provider_info["type"]
            logger.info(f"Routing to: {model} ({model_type}) -> {api_url}")
        else:
            error_msg = f"Model {model} not found"
            logger.error(f"ERROR: {error_msg}")
            return jsonify({"error": error_msg}), 404

        payload = {
            'model': model,
            'messages': messages,
            'stream': stream,
            'max_tokens': data.get('max_tokens', default_max_tokens),
            'temperature': data.get('temperature', 0.1),
            'top_p': data.get('top_p', 0.2)
        }

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        logger.info(">>> REQUEST PAYLOAD >>>")
        logger.info(ProxyController.format_json(payload))
        logger.info("<<< REQUEST PAYLOAD <<<")

        if api_key:
            # Only log that we're using an API key, not the actual key
            masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
            logger.info(f"Using API key: {masked_key}")
            headers['Authorization'] = f'Bearer {api_key}'

        try:
            logger.info("Sending request to provider...")
            response = requests.post(api_url, headers=headers, json=payload, stream=stream)

            if response.status_code != 200:
                error_msg = f"Provider error: Status {response.status_code}"
                logger.error(f"ERROR: {error_msg}")
                logger.error(f">>> ERROR RESPONSE >>>")
                logger.error(response.text[:500])
                logger.error("<<< ERROR RESPONSE <<<")
                return jsonify({"error": response.text}), response.status_code

            logger.info(f"Provider response received: Status {response.status_code}")

            if stream:
                def generate() -> Generator[bytes, None, None]:
                    chunk_count = 0
                    full_response = []

                    for line in response.iter_lines():
                        if line:
                            line_str = line.decode('utf-8').strip()

                            # Only log a sample of chunks for streamed responses to avoid flooding
                            if chunk_count == 0 or chunk_count == 1 or chunk_count % 50 == 0:
                                logger.info(f">>> STREAM CHUNK {chunk_count} >>>")
                                logger.info(line_str)
                                logger.info(f"<<< STREAM CHUNK {chunk_count} <<<")

                            if line_str == "data: [DONE]":
                                logger.info("Stream complete: [DONE]")
                                yield "data: [DONE]\n\n"
                            else:
                                full_response.append(line_str)
                                yield line_str + "\n\n"

                            chunk_count += 1

                    logger.info(f"Total chunks streamed: {chunk_count}")

                return Response(generate(), content_type='text/event-stream')
            else:
                # For non-streaming responses, log the complete response
                response_json = response.json()
                logger.info(">>> MODEL RESPONSE >>>")
                logger.info(ProxyController.format_json(response_json))
                logger.info("<<< MODEL RESPONSE <<<")
                return jsonify(response_json)

        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            logger.error(">>> EXCEPTION >>>")
            logger.error(error_msg)
            import traceback
            logger.error(traceback.format_exc())
            logger.error("<<< EXCEPTION <<<")
            return jsonify({"error": error_msg}), 500
        
    @staticmethod
    def proxy_kb_chat(kb_json_data=None) -> Union[Response, Tuple[Dict, int]]:
        logger = ProxyController.logger
        logger.info("-" * 100)
        logger.info("Processing KB chat request...")

        try:
            original_data = kb_json_data if kb_json_data is not None else request.get_json()
            logger.info(">>> KB CHAT REQUEST >>>")
            logger.info(ProxyController.format_json(original_data))
            logger.info("<<< KB CHAT REQUEST <<<")

            model = original_data.get("model")
            query = original_data.get("query")
            model_mapping = ProxyController.get_model_mapping()
            model_info = model_mapping.get(model, {})
            default_max_tokens = model_info.get("max_tokens", 1024) 
            history = original_data.get("history") if original_data.get("history") else []

            kb_search_payload = {
                "query": query,
                "knowledge_base_name": original_data.get("kb_name", "aiwu"),
                "top_k": original_data.get("top_k",3),
                "score_threshold": original_data.get("score_threshold", 1),
            }

            logger.info(">>> KB SEARCH REQUEST >>>")
            logger.info(ProxyController.format_json(kb_search_payload))
            logger.info("<<< KB SEARCH REQUEST <<<")

            response = requests.post(f"{kb_chat_url}/knowledge_base/search_docs", json=kb_search_payload)
            response_data = response.json()
            
            logger.info(">>> KB SEARCH RESPONSE >>>")
            logger.info(ProxyController.format_json(response_data))
            logger.info("<<< KB SEARCH RESPONSE <<<")
            
            formatted_docs = []
            for i, doc in enumerate(response_data, 1):
                source = doc.get("metadata", {}).get("source", "")
                score = doc.get("metadata", {}).get("score", 0)
                content = doc.get("page_content", "")
                
                doc_link = (
                    f'{kb_chat_url}/knowledge_base/download_doc?'
                    f'knowledge_base_name={original_data.get("kb_name")}&file_name={source}'
                )
                
                formatted_doc = f"出处 [{i}] [score:{score}] [{source}]({doc_link}) \n\n{content}\n\n"
                formatted_docs.append(formatted_doc)
                logger.info(f"Processed document {i}: {source} (score: {score})")

            if len(formatted_docs) == 0:
                logger.warning("No relevant documents found")
                formatted_docs.append("<span style='color:red'>未找到相关文档,该回答为大模型自身能力解答！</span>")
            
            context = "\n\n".join([doc.get("page_content", "") for doc in response_data])
            
            # 对话界面传入的history最后是user的query，需要删除
            # thinking_chain的history不包含user的query
            if history and history[-1]["content"] == query:
                history.pop()
                
            messages = history + [
                {
                    "role": "user",
                    "content": f"【指令】根据已知信息，简短和专业的来回答问题。如果无法从中得到确定答案或问题与已知信息不相关，请说 “知识库无相关信息”, 并忽略已知信息直接回答用户问题, 要符合逻辑不能编造事实。答案请使用中文。\n\
\n【已知信息】{context}\n\n【问题】{query}\n"
                }
            ]
            
            llm_payload = {
                "model": model,
                "messages": messages,
                "stream": str(original_data.get("stream", "true")).lower() == "true",
                "temperature": original_data.get("temperature", 0.1),
                "max_tokens": default_max_tokens
            }
            
            try:       
                logger.info("Calling LLM with context...")
                llm_response = ProxyController.proxy_llm(llm_payload)
                
                if str(original_data.get("stream", "true")).lower() == "true":
                    def generate() -> Generator[str, None, None]:
                        first_chunk = {
                            "id": f"chat{uuid.uuid4()}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "status":None,
                            "message_type": 1,
                            "message_id": None,
                            "is_ref": None,
                            "docs": formatted_docs,
                            "choices":[
                                {
                                    "delta":{
                                        "content":"",
                                        "tool_calls":[]
                                    },
                                    "role":"assistant"
                                }
                            ]
                        }
                        data_str = "data: " + json.dumps(first_chunk, ensure_ascii=False) + "\n\n"
                        yield data_str
                        
                        for chunk in llm_response.response:
                            yield chunk
                    
                    return Response(generate(), content_type='text/event-stream')
                else:
                    # 非流式响应
                    response_data = llm_response.get_json()
                    response_data["docs"] = formatted_docs
                    return jsonify(response_data)
            except Exception as e:
                logger.error(">>> KB CHAT EXCEPTION >>>")
                logger.error(f"Error in LLM processing: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                logger.error("<<< KB CHAT EXCEPTION <<<")
                return jsonify({"error": f"Error calling LLM API: {str(e)}"}), 500

        except Exception as e:
            logger.error(">>> KB CHAT EXCEPTION >>>")
            logger.error(f"Error in KB chat processing: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            logger.error("<<< KB CHAT EXCEPTION <<<")
            return jsonify({"error": f"Error processing KB chat request: {str(e)}"}), 500

