"""本地启动入口（等价于老项目 main.py 的启动方式）。

生产/容器环境同样可直接执行：``python run.py``；

    python run.py
    # 或
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8038
"""
from __future__ import annotations

import uvicorn

from app.config import LogConfig, ServerConfig

if __name__ == "__main__":
    LogConfig.setup_logging()
    print(f"正在 {ServerConfig.HOST}:{ServerConfig.PORT} 启动GeneralAgent V2 后端")
    print(f"接口文档: http://{ServerConfig.HOST}:{ServerConfig.PORT}/docs")
    uvicorn.run(
        "app.main:app",
        host=ServerConfig.HOST,
        port=ServerConfig.PORT,
        reload=ServerConfig.RELOAD,
        log_level=str(LogConfig.LEVEL).lower(),
    )