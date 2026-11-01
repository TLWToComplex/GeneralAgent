"""
Tool agent module.
Core implementation of the tool agent for executing various tools and functions.
"""
import os
import importlib
import inspect
import json
import httpx
import logging

from typing import List, Dict, Any
from src.utils.process_history import process_history

class ToolAgent:
    def __init__(
        self, 
        api_key: str, 
        model: str = "Qwen/Qwen2.5-7B-Instruct", 
        base_url: str = "https://api.siliconflow.cn/v1", 
        max_tokens: int = 10000
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.tools: List[Dict[str, Any]] = []
        self.functions: Dict[str, Any] = {}
        
        # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
    async def load_tools(self, tools_folder: str) -> None:
        """加载指定文件夹中的所有工具函数"""
        tools_path = os.path.join(os.path.dirname(__file__), tools_folder)
        if not os.path.exists(tools_path):
            raise ValueError(f"Tools folder {tools_folder} does not exist")
            
        for file in os.listdir(tools_path):
            if file.endswith('.py') and not file.startswith('__'):
                module_name = file[:-3]
                module = importlib.import_module(f"core.tool_agent.{tools_folder}.{module_name}")
                
                for name, obj in inspect.getmembers(module):
                    # 检查是否是被@tool装饰器标记的函数
                     if inspect.iscoroutinefunction(obj) and not name.startswith('_'):
                        # 获取函数文档字符串
                        description = inspect.getdoc(obj) or ""
                        
                        # 获取函数参数
                        params = inspect.signature(obj).parameters
                        properties = {}
                        required = []
                        
                        for param_name, param in params.items():
                            if param_name == 'self':
                                continue
                                
                            param_doc = inspect.getdoc(obj)
                            param_description = ""
                            if param_doc:
                                # 从文档字符串中提取参数描述
                                for line in param_doc.split('\n'):
                                    if line.strip().startswith(f":param {param_name}:"):
                                        param_description = line.split(':', 2)[-1].strip()
                                        
                            properties[param_name] = {
                                "type": "string",  # 默认类型，可以根据需要扩展
                                "description": param_description
                            }
                            
                            if param.default == inspect.Parameter.empty:
                                required.append(param_name)
                                
                        # 构建工具schema
                        tool_schema = {
                            "type": "function",
                            "function": {
                                "name": name,
                                "description": description,
                                "parameters": {
                                    "type": "object",
                                    "properties": properties,
                                    "required": required
                                }
                            }
                        }
                        
                        self.tools.append(tool_schema)
                        self.functions[name] = obj
                        self.logger.info(f"已加载工具函数: {name}")
                        
    async def _call_llm(
        self, 
        messages: List[Dict[str, Any]], 
        stream: bool = False, 
        call_type: str = "unknown"
    ) -> Dict[str, Any]:
        """使用模型API直接发送请求"""
        
        # 准备请求数据
        payload = {
            "model": self.model,
            "messages": messages,
            "tool_choice": "auto",
            "tools": self.tools,
            "stream": stream,
            "temperature": 0.1,
            "max_tokens": self.max_tokens
        }
        
        # 记录请求入参
        self.logger.info(f"[{call_type}] 模型调用入参: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        # 创建请求头
        headers = {
            "Content-Type": "application/json",
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # 发送异步请求
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=300.0
                )
                
                # 检查响应状态
                if response.status_code == 200:
                    response_data = response.json()
                    # 记录响应结果
                    self.logger.info(f"[{call_type}] 模型调用返回: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
                    return response_data
                else:
                    error_msg = f"Model API returned {response.status_code}: {response.text}"
                    self.logger.error(f"[{call_type}] 调用失败: {error_msg}")
                    return {"error": error_msg}
            except Exception as e:
                error_msg = f"Error calling model API: {str(e)}"
                self.logger.error(f"[{call_type}] 异常: {error_msg}")
                return {"error": error_msg}
            
    async def run(self, query: str, history: List[Dict[str, str]]) -> Dict[str, Any]:
        """运行工具代理"""
        shorttend_history = process_history(history)
        messages = shorttend_history + [{"role": "user", "content": query}]
        
        # 初始化返回结果
        result = {
            "final_answer": "",
            "tool_name": [],
            "tool_args": [],
            "tool_response": [],
            "success": False
        }
        
        # 第一步：获取模型推荐的函数调用
        response = await self._call_llm(messages, stream=False, call_type="第一次调用")
        
        # 处理OpenAI格式响应
        if "choices" in response and len(response["choices"]) > 0:
            choice = response["choices"][0]
            
            # 检查是否有工具调用
            if choice.get("finish_reason") == "tool_calls" and "message" in choice and "tool_calls" in choice["message"]:
                # 处理函数调用
                for tool_call in choice["message"]["tool_calls"]:
                    function_name = tool_call["function"]["name"]
                    arguments = json.loads(tool_call["function"]["arguments"])
                    
                    # 记录工具调用信息
                    result["tool_name"].append(function_name)
                    result["tool_args"].append(arguments)
                    
                    # 执行函数
                    function_result = await self.functions[function_name](**arguments)
                    result["tool_response"].append(function_result)
                    
                    # 添加函数调用结果到消息历史
                    messages.append({
                        "role": "assistant",
                        "content": choice["message"].get("content", ""),
                        "tool_calls": [tool_call]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(function_result, ensure_ascii=False)
                    })
                
                # 第二步：获取最终回复
                final_response = await self._call_llm(messages, call_type="第二次调用")
                
                # 处理最终回复OpenAI格式
                if "choices" in final_response and len(final_response["choices"]) > 0:
                    result["final_answer"] = final_response["choices"][0]["message"]["content"]
                    result["success"] = True
                elif "content" in final_response:
                    result["final_answer"] = final_response["content"]
                    result["success"] = True
                else:
                    result["final_answer"] = "无法获取有效回复"
            
            # 如果没有工具调用，直接返回内容
            elif "message" in choice and "content" in choice["message"]:
                result["final_answer"] = choice["message"]["content"]
                result["success"] = True
        
        # 无法解析的情况
        if not result["final_answer"]:
            result["final_answer"] = "无法解析模型响应"
            
        return result
