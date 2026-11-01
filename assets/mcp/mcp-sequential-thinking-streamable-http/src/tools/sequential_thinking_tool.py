import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from colorama import Fore, Style, init
import sys

from src.config import SecurityConfig, LogConfig

# 初始化colorama以支持Windows终端颜色
init()

logger = logging.getLogger("sequential_thinking_server")

@dataclass
class ThoughtData:
    """思考数据结构"""
    thought: str
    thought_number: int
    total_thoughts: int
    next_thought_needed: bool
    is_revision: Optional[bool] = None
    revises_thought: Optional[int] = None
    branch_from_thought: Optional[int] = None
    branch_id: Optional[str] = None
    needs_more_thoughts: Optional[bool] = None

class SequentialThinkingTool:
    """Sequential Thinking工具实现"""
    
    def __init__(self):
        self.thought_history: List[ThoughtData] = []
        self.branches: Dict[str, List[ThoughtData]] = {}
        self.disable_thought_logging = LogConfig.DISABLE_THOUGHT_LOGGING
        
    def validate_thought_data(self, input_data: Dict[str, Any]) -> ThoughtData:
        """验证并转换输入数据为ThoughtData对象"""
        
        # 验证必需字段
        if not input_data.get('thought') or not isinstance(input_data['thought'], str):
            raise ValueError('Invalid thought: must be a string')
            
        if not isinstance(input_data.get('thoughtNumber'), int):
            raise ValueError('Invalid thoughtNumber: must be an integer')
            
        if not isinstance(input_data.get('totalThoughts'), int):
            raise ValueError('Invalid totalThoughts: must be an integer')
            
        if not isinstance(input_data.get('nextThoughtNeeded'), bool):
            raise ValueError('Invalid nextThoughtNeeded: must be a boolean')
        
        # 使用安全配置验证参数
        validation_result = SecurityConfig.validate_thought_params(
            input_data['thought'],
            input_data['thoughtNumber'],
            input_data['totalThoughts']
        )
        
        if not validation_result['valid']:
            raise ValueError(f"Validation errors: {', '.join(validation_result['errors'])}")
        
        # 创建ThoughtData对象
        thought_data = ThoughtData(
            thought=input_data['thought'],
            thought_number=input_data['thoughtNumber'],
            total_thoughts=validation_result['total_thoughts'],  # 使用验证后的值
            next_thought_needed=input_data['nextThoughtNeeded'],
            is_revision=input_data.get('isRevision'),
            revises_thought=input_data.get('revisesThought'),
            branch_from_thought=input_data.get('branchFromThought'),
            branch_id=input_data.get('branchId'),
            needs_more_thoughts=input_data.get('needsMoreThoughts')
        )
        
        return thought_data
    
    def format_thought(self, thought_data: ThoughtData) -> str:
        """格式化思考内容用于显示"""
        thought_number = thought_data.thought_number
        total_thoughts = thought_data.total_thoughts
        thought = thought_data.thought
        is_revision = thought_data.is_revision
        revises_thought = thought_data.revises_thought
        branch_from_thought = thought_data.branch_from_thought
        branch_id = thought_data.branch_id
        
        prefix = ''
        context = ''
        
        if is_revision:
            prefix = f'{Fore.YELLOW}🔄 Revision{Style.RESET_ALL}'
            context = f' (revising thought {revises_thought})'
        elif branch_from_thought:
            prefix = f'{Fore.GREEN}🌿 Branch{Style.RESET_ALL}'
            context = f' (from thought {branch_from_thought}, ID: {branch_id})'
        else:
            prefix = f'{Fore.BLUE}💭 Thought{Style.RESET_ALL}'
            context = ''
        
        header = f"{prefix} {thought_number}/{total_thoughts}{context}"
        border_length = max(len(header.replace(Fore.YELLOW, '').replace(Fore.GREEN, '').replace(Fore.BLUE, '').replace(Style.RESET_ALL, '')), len(thought)) + 4
        border = '─' * border_length
        
        formatted_output = f"""
┌{border}┐
│ {header.ljust(border_length - 2)} │
├{border}┤
│ {thought.ljust(border_length - 2)} │
└{border}┘"""
        
        return formatted_output
    
    def process_thought(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理思考输入并返回结果"""
        try:
            # 验证输入数据
            validated_input = self.validate_thought_data(input_data)
            
            # 如果思考步数超过总步数，自动调整总步数
            if validated_input.thought_number > validated_input.total_thoughts:
                validated_input.total_thoughts = validated_input.thought_number
            
            # 添加到历史记录
            self.thought_history.append(validated_input)
            
            # 处理分支
            if validated_input.branch_from_thought and validated_input.branch_id:
                if validated_input.branch_id not in self.branches:
                    self.branches[validated_input.branch_id] = []
                self.branches[validated_input.branch_id].append(validated_input)
            
            # 如果未禁用思考日志，则输出格式化的思考内容
            if not self.disable_thought_logging:
                formatted_thought = self.format_thought(validated_input)
                # 输出到stderr以避免与MCP协议冲突
                print(formatted_thought, file=sys.stderr)
            
            # 构建返回结果
            result = {
                "thoughtNumber": validated_input.thought_number,
                "totalThoughts": validated_input.total_thoughts,
                "nextThoughtNeeded": validated_input.next_thought_needed,
                "branches": list(self.branches.keys()),
                "thoughtHistoryLength": len(self.thought_history)
            }
            
            # 验证输出token数量
            result_json = json.dumps(result, indent=2)
            token_validation = SecurityConfig.validate_output_tokens(result_json)
            
            if not token_validation['valid']:
                logger.warning(f"Output token validation warning: {token_validation['error']}")
            
            return {
                "content": [{
                    "type": "text",
                    "text": result_json
                }]
            }
            
        except Exception as error:
            error_message = str(error) if isinstance(error, Exception) else str(error)
            logger.error(f"Error processing thought: {error_message}")
            
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "error": error_message,
                        "status": "failed"
                    }, indent=2)
                }],
                "isError": True
            }
    
    def get_thought_history(self) -> List[Dict[str, Any]]:
        """获取思考历史记录 - 只返回最后一个从thought_number=1开始的序列"""
        if not self.thought_history:
            return []
        
        # 从后往前找最后一个thought_number=1的位置
        last_start_index = 0
        for i in range(len(self.thought_history) - 1, -1, -1):
            if self.thought_history[i].thought_number == 1:
                last_start_index = i
                break
        
        # 返回从最后一个序列开始的所有思考
        return [asdict(thought) for thought in self.thought_history[last_start_index:]]
    
    def get_branches(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取分支记录"""
        return {
            branch_id: [asdict(thought) for thought in thoughts]
            for branch_id, thoughts in self.branches.items()
        }
    
    def clear_history(self) -> None:
        """清空历史记录"""
        self.thought_history.clear()
        self.branches.clear()

def register_sequential_thinking_tool(mcp):
    """注册Sequential Thinking工具到MCP服务器"""
    
    # 创建工具实例
    thinking_tool = SequentialThinkingTool()
    
    @mcp.tool()
    def sequentialthinking(
        thought: str,
        nextThoughtNeeded: bool,
        thoughtNumber: int,
        totalThoughts: int,
        isRevision: Optional[bool] = None,
        revisesThought: Optional[int] = None,
        branchFromThought: Optional[int] = None,
        branchId: Optional[str] = None,
        needsMoreThoughts: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        A detailed tool for dynamic and reflective problem-solving through thoughts.
        This tool helps analyze problems through a flexible thinking process that can adapt and evolve.
        Each thought can build on, question, or revise previous insights as understanding deepens.

        When to use this tool:
        - Breaking down complex problems into steps
        - Planning and design with room for revision
        - Analysis that might need course correction
        - Problems where the full scope might not be clear initially
        - Problems that require a multi-step solution
        - Tasks that need to maintain context over multiple steps
        - Situations where irrelevant information needs to be filtered out

        Key features:
        - You can adjust total_thoughts up or down as you progress
        - You can question or revise previous thoughts
        - You can add more thoughts even after reaching what seemed like the end
        - You can express uncertainty and explore alternative approaches
        - Not every thought needs to build linearly - you can branch or backtrack
        - Generates a solution hypothesis
        - Verifies the hypothesis based on the Chain of Thought steps
        - Repeats the process until satisfied
        - Provides a correct answer

        Parameters explained:
        - thought: Your current thinking step, which can include:
        * Regular analytical steps
        * Revisions of previous thoughts
        * Questions about previous decisions
        * Realizations about needing more analysis
        * Changes in approach
        * Hypothesis generation
        * Hypothesis verification
        - next_thought_needed: True if you need more thinking, even if at what seemed like the end
        - thought_number: Current number in sequence (can go beyond initial total if needed)
        - total_thoughts: Current estimate of thoughts needed (can be adjusted up/down)
        - is_revision: A boolean indicating if this thought revises previous thinking
        - revises_thought: If is_revision is true, which thought number is being reconsidered
        - branch_from_thought: If branching, which thought number is the branching point
        - branch_id: Identifier for the current branch (if any)
        - needs_more_thoughts: If reaching end but realizing more thoughts needed

        You should:
        1. Start with an initial estimate of needed thoughts, but be ready to adjust
        2. Feel free to question or revise previous thoughts
        3. Don't hesitate to add more thoughts if needed, even at the "end"
        4. Express uncertainty when present
        5. Mark thoughts that revise previous thinking or branch into new paths
        6. Ignore information that is irrelevant to the current step
        7. Generate a solution hypothesis when appropriate
        8. Verify the hypothesis based on the Chain of Thought steps
        9. Repeat the process until satisfied with the solution
        10. Provide a single, ideally correct answer as the final output
        11. Only set next_thought_needed to false when truly done and a satisfactory answer is reached
        """
        
        # 构建输入数据
        input_data = {
            'thought': thought,
            'nextThoughtNeeded': nextThoughtNeeded,
            'thoughtNumber': thoughtNumber,
            'totalThoughts': totalThoughts,
            'isRevision': isRevision,
            'revisesThought': revisesThought,
            'branchFromThought': branchFromThought,
            'branchId': branchId,
            'needsMoreThoughts': needsMoreThoughts
        }
        
        # 处理思考
        return thinking_tool.process_thought(input_data)
    
    @mcp.tool()
    def get_thinking_results() -> str:
        """
        获取思考结果的工具，返回完整的思考历史和分支信息作为JSON格式字符串。
        
        这个工具用于：
        - 获取完整的思考过程历史记录
        - 查看所有分支的思考路径
        - 分析思考过程的结构和逻辑
        - 导出思考结果用于进一步分析
        
        返回格式：JSON字符串，包含以下结构：
        {
            "thought_history": [思考历史记录列表],
            "branches": {分支ID: [分支思考记录列表]},
            "summary": {
                "total_thoughts": 总思考数量,
                "total_branches": 总分支数量,
                "completed": 是否完成思考过程
            }
        }
        """
        
        # 获取思考历史和分支
        thought_history = thinking_tool.get_thought_history()
        branches = thinking_tool.get_branches()
        
        # 计算摘要信息
        total_thoughts = len(thought_history)
        total_branches = len(branches)
        
        # 判断是否完成思考过程（最后一个思考的next_thought_needed为False）
        completed = False
        if thought_history:
            last_thought = thought_history[-1]
            completed = not last_thought.get('next_thought_needed', True)
        
        result = {
            "thought_history": thought_history,
            "branches": branches,
            "summary": {
                "total_thoughts": total_thoughts,
                "total_branches": total_branches,
                "completed": completed
            }
        }
        
        # 使用json.dumps确保中文字符正确编码，不转义Unicode
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    logger.info("Sequential Thinking工具已注册")
    return thinking_tool