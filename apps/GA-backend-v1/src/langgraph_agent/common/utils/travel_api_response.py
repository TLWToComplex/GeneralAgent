import json

def search_user_info() -> str:
    """调用此工具获取用户信息的所有数据。"""
    try:
        # 模拟API调用，返回用户信息的所有数据
        # 包含REQUIRED_FIELDS中定义的所有字段
        mock_user_info = {
            "username": "张一男",
            "phone": "13800138000",
            "id_card": "610101199001011234",
            "job_level": "员工",
            "departure": "",
            "destination": "",
            "departuature_date": "",
            "destination_date": "",
            "flight_ticket_standard": "经济舱",
            "rail_ticket_standard": "二等座",
            "hotel_standard": "800元以下"
        }
        
        return json.dumps({
            "status": "success",
            "user_info": mock_user_info,
            "message": "成功获取用户信息"
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"获取用户信息失败: {e}"
        }, ensure_ascii=False)
