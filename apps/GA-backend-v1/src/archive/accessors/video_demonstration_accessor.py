"""
Video demonstration accessor module.
Handles database operations for video demonstration content.
"""
import os
import uuid
import tempfile
import logging
import secrets
from datetime import datetime
import cv2

from sqlalchemy import inspect

from accessors.database import db
from accessors.file_data_accessor import minio_accessor
from accessors.faq_accessor import Faq
from utils.embedding_utils import EmbeddingUtils
from typing import Dict, Any, Tuple, List, Union, Optional, BinaryIO

# 定义常量，解决字符串字面值重复问题
VIDEO_DEMO_DIR = "video_demonstration"
HTTPS_SCHEME = "https"
HTTP_SCHEME = "http"
VIDEO_TAG = "[Video]:"
AIWU_MODE_TAG = "艾武模式"
HOST_DOCKER_INTERNAL = "host.docker.internal"
LOCALHOST = "localhost"
VECTOR_DB_TYPE = os.getenv('VECTOR_DB_TYPE', '')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 新建视频演示模型
class VideoDemonstration(db.Model):
    __tablename__ = 'video_demonstrations'
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    video_path = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    cover_image_path = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, running, failed
    faq_id = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {c.key: getattr(self, c.key)
                for c in inspect(self).mapper.column_attrs}


