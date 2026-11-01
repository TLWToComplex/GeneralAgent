"""日报查询 Skill — 服务地址与常量"""

import os

# 日报后端 API 地址
REPORTS_API_BASE = os.environ.get("REPORTSApiBase", "http://172.22.16.1:8000")

# 知识库 API 地址（Langchain-Chatchat）
KB_API_BASE = os.environ.get("KBApiBase", "http://192.168.0.104:7861")

# 主系统地址（用户信息查询）
MAIN_SYSTEM_BASE = os.environ.get("MAINSystemBase", "http://172.22.16.1:8038")

# 用户 token
USER_TOKEN = os.environ.get("USER_TOKEN", "")
