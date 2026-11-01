#!/usr/bin/env python3
"""
Sequential Thinking MCP Server启动脚本
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.server import start_server

if __name__ == "__main__":
    start_server()