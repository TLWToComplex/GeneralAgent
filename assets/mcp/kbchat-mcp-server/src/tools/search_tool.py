import json
import logging
from typing import Any, Dict, Optional
from mcp.server.fastmcp import FastMCP
from src.client.chatchat_client import get_chatchat_client
from src.config import SecurityConfig
from .base_tool import BaseToolMixin

logger = logging.getLogger("chatchat_server")

def register_search_tools(mcp: FastMCP):
    """
    注册知识库搜索工具到MCP服务器
    
    Args:
        mcp: FastMCP服务器实例
    """
    logger.debug("注册知识库搜索工具...")
    
    @mcp.tool()
    @BaseToolMixin.handle_api_error
    async def search_knowledge_base(
        query: str,
        knowledge_base_name: str,
        top_k: int = 3,
        score_threshold: float = 0.2,
        file_name: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        在指定的知识库中检索相关的文档片段。

        注意：
        1. knowledge_base_name 必须来自 list_knowledge_bases 工具。
        2. 支持跨库搜索：若需同时检索多个库，请用逗号分隔，例如 "kb1,kb2,kb3"。
        3. score_threshold 越高，结果越精准但数量越少（1.0为完全一致）。
        
        Args:
            query: 用户的自然语言查询文本
            knowledge_base_name: 目标知识库名称或知识库名称列表 (逗号分隔，如: "kb1,kb2,kb3")
            top_k: 召回最相关的文档片段数量 (默认3，建议范围 3-10)
            score_threshold: 相似度阈值 (0.0-1.0，默认0.2)
            file_name: 文件名过滤 (可选)
            metadata: 元数据过滤 (可选)
            
        Returns:
            搜索结果的JSON字符串
        """
        # 简化日志：只记录输入请求
        logger.info(f"输入请求 - 知识库: {knowledge_base_name}, 查询: {query[:100]}{'...' if len(query) > 100 else ''}")
        
        # 参数验证
        validation = SecurityConfig.validate_query_params(query, top_k, score_threshold)
        if not validation["valid"]:
            error_response = BaseToolMixin.format_error_response(
                "; ".join(validation["errors"]),
                "ValidationError"
            )
            logger.info(f"输出响应 - 参数验证失败: {validation['errors']}")
            return error_response

        # 解析知识库名称列表
        kb_names = [name.strip() for name in knowledge_base_name.split(",") if name.strip()]
        if not kb_names:
            error_response = BaseToolMixin.format_error_response(
                "至少需要指定一个知识库名称",
                "ValidationError"
            )
            logger.info("输出响应 - 知识库名称为空")
            return error_response
        
        # 获取客户端并执行搜索
        client = get_chatchat_client()
        results = await client.search_docs(
            query=query,
            knowledge_base_name=kb_names,
            top_k=top_k,
            score_threshold=score_threshold,
            file_name=file_name,
            metadata=metadata
        )
        
        # 添加元数据信息
        metadata_info = {
            "query": query,
            "knowledge_base": knowledge_base_name,
            "top_k": top_k,
            "score_threshold": score_threshold,
            "result_count": len(results),
            "file_filter": file_name if file_name else None
        }
        
        response = BaseToolMixin.format_success_response(results, metadata_info)
        
        # Token验证
        token_validation = SecurityConfig.validate_output_tokens(response)
        if not token_validation["valid"]:
            error_response = BaseToolMixin.format_error_response(
                token_validation["error"],
                "TokenLimitExceeded"
            )
            logger.info(f"输出响应 - Token超限: {token_validation['estimated_tokens']}/{token_validation['max_tokens']}")
            return error_response
        
        # 简化日志：只记录输出结果概要
        logger.info(f"输出响应 - 成功搜索 {len(kb_names)} 个知识库, 成功返回 {len(results)} 个结果, Token数: {token_validation['estimated_tokens']}")
        
        return response
    
    @mcp.tool()
    @BaseToolMixin.handle_api_error
    async def list_knowledge_bases(dummy_param: Optional[str] = None) -> str:
        """
        列出系统中所有可用的知识库名称及其基本信息。
        当你不知道该查询哪个具体的知识库，或者用户提到的知识库名称不明确时，必须首先调用此工具。
        返回结果包含可用的知识库列表 available_knowledge_bases，后续搜索工具需使用此列表中的一个或多个知识库进行搜索。
        
        Args:
            dummy_param: 虚拟参数，用于防止空参数调用报错 设置为null即可
            
        Returns:
            知识库列表的JSON字符串
        """
        logger.info("输入请求 - 获取知识库列表")
        
        # 获取客户端并执行查询
        client = get_chatchat_client()
        knowledge_bases = await client.list_knowledge_bases()
        
        # 添加元数据信息
        metadata_info = {
            "total_count": len(knowledge_bases),
            "available_knowledge_bases": [kb.get("kb_name", "unknown") for kb in knowledge_bases]
        }
        
        response = BaseToolMixin.format_success_response(knowledge_bases, metadata_info)
        
        # Token验证
        token_validation = SecurityConfig.validate_output_tokens(response)
        if not token_validation["valid"]:
            error_response = BaseToolMixin.format_error_response(
                token_validation["error"],
                "TokenLimitExceeded"
            )
            logger.info(f"输出响应 - Token超限: {token_validation['estimated_tokens']}/{token_validation['max_tokens']}")
            return error_response
        
        logger.info(f"输出响应 - 成功返回 {len(knowledge_bases)} 个知识库, Token数: {token_validation['estimated_tokens']}")
        
        return response
    
    # @mcp.tool()
    # @BaseToolMixin.handle_api_error
    # async def search_multiple_knowledge_bases(
    #     query: str,
    #     knowledge_base_names: str,  # 逗号分隔的知识库名称
    #     top_k: int = 3,
    #     score_threshold: float = 0.5
    # ) -> str:
    #     """
    #     在多个知识库中搜索相关文档
    #
    #     Args:
    #         query: 搜索查询文本
    #         knowledge_base_names: 知识库名称列表 (逗号分隔，如: "kb1,kb2,kb3")
    #         top_k: 每个知识库返回结果数量 (默认3，最大50)
    #         score_threshold: 相似度阈值 (0.0-1.0，默认0.2)
    #
    #     Returns:
    #         搜索结果的JSON字符串
    #     """
    #     logger.info(f"输入请求 - 多知识库搜索: {knowledge_base_names}, 查询: {query[:100]}{'...' if len(query) > 100 else ''}")
    #
    #     # 参数验证
    #     validation = SecurityConfig.validate_query_params(query, top_k, score_threshold)
    #     if not validation["valid"]:
    #         error_response = BaseToolMixin.format_error_response(
    #             "; ".join(validation["errors"]),
    #             "ValidationError"
    #         )
    #         logger.info(f"输出响应 - 参数验证失败: {validation['errors']}")
    #         return error_response
    #
    #     # 解析知识库名称列表
    #     kb_names = [name.strip() for name in knowledge_base_names.split(",") if name.strip()]
    #     if not kb_names:
    #         error_response = BaseToolMixin.format_error_response(
    #             "至少需要指定一个知识库名称",
    #             "ValidationError"
    #         )
    #         logger.info("输出响应 - 知识库名称为空")
    #         return error_response
    #
    #     # 获取客户端
    #     client = get_chatchat_client()
    #
    #     # 并发搜索所有知识库
    #     all_results = {}
    #     total_results = 0
    #
    #     for kb_name in kb_names:
    #         try:
    #             results = await client.search_docs(
    #                 query=query,
    #                 knowledge_base_name=kb_name,
    #                 top_k=top_k,
    #                 score_threshold=score_threshold
    #             )
    #             all_results[kb_name] = {
    #                 "results": results,
    #                 "count": len(results)
    #             }
    #             total_results += len(results)
    #             # 不再记录每个知识库的详细结果
    #             pass
    #         except Exception as e:
    #             all_results[kb_name] = {
    #                 "error": str(e),
    #                 "count": 0
    #             }
    #             # 简化错误日志
    #             pass
    #
    #     # 添加元数据信息
    #     metadata_info = {
    #         "query": query,
    #         "searched_knowledge_bases": kb_names,
    #         "top_k_per_kb": top_k,
    #         "score_threshold": score_threshold,
    #         "total_results": total_results,
    #         "successful_searches": len([kb for kb, data in all_results.items() if "error" not in data])
    #     }
    #
    #     response = BaseToolMixin.format_success_response(all_results, metadata_info)
    #
    #     # Token验证
    #     token_validation = SecurityConfig.validate_output_tokens(response)
    #     if not token_validation["valid"]:
    #         error_response = BaseToolMixin.format_error_response(
    #             token_validation["error"],
    #             "TokenLimitExceeded"
    #         )
    #         logger.info(f"输出响应 - Token超限: {token_validation['estimated_tokens']}/{token_validation['max_tokens']}")
    #         return error_response
    #
    #     logger.info(f"输出响应 - 成功搜索 {len(kb_names)} 个知识库, 总结果数: {total_results}, Token数: {token_validation['estimated_tokens']}")
    #
    #     return response