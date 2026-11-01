# MySQL查询服务器 Streamable HTTP

一个基于MCP框架的MySQL查询服务器，支持通过Streamable HTTP协议进行实时数据库操作，具备完善的安全机制和高性能的异步处理能力。

## 项目概述

本项目是一个轻量级的MySQL查询服务器，基于Python开发，使用MCP框架和Streamable HTTP协议提供实时数据库操作能力。主要特点包括：

- 基于FastMCP框架，实现异步高性能处理
- 支持Streamable HTTP协议，提供更可靠的实时数据传输
- 高并发数据库连接池，参数灵活可调
- 多级SQL风险控制与注入防护
- 敏感信息自动隐藏与自定义
- 完善的日志与错误处理系统
- Docker支持，快速部署

## 整体架构

```
.
├── src/                    # 源代码目录
│   ├── server.py           # 主服务器入口
│   ├── config.py           # 配置项定义
│   ├── validators.py       # 参数校验
│   ├── db/                 # 数据库操作模块
│   │   └── mysql_operations.py # 数据库操作和连接池管理
│   ├── security/           # 安全相关模块
│   │   ├── interceptor.py      # SQL拦截器
│   │   ├── query_limiter.py    # 风险控制
│   │   └── sql_analyzer.py     # SQL分析器
│   └── tools/              # 工具类模块
│       ├── mysql_tool.py           # 基础查询工具
│       ├── mysql_metadata_tool.py  # 元数据查询工具
│       ├── mysql_info_tool.py      # 信息查询工具
│       ├── mysql_schema_tool.py    # 结构查询工具
│       └── metadata_base_tool.py   # 工具基类
├── example.env             # 环境变量示例
├── requirements.txt        # 依赖包列表
└── Dockerfile              # Docker构建文件
```

### 核心组件说明

1. **服务器模块** (server.py)
   - 基于FastMCP框架实现Streamable HTTP通信
   - 自动注册工具和管理连接池
   - 提供优雅的启动和关闭机制

2. **数据库操作模块** (db/mysql_operations.py)
   - 异步MySQL连接池管理
   - 事件循环隔离与资源回收
   - 事务管理与错误处理

3. **安全模块** (security/)
   - SQL注入防护与风险分析
   - 操作权限控制
   - 敏感信息保护

4. **工具模块** (tools/)
   - 基础SQL查询工具
   - 元数据与表结构查询工具
   - 数据库信息查询工具

## 实现细节

### 连接池管理

- **基于事件循环的隔离设计**：
  - 每个异步事件循环拥有独立的连接池，通过`id(current_loop)`作为标识符
  - 使用线程本地存储(`threading.local()`)管理多个连接池，避免资源竞争
  - 实现了`_cleanup_unused_pools()`定期(每5分钟)回收无效连接池

- **智能连接池资源管理**：
  ```python
  # 连接池回收与释放机制
  def _finalizer(p=pool, lid=loop_id):
      if not p.closed:
          p.close()
          logger.info(f"事件循环关闭时自动关闭连接池 (事件循环ID: {lid})")
  weakref.finalize(current_loop, _finalizer)
  ```

- **异步上下文管理器**：
  - 实现`@asynccontextmanager`修饰的连接获取函数
  - 通过`get_db_connection()`上下文管理器自动获取和释放连接
  - 出现异常时自动识别错误类型并提供友好错误信息

- **自适应连接池配置**：
  - 可通过环境变量精确控制连接池大小、超时时间和回收策略
  - 支持禁用连接池模式，自动降级为单连接模式
  - 实现了连接池`max_lifetime`参数支持，确保长连接定期更新

### Streamable HTTP通信实现

- **基于FastMCP框架的Streamable HTTP实现**：
  - 采用`StreamableHTTPServerTransport`类实现Streamable HTTP协议
  - 支持可靠的实时数据传输和会话管理

- **Starlette集成**：
  - 使用FastMCP的`streamable_http_app`方法创建应用
  - 支持标准HTTP请求/响应模式
  - 提供CORS中间件支持，允许跨域访问

