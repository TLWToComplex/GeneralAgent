"""
Thinking chain controller V2 module.
Enhanced version of thinking chain controller with improved reasoning capabilities.
"""
import re
import base64
import secrets
import urllib.parse
import os
import logging
import json
from typing import Dict, Any, List, Tuple, Optional, Union
from flask import request, jsonify, json, Response

from controllers.faq_controller import FaqController
from controllers.system_recommendation_controller import SystemRecommendationController
from controllers.proxy_controller import ProxyController
from core.tool_agent.tool_agent_engine import ToolAgentEngine
from utils.http_client import HTTPClient
from controllers.configuration_controller import ConfigurationController
from utils.rerank_utils import RerankUtils

FAQ_THRESHOLD = float(os.getenv('FAQ_THRESHOLD', 0.5))
VLM_IDS = os.getenv('VLM_IDS', 'glm-4v-9b')
SILENT_LOGIN_CAS_URL = os.getenv('SILENT_LOGIN_CAS_URL', "")
SILENT_LOGIN_C1_PORTAL_URL = os.getenv('SILENT_LOGIN_C1_PORTAL_URL', "")
RECOMMENDATION_SOURCE = os.getenv('RECOMMENDATION_SOURCE', 'internal')
ENVIROMENT = os.getenv('ENVIROMENT', 'Production')
# 使用环境变量存储访问令牌，避免硬编码
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN', "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3MzAxNjc0MzIsInVzZXJuYW1lIjoibGl1eXUifQ._S7v7oQza1DRXp6mG3koJA6y77ULomKx-cj1rUyjDlw")

