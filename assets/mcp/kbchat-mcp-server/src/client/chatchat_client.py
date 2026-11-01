import httpx
import json
import logging
from typing import Dict, Any, List, Optional, Union
from src.config import ChatChatConfig

logger = logging.getLogger("chatchat_server")

class ChatChatAPIError(Exception):
    """ChatChat API错误"""
    pass

class ChatChatClient:
    """ChatChat API客户端"""
    
    def __init__(self):
        self.base_url = ChatChatConfig.API_BASE_URL
        self.timeout = ChatChatConfig.API_TIMEOUT
        
    async def search_docs(
        self,
        query: str,
        knowledge_base_name: Union[str, List[str]],
        top_k: int = 3,
        score_threshold: float = 0.5,
        file_name: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索知识库文档
        
        Args:
            query: 查询文本
            knowledge_base_name: 知识库名称或知识库名称列表
            top_k: 返回结果数量
            score_threshold: 相似度阈值
            file_name: 文件名过滤（可选）
            metadata: 元数据过滤（可选）
            
        Returns:
            搜索结果列表
            
        Raises:
            ChatChatAPIError: API调用失败时抛出
        """
        url = ChatChatConfig.get_search_docs_url()
        
        payload = {
            "query": query,
            "knowledge_base_name": knowledge_base_name,
            "top_k": top_k,
            "score_threshold": score_threshold,
            "file_name": file_name,
            "metadata": metadata or {}
        }
        
        logger.debug(f"调用search_docs API: {url}")
        logger.debug(f"请求参数: {payload}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code != 200:
                    error_msg = f"API调用失败: HTTP {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f" - {error_detail}"
                    except:
                        error_msg += f" - {response.text}"
                    
                    logger.error(error_msg)
                    raise ChatChatAPIError(error_msg)
                
                result = response.json()
                logger.debug(f"API响应: {len(result)}个结果")
                return result
                
        except httpx.TimeoutException:
            error_msg = f"API调用超时 (>{self.timeout}秒)"
            logger.error(error_msg)
            raise ChatChatAPIError(error_msg)
        except httpx.RequestError as e:
            error_msg = f"API请求错误: {str(e)}"
            logger.error(error_msg)
            raise ChatChatAPIError(error_msg)
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            logger.error(error_msg)
            raise ChatChatAPIError(error_msg)
    
    async def list_knowledge_bases(self) -> List[Dict[str, Any]]:
        """
        获取知识库列表
        
        Returns:
            知识库列表
            
        Raises:
            ChatChatAPIError: API调用失败时抛出
        """
        url = ChatChatConfig.get_list_knowledge_bases_url()
        
        logger.debug(f"调用list_knowledge_bases API: {url}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                
                if response.status_code != 200:
                    error_msg = f"API调用失败: HTTP {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f" - {error_detail}"
                    except:
                        error_msg += f" - {response.text}"
                    
                    logger.error(error_msg)
                    raise ChatChatAPIError(error_msg)
                
                result = response.json()
                
                # 提取data字段中的知识库列表
                if isinstance(result, dict) and "data" in result:
                    knowledge_bases = result["data"]
                else:
                    knowledge_bases = result
                
                logger.debug(f"获取到{len(knowledge_bases)}个知识库")
                return knowledge_bases
                
        except httpx.TimeoutException:
            error_msg = f"API调用超时 (>{self.timeout}秒)"
            logger.error(error_msg)
            raise ChatChatAPIError(error_msg)
        except httpx.RequestError as e:
            error_msg = f"API请求错误: {str(e)}"
            logger.error(error_msg)
            raise ChatChatAPIError(error_msg)
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            logger.error(error_msg)
            raise ChatChatAPIError(error_msg)

# 全局客户端实例
_client_instance = None

def get_chatchat_client() -> ChatChatClient:
    """获取ChatChat客户端实例（单例模式）"""
    global _client_instance
    if _client_instance is None:
        _client_instance = ChatChatClient()
    return _client_instance