### 安全机制

- **多级SQL风险分析**：
  - 实现了4级风险评估`SQLRiskLevel`: `LOW`/`MEDIUM`/`HIGH`/`CRITICAL`
  - 基于SQL语句类型、影响范围和WHERE条件智能分析风险
  - 针对DELETE/UPDATE操作强制检查WHERE条件

- **SQL拦截器实现**：
  ```python
  class SQLInterceptor:
      def __init__(self, analyzer: SQLOperationType):
          self.analyzer = analyzer
          self.max_sql_length = SecurityConfig.MAX_SQL_LENGTH

      async def check_operation(self, sql_query: str) -> bool:
          # SQL长度与格式检查
          if len(sql_query) > self.max_sql_length:
              raise SecurityException(f"SQL语句长度({len(sql_query)})超出限制({self.max_sql_length})")
              
          # SQL风险分析
          risk_analysis = self.analyzer.analyze_risk(sql_query)
          
          # 风险级别检查
          if not risk_analysis['is_allowed']:
              raise SecurityException(
                  f"当前操作风险等级({risk_analysis['risk_level'].name})不被允许执行，"
                  f"允许的风险等级: {[level.name for level in self.analyzer.allowed_risk_levels]}"
              )
  ```

- **敏感信息保护**：
  - 自动识别并掩码敏感字段(password/token等)
  - 支持通过环境变量自定义敏感字段列表
  - 不同环境(开发/生产)应用不同级别的安全策略

### 自动化工具注册

- **反射式工具发现**：
  ```python
  def auto_register_tools(mcp):
      """自动扫描src.tools目录下所有register_开头的函数并注册到mcp"""
      import tools
      package = tools
      for finder, name, ispkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
          if ispkg:
              continue
          module = importlib.import_module(name)
          for func_name, func in inspect.getmembers(module, inspect.isfunction):
              if func_name.startswith("register_") and func_name.endswith("tool") or func_name.endswith("tools"):
                  try:
                      func(mcp)
                      logger.info(f"自动注册工具: {name}.{func_name}")
                  except Exception as e:
                      logger.error(f"自动注册工具失败: {name}.{func_name} - {e}")
  ```

- **装饰器模式的错误处理**：
  - 实现了`handle_query_error`装饰器统一处理工具错误
  - 自动转换异常为友好的错误消息
  - 支持参数验证与类型转换

### 事务管理

- **自动事务处理**：
  - 支持多语句事务，包含自动回滚机制
  - SQL执行错误时自动回滚，并提供详细错误信息 
  - 支持显式事务控制(BEGIN/COMMIT/ROLLBACK)

- **异常细分**：
  - 实现了细粒度的异常类型，包括连接错误、认证错误、数据库不存在等
  - 通过异常类型提供精确的诊断信息

## 部署指南

### 环境要求

- Python 3.12.3 及以上版本
- 依赖包:
  - mcp >= 1.4.1
  - aiomysql >= 0.2.0
  - python-dotenv >= 1.0.1
  - sqlparse >= 0.5.3

### 本地启动方式

1. 安装依赖:
   ```
   pip install -r requirements.txt
   ```

2. 配置环境变量:
   - 复制 `example.env` 为 `.env`
   - 根据实际情况修改配置

3. 启动服务:
   ```
   python -m src.server
   ```

4. 默认服务地址:
   - http://127.0.0.1:3000
   - Streamable HTTP 端点: http://127.0.0.1:3000/message

### Docker部署

1. 构建镜像:
   ```
   docker build -t aisix-mysql-server-streamable-http:1.0.0 .
   ```

2. 运行容器:
   ```
   docker run -d --name mysql-mcp-server-streamable-http \
     -e HOST=0.0.0.0 \
     -e PORT=3000 \
     -e MYSQL_HOST=host.docker.internal \
     -e MYSQL_PORT=3306 \
     -e MYSQL_USER=root \
     -e MYSQL_PASSWORD=123456 \
     -e MYSQL_DATABASE=edu_event \
     -p 3004:3000 \
     aisix/mysql-mcp-server-streamable-http:1.0.0
   ```

