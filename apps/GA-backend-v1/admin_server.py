"""Main admin server application module.
Initializes and configures the Flask application with all API routes for the admin backend.
"""
import os
import logging
import mimetypes
import urllib.parse
from flask import Flask, Response, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from src.config import ServerConfig, LogConfig, DatabaseConfig, SSOConfig

from src.utils.database import db
from src.utils.config_manager import config_manager
from src.controllers.ai_agent_controller import AIAgentController
from src.controllers.ai_mcp_server_controller import AIMCPServerController
from src.controllers.ai_user_controller import AIUserController
from src.controllers.ai_user_feedback_controller import AIUserFeedbackController
from src.controllers.ai_usage_metrics_controller import AIUsageMetricsController
from src.controllers.auth_controller import AuthController
from src.controllers.ai_user_preferences_controller import AIUserPreferencesController
from src.controllers.ai_prompt_controller import AIPromptController
from src.controllers.ai_platform_model_controller import AIPlatformModelController
from src.controllers.ai_knowledge_base_controller import AIKnowledgeBaseController
from src.controllers.ai_user_group_controller import AIUserGroupController
from src.controllers.ai_user_group_relation_controller import AIUserGroupRelationController
from src.controllers.ai_permissions_controller import AIPermissionsController
from src.controllers.ai_file_processor_controller import AIFileProcessorController
from src.controllers.ai_skill_controller import AISkillController
from src.controllers.ai_chat_controller import AIChatController
from src.controllers.ai_chat_record_controller import AIChatRecordController
from src.controllers.ai_chat_session_summary_controller import AIChatSessionSummaryController
from src.controllers.memory_controller import MemoryController
from src.controllers.tree_controller import TreeController
from src.controllers.ai_entity_permission_controller import AIEntityPermissionController
from src.utils.entity_type import EntityType
from src.utils.jwt_required import jwt_required
from src.utils.stream_hub import stream_hub
from src.utils.permission_check import permission_check
from src.utils.admin_required import admin_required
from src.core.tool_agent.tool_agent_utils import initialize_tool_agent
from src.utils.async_route import async_route
from src.controllers.screenshot_controller import ScreenshotController
from src.controllers.ai_system_config_controller import AISystemConfigController

# 创建Flask应用实例
app = Flask(
    __name__,
    static_url_path="/files",                                   # [新增] 访问前缀
    static_folder=os.getenv("MINIO_LOCAL_DIR", "./data/minio")   # [新增] 实际磁盘目录
)

# 配置JWT密钥和过期时间
import secrets
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', secrets.token_urlsafe(32))
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600  # token过期时间设为1小时

jwt = JWTManager(app)
CORS(app)

# 从配置中获取SSO URL
sso_url = SSOConfig.URL
# 从环境变量获取所需权限码
permission_codes = os.getenv('REQUIRED_PERMISSION_CODES', '37').split(',')

# 配置数据库连接
app.config['SQLALCHEMY_DATABASE_URI'] = DatabaseConfig.URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = DatabaseConfig.TRACK_MODIFICATIONS

# 初始化数据库连接
db.init_app(app)

# 配置应用日志记录器
LogConfig.setup_logging()
logger = logging.getLogger(__name__)

# 启动初始化：默认数据 + 截图服务 + 退出清理
from src.core.bootstrap import ensure_default_data, init_screenshot, register_shutdown_hooks

with app.app_context():
    ensure_default_data()

init_screenshot()
register_shutdown_hooks()

# @app.route('/validate_cas_login', methods=['POST'])
# def validate_cas_login() -> Response:
#     return LoginController.validate_cas_login(sso_url, permission_codes)


