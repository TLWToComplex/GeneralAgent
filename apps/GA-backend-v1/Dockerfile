# 基于 Python 3.11.8 镜像构建
FROM python:3.11.8

# 设置工作目录
WORKDIR /code

# 复制项目文件到容器中
COPY . /code

# 安装 Python 依赖项
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 安装 Playwright Chromium 浏览器及系统依赖
RUN playwright install --with-deps chromium

# 暴露容器端口
EXPOSE 8038

# 启动应用（可根据需要选择 CMD 或 ENTRYPOINT，这里只使用 CMD）
CMD ["python", "/code/main.py"]