Windows PowerShell 格式:
```powershell
docker run -d `
  --name mysql-mcp-server-streamable-http `
  -e HOST=0.0.0.0 `
  -e PORT=3000 `
  -e MYSQL_HOST=host.docker.internal `
  -e MYSQL_PORT=3306 `
  -e MYSQL_USER=root `
  -e MYSQL_PASSWORD=123456 `
  -e MYSQL_DATABASE=edu_event `
  -p 3004:3000 `
  aisix/mysql-mcp-server-streamable-http:1.0.0
```

## 配置选项

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| HOST | 服务器监听地址 | 127.0.0.1 |
| PORT | 服务器监听端口 | 3000 |
| MYSQL_HOST | MySQL服务器地址 | localhost |
| MYSQL_PORT | MySQL服务器端口 | 3306 |
| MYSQL_USER | MySQL用户名 | root |
| MYSQL_PASSWORD | MySQL密码 | (空) |
| MYSQL_DATABASE | 要连接的数据库名 | (空) |
| DB_CONNECTION_TIMEOUT | 连接超时时间(秒) | 5 |
| DB_AUTH_PLUGIN | 认证插件类型 | mysql_native_password |
| DB_POOL_ENABLED | 是否启用连接池 | true |
| DB_POOL_MIN_SIZE | 连接池最小连接数 | 5 |
| DB_POOL_MAX_SIZE | 连接池最大连接数 | 20 |
| DB_POOL_RECYCLE | 连接回收时间(秒) | 300 |
| DB_POOL_MAX_LIFETIME | 连接最大存活时间(秒) | 0 |
| ENV_TYPE | 环境类型 | development |
| ALLOWED_RISK_LEVELS | 允许的风险等级 | LOW,MEDIUM |
| ALLOW_SENSITIVE_INFO | 允许查询敏感字段 | false |
| MAX_SQL_LENGTH | 最大SQL语句长度 | 5000 |
| LOG_LEVEL | 日志级别 | DEBUG |

> 注: 部分云MySQL需指定`DB_AUTH_PLUGIN`为`mysql_native_password`

## API工具列表

服务器提供以下主要API工具:

1. **mysql_query** - 执行基础SQL查询
   ```
   参数:
     - query: SQL查询语句
     - params: 查询参数 (可选)
   ```

2. **mysql_show_databases** - 获取数据库列表
   ```
   参数:
     - pattern: 数据库名称匹配模式 (可选, 例如 '%test%')
     - limit: 返回结果的最大数量 (默认100)
     - exclude_system: 是否排除系统数据库 (默认为True)
   ```

3. **mysql_show_tables** - 获取数据库中的表列表
   ```
   参数:
     - database: 数据库名称 (可选)
     - pattern: 表名匹配模式 (可选, 例如 '%user%')
     - limit: 返回结果的最大数量 (默认100)
     - exclude_views: 是否排除视图 (默认为False)
   ```

4. **mysql_show_columns** - 获取表的列信息
   ```
   参数:
     - table: 表名
     - database: 数据库名称 (可选)
   ```

5. **mysql_show_create_table** - 获取表的创建语句
   ```
   参数:
     - table: 表名
     - database: 数据库名称 (可选)
   ```

6. **mysql_show_variables** - 获取MySQL系统变量
   ```
   参数:
     - pattern: 变量名称匹配模式 (可选)
     - global_scope: 是否查询全局变量 (默认为False)
   ```

7. **mysql_show_status** - 获取MySQL服务器状态
   ```
   参数:
     - pattern: 状态名称匹配模式 (可选)
     - global_scope: 是否查询全局状态 (默认为False)
   ```

8. **mysql_describe_table** - 描述表结构
   ```
   参数:
     - table: 表名
     - database: 数据库名称 (可选)
   ```

9. **mysql_show_indexes** - 获取表的索引信息
   ```
   参数:
     - table: 表名
     - database: 数据库名称 (可选)
   ```