class VideoDemonstrationAccessor:
    _instance = None
    ALLOWED_EXTENSIONS = ['mp4', 'avi', 'mov', 'mkv']

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VideoDemonstrationAccessor, cls).__new__(cls)
        return cls._instance

    def create_video_demonstration(
        self, 
        name: str, 
        description: str, 
        trigger_data: str, 
        file_data, 
        original_filename: str, 
        reply: str
    ) -> Tuple[bool, Union[Dict[str, Any], str]]:
        try:
            demo_id = str(uuid.uuid4())
            logger.debug(f"生成的 demo_id: {demo_id}")

            # 检查文件扩展名
            if '.' in original_filename:
                extension = original_filename.rsplit('.', 1)[1].lower()
            else:
                extension = ''
            if extension not in self.ALLOWED_EXTENSIONS:
                logger.error("文件类型不支持，仅允许： " + ", ".join(self.ALLOWED_EXTENSIONS))
            

            # 读取视频数据到变量中
            video_bytes = file_data.read()

            # 构造 BytesIO 对象供上传使用
            from io import BytesIO
            video_stream = BytesIO(video_bytes)

            # 构建视频在 MinIO 中的对象名
            video_object_name = f"{VIDEO_DEMO_DIR}/{demo_id}/{demo_id}.{extension}"
            logger.debug(f"上传视频对象名: {video_object_name}")

            success, result = minio_accessor.upload_file(
                file_data=video_stream,
                object_name=video_object_name,
                content_type="video/mp4" if extension == 'mp4' else "application/octet-stream"
            )
            if not success:
                logger.error(f"视频文件上传失败: {result}")

            # 生成永久有效的 URL（因为Bucket已公开）

            video_url = f"{minio_accessor.file_sever_ip}/files/{minio_accessor.default_bucket}/{video_object_name}"
            # 用 reply 参数动态构造 answer_value
            answer_value = f"{reply}[Video]:{video_url}"

            # 将 video_bytes 写入临时文件用于截取封面图
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as tmp_video:
                tmp_video.write(video_bytes)
                tmp_video_path = tmp_video.name

            # 提取随机一帧作为封面
            success, cover_image_object_name = self._extract_cover_image(demo_id, tmp_video_path)
            os.remove(tmp_video_path)  # 清理临时文件
            if not success:
                return False, f"封面截取失败: {cover_image_object_name}"

            # 处理 trigger 数据（支持列表或逗号分隔字符串）
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

            # 创建数据库记录，状态设置为 running（视频上传和封面截取已完成）
            video_demo = VideoDemonstration(
                id=demo_id,
                name=name,
                description=description,
                video_path=video_object_name,
                original_filename=original_filename,
                cover_image_path=cover_image_object_name,
                status='running',
                faq_id=faq_ids_str
            )
            db.session.add(video_demo)
            db.session.commit()
            return True, video_demo.to_dict()

        except Exception as e:
            db.session.rollback()
            logger.error(f"创建视频演示工程出错: {str(e)}", exc_info=True)
            return False, str(e)

    @staticmethod
    def _extract_cover_image(demo_id: str, video_path: str) -> Tuple[bool, str]:
        """
        从视频中截取一个随机帧作为封面图片，
        并将其上传到 MinIO，返回上传后的对象名。
        """
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error("无法打开视频文件")
            
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if frame_count <= 0:
                cap.release()
                return False, "视频帧数为 0"
            random_frame = secrets.randbelow(frame_count)
            cap.set(cv2.CAP_PROP_POS_FRAMES, random_frame)
            ret, frame = cap.read()
            cap.release()
            if not ret:
                return False, "读取视频帧失败"

            # 将截取的帧保存为 JPEG 格式的临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
                tmp_img_path = tmp_img.name
                cv2.imwrite(tmp_img_path, frame)

            # 构造封面在 MinIO 中的对象名
            cover_object_name = f"{VIDEO_DEMO_DIR}/{demo_id}/cover.jpg"
            with open(tmp_img_path, 'rb') as f:
                success, result = minio_accessor.upload_file(
                    file_data=f,
                    object_name=cover_object_name,
                    content_type="image/jpeg"
                )
            os.remove(tmp_img_path)
            if not success:
                return False, f"上传封面图失败: {result}"
            return True, cover_object_name
        except Exception as e:
            logger.error(f"截取封面图时出错: {str(e)}", exc_info=True)
            return False, str(e)

    def update_video_demonstration(
        self, 
        demo_id: str, 
        name: str, 
        description: str, 
        trigger_data: str, 
        reply: str, 
        file_data = None, 
        original_filename: str = None
    ) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        修改视频演示工程：
          - 如果 file_data 存在，则更新视频文件（删除旧视频及封面，上传新文件并截取新封面，同时更新 answer）。
          - 若触发词 trigger_data 变化，则重新更新 FAQ 记录。
          - 仅更新数据库中的其它文本信息时，仅修改对应字段。
        """
        try:
            video_demo = VideoDemonstration.query.get(demo_id)
            if not video_demo:
                return False, "视频演示工程不存在"

            video_demo.name = name
            video_demo.description = description

            answer_value = None
            # 若上传新视频，则更新视频文件及封面
            if file_data:
                # 删除旧视频及封面
                minio_accessor.delete_file(video_demo.video_path)
                minio_accessor.delete_file(video_demo.cover_image_path)

                if '.' in original_filename:
                    extension = original_filename.rsplit('.', 1)[1].lower()
                else:
                    extension = ''
                if extension not in self.ALLOWED_EXTENSIONS:
                    return False, "文件类型不支持，仅允许：" + ", ".join(self.ALLOWED_EXTENSIONS)
                video_object_name = f"{VIDEO_DEMO_DIR}/{demo_id}/{demo_id}.{extension}"
                success, result = minio_accessor.upload_file(
                    file_data=file_data,
                    object_name=video_object_name,
                    content_type="video/mp4" if extension == 'mp4' else "application/octet-stream"
                )
                if not success:
                    return False, f"新视频文件上传失败: {result}"
                video_demo.video_path = video_object_name
                video_demo.original_filename = original_filename

                # 生成新视频的永久 URL
                video_url = f"{minio_accessor.file_sever_ip}/files/{minio_accessor.default_bucket}/{video_object_name}"
                answer_value = f"{reply}[Video]:{video_url}"

                # 保存上传后的视频文件到临时文件中，用于截取封面
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as tmp_video:
                    tmp_video.write(file_data.read())
                    tmp_video_path = tmp_video.name

                success, cover_object_name = self._extract_cover_image(demo_id, tmp_video_path)
                os.remove(tmp_video_path)
                if not success:
                    return False, f"新封面截取失败: {cover_object_name}"
                video_demo.cover_image_path = cover_object_name
            else:
                # 若没有更新视频，则保持原视频及封面不变，同时使用原视频构造永久 URL 用于 FAQ 更新
                video_url = f"{minio_accessor.file_sever_ip}/files/{minio_accessor.default_bucket}/{video_demo.video_path}"
                answer_value = f"{reply}[Video]:{video_url}"

            # 若触发词发生变化，则更新 FAQ 记录
            if trigger_data:
                if isinstance(trigger_data, list):
                    triggers = [str(t).strip() for t in trigger_data if str(t).strip()]
                else:
                    triggers = [t.strip() for t in str(trigger_data).split(',') if t.strip()]
                if not triggers:
                    return False, "至少需要一个有效的触发词"

                # 删除旧的 FAQ 记录
                if video_demo.faq_id:
                    for fid in [fid.strip() for fid in video_demo.faq_id.split(',') if fid.strip()]:
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
                        "answer": answer_value,
                        "tags": [AIWU_MODE_TAG] if VECTOR_DB_TYPE == 'milvus' else ','.join([AIWU_MODE_TAG]),
                        "create_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "update_date": ""
                    }
                    faq_success, faq_result = Faq.add_faq(faq_payload)
                    if not faq_success:
                        return False, f"添加 FAQ 记录失败，触发词 {t}: {faq_result}"
                    faq_ids.append(new_faq_id)
                video_demo.faq_id = ",".join(faq_ids)

            db.session.commit()
            return True, video_demo.to_dict()

        except Exception as e:
            db.session.rollback()
            logger.error(f"修改视频演示工程时出错: {str(e)}", exc_info=True)
            return False, str(e)

    @staticmethod
    def get_video_demonstration(demo_id: str) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        获取视频演示工程详情，附带视频及封面的永久URL，
        同时从FAQ模块获取触发词（question）以及reply信息。
        """
        try:
            video_demo = VideoDemonstration.query.get(demo_id)
            if not video_demo:
                return False, "视频演示工程不存在"
            result = video_demo.to_dict()

            # 构造视频和封面图片的绝对URL
            # 替换 URL 中的 host.docker.internal 为 localhost
            video_url = f"{minio_accessor.file_sever_ip}/files/{minio_accessor.default_bucket}/{video_demo.video_path}"
            cover_image_url = f"{minio_accessor.file_sever_ip}/files/{minio_accessor.default_bucket}/{video_demo.cover_image_path}"

            if HOST_DOCKER_INTERNAL in video_url:
                video_url = video_url.replace(HOST_DOCKER_INTERNAL, LOCALHOST)

            if HOST_DOCKER_INTERNAL in cover_image_url:
                cover_image_url = cover_image_url.replace(HOST_DOCKER_INTERNAL, LOCALHOST)

            result['video_url'] = video_url
            result['cover_image_url'] = cover_image_url

            # 移除原始文件路径字段，避免混淆
            result.pop("video_path", None)
            result.pop("cover_image_path", None)

            # 处理FAQ记录，返回触发词和reply信息
            reply_text = ""
            if video_demo.faq_id:
                if ',' in video_demo.faq_id:
                    faq_ids = [fid.strip() for fid in video_demo.faq_id.split(',') if fid.strip()]
                    triggers = []
                    for fid in faq_ids:
                        faq_data = Faq.get_faq_by_id(fid)
                        if isinstance(faq_data, dict) and "error" not in faq_data:
                            triggers.append(faq_data.get('question', ''))
                            if not reply_text:
                                answer = faq_data.get('answer', '')
                                if VIDEO_TAG in answer:
                                    reply_text = answer.split(VIDEO_TAG)[0]
                    result['trigger'] = ",".join(triggers)
                else:
                    faq_data = Faq.get_faq_by_id(video_demo.faq_id)
                    if isinstance(faq_data, dict) and "error" not in faq_data:
                        result['trigger'] = faq_data.get('question', '')
                        answer = faq_data.get('answer', '')
                        if VIDEO_TAG in answer:
                            reply_text = answer.split(VIDEO_TAG)[0]
                    else:
                        result['trigger'] = ''
            else:
                result['trigger'] = ""
            result['reply'] = reply_text

            return True, result

        except Exception as e:
            logger.error(f"获取视频演示工程详情出错: {str(e)}", exc_info=True)
            return False, str(e)

    @staticmethod
    def list_video_demonstrations() -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """
        列出所有视频演示工程，返回数据库中的全部信息，
        同时返回FAQ中的触发词（question）、reply、视频与封面的永久URL，
        以及视频文件的格式（全大写）。
        """
        try:
            demos = VideoDemonstration.query.order_by(VideoDemonstration.created_at.desc()).all()
            result = []
            for demo in demos:
                demo_dict = demo.to_dict()

                # 构造视频和封面图片的绝对URL
                # 替换 URL 中的 host.docker.internal 为 localhost
                video_url = f"{minio_accessor.file_sever_ip}/files/{minio_accessor.default_bucket}/{demo.video_path}"
                cover_image_url = f"{minio_accessor.file_sever_ip}/files/{minio_accessor.default_bucket}/{demo.cover_image_path}"

                if HOST_DOCKER_INTERNAL in video_url:
                    video_url = video_url.replace(HOST_DOCKER_INTERNAL, LOCALHOST)

                if HOST_DOCKER_INTERNAL in cover_image_url:
                    cover_image_url = cover_image_url.replace(HOST_DOCKER_INTERNAL, LOCALHOST)

                demo_dict['video_url'] = video_url
                demo_dict['cover_image_url'] = cover_image_url

                # 从original_filename中提取视频格式（扩展名）并转换为全大写
                if demo_dict.get('original_filename') and '.' in demo_dict['original_filename']:
                    video_format = demo_dict['original_filename'].rsplit('.', 1)[1].upper()
                else:
                    video_format = ''
                demo_dict['video_format'] = video_format

                # 移除原始的文件路径字段，避免混淆
                demo_dict.pop("video_path", None)
                demo_dict.pop("cover_image_path", None)

                # 处理FAQ记录，返回触发词和reply信息
                reply_text = ""
                if demo.faq_id:
                    if ',' in demo.faq_id:
                        faq_ids = [fid.strip() for fid in demo.faq_id.split(',') if fid.strip()]
                        triggers = []
                        for fid in faq_ids:
                            faq_data = Faq.get_faq_by_id(fid)
                            if isinstance(faq_data, dict) and "error" not in faq_data:
                                triggers.append(faq_data.get('question', ''))
                                if not reply_text:
                                    answer = faq_data.get('answer', '')
                                    if VIDEO_TAG in answer:
                                        reply_text = answer.split(VIDEO_TAG)[0]
                        demo_dict['trigger'] = ",".join(triggers)
                    else:
                        faq_data = Faq.get_faq_by_id(demo.faq_id)
                        if isinstance(faq_data, dict) and "error" not in faq_data:
                            demo_dict['trigger'] = faq_data.get('question', '')
                            answer = faq_data.get('answer', '')
                            if VIDEO_TAG in answer:
                                reply_text = answer.split(VIDEO_TAG)[0]
                        else:
                            demo_dict['trigger'] = ''
                else:
                    demo_dict['trigger'] = ''
                demo_dict['reply'] = reply_text

                result.append(demo_dict)
            return True, result

        except Exception as e:
            logger.error(f"列出视频演示工程出错: {str(e)}", exc_info=True)
            return False, str(e)

    @staticmethod
    def delete_video_demonstration(demo_id: str) -> Tuple[bool, str]:
        """
        删除视频演示工程：
          - 删除 MinIO 中上传的视频文件和封面文件；
          - 删除 FAQ 向量库中的记录；
          - 删除数据库中的记录。
        """
        try:
            video_demo = VideoDemonstration.query.get(demo_id)
            if not video_demo:
                logger.error("视频演示工程不存在")

            # 删除 FAQ 记录
            if video_demo.faq_id:
                for fid in [fid.strip() for fid in video_demo.faq_id.split(',') if fid.strip()]:
                    faq_success, faq_result = Faq.delete_faq(fid)
                    if not faq_success:
                        logger.warning(f"删除 FAQ 记录失败, faq_id: {fid}, 错误: {faq_result}")

            # 删除视频文件及封面文件
            minio_accessor.delete_file(video_demo.video_path)
            minio_accessor.delete_file(video_demo.cover_image_path)

            db.session.delete(video_demo)
            db.session.commit()
            return True, "视频演示工程删除成功"
        except Exception as e:
            db.session.rollback()
            logger.error(f"删除视频演示工程时出错: {str(e)}", exc_info=True)
            return False, str(e)

    @staticmethod
    def prepare_download_video_package_by_id(demo_id: str) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        根据视频演示工程的 id 准备下载包，
        将视频文件下载到临时目录后打包成 ZIP 文件，并返回 ZIP 文件路径。
        """
        try:
            video_demo = VideoDemonstration.query.get(demo_id)
            if not video_demo:
                return False, "视频演示工程不存在"

            import tempfile, shutil, os
            # 创建临时目录，用于保存视频文件
            temp_dir = tempfile.mkdtemp()

            # 下载视频文件
            success, video_data = minio_accessor.download_file(video_demo.video_path)
            if not success:
                shutil.rmtree(temp_dir)
                return False, f"视频文件下载失败: {video_data}"

            # 保存视频文件到临时目录
            video_local_path = os.path.join(temp_dir, video_demo.original_filename)
            with open(video_local_path, 'wb') as f:
                f.write(video_data)

            # 使用临时目录下的内容生成 ZIP 包
            base_name = os.path.join(tempfile.gettempdir(), f"{demo_id}_video_package")
            zip_path = shutil.make_archive(base_name, 'zip', temp_dir)

            # 清理临时目录
            shutil.rmtree(temp_dir)

            return True, zip_path
        except Exception as e:
            return False, str(e)


# 全局实例
video_demonstration_accessor = VideoDemonstrationAccessor()
