"""知识库代理路由模块"""
import os
from flask import Blueprint, Response
from src.controllers.ai_knowledge_base_controller import AIKnowledgeBaseController
from src.utils.jwt_required import jwt_required
from src.utils.permission_check import permission_check
from src.utils.entity_type import EntityType
from src.utils.async_route import async_route
from src.config import SSOConfig

kb_chat_bp = Blueprint('kb_chat', __name__)

sso_url = SSOConfig.URL
permission_codes = os.getenv('REQUIRED_PERMISSION_CODES', '37').split(',')


# 知识库文件下载（无需JWT认证，方便前端直接下载）
@kb_chat_bp.route('/knowledge_base/download_doc', methods=['GET'])
@async_route
async def proxy_kb_download_doc() -> Response:
    return await AIKnowledgeBaseController.proxy_kb_request('knowledge_base/download_doc', 'admin')


# 代理知识库API（需要JWT认证）
@kb_chat_bp.route('/', defaults={'api_path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE'])
@kb_chat_bp.route('/<path:api_path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@async_route
@jwt_required(sso_url, permission_codes)
@permission_check(entity_type=EntityType.KB_CHAT)
async def proxy_kb_chat_request(current_user: str = 'admin', api_path: str = '', allowed_entity_ids: list = None) -> Response:
    return await AIKnowledgeBaseController.proxy_kb_request(api_path, current_user)