# AI智能体相关API
@app.route('/aiAgent/add', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def add_ai_agent(current_user: str = 'admin') -> Response:
    return await AIAgentController.add_agent(current_user)

@app.route('/aiAgent/list', methods=['GET'])
@async_route
@jwt_required(sso_url, permission_codes)
@permission_check(entity_type=EntityType.AGENT)
async def list_ai_agents(current_user: str = 'admin', allowed_entity_ids: list = None) -> Response:
    return await AIAgentController.list_agents(current_user)

@app.route('/aiAgent/record', methods=['GET'])
@async_route
@jwt_required(sso_url, permission_codes)
@permission_check(entity_type=EntityType.AGENT)
async def get_ai_agent(current_user: str = 'admin', allowed_entity_ids: list = None) -> Response:
    return await AIAgentController.get_agent(current_user)

@app.route('/aiAgent/update', methods=['POST'])
@async_route
@jwt_required(sso_url, permission_codes)
@permission_check(entity_type=EntityType.AGENT)
async def update_ai_agent(current_user: str = 'admin') -> Response:
    return await AIAgentController.update_agent(current_user)

@app.route('/aiAgent/delete', methods=['POST'])
@async_route
@jwt_required(sso_url, permission_codes)
@permission_check(entity_type=EntityType.AGENT)
async def delete_ai_agent(current_user: str = 'admin') -> Response:
    return await AIAgentController.delete_agent(current_user)

# 树结构查询API
@app.route('/aiPermission/tree', methods=['GET'])
@async_route
@jwt_required(sso_url, permission_codes)
async def get_tree_structure(current_user: str = 'admin') -> Response:
    return await TreeController.get_tree_structure(current_user)

# AI MCP服务器相关API
@app.route('/aiMCPServer/add', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def add_ai_mcp_server(current_user: str = 'admin') -> Response:
    return await AIMCPServerController.add_mcp_server(current_user)

@app.route('/aiMCPServer/data', methods=['GET'])
@async_route
@jwt_required(sso_url, permission_codes)
@permission_check(entity_type=EntityType.MCP_SERVER)
async def list_ai_mcp_servers(current_user: str = 'admin') -> Response:
    return await AIMCPServerController.list_mcp_servers_async(current_user)

@app.route('/aiMCPServer/list', methods=['GET'])
@async_route
@jwt_required(sso_url, permission_codes)
@permission_check(entity_type=EntityType.MCP_SERVER)
async def list_ai_mcp_servers_basic(current_user: str = 'admin', allowed_entity_ids: list = None) -> Response:
    return await AIMCPServerController.list_mcp_servers_basic(current_user)

@app.route('/aiMCPServer/record', methods=['GET'])
@async_route
@jwt_required(sso_url, permission_codes)
@permission_check(entity_type=EntityType.MCP_SERVER)
async def get_ai_mcp_server(current_user: str = 'admin', allowed_entity_ids: list = None) -> Response:
    return await AIMCPServerController.get_mcp_server_async(current_user)

@app.route('/aiMCPServer/update', methods=['POST'])
@async_route
@jwt_required(sso_url, permission_codes)
@permission_check(entity_type=EntityType.MCP_SERVER)
async def update_ai_mcp_server(current_user: str = 'admin') -> Response:
    return await AIMCPServerController.update_mcp_server_async(current_user)

@app.route('/aiMCPServer/delete', methods=['POST'])
@async_route
@jwt_required(sso_url, permission_codes)
@permission_check(entity_type=EntityType.MCP_SERVER)
async def delete_ai_mcp_server(current_user: str = 'admin') -> Response:
    return await AIMCPServerController.delete_mcp_server_async(current_user)

@app.route('/aiMCPServer/test', methods=['POST'])
@async_route
@jwt_required(sso_url, permission_codes)
async def test_ai_mcp_connection(current_user: str = 'admin') -> Response:
    """测试MCP服务连接"""
    return await AIMCPServerController.test_mcp_connection(current_user)

# AI用户相关API
@app.route('/aiUser/add', methods=['POST'])
# @jwt_required(sso_url, permission_codes)  # 创建用户无需认证
@async_route
async def add_ai_user() -> Response:
    return await AIUserController.add_user()

@app.route('/aiUser/list', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def list_ai_users(current_user: str = 'admin') -> Response:
    return await AIUserController.list_users()

@app.route('/aiUser/record', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def get_ai_user(current_user: str = 'admin') -> Response:
    return await AIUserController.get_user()

@app.route('/aiUser/update', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def update_ai_user(current_user: str = 'admin') -> Response:
    return await AIUserController.update_user()

@app.route('/aiUser/delete', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def delete_ai_user(current_user: str = 'admin') -> Response:
    return await AIUserController.delete_user()

@app.route('/aiUser/query', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def query_ai_users(current_user: str = 'admin') -> Response:
    return await AIUserController.query_users()

@app.route('/aiUser/listWithGroups', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def list_ai_users_with_groups(current_user: str = 'admin') -> Response:
    return await AIUserController.list_users_with_groups(current_user)

@app.route('/aiUser/syncGroups', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def sync_ai_user_groups(current_user: str = 'admin') -> Response:
    """批量同步用户与用户组的关联关系（仅 admin 可访问）"""
    return await AIUserController.sync_user_groups(current_user)

# AI用户反馈与改进追溯相关API
@app.route('/aiUserFeedback/add', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def add_ai_user_feedback(current_user: str = 'admin') -> Response:
    return await AIUserFeedbackController.add_feedback(current_user)

@app.route('/aiUserFeedback/list', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def list_ai_user_feedback(current_user: str = 'admin') -> Response:
    return await AIUserFeedbackController.list_feedback(current_user)

@app.route('/aiUserFeedback/record', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def get_ai_user_feedback(current_user: str = 'admin') -> Response:
    return await AIUserFeedbackController.get_feedback(current_user)

@app.route('/aiUserFeedback/query', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def query_ai_user_feedback(current_user: str = 'admin') -> Response:
    return await AIUserFeedbackController.query_feedback(current_user)

@app.route('/aiUserFeedback/update', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def update_ai_user_feedback(current_user: str = 'admin') -> Response:
    return await AIUserFeedbackController.update_feedback(current_user)

@app.route('/aiUserFeedback/delete', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def delete_ai_user_feedback(current_user: str = 'admin') -> Response:
    return await AIUserFeedbackController.delete_feedback(current_user)

# AI 平台使用追踪指标相关API（基于 Langfuse traces 聚合）
@app.route('/aiUsageMetrics/summary', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def ai_usage_metrics_summary(current_user: str = 'admin') -> Response:
    return await AIUsageMetricsController.summary(current_user)

@app.route('/aiUsageMetrics/topUsers', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def ai_usage_metrics_top_users(current_user: str = 'admin') -> Response:
    return await AIUsageMetricsController.top_users(current_user)

@app.route('/aiUsageMetrics/userActivity', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def ai_usage_metrics_user_activity(current_user: str = 'admin') -> Response:
    return await AIUsageMetricsController.user_activity(current_user)

@app.route('/aiUsageMetrics/deepAgentLatency', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def ai_usage_metrics_deep_agent_latency(current_user: str = 'admin') -> Response:
    return await AIUsageMetricsController.deep_agent_latency(current_user)

@app.route('/captcha', methods=['GET'])
@async_route
async def get_captcha() -> Response:
    """获取验证码接口（无需认证）"""
    return await AuthController.generate_captcha()

@app.route('/aiUser/login', methods=['POST'])
@async_route
async def ai_user_login() -> Response:
    return await AuthController.login()

@app.route('/aiUser/changePassword', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def change_user_password(current_user: str = 'admin') -> Response:
    return await AuthController.change_password(current_user)

@app.route('/aiUser/unlockAccount', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
@admin_required
async def unlock_user_account(current_user: str = 'admin') -> Response:
    """管理员解锁因超过30天未登录而被锁定的账号"""
    return await AuthController.unlock_account(current_user)

# AI用户偏好设置相关API
@app.route('/aiUserPreferences/get', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def get_user_preferences(current_user: str = 'admin') -> Response:
    AuthController.update_last_login_time(current_user)
    return await AIUserPreferencesController.get_user_preferences(current_user)

@app.route('/aiUserPreferences/update', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def update_user_preferences(current_user: str = 'admin') -> Response:
    return await AIUserPreferencesController.update_user_preferences(current_user)

@app.route('/aiUserPreferences/add', methods=['POST'])
# @jwt_required(sso_url, permission_codes)
@async_route
async def add_user_preferences(current_user: str = 'admin') -> Response:
    return await AIUserPreferencesController.add_user_preferences(current_user)

# AI用户组相关API
@app.route('/aiUserGroup/add', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def add_ai_user_group(current_user: str = 'admin') -> Response:
    return await AIUserGroupController.add_user_group(current_user)

@app.route('/aiUserGroup/list', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def list_ai_user_groups(current_user: str = 'admin') -> Response:
    return await AIUserGroupController.list_user_groups_async(current_user)

@app.route('/aiUserGroup/record', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def get_ai_user_group(current_user: str = 'admin') -> Response:
    return await AIUserGroupController.get_user_group_async(current_user)

@app.route('/aiUserGroup/update', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def update_ai_user_group(current_user: str = 'admin') -> Response:
    return await AIUserGroupController.update_user_group_async(current_user)

@app.route('/aiUserGroup/delete', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def delete_ai_user_group(current_user: str = 'admin') -> Response:
    return await AIUserGroupController.delete_user_group_async(current_user)

@app.route('/aiUserGroup/setDefault', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def set_default_ai_user_group(current_user: str = 'admin') -> Response:
    return await AIUserGroupController.set_default_user_group_async(current_user)

@app.route('/aiUserGroup/getDefault', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def get_default_ai_user_group(current_user: str = 'admin') -> Response:
    return await AIUserGroupController.get_default_user_group_async(current_user)

# 用户组关联相关API
@app.route('/aiUserGroupRelation/record', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def get_ai_user_group_relation(current_user: str = 'admin') -> Response:
    return await AIUserGroupRelationController.get_user_group_relation_async(current_user)

@app.route('/aiUserGroupRelation/update', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def sync_ai_user_group_relations(current_user: str = 'admin') -> Response:
    return await AIUserGroupRelationController.sync_user_group_relations_async(current_user)


# AI提示词相关API
@app.route('/aiPrompt/add', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def add_ai_prompt(current_user: str = 'admin') -> Response:
    return await AIPromptController.add_prompt(current_user)

@app.route('/aiPrompt/list', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
@permission_check(entity_type=EntityType.PROMPT)
async def list_ai_prompts(current_user: str = 'admin', allowed_entity_ids: list = None) -> Response:
    return await AIPromptController.list_prompts(current_user, allowed_entity_ids)


@app.route('/aiPrompt/update', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def update_ai_prompt(current_user: str = 'admin') -> Response:
    return await AIPromptController.update_prompt(current_user)

@app.route('/aiPrompt/delete', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def delete_ai_prompt(current_user: str = 'admin') -> Response:
    return await AIPromptController.delete_prompt(current_user)

# AI权限相关API
@app.route('/aiPermission/update', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def update_ai_permission(current_user: str = 'admin') -> Response:
    return await AIPermissionsController.update_permission(current_user)

# AI平台模型相关API
@app.route('/aiPlatformModel/add', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def add_ai_platform_model(current_user: str = 'admin') -> Response:
    return await AIPlatformModelController.create_platform_with_models(current_user)

@app.route('/aiPlatformModel/list', methods=['GET'])
@async_route
@jwt_required(sso_url, permission_codes)
async def list_ai_platform_models(current_user: str = 'admin') -> Response:
    return await AIPlatformModelController.list_platforms(current_user)

@app.route('/aiPlatformModel/record', methods=['GET'])
@async_route
@jwt_required(sso_url, permission_codes)
async def get_ai_platform_model(current_user: str = 'admin') -> Response:
    return await AIPlatformModelController.get_platform_with_models(current_user)

@app.route('/aiPlatformModel/update', methods=['POST'])
@async_route
@jwt_required(sso_url, permission_codes)
async def update_ai_platform_model(current_user: str = 'admin') -> Response:
    return await AIPlatformModelController.update_platform(current_user)

@app.route('/aiPlatformModel/delete', methods=['POST'])
@async_route
@jwt_required(sso_url, permission_codes)
async def delete_ai_platform_model(current_user: str = 'admin') -> Response:
    return await AIPlatformModelController.delete_platform(current_user)

@app.route('/aiPlatformModel/reorder', methods=['POST'])
@async_route
@jwt_required(sso_url, permission_codes)
async def reorder_ai_platforms(current_user: str = 'admin') -> Response:
    return await AIPlatformModelController.reorder_platforms(current_user)

# 系统配置API（仅 admin 可访问）
@app.route('/aiSystemConfig/list', methods=['GET'])
@async_route
@jwt_required(sso_url, permission_codes)
async def get_system_configs(current_user: str = 'admin') -> Response:
    result, status = await AISystemConfigController.get_configs(current_user)
    return result, status

@app.route('/aiSystemConfig/add', methods=['POST'])
@async_route
@jwt_required(sso_url, permission_codes)
async def add_system_config(current_user: str = 'admin') -> Response:
    result, status = await AISystemConfigController.add_config(current_user)
    return result, status

@app.route('/aiSystemConfig/update', methods=['PUT'])
@async_route
@jwt_required(sso_url, permission_codes)
async def update_system_configs(current_user: str = 'admin') -> Response:
    result, status = await AISystemConfigController.update_configs(current_user)
    return result, status

# 注册知识库代理路由 Blueprint
from src.routes.kb_chat_routes import kb_chat_bp
app.register_blueprint(kb_chat_bp, url_prefix='/kb_chat')

# 文件处理API
@app.route('/aiFileProcessor/upload', methods=['POST'])
@async_route
@jwt_required(sso_url, permission_codes)
async def upload_and_process_files(current_user: str = 'admin') -> Response:
    return await AIFileProcessorController.upload_and_process_files(current_user)


@app.route('/aiFileProcessor/download', methods=['GET'])
def download_file() -> Response:
    """根据容器中的文件路径下载文件（无需鉴权，供浏览器直接访问）"""
    file_path = request.args.get('file_path', '')
    if not file_path:
        return jsonify({'error': '文件路径为必填字段'}), 400

    # 防止路径穿越
    if '..' in file_path:
        return jsonify({'error': '非法的文件路径'}), 400

    # 验证文件路径在允许的目录内
    base_dir = config_manager.get_file_container_path()
    real_path = os.path.realpath(file_path)
    real_base = os.path.realpath(base_dir)
    if not real_path.startswith(real_base + os.sep) and real_path != real_base:
        return jsonify({'error': '非法的文件路径'}), 400

    if not os.path.isfile(file_path):
        return jsonify({'error': '文件不存在'}), 404

    filename = os.path.basename(file_path)
    media_type, _ = mimetypes.guess_type(filename)
    if not media_type:
        media_type = 'application/octet-stream'

    encoded_filename = urllib.parse.quote(filename)
    with open(file_path, 'rb') as f:
        content = f.read()
    return Response(
        content,
        mimetype=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
    )

# AI聊天相关API
@app.route('/aiChat/model', methods=['POST'])
@async_route
@jwt_required(sso_url, permission_codes)
async def chat_with_model(current_user: str = 'admin') -> Response:
    return await AIChatController.chat_with_model(current_user)

@app.route('/aiChat/stream/resume', methods=['GET'])
@jwt_required(sso_url, permission_codes)
def resume_model_stream(current_user: str = 'admin') -> Response:
    """重连/续订 model 对话的输出流（SSE 断线重连，全量回放）。

    - 本轮未结束（starting/running）：从内存全量回放本轮事件（与原始流格式
      完全一致，无附加结构），随后无缝转入实时，直到流关闭（流关闭即本轮
      已结束并落库）；
    - 无活跃流（已结束清除 / 从未开始）：返回 404，前端应兜底查询已落库
      的对话记录。

    前端回放前需清空本轮 assistant 消息的进行中渲染。
    """
    session_thread_id = request.args.get('session_thread_id', '')
    if not session_thread_id:
        return jsonify({'error': '缺少 session_thread_id 参数'}), 400
    stream = stream_hub.get(session_thread_id)
    if stream is None or not stream.is_active:
        return jsonify({'code': 404, 'message': 'no active stream',
                        'data': {'exists': False}}), 404
    return Response(
        stream_hub.subscribe_sync(session_thread_id),
        mimetype='text/event-stream',
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

@app.route('/aiChat/stream/status', methods=['GET'])
@jwt_required(sso_url, permission_codes)
def model_stream_status(current_user: str = 'admin') -> Response:
    """查询 model 对话输出流状态（JSON），用于判断本轮对话是否结束。

    前端进入会话页 / 断线后可先调用本接口：
    - exists=true 且 status=running/starting → 本轮未结束，调 /aiChat/stream/resume
      全量回放 + 实时续订；
    - exists=false → 本轮已结束并落库（或从未开始），走已落库的对话记录。
    """
    session_thread_id = request.args.get('session_thread_id', '')
    if not session_thread_id:
        return jsonify({'error': '缺少 session_thread_id 参数'}), 400
    data = stream_hub.status(session_thread_id)
    return jsonify({"code": 0, "message": "success",
                    "data": data if data is not None else {"exists": False}})

@app.route('/aiChat/agent', methods=['POST'])
@async_route
@jwt_required(sso_url, permission_codes)
async def chat_with_agent(current_user: str = 'admin') -> Response:
    return await AIChatController.chat_with_agent(current_user)

@app.route('/aiChat/initialize', methods=['POST'])
@async_route
@jwt_required(sso_url, permission_codes)
async def initialize_agent(current_user: str = 'admin') -> Response:
    """初始化接口：初始化 MCP、KB Chat 和 Agent 实例"""
    from src.services.agent_init_service import AgentInitService

    # 获取原始 token
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    # 兜底：SSO 模式下也可能走 X-ACCESS-TOKEN
    if not token:
        token = request.headers.get('X-ACCESS-TOKEN', '')

    data = request.json or {}
    agent_uuid = data.get('agentUuid') or data.get('uuid')
    session_thread_id = data.get('sessionThreadId') or data.get('sessionId')
    user_uuid, err = MemoryController._resolve_user_uuid(current_user)

    if not agent_uuid:
        return jsonify({'error': '缺少必要参数：agentUuid'}), 400

    if not session_thread_id:
        return jsonify({'error': '缺少必要参数：sessionThreadId'}), 400

    # 调用 Service 层初始化所有资源（Service 层负责查询数据库）
    result = await AgentInitService.initialize_all(agent_uuid, session_thread_id, user_uuid, token)

    status_code = 200 if result.get('success') else 500
    return jsonify(result), status_code


@app.route('/llm', methods=['POST'])
@async_route
@jwt_required(sso_url, permission_codes)
async def chat_with_search_response(current_user: str = 'admin') -> Response:
    return await AIChatController.chat_with_search_response(current_user)


@app.route('/aiChatRecord/list', methods=['GET'])
@async_route
@jwt_required(sso_url, permission_codes)
async def list_chat_records(current_user: str = 'admin') -> Response:
    """查询对话记录：按 session_thread_id/chat_type/user_id/agent_id（可选）过滤"""
    return await AIChatRecordController.list_records(current_user)

@app.route('/aiChatRecord/list_files', methods=['GET'])
@async_route
@jwt_required(sso_url, permission_codes)
async def list_chat_files(current_user: str = 'admin') -> Response:
    """查询当前用户所有会话的 output 文件"""
    return await AIChatRecordController.list_files(current_user)

@app.route('/aiChatRecord/list_summary', methods=['GET'])
@async_route
@jwt_required(sso_url, permission_codes)
async def list_chat_summary(current_user: str = 'admin') -> Response:
    """查询当前用户所有会话的摘要"""
    return await AIChatSessionSummaryController.list_summaries(current_user)

@app.route('/aiChatRecord/check_summary', methods=['GET'])
@async_route
@jwt_required(sso_url, permission_codes)
async def check_chat_summary(current_user: str = 'admin') -> Response:
    """查询当前用户所有会话的摘要"""
    return await AIChatSessionSummaryController.check_summary(current_user)

@app.route('/aiChatRecord/edit_summary', methods=['POST'])
@async_route
@jwt_required(sso_url, permission_codes)
async def edit_chat_summary(current_user: str = 'admin') -> Response:
    """编辑当前用户的会话摘要"""
    return await AIChatSessionSummaryController.edit_summary(current_user)

@app.route('/aiChatRecord/delete', methods=['DELETE'])
@async_route
@jwt_required(sso_url, permission_codes)
async def delete_chat_records(current_user: str = 'admin') -> Response:
    """软删除对话记录：按 session_thread_id/chat_type/user_id/agent_id（可选）过滤"""
    return await AIChatRecordController.delete_records(current_user)


# AI技能相关API
@app.route('/aiSkill/upload', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def upload_ai_skill(current_user: str = 'admin') -> Response:
    return await AISkillController.upload_skill(current_user)

@app.route('/aiSkill/list', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
@permission_check(entity_type=EntityType.SKILL)
async def list_ai_skills(current_user: str = 'admin', allowed_entity_ids: list = None) -> Response:
    return await AISkillController.list_skills(current_user, allowed_entity_ids)

@app.route('/aiSkill/record', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
@permission_check(entity_type=EntityType.SKILL)
async def get_ai_skill(current_user: str = 'admin', allowed_entity_ids: list = None) -> Response:
    return await AISkillController.get_skill(current_user)

@app.route('/aiSkill/read', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def get_ai_skill_md(current_user: str = 'admin') -> Response:
    """查看 skills_repo 下某一文件夹内的 SKILL.md 文件内容"""
    return await AISkillController.get_skill_md(current_user)

@app.route('/aiSkill/delete', methods=['DELETE'])
@jwt_required(sso_url, permission_codes)
@async_route
@permission_check(entity_type=EntityType.SKILL)
async def delete_ai_skill(current_user: str = 'admin') -> Response:
    return await AISkillController.delete_skill(current_user)

@app.route('/aiSkill/update', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
@permission_check(entity_type=EntityType.SKILL)
async def update_ai_skill(current_user: str = 'admin') -> Response:
    return await AISkillController.update_skill(current_user)

# 实体权限相关API
@app.route('/aiEntityPermission/assignedGroups', methods=['GET'])
@async_route
@jwt_required(sso_url, permission_codes)
async def get_entity_assigned_groups(current_user: str = 'admin') -> Response:
    """获取实体分配的用户组列表"""
    return await AIEntityPermissionController.get_entity_assigned_groups(current_user)


# 截图服务API
@app.route('/api/screenshot', methods=['POST'])
@jwt_required(sso_url, permission_codes)
def take_screenshot(current_user: str = 'admin') -> Response:
    """网页截图接口"""
    return ScreenshotController.take_screenshot()

@app.route('/api/screenshot/health', methods=['GET'])
def screenshot_health() -> Response:
    """截图服务健康检查"""
    return ScreenshotController.health()


# DeepAgent 记忆管理 API（per-user 隔离，user_uuid 通过 current_user 查 AIUser 得到）
@app.route('/aiMemory/list', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def list_ai_memory(current_user: str = 'admin') -> Response:
    return MemoryController.list(current_user)

@app.route('/aiMemory/get', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def get_ai_memory(current_user: str = 'admin') -> Response:
    return MemoryController.get(current_user)

@app.route('/aiMemory/update', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def update_ai_memory(current_user: str = 'admin') -> Response:
    return MemoryController.update(current_user)

@app.route('/aiMemory/reset', methods=['POST'])
@jwt_required(sso_url, permission_codes)
@async_route
async def reset_ai_memory(current_user: str = 'admin') -> Response:
    return MemoryController.reset(current_user)

@app.route('/aiMemory/download', methods=['GET'])
@jwt_required(sso_url, permission_codes)
@async_route
async def download_ai_memory(current_user: str = 'admin') -> Response:
    return MemoryController.download(current_user)


# 主程序入口点
if __name__ == '__main__':
    port = ServerConfig.PORT
    host = ServerConfig.HOST
    # 初始化ToolAgentEngine

    initialize_tool_agent()
    # 以debug模式启动服务器
    app.run(host=host, port=port, debug=True)