class ThinkingChainControllerV2:
    """
    Controller for handling thinking chain logic.
    """
    # Configure logging
    # logging.basicConfig(
    #     level=logging.INFO,
    #     format='%(asctime)s [%(levelname)s] %(message)s',
    #     handlers=[
    #         logging.StreamHandler(),
    #         logging.FileHandler('thinking_chain_v2.log')
    #     ]
    # )
    logger = logging.getLogger('thinking_chain_v2')

    @staticmethod
    def format_json(data: Any) -> str:
        """Format JSON data for pretty printing in logs"""
        if not data:
            return "None"
        try:
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            return str(data)

    @staticmethod
    async def thinking_chain() -> Tuple[Response, int]:
        logger = ThinkingChainControllerV2.logger
        logger.info("-" * 100)

        """
        Main method to process the incoming query and provide an appropriate response.
        """
        try:
            # Extract query parameters
            query = request.json.get("query")
            history = request.json.get("history")
            image = request.json.get("image")

            # Log basic request info
            logger.info(">>> REQUEST PAYLOAD >>>")
            logger.info(ThinkingChainControllerV2.format_json(request.json))
            logger.info("<<< REQUEST PAYLOAD <<<")

            if not query:
                logger.error("Query parameter is missing")
                return jsonify({"error": "Query parameter is missing"}), 400

            if ThinkingChainControllerV2._contains_keywords(query, ['请看']):
                logger.info(f"Processing VLM request for query: {query}")
                query = ThinkingChainControllerV2._remove_keywords(query, [
                    "请看",
                    "艾武",
                    "秦翎"
                ])
                return ThinkingChainControllerV2.query_vlm(image, query)

            # Check and handle special keywords in the query
            if ThinkingChainControllerV2._contains_keywords(query, ['受领任务', '首领任务', '收领任务']):
                logger.info(f"Processing task request for query: {query}")
                query = ThinkingChainControllerV2._remove_keywords(query, [
                    "请受领任务", "请首领任务", "请收领任务",
                    "受领任务", "首领任务", "收领任务",
                    "艾武",
                    "秦翎"
                ])

                if ThinkingChainControllerV2._contains_keywords(query, ['搜索', '检索', '查询', '查找']):
                    logger.info(f"Calling K1 and F1 systems for search query: {query}")
                    return ThinkingChainControllerV2.query_k1_and_f1('艾武收到', query)
                else:
                    logger.info(f"Calling F1 system for analysis query: {query}")
                    return ThinkingChainControllerV2.query_f1('艾武收到', query, 'HTTP')
            else:
                # Handle FAQ response
                logger.info(f"Checking FAQ for query: {query}")
                response = FaqController.qa_get_by_question(query, 3)               
                filtered_answers = [
                    item for item in response if
                    float(item.get('scores', 1)) < FAQ_THRESHOLD and '艾武模式' in item.get('tags')
                ]
                if not filtered_answers:
                    
                    
                    # 如果配置了TOOL_AGENT_MODEL
                    if os.getenv('TOOL_AGENT_MODEL'):
                        logger.info("No matching FAQ found, using tool agent")
                        engine = ToolAgentEngine.get_instance()
                        response = await engine.process_query(query, history)
                        
                        if not response["success"]:
                            return jsonify({"answer": "对不起，执行任务过程中出现错误，请重试。", "active": "Text", "systemUrl": ""}), 200
                        
                        tool_call_info_formatted = ThinkingChainControllerV2._format_response_to_string(response)
                        return jsonify({"answer": response["final_answer"], "active": "Agent", "systemUrl": tool_call_info_formatted}), 200
                    
                    else: 
                        logger.info("No matching FAQ found, querying knowledge base")
                        return ThinkingChainControllerV2.query_knowledge_base(query, history)                                          
                else:
                    logger.info("Found matching FAQ, processing response")
                    # Deem most relevant (min score) faq as the determined action
                    min_score_answer = min(filtered_answers, key=lambda x: float(x['scores']))
                    active, answer_text, system_url = ThinkingChainControllerV2._determine_active_type(query,
                                                                                                     min_score_answer[
                                                                                                         'answer'])
                    logger.info(f"FAQ response -Answer: {answer_text} Active: {active}, systemUrl: {system_url}")
                    return jsonify({"answer": answer_text, "active": active, "systemUrl": system_url}), 200
        except Exception as e:
            # Log the exception and return an error response
            logger.error(">>> EXCEPTION >>>")
            logger.error(f"Error in thinking_chain: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            logger.error("<<< EXCEPTION <<<")
            return jsonify(
                {"answer": "对不起，执行任务过程中出现错误，请重试。", "active": "Text", "systemUrl": f"{e}"}), 200

    @staticmethod
    def query_knowledge_base(query: str, history: List[Dict[str, Any]]) -> Tuple[Response, int]:
        """
        Query the knowledge base with the provided query.

        :param query: User query.
        :param history: Conversation history.
        :return: JSON response.
        """
        logger = ThinkingChainControllerV2.logger
        logger.info(f"Querying knowledge base for: {query}")

        response, _ = ConfigurationController.get_configurations()
        config_data = response.get_json()
        logger.info("--------------------------------")
        logger.info("Environment配置:")
        
        # 获取Environment配置
        env_config = config_data.get('Environment', {})
        # 获取value列表
        env_values = env_config.get('value', [])
        
        # 根据环境变量选择配置
        current_config = {}
        logger.info(f"ENVIROMENT: {ENVIROMENT}")
        if ENVIROMENT == 'Production':
            current_config = next((env for env in env_values if env.get('name') == 'Production'), {})
        elif ENVIROMENT == 'Development':
            current_config = next((env for env in env_values if env.get('name') == 'Development'), {})
        
        # 提取配置值，设置默认值
        llm_url = current_config.get('LlmURL', '')
        llm_id = current_config.get('LlmId', 'glm-4-9b-chat')
        llm_tokens = current_config.get('LlmMaxTokens', '4096')
        
        logger.info(f"{ENVIROMENT}环境配置:")
        logger.info(f"LlmURL: {llm_url}")
        logger.info(f"LlmId: {llm_id}")
        logger.info(f"LlmMaxTokens: {llm_tokens}")
        logger.info("--------------------------------")
        
        kb_json_data = {
            "query": query,
            "mode": "local_kb",
            "kb_name": "aiwu",
            "top_k": 3,
            "score_threshold": 0.5,
            "history": history,
            "stream": "false",
            "model": llm_id,
            "temperature": 0.1,
            "max_tokens": int(llm_tokens),
            "prompt_name": "default",
            "return_direct": "false"
        }
        
        logger.info(">>> KB REQUEST >>>")
        logger.info(ThinkingChainControllerV2.format_json(kb_json_data))
        logger.info("<<< KB REQUEST <<<")
        
        kb_response = ProxyController.proxy_kb_chat(kb_json_data)
        
        if isinstance(kb_response, Response):
            kb_response = kb_response.get_json()
            
        logger.info(">>> KB RESPONSE >>>")
        logger.info(ThinkingChainControllerV2.format_json(kb_response))
        logger.info("<<< KB RESPONSE <<<")
        
        for choice in kb_response.get('choices', []):
            message = choice.get('message')
            if message:
                kb_response = message.get('content')
                break
        kb_response = re.sub(r'[\n*]', '', kb_response)
        kb_response = re.sub(r'[\W_&&[^。，、，？！；：．:;!?]]', ' ', kb_response)

        return jsonify({"answer": kb_response, "active": "LLM", "systemUrl": ""}), 200

    @staticmethod
    def query_vlm(image: str, query: str) -> Tuple[Response, int]:
        logger = ThinkingChainControllerV2.logger
        logger.info(f"Processing VLM request for query: {query}")
        
        vlm_json_data = {
            'model': VLM_IDS,
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': query
                        },
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': "data:image/png;base64," + image
                            }
                        }
                    ]
                }
            ],
            'stream': True,
            'max_tokens': 128000,
            'temperature': 0.1,
            'top_p': 0.2
        }

        logger.info(">>> VLM REQUEST >>>")
        logger.info(ThinkingChainControllerV2.format_json(vlm_json_data))
        logger.info("<<< VLM REQUEST <<<")

        vlm_response = HTTPClient().post("vlm_service", "/chat/completions", json=vlm_json_data)
        
        logger.info(">>> VLM RESPONSE >>>")
        logger.info(ThinkingChainControllerV2.format_json(vlm_response))
        logger.info("<<< VLM RESPONSE <<<")
        
        content = vlm_response['choices'][0]['message']['content']
        return jsonify({"answer": content, "active": "Text", "systemUrl": ""}), 200

    @staticmethod
    def query_f1(answer: str, query: str, method: str) -> Union[Tuple[Response, int], List[Dict[str, Any]]]:
        """
        Get information from the F1 system based on the query.

        :param answer: Default answer.
        :param query: User query.
        :param method: Method type ('HTTP' or 'Function').
        :return: JSON response or data list.
        """
        logger = ThinkingChainControllerV2.logger
        logger.info(f"Querying F1 system for: {query} (method: {method})")

        f1_json_data = {
            "message": query,
            "userName": "liuyu",
            "token": ACCESS_TOKEN,
            "topK": 10
        }

        logger.info(">>> F1 REQUEST >>>")
        logger.info(ThinkingChainControllerV2.format_json(f1_json_data))
        logger.info("<<< F1 REQUEST <<<")

        if RECOMMENDATION_SOURCE == 'internal':
            f1_response = HTTPClient().post("f1_service", "yhmd/chat/aiWuChat", json=f1_json_data)
        if RECOMMENDATION_SOURCE == 'external':
            f1_response = SystemRecommendationController.get_system_recommendation_by_description(json=f1_json_data)

        logger.info(">>> F1 RESPONSE >>>")
        logger.info(ThinkingChainControllerV2.format_json(f1_response))
        logger.info("<<< F1 RESPONSE <<<")

        # If f1_response is None or empty, return early
        if not f1_response:
            logger.warning("No response from F1 service")
            return ThinkingChainControllerV2._handle_no_data(method)

        pk_list = f1_response.get('data', {}).get('pk', [])
        xt_list = f1_response.get('data', {}).get('xt', [])
        cp_list = f1_response.get('data', {}).get('cp', [])
        mx_list = f1_response.get('data', {}).get('mx', [])

        combined_list = pk_list + xt_list + cp_list + mx_list

        # If combined_list is empty, return early
        if not combined_list:
            logger.warning("No data found in F1 response")
            return ThinkingChainControllerV2._handle_no_data(method)

        adjusted_list = ThinkingChainControllerV2._adjust_combined_list(combined_list, query)
        adjusted_list.sort(key=lambda x: x.get('score', 0), reverse=True)
        adjusted_list = adjusted_list[:5]

        first_system_name = adjusted_list[0]["mc"] if adjusted_list and isinstance(adjusted_list[0], dict) else None
        response_text = ThinkingChainControllerV2._get_response_text(query, first_system_name)

        if method == "HTTP":
            response = {
                "answer": response_text,
                "active": "Selection",
                "data": adjusted_list
            }
            logger.info(">>> F1 FINAL RESPONSE >>>")
            logger.info(ThinkingChainControllerV2.format_json(response))
            logger.info("<<< F1 FINAL RESPONSE <<<")
            return jsonify(response), 200
        else:
            return adjusted_list[:4]

    @staticmethod
    def query_k1_and_f1(answer: str, query: str) -> Tuple[Response, int]:
        """
        Get information from both K1 and F1 systems.

        :param answer: Default answer.
        :param query: User query.
        :return: JSON response.
        """
        logger = ThinkingChainControllerV2.logger
        logger.info(f"Querying K1 and F1 systems for: {query}")
        
        # query f1 with "in Function" call
        f1_data = ThinkingChainControllerV2.query_f1(answer, query, "Function")
        if not f1_data:
            logger.warning("No data from F1 service")
            f1_data = []

        # query k1
        k1_params = {"text": query}
        logger.info(">>> K1 REQUEST >>>")
        logger.info(ThinkingChainControllerV2.format_json(k1_params))
        logger.info("<<< K1 REQUEST <<<")
        
        k1_response = HTTPClient().get(
            "k1_service",
            "/center-data/magic-api/api/data-service/superSearchByCenterDataV",
            params=k1_params
        )

        logger.info(">>> K1 RESPONSE >>>")
        logger.info(ThinkingChainControllerV2.format_json(k1_response))
        logger.info("<<< K1 RESPONSE <<<")

        # Deem K1 as a card of F1 and rerank together
        k1_card_name = "数据查询检索引擎"
        f1_data.append({
            "fcmc": "K2可视化分析系统",
            "mc": k1_card_name,
            # "ms": "搜索、检索、查询、查找数据，搜索、检索、查询、查找数据集，搜索、检索、查询、查找数据产品，并返回检索到的数据。",
            "ms": "使用数据搜索引擎搜索：" + query,
            "type": "检索",
            "score": 0,
            "url": k1_response.get('data', "")
        })

        documents = [item['ms'] for item in f1_data]
        rerank_results = RerankUtils.rerank(query, documents)

        if not rerank_results:
            logger.warning("No rerank results found")
            return jsonify({"answer": "未查询到对应的系统或配块", "active": "Text", "systemUrl": ""}), 200

        sorted_data = []
        for result in rerank_results['results']:
            index = result['index']
            f1_data[index]['score'] = result['relevance_score']
            sorted_data.append(f1_data[index])

        sorted_data.sort(key=lambda x: x['score'], reverse=True)
        for item in sorted_data:
            if item['mc'] == k1_card_name:
                item['ms'] = query
                break

        first_system_name = sorted_data[0]["mc"] if sorted_data and isinstance(sorted_data[0], dict) else None
        response_text = ThinkingChainControllerV2._get_response_text(query, first_system_name)

        response = {
            "answer": response_text,
            "active": "Selection",
            "data": sorted_data
        }
        
        logger.info(">>> K1 AND F1 FINAL RESPONSE >>>")
        logger.info(ThinkingChainControllerV2.format_json(response))
        logger.info("<<< K1 AND F1 FINAL RESPONSE <<<")
        
        return jsonify(response), 200

    @staticmethod
    def query_rerank(query: str, documents: List[str]) -> Dict[str, Any]:
        """
        Get rerank results based on the query and documents.

        :param query: User query.
        :param documents: List of document strings.
        :return: Rerank response.
        """
        rerank_json_data = {
            "model": "bge-reranker-v2-m3-local",
            "query": query,
            "documents": documents
        }
        return HTTPClient().post("rerank_service", "/v1/rerank", json=rerank_json_data)

    @staticmethod
    def _handle_no_data(method: str) -> Union[Tuple[Response, int], List]:
        """
        Handle the scenario where no data is returned from F1 service.

        :param method: Method type ('HTTP' or 'Function').
        :return: JSON response or empty list.
        """
        if method == "HTTP":
            return jsonify({
                "answer": "未查询到对应的系统或配块",
                "active": "Text",
                "systemUrl": ""
            }), 200
        else:
            return []

    @staticmethod
    def _get_response_text(query: str, first_system_name: Optional[str] = None) -> str:
        """
        Get response text from FAQ or default.

        :param method: string.
        :return: answer_text from FAQ or default.
        """
        response = FaqController.qa_get_by_question(query, 3)
        filtered_answers = [
            item for item in response if float(item.get('scores', 1)) < FAQ_THRESHOLD and '艾武模式' in item.get('tags')
        ]

        if first_system_name:
            first_system_name = re.sub(r'^\w\d', '', first_system_name) if re.search(r'^\w\d',
                                                                                     first_system_name) else first_system_name

        if not filtered_answers:
            confirm_text_list = [f"是否要进入{first_system_name}，请确认", f"是否要进入{first_system_name}，请指示",
                                 f"为您推荐{first_system_name}，请指示", f"为您推荐{first_system_name}，请确认"]
            default_text_list = ["已为您准备好，请选择。", "已为您推荐，请选择。", "已推荐，请指示", "已准备好，请指示"]
            combined_list = confirm_text_list + default_text_list if first_system_name else default_text_list
            return secrets.choice(combined_list)
        else:
            # Deem most relevant (min score) faq as the determined action
            min_score_answer = min(filtered_answers, key=lambda x: float(x['scores']))
            answer_text = min_score_answer['answer']

            first_bracket_index = answer_text.find('[')
            if first_bracket_index != -1:
                answer_text = answer_text[:first_bracket_index]

            # 使用正则表达式移除末尾括号以及括号内的内容
            return answer_text

    @staticmethod
    def _adjust_combined_list(combined_list: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        Adjust the combined list from F1 response for the response.

        :param combined_list: List of items from F1 response.
        :return: Adjusted list of items.
        """
        adjusted_list = []
        for item in combined_list:
            adjusted_item = {
                "fcmc": item.get('fcmc', ""),
                "mc": item.get('mc', ""),
                "ms": item.get('ms', ""),
                "type": item.get('type', ""),
                "score": item.get('score', 0),
                "url": "",
                "constructed_url": ""
            }

            if item.get('type') == "系统":
                if "系统" not in adjusted_item['mc'] and "平台" not in adjusted_item['mc']:
                    adjusted_item['mc'] += "系统"
                if RECOMMENDATION_SOURCE == 'internal':
                    adjusted_item['url'] = ThinkingChainControllerV2._construct_cas_silent_login_url(
                        item.get('xtUrl', ""),
                        adjusted_item['mc'],
                        query
                    )
                if RECOMMENDATION_SOURCE == 'external':
                    adjusted_item['url'] = item.get('xtUrl', "")    

            elif item.get('type') == "配块": # type == "配块"
                if "配块" not in adjusted_item['mc']:
                    adjusted_item['mc'] += "配块"
                pk_url = item.get('pkUrl')
                xt_url = item.get('xtUrl')
                city = item.get('city')
                bm = item.get('bm')

                if pk_url:
                    adjusted_item['url'] = pk_url
                elif xt_url and RECOMMENDATION_SOURCE == 'internal':
                    adjusted_item['url'] = f"{xt_url}?query={city}&pkbm={bm}"
                elif xt_url and RECOMMENDATION_SOURCE == 'external':
                    adjusted_item['url'] = xt_url
                else:
                    adjusted_item['url'] = ''
            elif item.get('type') == "模型":
                if "模型" not in adjusted_item['mc']:
                    adjusted_item['mc'] += "模型"
                    adjusted_item['url'] = item.get('xtUrl', "")

            elif item.get('type') == "产品":
                if "产品" not in adjusted_item['mc']:
                    adjusted_item['mc'] += "产品"
                    adjusted_item['url'] = item.get('xtUrl', "")

            adjusted_list.append(adjusted_item)
        return adjusted_list

    @staticmethod
    def _contains_keywords(text: str, keywords: List[str]) -> bool:
        """
        Check if any of the keywords are present in the text.

        :param text: Text to search.
        :param keywords: List of keywords.
        :return: True if any keyword is found, else False.
        """
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _remove_keywords(text: str, keywords: List[str]) -> str:
        """
        Remove specified keywords from the text.

        :param text: Original text.
        :param keywords: List of keywords to remove.
        :return: Cleaned text.
        """
        pattern = r'(?s)(?:\s*(' + '|'.join(map(re.escape, keywords)) + r')\s*[' + re.escape('，。') + r']?\s*)+'
        return re.sub(pattern, '', text).strip()

    @staticmethod
    def _determine_active_type(query: str, answer_text: str) -> Tuple[str, str, str]:
        """
        Determine the active type based on the answer text.

        :param answer_text: Text of the answer.
        :return: Active type as a string.
        """
        if '再见' in answer_text:
            return 'Quit', answer_text, ""
        elif '[Video]' in answer_text:
            start_index = answer_text.index("[Video]")
            colon_index = answer_text.index(":", start_index)
            system_url = answer_text[colon_index + 1:].strip()
            modified_answer_text = answer_text[:start_index].strip()
            return 'Video', modified_answer_text, system_url
        elif "[SystemLink]" in answer_text:
            start_index = answer_text.index("[SystemLink]")
            colon_index = answer_text.index(":", start_index)
            system_url = answer_text[colon_index + 1:].strip()
            modified_answer_text = answer_text[:start_index].strip()
            return 'SystemLink', modified_answer_text, system_url
        elif "[WebURL]" in answer_text:
            start_index = answer_text.index("[WebURL]")
            colon_index = answer_text.index(":", start_index)
            system_url = answer_text[colon_index + 1:].strip()
            modified_answer_text = answer_text[:start_index].strip()
            return 'WebURL', modified_answer_text, system_url
        elif "[PPT]" in answer_text:
            start_index = answer_text.index("[PPT]")
            colon_index = answer_text.index(":", start_index)
            system_url = answer_text[colon_index + 1:].strip()
            modified_answer_text = answer_text[:start_index].strip()
            return 'PPT', modified_answer_text, system_url
        else:
            return 'Text', answer_text, ""

    @staticmethod
    def _construct_cas_silent_login_url(service_url: str, service_name: str, query: str) -> str:
        """
        Constructs the CAS silent login url

        :param service_url: The input url.
        :return: Contructed url.
        """
        if not service_url:
            return ""

        if service_url.endswith("/"):
            service_url = service_url.rstrip('/')

        base_64_query_str = ThinkingChainControllerV2._string_to_base64(query)

        if SILENT_LOGIN_CAS_URL not in service_url:
            if service_name.startswith("A5"):
                service_url_with_query = f"{service_url}/analysis?userMsg={base_64_query_str}"

                return service_url_with_query
            elif service_name.startswith("C1"):
                return f"{SILENT_LOGIN_CAS_URL}?service={SILENT_LOGIN_C1_PORTAL_URL}&token={ACCESS_TOKEN}"
            elif service_name.startswith("T") or service_name.startswith("B"):
                if "?" not in service_url:
                    service_url_with_query = f"{service_url}?userMsg={query}"
                else:
                    service_url_with_query = f"{service_url}&userMsg={query}"
                return f"{SILENT_LOGIN_CAS_URL}?service={service_url_with_query}&token={ACCESS_TOKEN}"
            elif service_name.startswith("D1") or service_name.startswith("D2"):
                splited_url_list = service_url.split('#')

                return (
                    f"{SILENT_LOGIN_CAS_URL}?service={splited_url_list[0]}"
                    f"?userMsg={base_64_query_str}#{splited_url_list[1]}&token={ACCESS_TOKEN}"
                )
            elif service_name.startswith("艾"):
                return service_url
            else:
                return f"{SILENT_LOGIN_CAS_URL}?service={service_url}&token={ACCESS_TOKEN}"

        return f"{service_url}&token={ACCESS_TOKEN}"

    @staticmethod
    def _format_response_to_string(response: Dict[str, Any]) -> str:
        """将响应转换为可读的字符串格式"""
        formatted_text = ""
        
        if response["tool_name"] and isinstance(response["tool_name"], list) and len(response["tool_name"]) > 0:
            formatted_text += "工具调用信息:\n"
            
            for i in range(len(response["tool_name"])):
                if i > 0:
                    formatted_text += "\n\n"  # 在多个工具调用之间添加空行分隔
                
                formatted_text += f"工具调用 #{i+1}:\n"
                formatted_text += f"- 工具名称: {response['tool_name'][i]}\n"
                
                # 格式化工具参数
                if i < len(response["tool_args"]):
                    formatted_text += f"- 工具参数: {json.dumps(response['tool_args'][i], ensure_ascii=False, indent=2)}\n"
                else:
                    formatted_text += "- 工具参数: 无参数\n"
                
                # 格式化工具返回值
                if i < len(response["tool_response"]):
                    formatted_text += (
                        f"- 工具返回: "
                        f"{json.dumps(response['tool_response'][i], ensure_ascii=False, indent=2)}"
                    )
                else:
                    formatted_text += "- 工具返回: 无返回值"
            
        return formatted_text

    @staticmethod
    def _string_to_base64(input_string: str) -> str:


        # 使用 base64 编码
        encoded_base64 = base64.b64encode(input_string.encode('utf-8')).decode('utf-8')
        # 替换 '+' 和 '_' 符号后进行 URL 编码
        encoded_url_safe = urllib.parse.quote_plus(encoded_base64.replace('+', '-').replace('/', '_'))
        return encoded_url_safe
        