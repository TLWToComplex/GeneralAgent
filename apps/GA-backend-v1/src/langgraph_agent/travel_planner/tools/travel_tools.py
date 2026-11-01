import json
from langchain_core.tools import tool
from src.langgraph_agent.travel_planner.core.llm import llm_no_stream
import datetime
# 获取当前时间
current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
REQUIRED_FIELDS = {
    "username": "姓名",
    "phone": "电话",
    "id_card": "身份证号",
    "job_level": "职级",
    "departure": "出发地",
    "destination": "目的地",
    "departuature_date": "出发时间",
    "destination_date": "返程时间",
    "flight_ticket_standard": "机票标准",
    "rail_ticket_standard": "高铁标准",
    "hotel_standard": "住宿标准"
}

@tool
def extract_and_update_info(user_input: str) -> str:
    """调用此工具提取用户输入的信息并返回提取结果（由 Node 负责更新 State）。"""
    
    # 定义示例输出为单独的字符串，避免f-string转义问题
    example_output = '''
    {
        "departure": "出发地",
        "destination": "目的地",
        "departure_date": "出发日期",
        "destination_date": "返程日期"
    }
    '''
    
    extraction_prompt = f"""
    你是一个负责提取差旅信息的助手。请分析用户输入: "{user_input}"
    **当前时间**: {current_time}
    【提取规则】
    1. 严格区分出发地(departure)和目的地(destination)。
    2. 必须是明确日期，出发时间(departuature_date)和返程时间(destination_date)。
    3. 输出 JSON 格式，仅包含提取到的字段。
    4. 日期格式统一为 YYYY-MM-DD。
    5. 如果用户输入中没有包含出发地、目的地、出发时间或返程时间等信息时，返回空字符串。
    【示例输出】
    {example_output}
    请输出 JSON:
    """
    try:
        response = llm_no_stream.invoke(extraction_prompt)
        content = response.content.strip().replace("```json", "").replace("```", "")
        extracted_data = json.loads(content)
        
        # 返回提取结果，让 Node 处理 State 更新
        updated_log = []
        valid_data = {}
        
        if isinstance(extracted_data, dict):
            # 字段名映射：正确拼写 -> 系统使用的拼写
            field_mapping = {
                "departure": "departure",
                "departure_date": "departuature_date",
                "return_date": "destination_date"
            }
            
            for key, val in extracted_data.items():
                # 处理字段名映射
                system_key = field_mapping.get(key, key)
                if system_key in REQUIRED_FIELDS and val:
                    valid_data[system_key] = val
                    updated_log.append(f"{REQUIRED_FIELDS[system_key]}: {val}")
        
        if not valid_data:
            return json.dumps({"status": "failed", "message": "未能从输入中提取到有效信息。"})
        
        return json.dumps({
            "status": "success",
            "extracted": valid_data,
            "message": f"已提取: {', '.join(updated_log)}"
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({"status": "error", "message": f"提取处理出错: {e}"})

@tool
def check_missing_fields(
    username: str = None,
    phone: str = None,
    id_card: str = None,
    job_level: str = None,
    departure: str = None,
    destination: str = None,
    departuature_date: str = None,
    destination_date: str = None,
    flight_ticket_standard: str = None,
    rail_ticket_standard: str = None,
    hotel_standard: str = None
) -> str:
    """检查还有哪些字段没填。接收当前 State 的字段作为参数。"""
    missing = []
    fields = {
        "username": username,
        "phone": phone,
        "id_card": id_card,
        "job_level": job_level,
        "departure": departure,
        "destination": destination,
        "departuature_date": departuature_date,
        "destination_date": destination_date,
        "flight_ticket_standard": flight_ticket_standard,
        "rail_ticket_standard": rail_ticket_standard,
        "hotel_standard": hotel_standard
    }
    
    for key, val in fields.items():
        if not val:
            missing.append(REQUIRED_FIELDS[key])
    
    if not missing:
        return "COMPLETE"
    else:
        return f"MISSING: {', '.join(missing)}"


tools = [extract_and_update_info, check_missing_fields]
