"""
对话摘要中间件 - 用于压缩长对话历史
当对话轮数超过阈值时，自动将早期对话压缩为摘要
"""
from typing import Dict, Any, List
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
import logging

logger = logging.getLogger(__name__)


class AutoSummaryMiddleware(AgentMiddleware):
    """自动对话摘要中间件
    
    当对话消息数量超过 max_turns * 2（因为每轮包含 user + assistant）时，
    将早期的对话压缩为摘要，保留最近的几轮对话原文。
    """
    
    def __init__(self, llm: BaseChatModel, max_turns: int = 20, keep_recent_turns: int = 5):
        """
        Args:
            llm: 用于生成摘要的语言模型
            max_turns: 最大对话轮数阈值（超过此值开始压缩）
            keep_recent_turns: 保留最近多少轮对话不压缩
        """
        self.llm = llm
        self.max_messages = max_turns * 2  # 每轮包含 user + assistant
        self.keep_recent_messages = keep_recent_turns * 2  # 保留最近的消息数
        
    def before_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """在 agent 执行前处理消息，进行对话压缩"""
        messages = state.get("messages", [])
        
        if not messages or len(messages) <= self.max_messages:
            # 消息数量未超限，无需压缩
            logger.debug(f"对话消息数 {len(messages)} 未超过阈值 {self.max_messages}，无需压缩")
            return {}
        
        logger.info(f"对话消息数 {len(messages)} 超过阈值 {self.max_messages}，开始压缩...")
        logger.info(f"配置参数: max_turns={int(self.max_messages/2)}, keep_recent_turns={int(self.keep_recent_messages/2)}")
        
        try:
            # 分离系统消息、待压缩消息和保留消息
            system_messages = [msg for msg in messages if isinstance(msg, SystemMessage)]
            non_system_messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]
            
            # 保留最近的消息
            recent_messages = non_system_messages[-self.keep_recent_messages:]
            # 需要压缩的消息
            old_messages = non_system_messages[:-self.keep_recent_messages]
            
            if not old_messages:
                return {}
            
            # 生成摘要
            summary = self._generate_summary(old_messages)
            
            # 创建摘要消息
            summary_message = HumanMessage(
                content=f"[之前的对话摘要]\n{summary}\n[继续当前对话]"
            )
            
            # 重组消息：系统消息 + 摘要 + 最近的消息
            compressed_messages = system_messages + [summary_message] + recent_messages
            
            logger.info(f"对话压缩完成: {len(old_messages)} 条消息 -> 1 条摘要，保留 {len(recent_messages)} 条最近消息")
            logger.info(f"压缩前总消息数: {len(messages)}, 压缩后总消息数: {len(compressed_messages)}")
            logger.info(f"摘要内容预览: {summary}...")
            
            return {"messages": compressed_messages}
            
        except Exception as e:
            logger.error(f"对话压缩失败: {e}", exc_info=True)
            # 压缩失败时返回空字典，不影响原有流程
            return {}
    
    def _generate_summary(self, messages: List[BaseMessage]) -> str:
        """使用 LLM 生成对话摘要"""
        # 构建摘要提示词
        conversation_text = "\n".join([
            f"{'用户' if isinstance(msg, HumanMessage) else '助手'}: {msg.content}"
            for msg in messages[:50]  # 限制最多处理 50 条消息，避免 token 过多
        ])
        
        summary_prompt = f"""请对以下对话内容进行简洁的摘要总结，保留关键信息和上下文：

{conversation_text}

摘要："""
        
        # 调用 LLM 生成摘要
        response = self.llm.invoke([HumanMessage(content=summary_prompt)])
        
        return response.content.strip()