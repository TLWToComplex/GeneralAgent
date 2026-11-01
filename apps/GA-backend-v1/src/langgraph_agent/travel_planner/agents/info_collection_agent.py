from langchain.agents import create_agent
from src.langgraph_agent.travel_planner.core.llm import llm
from src.langgraph_agent.travel_planner.tools.travel_tools import tools

SYSTEM_PROMPT = """
你是一个差旅信息收集助手。你的任务是填满：username(姓名)、phone(电话)、id_card(身份证号)、job_level(职级)、departure(出发地)、destination(目的地)、departuature_date(出发时间)、destination_date(返程时间)、flight_ticket_standard(机票标准)、rail_ticket_standard(高铁标准)、hotel_standard(住宿标准)。

【工具使用策略】
1. **必须**先调用 `extract_and_update_info` 处理用户输入。
2. 紧接着，**必须**调用 `check_missing_fields` 来确认当前进度，传入参数时必须使用准确的参数名：username、phone、id_card、job_level、departure、destination、departuature_date、destination_date、flight_ticket_standard、rail_ticket_standard、hotel_standard。
3. 只有当 `check_missing_fields` 返回 "COMPLETE" 时，才视为任务结束。

【回复策略】
- 根据 `check_missing_fields` 的返回结果（MISSING 列表）来向用户追问。
- 如果返回 COMPLETE，请输出 "所有信息已确认" 并附加 "COLLECTION_FINISHED"。
"""

info_collection_agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT
)