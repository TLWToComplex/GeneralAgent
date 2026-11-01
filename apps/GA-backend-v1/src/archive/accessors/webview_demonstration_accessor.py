"""
Webview demonstration accessor module.
Handles database operations for web-based demonstration content.
"""
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Tuple, List, Union, Optional
from sqlalchemy import inspect

from accessors.database import db
from accessors.faq_accessor import Faq
from utils.embedding_utils import EmbeddingUtils

# 定义常量，解决字符串字面值重复问题
WEBURL_TAG = "[WebURL]:"
AIWU_MODE_TAG = "艾武模式"
VECTOR_DB_TYPE = os.getenv('VECTOR_DB_TYPE', '')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class WebviewDemonstration(db.Model):
    __tablename__ = 'webview_demonstrations'
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    url = db.Column(db.String(255), nullable=False)  # 网页 URL
    # reply 字段不再存储于数据库中
    faq_id = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        # 返回数据库中字段，不包含 reply 字段
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}


class WebviewDemonstrationAccessor:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebviewDemonstrationAccessor, cls).__new__(cls)
        return cls._instance

    @staticmethod
    def create_webview_demonstration(name: str, description: str, trigger_data: str, url: str, reply: str) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        创建新的网页演示项目：
          - 参数：name, description, trigger（列表或逗号分隔字符串）, url, reply。
          - FAQ 中的 answer 字段格式为 "{reply}[WebURL]:{url}"。
          - 不进行网页截图操作，直接存储 URL 信息（FAQ 中存储拼接后的 answer）。
          - 成功后将数据存入数据库，不在本表存储 reply 字段。
        """
        try:
            demo_id = str(uuid.uuid4())
            logger.debug(f"生成的 demo_id: {demo_id}")

            if not url:
                logger.error("url不能为空")
            if not reply:
                return False, "回复内容（reply）不能为空"

            answer_value = f"{reply}{WEBURL_TAG}{url}"

            # 处理触发词 trigger 数据（支持列表或逗号分隔字符串）
            if isinstance(trigger_data, list):
                triggers = [str(t).strip() for t in trigger_data if str(t).strip()]
            else:
                triggers = [t.strip() for t in str(trigger_data).split(',') if t.strip()]
            if not triggers:
                return False, "至少需要一个有效的触发词"

            faq_ids = []
            for t in triggers:
                question_v = EmbeddingUtils.get_embedding(t)
                if question_v is None:
                    return False, f"获取触发词 embedding 失败: {t}"
                new_faq_id = str(uuid.uuid4())
                faq_payload = {
                    "id": new_faq_id,
                    "question": t,
                    "question_v": question_v,
                    "answer": answer_value,
                    "tags": [AIWU_MODE_TAG] if VECTOR_DB_TYPE == 'milvus' else ','.join([AIWU_MODE_TAG]),
                    "create_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "update_date": ""
                }
                faq_success, faq_result = Faq.add_faq(faq_payload)
                if not faq_success:
                    return False, f"添加 FAQ 记录失败，触发词 {t}: {faq_result}"
                faq_ids.append(new_faq_id)
            faq_ids_str = ",".join(faq_ids)

            # 创建数据库记录（不存 reply 字段）
            web_demo = WebviewDemonstration(
                id=demo_id,
                name=name,
                description=description,
                url=url,
                faq_id=faq_ids_str
            )
            db.session.add(web_demo)
            db.session.commit()
            # 解析 reply 值后返回（此处直接返回前端传入的 reply，可根据需要从 FAQ answer 中解析）
            result = web_demo.to_dict()
            result["reply"] = reply
            return True, result
        except Exception as e:
            db.session.rollback()
            logger.error(f"创建网页演示工程出错: {str(e)}", exc_info=True)
            return False, str(e)

    @staticmethod
    def update_webview_demonstration(demo_id: str, name: str, description: str, trigger_data: str, url: str = None, reply: str = None) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        修改网页演示项目：
          - 若传入 url 与原记录不同，则更新 URL 及 FAQ 中的 answer（格式为 "{reply}[WebURL]:{url}"）。
          - 更新时 reply 字段仅用于拼接 FAQ answer，不存储到数据库中。
          - 若触发词 trigger_data 变化，则删除旧 FAQ 记录并重新创建新记录。
          - 若仅修改其他文本信息，则只更新数据库记录。
        """
        try:
            web_demo = WebviewDemonstration.query.get(demo_id)
            if not web_demo:
                logger.error("网页演示工程不存在")
                
            if not reply:
                logger.error("回复内容（reply）不能为空")

            url_changed = url is not None and url != web_demo.url

            web_demo.name = name
            web_demo.description = description

            if url_changed:
                web_demo.url = url
                new_answer_value = f"{reply}{WEBURL_TAG}{url}"
            else:
                new_answer_value = f"{reply}{WEBURL_TAG}{web_demo.url}"

            if trigger_data:
                if isinstance(trigger_data, list):
                    triggers = [str(t).strip() for t in trigger_data if str(t).strip()]
                else:
                    triggers = [t.strip() for t in str(trigger_data).split(',') if t.strip()]
                if not triggers:
                    return False, "至少需要一个有效的触发词"

                if web_demo.faq_id:
                    for fid in [fid.strip() for fid in web_demo.faq_id.split(',') if fid.strip()]:
                        Faq.delete_faq(fid)

                faq_ids = []
                for t in triggers:
                    question_v = EmbeddingUtils.get_embedding(t)
                    if question_v is None:
                        return False, f"获取触发词 embedding 失败: {t}"
                    new_faq_id = str(uuid.uuid4())
                    faq_payload = {
                        "id": new_faq_id,
                        "question": t,
                        "question_v": question_v,
                        "answer": new_answer_value,
                        "tags": [AIWU_MODE_TAG] if VECTOR_DB_TYPE == 'milvus' else ','.join([AIWU_MODE_TAG]),
                        "create_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "update_date": ""
                    }
                    faq_success, faq_result = Faq.add_faq(faq_payload)
                    if not faq_success:
                        return False, f"添加 FAQ 记录失败，触发词 {t}: {faq_result}"
                    faq_ids.append(new_faq_id)
                web_demo.faq_id = ",".join(faq_ids)

            db.session.commit()
            result = web_demo.to_dict()
            result["reply"] = reply
            return True, result
        except Exception as e:
            db.session.rollback()
            logger.error(f"修改网页演示工程时出错: {str(e)}", exc_info=True)
            return False, str(e)

    @staticmethod
    def get_webview_demonstration(demo_id: str) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        获取网页演示项目详情，返回数据库信息及 FAQ 中的触发词（question）和解析后的 reply 字段。
        从 FAQ 的 answer 中提取 reply 部分（格式："{reply}[WebURL]:{url}"）。
        """
        try:
            web_demo = WebviewDemonstration.query.get(demo_id)
            if not web_demo:
                return False, "网页演示工程不存在"
            result = web_demo.to_dict()

            # 默认 reply 为空
            reply_value = ""
            if web_demo.faq_id:
                faq_ids = [fid.strip() for fid in web_demo.faq_id.split(',') if fid.strip()]
                if faq_ids:
                    faq_data = Faq.get_faq_by_id(faq_ids[0])
                    if isinstance(faq_data, dict) and "error" not in faq_data:
                        answer_text = faq_data.get('answer', '')
                        # 解析 reply，格式为 "{reply}[WebURL]:{url}"
                        if WEBURL_TAG in answer_text:
                            reply_value = answer_text.split(WEBURL_TAG)[0]
            result["reply"] = reply_value

            # 同时处理触发词
            if web_demo.faq_id:
                if ',' in web_demo.faq_id:
                    faq_ids = [fid.strip() for fid in web_demo.faq_id.split(',') if fid.strip()]
                    triggers = []
                    for fid in faq_ids:
                        faq_data = Faq.get_faq_by_id(fid)
                        if isinstance(faq_data, dict) and "error" not in faq_data:
                            triggers.append(faq_data.get('question', ''))
                    result['trigger'] = ",".join(triggers)
                else:
                    faq_data = Faq.get_faq_by_id(web_demo.faq_id)
                    if isinstance(faq_data, dict) and "error" not in faq_data:
                        result['trigger'] = faq_data.get('question', '')
                    else:
                        result['trigger'] = ""
            else:
                result['trigger'] = ""

            return True, result
        except Exception as e:
            logger.error(f"获取网页演示工程详情出错: {str(e)}", exc_info=True)
            return False, str(e)

    @staticmethod
    def list_webview_demonstrations() -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """
        列出所有网页演示项目，返回数据库中所有信息、FAQ 中的触发词（question）和解析后的 reply 字段。
        从 FAQ 的 answer 字段中提取 reply（格式："{reply}[WebURL]:{url}"）。
        """
        try:
            demos = WebviewDemonstration.query.order_by(WebviewDemonstration.created_at.desc()).all()
            result = []
            for demo in demos:
                demo_dict = demo.to_dict()
                # 解析 reply
                reply_value = ""
                if demo.faq_id:
                    faq_ids = [fid.strip() for fid in demo.faq_id.split(',') if fid.strip()]
                    if faq_ids:
                        faq_data = Faq.get_faq_by_id(faq_ids[0])
                        if isinstance(faq_data, dict) and "error" not in faq_data:
                            answer_text = faq_data.get('answer', '')
                            if WEBURL_TAG in answer_text:
                                reply_value = answer_text.split(WEBURL_TAG)[0]
                demo_dict["reply"] = reply_value

                # 解析触发词 trigger
                if demo.faq_id:
                    if ',' in demo.faq_id:
                        faq_ids = [fid.strip() for fid in demo.faq_id.split(',') if fid.strip()]
                        triggers = []
                        for fid in faq_ids:
                            faq_data = Faq.get_faq_by_id(fid)
                            if isinstance(faq_data, dict) and "error" not in faq_data:
                                triggers.append(faq_data.get('question', ''))
                        demo_dict['trigger'] = ",".join(triggers)
                    else:
                        faq_data = Faq.get_faq_by_id(demo.faq_id)
                        if isinstance(faq_data, dict) and "error" not in faq_data:
                            demo_dict['trigger'] = faq_data.get('question', '')
                        else:
                            demo_dict['trigger'] = ''
                else:
                    demo_dict['trigger'] = ''
                result.append(demo_dict)
            return True, result
        except Exception as e:
            logger.error(f"列出网页演示工程出错: {str(e)}", exc_info=True)
            return False, str(e)

    @staticmethod
    def delete_webview_demonstration(demo_id: str) -> Tuple[bool, str]:
        """
        删除网页演示项目：
          - 删除 FAQ 向量库中的记录；
          - 删除数据库中的记录。
        """
        try:
            web_demo = WebviewDemonstration.query.get(demo_id)
            if not web_demo:
                return False, "网页演示工程不存在"

            if web_demo.faq_id:
                for fid in [fid.strip() for fid in web_demo.faq_id.split(',') if fid.strip()]:
                    faq_success, faq_result = Faq.delete_faq(fid)
                    if not faq_success:
                        logger.warning(f"删除 FAQ 记录失败, faq_id: {fid}, 错误: {faq_result}")

            db.session.delete(web_demo)
            db.session.commit()
            return True, "网页演示工程删除成功"
        except Exception as e:
            db.session.rollback()
            logger.error(f"删除网页演示工程时出错: {str(e)}", exc_info=True)
            return False, str(e)


# 全局实例
webview_demonstration_accessor = WebviewDemonstrationAccessor()
