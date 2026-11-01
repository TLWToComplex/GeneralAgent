# 使用官方 Python 3.12 镜像作为基础镜像
FROM python:3.12.3-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY src/ ./src/
COPY start.py .

# 复制默认配置文件
COPY config.yaml ./config.yaml

# 创建配置目录（用于外部挂载）
RUN mkdir -p /config

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app && \
    chown -R app:app /config
USER app

# 暴露端口
EXPOSE 8848

# 声明配置文件挂载点
VOLUME ["/config"]

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8848/health || exit 1

# 启动命令
CMD ["python", "start.py"]