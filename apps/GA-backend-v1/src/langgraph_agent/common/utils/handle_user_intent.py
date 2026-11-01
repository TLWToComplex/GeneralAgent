import json
from src.langgraph_agent.travel_planner.core.llm import llm_no_stream

# 使用大模型判断用户意图：是只想换信息，还是想换用户
# 输入：用户当前 query + 上下文历史
# 输出：True 表示“换用户”，False 表示“仅换信息”
def is_user_switch(query: str) -> bool:
    """
    判断用户是否想切换账号/身份
    """
    sys_prompt = """
## 【角色(Role)】
你是意图判断助手。请仅回答 true 或 false，不要输出其他内容。

【核心准则(Top Priority)】
- 仅根据用户当前输入判断意图，不考虑上下文历史。
- 严格按照 true 或 false 回答。

【执行规范】
- 仅根据用户当前输入判断意图，不考虑上下文历史。
- true：用户明确想切换用户/账号/身份（如"换个用户"、"登录另一个号"）。
- false：用户只想换信息或继续当前身份（如"换出发地"、"换目的地"、"换出发日期"、"换返程日期"）。
"""

    messages = [{"role": "system", "content": sys_prompt}]
    messages.append({"role": "user", "content": query})

    ans = llm_no_stream.invoke(messages)
    return ans.content.strip().lower() == "true"