10. **mysql_paginate_results** - 分页执行查询
    ```
    参数:
      - query: SQL查询语句
      - page: 页码 (从1开始)
      - page_size: 每页记录数 (默认50)
    ```

## 常见问题

1. **Q: DELETE操作未执行成功？**
   A: 检查是否有WHERE条件，无WHERE条件的DELETE为高风险操作，需在ALLOWED_RISK_LEVELS中允许CRITICAL级别。

2. **Q: 如何自定义敏感字段？**
   A: 设置环境变量SENSITIVE_INFO_FIELDS，例如：SENSITIVE_INFO_FIELDS=password,token

3. **Q: limit参数报错？**
   A: limit必须为非负整数。

4. **Q: Docker容器无法连接到宿主机MySQL？**
   A: 使用`host.docker.internal`替代`localhost`作为MySQL主机名，或使用宿主机的实际IP地址。

5. **Q: 生产环境安全建议？**
   A: 设置`ENV_TYPE=production`和`ALLOWED_RISK_LEVELS=LOW`，确保`ALLOW_SENSITIVE_INFO=false`。

6. **Q: 遇到"Authentication plugin 'caching_sha2_password' is not supported"错误？**
   A: 这是因为MySQL 8.0+默认使用caching_sha2_password认证插件，而本服务使用的连接器支持mysql_native_password。解决步骤：
   
   1. 检查当前用户的认证插件：
      ```sql
      SELECT User, Host, plugin 
      FROM mysql.user 
      WHERE User = 'your_username';
      ```
   
   2. 如果plugin显示为sha256_password或caching_sha2_password，执行以下SQL修改认证方式：
      ```sql
      ALTER USER 'your_username'@'your_host' 
      IDENTIFIED WITH mysql_native_password 
      BY 'your_password';
      FLUSH PRIVILEGES;
      ```
   
   3. 或者在环境变量中指定认证插件：`DB_AUTH_PLUGIN=mysql_native_password`

7. **Q: 当模型的能力不强时，可利用系统提示词增强，比如**
   
   你是一个数据库专家，你可以通过调通工具去访问MySQL数据库，负责回答用户的查询请求。

   以下是edu_event数据库的表结构:

   -- ----------------------------
   -- Table structure for classes
   -- ----------------------------
   CREATE TABLE `classes`  (
   `id` int NOT NULL AUTO_INCREMENT,
   `class_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
   `monitor_id` int NULL DEFAULT NULL,
   `vice_monitor_id` int NULL DEFAULT NULL,
   `meeting_place` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
   `instructors` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
   PRIMARY KEY (`id`) USING BTREE
   ) ENGINE = InnoDB AUTO_INCREMENT = 5 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

   -- ----------------------------
   -- Table structure for computer_courses
   -- ----------------------------
   CREATE TABLE `computer_courses`  (
   `id` int NOT NULL AUTO_INCREMENT,
   `course_date` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '日期信息',
   `time_slot` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '上课时间段',
   `course_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '课程名称',
   `course_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '课程类型(必修/选修/实验)',
   `location` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '上课地点',
   `instructor` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '授课教师',
   `department` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '开课院系',
   `credit` tinyint NULL DEFAULT NULL COMMENT '学分',
   `capacity` smallint NULL DEFAULT NULL COMMENT '课程容量',
   PRIMARY KEY (`id`) USING BTREE
   ) ENGINE = InnoDB AUTO_INCREMENT = 37 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

   -- ----------------------------
   -- Table structure for persons
   -- ----------------------------
   CREATE TABLE `persons`  (
   `id` int NOT NULL AUTO_INCREMENT,
   `name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
   `position` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
   `room_number` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
   `dining_table_number` int NULL DEFAULT NULL,
   `phone` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
   `class_id` int NULL DEFAULT NULL,
   PRIMARY KEY (`id`) USING BTREE,
   INDEX `class_id`(`class_id` ASC) USING BTREE,
   CONSTRAINT `persons_ibfk_1` FOREIGN KEY (`class_id`) REFERENCES `classes` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
   ) ENGINE = InnoDB AUTO_INCREMENT = 41 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

## 许可证

MIT License