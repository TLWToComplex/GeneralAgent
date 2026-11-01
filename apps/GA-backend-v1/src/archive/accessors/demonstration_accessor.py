"""
Demonstration accessor module.
Handles database operations for system demonstrations including PPT/PPTX file processing.
"""
import os
import json
import fitz
import uuid
import shutil
import logging
import zipfile
import hashlib
import asyncio
import tempfile
import threading
import websockets
import subprocess
from io import BytesIO
from datetime import datetime
from flask import current_app
from sqlalchemy import inspect, func
from utils.md5_utils import demonstration_accessor_md, run_subprocess

from .database import db
from .faq_accessor import Faq
from accessors.file_data_accessor import minio_accessor
from controllers.proxy_controller import ProxyController
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.embedding_utils import EmbeddingUtils
DEMO_DIR = "demonstrations"
AIWU_MODE_TAG = "艾武模式"
VECTOR_DB_TYPE = os.getenv('VECTOR_DB_TYPE', '')
base = os.getenv("FILE_SERVER_BASE")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def get_tts_url() -> str:
    model_list = ProxyController.get_model_list_tts()
    for model in model_list.get('models', []):
        if model['type'] == 'TTS' and model['id'] == 'TTS_AIWU':
            return model['url']
    return None

def create_deterministic_zip(source_dir, output_zip_path):
    """
    使用固定文件属性创建确定性的ZIP文件，保证只要源文件不变，
    ZIP文件内容及其sha256也保持一致。
    """
    source_dir = str(source_dir)
    output_zip_path = str(output_zip_path)
    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        file_list = []
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, source_dir)
                file_list.append((full_path, relative_path))
        file_list.sort(key=lambda x: x[1])
        fixed_date = (1980, 1, 1, 0, 0, 0)
        for full_path, relative_path in file_list:
            info = zipfile.ZipInfo(relative_path)
            info.date_time = fixed_date
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(full_path, "rb") as f:
                data = f.read()
            zipf.writestr(info, data)

# 定义全局缓存目录，用于存放预生成的ZIP包
BULK_PACKAGE_CACHE_DIR = os.path.join(tempfile.gettempdir(), "bulk_zip_cache")
if not os.path.exists(BULK_PACKAGE_CACHE_DIR):
    os.makedirs(BULK_PACKAGE_CACHE_DIR)

class Demonstration(db.Model):
    __tablename__ = 'demonstrations'
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    total_slides = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.now, onupdate=datetime.now)
    slides = db.relationship('DemonstrationSlide', backref='demonstration', lazy=True, cascade="all, delete-orphan")
    faq_id = db.Column(db.Text, nullable=True)
    mode = db.Column(db.String(10), nullable=False, default='1')

    def to_dict(self):
        return {c.key: getattr(self, c.key)
                for c in inspect(self).mapper.column_attrs}

class DemonstrationSlide(db.Model):
    __tablename__ = 'demonstration_slides'
    id = db.Column(db.String(36), primary_key=True)
    demonstration_id = db.Column(db.String(36), db.ForeignKey('demonstrations.id', ondelete='CASCADE'), nullable=False)
    slide_number = db.Column(db.Integer, nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    narration = db.Column(db.Text, nullable=True)
    audio_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)

    __table_args__ = (
        db.UniqueConstraint('demonstration_id', 'slide_number', name='uq_demo_slide'),
    )

    def to_dict(self):
        return {c.key: getattr(self, c.key)
                for c in inspect(self).mapper.column_attrs}

class DemonstrationAccessor:
    _instance = None
    ENV = os.getenv('FLASK_ENV', 'development').lower()
    lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DemonstrationAccessor, cls).__new__(cls)
        return cls._instance

    # 计算所有状态为 running 的演示项目的缓存键
    @staticmethod
    def get_bulk_package_cache_key():
        try:
            demos = Demonstration.query.filter_by(status="running").all()
            demos = sorted(demos, key=lambda d: d.id)
            key_str = ""
            for demo in demos:
                key_str += demo.id + (demo.updated_at.strftime("%Y%m%d%H%M%S") if demo.updated_at else "")
            if not key_str:
                key_str = "empty"
            return demonstration_accessor_md(key_str)
        except Exception as e:
            logger.error(f"Error computing bulk package cache key: {str(e)}", exc_info=True)
            return "error"

    @staticmethod
    def invalidate_bulk_package_cache():
        try:
            os.makedirs(BULK_PACKAGE_CACHE_DIR, exist_ok=True)
            for filename in os.listdir(BULK_PACKAGE_CACHE_DIR):
                file_path = os.path.join(BULK_PACKAGE_CACHE_DIR, filename)
                os.remove(file_path)
            logger.debug("Bulk package cache invalidated.")
        except Exception as e:
            logger.error(f"Error invalidating bulk package cache: {str(e)}", exc_info=True)

    # 重新生成ZIP包缓存（后台执行时需设置应用上下文）
    def regenerate_bulk_package_cache(self):
        try:
            # 获取当前应用实例
            app = current_app._get_current_object()
            def task():
                with app.app_context():
                    success, package_path = self.prepare_bulk_download_package()
                    if success:
                        logger.debug("Bulk package cache regenerated at %s", package_path)
                    else:
                        logger.error("Failed to regenerate bulk package cache: %s", package_path)
            thread = threading.Thread(target=task)
            thread.start()
        except Exception as e:
            logger.error(f"Error regenerating bulk package cache: {str(e)}", exc_info=True)

    # 创建阶段不刷新ZIP缓存，因为状态还未转为 running
    def create_demonstration(self, name: str, description: str, mode: str, file_data: bytes, original_filename: str, faq_id: str):
        try:
            demo_id = str(uuid.uuid4())
            logger.debug(f"生成的demo_id: {demo_id}")
            file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
            logger.debug(f"文件扩展名: {file_extension}")
            if file_extension not in ['ppt', 'pptx']:
                logger.error("File type not supported. Only PPT or PPTX allowed.")
            object_name = f"{DEMO_DIR}/{demo_id}/{demo_id}.{file_extension}"
            logger.debug(f"上传MinIO的对象名: {object_name}")
            success, result = minio_accessor.upload_file(
                file_data=file_data,
                object_name=object_name,
                content_type="application/vnd.ms-powerpoint" if file_extension == 'ppt' else
                             "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )
            logger.debug(f"上传文件结果: success={success}, result={result}")

            demo = Demonstration(
                id=demo_id,
                name=name,
                description=description,
                mode=mode,
                file_path=object_name,
                original_filename=original_filename,
                status='pending',
                faq_id=faq_id
            )
            db.session.add(demo)
            db.session.commit()
            logger.debug("创建演示项目记录成功，并提交到数据库。")
            app_instance = current_app._get_current_object()
            thread = threading.Thread(target=self._background_conversion, args=(demo_id, app_instance))
            thread.start()
            return True, demo.to_dict()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating demonstration: {str(e)}", exc_info=True)
            return False, str(e)

    def _background_conversion(self, demo_id: str, app):
        with app.app_context():
            self.start_conversion(demo_id)

    def start_conversion(self, demo_id: str):
        try:
            demo = Demonstration.query.get(demo_id)
            if not demo:
                logger.error("Demonstration not found")
            demo.status = 'processing'
            db.session.commit()
            logger.debug(f"演示项目 {demo_id} 状态更新为 processing。")
            success, result = self.convert_ppt_to_images(demo_id)
            logger.debug(f"转换结果: success={success}, result={result}")
            return success, result
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error starting conversion: {str(e)}", exc_info=True)
            return False, str(e)

    def retry_conversion(self, demo_id: str):
        try:
            demo = Demonstration.query.get(demo_id)
            if not demo:
                return False, f"找不到ID为 {demo_id} 的演示项目"
            demo.status = "processing"
            db.session.commit()
            app_instance = current_app._get_current_object()
            def background_task(app):
                with app.app_context():
                    try:
                        try:
                            DemonstrationSlide.query.filter_by(demonstration_id=demo_id).delete()
                            db.session.commit()
                            logging.debug(f"已清除演示项目 {demo_id} 的现有幻灯片")
                        except Exception as clear_error:
                            logging.error(f"清除幻灯片记录时出错: {str(clear_error)}")
                            db.session.rollback()
                            self._update_demo_status(demo_id, "failed")
                            return
                        success, result = self.convert_ppt_to_images(demo_id)
                        if not success:
                            logging.error(f"转换过程失败: {result}")
                            self._update_demo_status(demo_id, "failed")
                        else:
                            self._update_demo_status(demo_id, "completed")
                            logging.debug(f"演示项目 {demo_id} 转换完成")
                    except Exception as error:
                        logging.error(f"后台转换过程出错: {str(error)}")
                        self._update_demo_status(demo_id, "failed")
            thread = threading.Thread(target=background_task, args=(app_instance,))
            thread.daemon = True
            thread.start()
            return True, "Conversion restarted successfully"
        except Exception as e:
            db.session.rollback()
            logging.error(f"启动异步转换任务时出错: {str(e)}")
            return False, str(e)


    def update_demonstration(
        self, 
        demo_id: str, 
        name: str, 
        description: str, 
        mode: str, 
        trigger: str, 
        path: str, 
        file_data: bytes = None, 
        original_filename: str = None
    ):
        try:
            demo = Demonstration.query.get(demo_id)
            if not demo:
                logger.error(f"Demonstration not found")
            demo.name = name
            demo.description = description
            demo.mode = mode
            db.session.commit()
            if file_data:
                success, _ = minio_accessor.delete_file(demo.file_path)
                if not success:
                    logger.warning(f"Failed to delete old PPT file: {demo.file_path}")
                slides_list = DemonstrationSlide.query.filter_by(demonstration_id=demo_id).all()
                for slide in slides_list:
                    success, _ = minio_accessor.delete_file(slide.image_path)
                    if not success:
                        logger.warning(f"Failed to delete slide image: {slide.image_path}")
                    if slide.audio_path:
                        success, _ = minio_accessor.delete_file(slide.audio_path)
                        if not success:
                            logger.warning(f"Failed to delete slide audio: {slide.audio_path}")
                    db.session.delete(slide)
                db.session.commit()
                info_path = f"{DEMO_DIR}/{demo_id}/ppt_info.txt"
                minio_accessor.delete_file(info_path)
                audio_count_path = f"{DEMO_DIR}/{demo_id}/audio/audioCount.json"
                minio_accessor.delete_file(audio_count_path)
                file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
                if file_extension not in ['ppt', 'pptx']:
                    logger.error(f"Only PPT and PPTX files are supported")
                object_name = f"{DEMO_DIR}/{demo_id}/{demo_id}.{file_extension}"
                success, result = minio_accessor.upload_file(
                    file_data=file_data,
                    object_name=object_name,
                    content_type="application/vnd.ms-powerpoint" if file_extension == 'ppt' else
                                 "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                )
                if not success:
                    logger.error(f"Failed to upload new file: {result}")
                demo.file_path = object_name
                demo.original_filename = original_filename
                demo.status = 'pending'
                demo.total_slides = 0
                db.session.commit()
                app_instance = current_app._get_current_object()
                thread = threading.Thread(target=self._background_conversion, args=(demo_id, app_instance))
                thread.start()
            success_faq, new_faq_ids_str = self._update_faq_records(demo, trigger, path)
            if not success_faq:
                logger.error(new_faq_ids_str)
            demo.faq_id = new_faq_ids_str
            db.session.commit()
            # 如果更新后项目状态为running，则刷新ZIP缓存
            if demo.status == 'running':
                self.invalidate_bulk_package_cache()
                self.regenerate_bulk_package_cache()
            return True, demo.to_dict()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating demonstration: {str(e)}", exc_info=True)
            return False, str(e)

    @staticmethod
    def _update_faq_records(demo: Demonstration, trigger: str, path: str):
        try:
            if demo.faq_id:
                old_faq_ids = [fid.strip() for fid in demo.faq_id.split(',') if fid.strip()]
                for fid in old_faq_ids:
                    Faq.delete_faq(fid)
            triggers = [t.strip() for t in trigger.split(',') if t.strip()]
            if not triggers:
                return False, "至少需要一个有效的触发词"
            new_faq_ids = []
            faq_details = []
            answer_value = path
            for t in triggers:
                question_v = EmbeddingUtils.get_embedding(t)
                if question_v is None:
                    return False, f"Failed to get embedding for trigger: {t}"
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
                    logger.error(f"Failed to add FAQ for trigger {t}: {faq_result}")
                new_faq_ids.append(new_faq_id)
                faq_details.append((t, question_v, new_faq_id))
            new_faq_ids_str = ",".join(new_faq_ids)
            if f"<{demo.id}>" not in answer_value:
                if "StreamingAssets" in answer_value:
                    updated_answer = answer_value.replace("StreamingAssets", f"StreamingAssets<{demo.id}>")
                else:
                    updated_answer = answer_value + f"<{demo.id}>"
            else:
                updated_answer = answer_value
            update_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for (t, question_v, faq_id) in faq_details:
                update_data = {
                    "id": faq_id,
                    "question": t,
                    "question_v": question_v,
                    "answer": updated_answer,
                    "tags": [AIWU_MODE_TAG] if VECTOR_DB_TYPE == 'milvus' else ','.join([AIWU_MODE_TAG]),
                    "create_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "update_date": update_date
                }
                faq_result = Faq.upsert_faq(update_data)
                if not (faq_result and faq_result[0]):
                        logger.error(f"Failed to update FAQ record for trigger {t}: "
                               f"{faq_result[1] if faq_result else '未知错误'}")
            return True, new_faq_ids_str
        except Exception as e:
            return False, str(e)

    def convert_ppt_to_images(self, demo_id: str):
        try:
            demo = Demonstration.query.get(demo_id)
            if not demo:
                logger.error("Demonstration not found")
            logger.debug(f"开始下载PPT文件: {demo.file_path}")
            success, ppt_data = minio_accessor.download_file(demo.file_path)
            logger.debug(f"下载PPT文件结果: success={success}, "
                          f"数据长度={len(ppt_data) if ppt_data else 'None'}")
            if not success:
                self._update_demo_status(demo_id, 'failed')
                logger.error(f"Failed to download PPT: {ppt_data}")
            with tempfile.TemporaryDirectory() as temp_dir:
                logger.debug(f"创建临时目录: {temp_dir}")
                file_extension = demo.file_path.split('.')[-1]
                ppt_path = os.path.join(temp_dir, f"presentation.{file_extension}")
                with open(ppt_path, 'wb') as f:
                    f.write(ppt_data)
                logger.debug(f"PPT文件保存到临时路径: {ppt_path}")
                success, pdf_result = self._convert_to_pdf(ppt_path, temp_dir)
                if not success:
                    self._update_demo_status(demo_id, 'failed')
                    logger.error(pdf_result)
                pdf_path = pdf_result
                logger.debug(f"PDF转换成功: {pdf_path}")
                success, slide_paths = self._convert_pdf_to_images(pdf_path, temp_dir)
                logger.debug(f"PDF转图片结果: success={success}, slide_paths={slide_paths}")
                if not success:
                    self._update_demo_status(demo_id, 'failed')
                    return False, slide_paths
                for i, slide_path in enumerate(slide_paths, 1):
                    with open(slide_path, 'rb') as slide_file:
                        object_name = f"{DEMO_DIR}/{demo_id}/slides/slide_{i}.png"
                        logger.debug(f"上传幻灯片{i}到MinIO, 对象名: {object_name}")
                        success, result = minio_accessor.upload_file(
                            file_data=slide_file,
                            object_name=object_name,
                            content_type="image/png"
                        )
                        logger.debug(f"上传幻灯片{i}结果: success={success}, result={result}")
                        if not success:
                            self._update_demo_status(demo_id, 'failed')
                            return False, f"Failed to upload slide {i}: {result}"
                        slide = DemonstrationSlide(
                            id=str(uuid.uuid4()),
                            demonstration_id=demo_id,
                            slide_number=i,
                            image_path=object_name
                        )
                        db.session.add(slide)
                demo.total_slides = len(slide_paths)
                demo.status = 'completed'
                db.session.commit()
                logger.debug(f"转换成功，共 {len(slide_paths)} 幻灯片，状态更新为 completed。")
                return True, {"total_slides": len(slide_paths)}
        except Exception as e:
            self._update_demo_status(demo_id, 'failed')
            logger.error(f"Error converting PPT: {str(e)}", exc_info=True)
            return False, str(e)

    @staticmethod
    def _convert_to_pdf(ppt_path: str, output_dir: str):
        logger.debug(f"当前环境: {DemonstrationAccessor.ENV}")
        pdf_path = os.path.join(output_dir, "presentation.pdf")

        if DemonstrationAccessor.ENV == "development":
            try:
                import comtypes.client
                import comtypes

                comtypes.CoInitialize()
                powerpoint = comtypes.client.CreateObject("Powerpoint.Application")
                powerpoint.Visible = 1
                presentation = powerpoint.Presentations.Open(ppt_path, WithWindow=False)
                presentation.SaveAs(pdf_path, 32)
                presentation.Close()
                powerpoint.Quit()
                comtypes.CoUninitialize()
                if os.path.exists(pdf_path):
                    return True, pdf_path
            except Exception as e:
                logger.error(f"使用COM转换PPT为PDF失败: {str(e)}", exc_info=True)
                try:
                    import comtypes.client
                    import comtypes

                    comtypes.CoUninitialize()
                except Exception:
                    pass
            libreoffice_path = shutil.which("libreoffice") or shutil.which("soffice")
            if libreoffice_path:
                try:
                    cmd = [libreoffice_path, "--headless", "--convert-to", "pdf", "--outdir", output_dir, ppt_path]
                    logger.debug(f"执行LibreOffice命令: {' '.join(cmd)}")
                    process = run_subprocess(cmd)
                    stdout, stderr = process.communicate()
                    logger.debug(f"LibreOffice输出: {stdout.decode('utf-8')}, 错误: {stderr.decode('utf-8')}")
                    if os.path.exists(pdf_path):
                        return True, pdf_path
                    else:
                        return False, "LibreOffice转换失败，未生成PDF。"
                except Exception as e:
                    logger.error(f"使用LibreOffice转换PPT为PDF失败: {str(e)}", exc_info=True)
                    # return False, f"转换失败: {str(e)}"
            else:
                return False, "在Windows环境中，未安装comtypes或LibreOffice，无法转换PPT为PDF。"
        else:
            libreoffice_path = shutil.which("libreoffice") or shutil.which("soffice")
            if libreoffice_path:
                try:
                    cmd = [libreoffice_path, "--headless", "--convert-to", "pdf", "--outdir", output_dir, ppt_path]
                    logger.debug(f"执行LibreOffice命令: {' '.join(cmd)}")
                    process = run_subprocess(cmd)
                    stdout, stderr = process.communicate()
                    logger.debug(f"LibreOffice输出: {stdout.decode('utf-8')}, 错误: {stderr.decode('utf-8')}")
                    if os.path.exists(pdf_path):
                        return True, pdf_path
                    else:
                        return False, "LibreOffice转换失败，未生成PDF。"
                except Exception as e:
                    logger.error(f"使用LibreOffice转换PPT为PDF失败: {str(e)}", exc_info=True)
                    # return False, f"转换失败: {str(e)}"
            else:
                return False, "未找到LibreOffice，无法转换PPT为PDF。"

    @staticmethod
    def _convert_pdf_to_images(pdf_path: str, output_dir: str):
        try:
            logger.debug("使用PyMuPDF转换PDF为图片。")
            pdf_document = fitz.open(pdf_path)
            slide_paths = []
            zoom = 150 / 72
            matrix = fitz.Matrix(zoom, zoom)
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                pix = page.get_pixmap(matrix=matrix)
                image_path = os.path.join(output_dir, f"slide_{page_num + 1}.jpg")
                pix.save(image_path, output="jpeg")
                slide_paths.append(image_path)
            pdf_document.close()
            if not slide_paths:
                return False, "未能从PDF生成任何幻灯片图片。"
            return True, slide_paths
        except Exception as e:
            logger.error(f"转换PDF为图片出错: {str(e)}", exc_info=True)
            return False, f"转换PDF为图片出错: {str(e)}"

    @staticmethod
    def _update_demo_status(demo_id: str, status: str):
        try:
            demo = Demonstration.query.get(demo_id)
            if demo:
                demo.status = status
                db.session.commit()
                logger.debug(f"更新演示项目 {demo_id} 状态为 {status}。")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating demonstration status: {str(e)}", exc_info=True)

    def save_narrations(self, demo_id: str, narrations: list):
        try:
            demo = Demonstration.query.get(demo_id)
            if not demo:
                logger.error("Demonstration not found")
            if demo.status != 'completed':
                logger.error("Demonstration is not yet completed. Please wait for the conversion to finish.")
            if len(narrations) != demo.total_slides:
                logger.error(f"Narration count mismatch. Expected {demo.total_slides}, got {len(narrations)}")
            base_path = f"{DEMO_DIR}/{demo_id}"
            slides = DemonstrationSlide.query.filter_by(demonstration_id=demo_id).order_by(
                DemonstrationSlide.slide_number).all()
            ppt_info_content = ""
            for i, slide in enumerate(slides):
                narration_text = narrations[i]
                slide.narration = narration_text
                cleaned_narration = narration_text.replace('\n', ' ').replace('\r', ' ')
                ppt_info_content += cleaned_narration + "\n"
            ppt_info_path = f"{base_path}/ppt_info.txt"
            success, result = minio_accessor.upload_file(
                file_data=BytesIO(ppt_info_content.encode('utf-8')),
                object_name=ppt_info_path,
                content_type="text/plain"
            )
            if not success:
                logger.error(f"Failed to upload ppt_info.txt: {result}")
            audio_count = {"count": len(narrations)}
            audio_count_path = f"{base_path}/audio/audioCount.json"
            success, result = minio_accessor.upload_file(
                file_data=BytesIO(json.dumps(audio_count).encode('utf-8')),
                object_name=audio_count_path,
                content_type="application/json"
            )
            if not success:
                logger.error(f"Failed to upload audioCount.json: {result}")
            demo.status = 'audio_processing'
            db.session.commit()
            app_instance = current_app._get_current_object()
            thread = threading.Thread(target=self._background_tts, args=(demo_id, app_instance))
            thread.start()
            return True, {"message": "Narrations saved successfully. Audio generation started."}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving narrations: {str(e)}", exc_info=True)
            return False, str(e)

    def _background_tts(self, demo_id: str, app):
        with app.app_context():
            self.generate_audio(demo_id)

    @staticmethod
    async def _connect_tts_websocket(narrations: list):
        TTS_URL = get_tts_url()
        try:
            audio_results = []
            for narration in narrations:
                async with websockets.connect(
                        TTS_URL,
                        max_size=None,
                        ping_interval=30,
                        ping_timeout=30
                ) as websocket:
                    await websocket.send(json.dumps([narration]))
                    audio_data = None
                    while audio_data is None:
                        message = await websocket.recv()
                        if isinstance(message, bytes):
                            audio_data = message
                        elif isinstance(message, str) and not message.startswith("Segment"):
                            audio_data = message.encode("utf-8")
                        else:
                            logger.info(f"忽略状态消息: {message}")
                    # 合成完成后发送停止指令关闭 websocket
                    await websocket.send(json.dumps({"stop": True}))
                    audio_results.append(audio_data)
            return True, audio_results
        except Exception as e:
            logger.error(f"WebSocket连接错误: {str(e)}", exc_info=True)
            return False, str(e)

    def generate_audio(self, demo_id: str):
        try:
            demo = Demonstration.query.get(demo_id)
            if not demo:
                logger.error(f"找不到演示项目: {demo_id}")
                return
            slides = DemonstrationSlide.query.filter_by(demonstration_id=demo_id).order_by(
                DemonstrationSlide.slide_number).all()
            if not slides:
                logger.error(f"演示项目没有幻灯片: {demo_id}")
                self._update_demo_status(demo_id, 'generate_failed')
                return
            for slide in slides:
                if slide.audio_path:
                    try:
                        success, _ = minio_accessor.delete_file(slide.audio_path)
                        if not success:
                            logger.warning(f"无法删除旧的音频文件: {slide.audio_path}")
                    except Exception as e:
                        logger.warning(f"删除音频文件时出错: {str(e)}")
                    slide.audio_path = None
            db.session.commit()
            narrations = [slide.narration for slide in slides if slide.narration]
            if not narrations:
                logger.error(f"演示项目没有独白内容: {demo_id}")
                self._update_demo_status(demo_id, 'generate_failed')
                return
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success, audio_results = loop.run_until_complete(self._connect_tts_websocket(narrations))
            if not success:
                logger.error(f"生成音频失败: {audio_results}")
                self._update_demo_status(demo_id, 'generate_failed')
                return
            for i, audio_data in enumerate(audio_results):
                slide = slides[i]
                if isinstance(audio_data, str):
                    audio_bytes = audio_data.encode("utf-8")
                else:
                    audio_bytes = audio_data
                audio_path = f"{DEMO_DIR}/{demo_id}/audio/{i}.wav"
                success, result = minio_accessor.upload_file(
                    file_data=BytesIO(audio_bytes),
                    object_name=audio_path,
                    content_type="audio/wav"
                )
                if not success:
                    logger.error(f"上传音频文件失败: {result}")
                    continue
                slide.audio_path = audio_path
            demo.status = 'running'
            db.session.commit()
            logger.debug(f"演示项目 {demo_id} 的所有音频生成完成，状态已更新为运行中(running)。")
            # 状态更新为 running 后刷新ZIP缓存
            self.invalidate_bulk_package_cache()
            self.regenerate_bulk_package_cache()
        except Exception as e:
            db.session.rollback()
            logger.error(f"生成音频时出错: {str(e)}", exc_info=True)
            self._update_demo_status(demo_id, 'generate_failed')

    @staticmethod
    def get_demonstration(demo_id: str):
        try:
            demo = Demonstration.query.get(demo_id)
            if not demo:
                return False, "Demonstration not found"
            result = demo.to_dict()
            slides_list = DemonstrationSlide.query.filter_by(demonstration_id=demo_id).order_by(
                DemonstrationSlide.slide_number).all()
            slides_data = []
            for slide in slides_list:
                slide_dict = slide.to_dict()
                success, url = minio_accessor.get_file_url(slide.image_path)
                slide_dict['image_url'] = url if success else None
                if slide.audio_path:
                    success, audio_url = minio_accessor.get_file_url(slide.audio_path)
                    slide_dict['audio_url'] = audio_url if success else None
                slides_data.append(slide_dict)
            result['slides'] = slides_data
            return True, result
        except Exception as e:
            logger.error(f"Error getting demonstration: {str(e)}", exc_info=True)
            return False, str(e)

    @staticmethod
    def list_demonstrations():
        try:
            demos = Demonstration.query.order_by(
                func.greatest(Demonstration.created_at, Demonstration.updated_at).desc()
            ).all()
            result = []
            for demo in demos:
                demo_dict = demo.to_dict()
                if demo.status != 'processing':
                    first_slide = DemonstrationSlide.query.filter_by(
                        demonstration_id=demo.id,
                        slide_number=1
                    ).first()
                    if first_slide:
                        success, url = minio_accessor.get_file_url(first_slide.image_path)
                        if success:
                            demo_dict['cover_image_url'] = url
                if demo.faq_id:
                    if ',' in demo.faq_id:
                        faq_ids = [fid.strip() for fid in demo.faq_id.split(',') if fid.strip()]
                        triggers = []
                        paths = []
                        for fid in faq_ids:
                            faq_data = Faq.get_faq_by_id(fid)
                            if isinstance(faq_data, dict) and "error" not in faq_data:
                                triggers.append(faq_data.get('question', ''))
                                paths.append(faq_data.get('answer', ''))
                        demo_dict['trigger'] = ",".join(triggers)
                        demo_dict['path'] = ",".join(paths)
                    else:
                        faq_data = Faq.get_faq_by_id(demo.faq_id)
                        if isinstance(faq_data, dict) and "error" not in faq_data:
                            demo_dict['trigger'] = faq_data.get('question', '')
                            demo_dict['path'] = faq_data.get('answer', '')
                        else:
                            demo_dict['trigger'] = ''
                            demo_dict['path'] = ''
                else:
                    demo_dict['trigger'] = ''
                    demo_dict['path'] = ''
                demo_dict['mode'] = demo.mode
                result.append(demo_dict)
            return True, result
        except Exception as e:
            logger.error(f"Error listing demonstrations: {str(e)}", exc_info=True)
            return False, str(e)

    def delete_demonstration(self, demo_id: str):
        try:
            demo = Demonstration.query.get(demo_id)
            if not demo:
                return False, "Demonstration not found"
            if demo.faq_id:
                faq_ids = [fid.strip() for fid in demo.faq_id.split(',') if fid.strip()]
                for fid in faq_ids:
                    faq_success, faq_result = Faq.delete_faq(fid)
                    if not faq_success:
                        logger.warning(f"删除FAQ记录失败, faq_id: {fid}, 错误: {faq_result}")
            success, _ = minio_accessor.delete_file(demo.file_path)
            if not success:
                logger.warning(f"Failed to delete PPT file: {demo.file_path}")
            info_path = f"{DEMO_DIR}/{demo_id}/ppt_info.txt"
            minio_accessor.delete_file(info_path)
            audio_count_path = f"{DEMO_DIR}/{demo_id}/audio/audioCount.json"
            minio_accessor.delete_file(audio_count_path)
            slides_list = DemonstrationSlide.query.filter_by(demonstration_id=demo_id).all()
            for slide in slides_list:
                success, _ = minio_accessor.delete_file(slide.image_path)
                if not success:
                    logger.warning(f"Failed to delete slide image: {slide.image_path}")
                if slide.audio_path:
                    success, _ = minio_accessor.delete_file(slide.audio_path)
                    if not success:
                        logger.warning(f"Failed to delete slide audio: {slide.audio_path}")
            db.session.delete(demo)
            db.session.commit()
            # 删除项目后刷新ZIP缓存
            self.invalidate_bulk_package_cache()
            self.regenerate_bulk_package_cache()
            logger.debug(f"删除演示项目 {demo_id} 成功。")
            return True, "Demonstration deleted successfully"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting demonstration: {str(e)}", exc_info=True)
            return False, str(e)

    def update_slide_narration(self, demo_id: str, slide_number: int, narration_text: str):
        try:
            with self.lock:
                demo = Demonstration.query.get(demo_id)
                if not demo:
                    logger.error("Demonstration not found")
                if demo.status not in ['completed', 'running', 'audio_processing']:
                    logger.error("Demonstration is not ready. Current status: " + demo.status)
                slide = DemonstrationSlide.query.filter_by(
                    demonstration_id=demo_id,
                    slide_number=slide_number
                ).first()
                if not slide:
                    logger.error(f"Slide number {slide_number} not found")
                slide.narration = narration_text
                ppt_info_path = f"{DEMO_DIR}/{demo_id}/ppt_info.txt"
                success, ppt_info_data = minio_accessor.download_file(ppt_info_path)
                if success:
                    ppt_info_lines = ppt_info_data.decode('utf-8').splitlines()
                    while len(ppt_info_lines) < slide_number:
                        ppt_info_lines.append("")
                    cleaned_narration = narration_text.replace('\n', ' ').replace('\r', ' ')
                    ppt_info_lines[slide_number - 1] = cleaned_narration
                    new_ppt_info = "\n".join(ppt_info_lines)
                    success, result = minio_accessor.upload_file(
                        file_data=BytesIO(new_ppt_info.encode('utf-8')),
                        object_name=ppt_info_path,
                        content_type="text/plain"
                    )
                    if not success:
                        logger.error(f"Failed to update ppt_info.txt: {result}")
                demo.status = 'audio_processing'
                db.session.commit()
                app_instance = current_app._get_current_object()
                thread = threading.Thread(
                    target=self._background_single_slide_tts,
                    args=(demo_id, slide_number, narration_text, app_instance)
                )
                thread.start()
                # 如果项目当前状态为running，刷新ZIP缓存（单个幻灯片更新）
                demo = Demonstration.query.get(demo_id)
                if demo and demo.status == 'running':
                    self.invalidate_bulk_package_cache()
                    self.regenerate_bulk_package_cache()
                return True, {
                    "message": f"Narration for slide {slide_number} updated successfully. Audio generation started."}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating slide narration: {str(e)}", exc_info=True)
            return False, str(e)

    def _background_single_slide_tts(self, demo_id: str, slide_number: int, narration_text: str, app):
        with app.app_context():
            self.generate_single_slide_audio(demo_id, slide_number, narration_text)

    @staticmethod
    async def _connect_single_tts_websocket(narration_text: str):
        TTS_URL = get_tts_url()
        try:
            async with websockets.connect(
                    TTS_URL,
                    max_size=None,
                    ping_interval=30,
                    ping_timeout=30
            ) as websocket:
                await websocket.send(json.dumps([narration_text]))
                audio_data = None
                while audio_data is None:
                    message = await websocket.recv()
                    if isinstance(message, bytes):
                        audio_data = message
                    elif isinstance(message, str):
                        if not message.startswith("Segment"):
                            audio_data = message.encode("utf-8")
                        else:
                            logger.info(f"忽略状态消息: {message}")
                await websocket.send(json.dumps({"stop": True}))
                return True, audio_data
        except Exception as e:
            logger.error(f"WebSocket连接错误: {str(e)}", exc_info=True)
            return False, str(e)

    def generate_single_slide_audio(self, demo_id: str, slide_number: int, narration_text: str):
        try:
            demo = Demonstration.query.get(demo_id)
            if not demo:
                logger.error(f"找不到演示项目: {demo_id}")
                return
            slide = DemonstrationSlide.query.filter_by(
                demonstration_id=demo_id,
                slide_number=slide_number
            ).first()
            if not slide:
                logger.error(f"找不到幻灯片: 演示项目 {demo_id}, 幻灯片编号 {slide_number}")
                demo.status = 'generate_failed'
                db.session.commit()
                return
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success, audio_data = loop.run_until_complete(self._connect_single_tts_websocket(narration_text))
            if not success:
                logger.error(f"生成音频失败: {audio_data}")
                demo.status = 'generate_failed'
                db.session.commit()
                return
            audio_path = f"{DEMO_DIR}/{demo_id}/audio/{slide_number - 1}.wav"
            if isinstance(audio_data, str):
                audio_bytes = audio_data.encode("utf-8")
            else:
                audio_bytes = audio_data
            success, result = minio_accessor.upload_file(
                file_data=BytesIO(audio_bytes),
                object_name=audio_path,
                content_type="audio/wav"
            )
            if not success:
                logger.error(f"上传音频文件失败: {result}")
                demo.status = 'generate_failed'
                db.session.commit()
                return
            slide.audio_path = audio_path
            demo.status = 'running'
            db.session.commit()
            logger.debug(f"演示项目 {demo_id} 的幻灯片 {slide_number} 音频生成完成，状态已更新为running。")
            # 刷新ZIP缓存（running状态下的单页更新）
            self.invalidate_bulk_package_cache()
            self.regenerate_bulk_package_cache()
        except Exception as e:
            db.session.rollback()
            logger.error(f"生成单个幻灯片音频时出错: {str(e)}", exc_info=True)
            try:
                demo = Demonstration.query.get(demo_id)
                if demo:
                    demo.status = 'generate_failed'
                    db.session.commit()
            except Exception as inner_e:
                db.session.rollback()
                logger.error(f"更新演示项目状态为'generate_failed'时出错: {str(inner_e)}", exc_info=True)

    def retry_audio_synthesis(self, demo_id: str):
        try:
            demo = Demonstration.query.get(demo_id)
            if not demo:
                logger.error("找不到演示项目")
            if demo.status not in ['generate_failed', 'running']:
                logger.error(f"无法重新合成音频。当前状态: {demo.status}")
            slides = DemonstrationSlide.query.filter_by(demonstration_id=demo_id).all()
            if not slides:
                logger.error("该演示项目没有幻灯片")
            missing_narrations = [slide.slide_number for slide in slides if not slide.narration]
            if missing_narrations:
                logger.error(f"以下幻灯片缺少独白内容: {', '.join(map(str, missing_narrations))}")
            demo.status = 'audio_processing'
            db.session.commit()
            app_instance = current_app._get_current_object()
            thread = threading.Thread(
                target=self._background_tts,
                args=(demo_id, app_instance)
            )
            thread.daemon = True
            thread.start()
            logger.debug(f"演示项目 {demo_id} 的音频合成重启任务已启动")
            return True, "音频合成重启成功"
        except Exception as e:
            db.session.rollback()
            logger.error(f"重启音频合成时出错: {str(e)}", exc_info=True)
            return False, str(e)

    @staticmethod
    def prepare_download_package_by_id(demo_id: str):
        try:
            demo = Demonstration.query.get(demo_id)
            if not demo:
                logger.error("Demonstration not found")
            temp_dir = tempfile.mkdtemp()
            app_logger = current_app.logger
            success, ppt_data = minio_accessor.download_file(demo.file_path)
            if not success:
                shutil.rmtree(temp_dir)
                logger.error(f"Failed to download PPT file: {ppt_data}")
            ppt_local_path = os.path.join(temp_dir, demo.original_filename)
            with open(ppt_local_path, 'wb') as f:
                f.write(ppt_data)
            slides = DemonstrationSlide.query.filter_by(demonstration_id=demo_id).all()
            for slide in slides:
                success, slide_data = minio_accessor.download_file(slide.image_path)
                if success:
                    slide_filename = f"slide_{slide.slide_number}.jpg"
                    slide_local_path = os.path.join(temp_dir, slide_filename)
                    with open(slide_local_path, 'wb') as f:
                        f.write(slide_data)
                else:
                    app_logger.warning(f"Failed to download slide {slide.slide_number} image: {slide_data}")
            base_name = os.path.join(tempfile.gettempdir(), f"{demo_id}_package")
            zip_path = shutil.make_archive(base_name, 'zip', temp_dir)
            shutil.rmtree(temp_dir)
            return True, zip_path
        except Exception as e:
            return False, str(e)

    @staticmethod
    def download_and_save(object_name: str, local_path: str):
        success, data = minio_accessor.download_file(object_name)
        if success and data:
            with open(local_path, 'wb') as f:
                f.write(data)
            return True, local_path
        else:
            return False, f"Failed to download {object_name}: {data}"

    def prepare_bulk_download_package(self):
        try:
            # 如果缓存目录不存在，则重新创建目录
            os.makedirs(BULK_PACKAGE_CACHE_DIR, exist_ok=True)

            # 计算缓存键及缓存 ZIP 包路径
            cache_key = self.get_bulk_package_cache_key()
            cache_zip_path = os.path.join(BULK_PACKAGE_CACHE_DIR, f"{cache_key}.zip")

            # 如果已存在缓存的 ZIP 包，则直接返回
            if os.path.exists(cache_zip_path):
                logger.debug("Returning cached bulk download package.")
                return True, cache_zip_path

            # 创建临时目录，用于生成 ZIP 包内容
            temp_dir = tempfile.mkdtemp()
            app_logger = current_app.logger

            # 获取所有状态为 running 的演示项目
            demos = Demonstration.query.filter_by(status="running").all()
            tasks = []
            with ThreadPoolExecutor(max_workers=8) as executor:
                for demo in demos:
                    demo_folder = os.path.join(temp_dir, demo.id)
                    os.makedirs(demo_folder, exist_ok=True)
                    # 如果模式为1，下载 PPT 文件
                    if demo.mode == "1":
                        extension = demo.original_filename.rsplit('.', 1)[1] if '.' in demo.original_filename else 'pptx'
                        ppt_local_path = os.path.join(demo_folder, f"{demo.id}.{extension}")
                        tasks.append(executor.submit(self.download_and_save, demo.file_path, ppt_local_path))
                    # 下载 ppt_info.txt
                    ppt_info_path = f"{DEMO_DIR}/{demo.id}/ppt_info.txt"
                    ppt_info_local_path = os.path.join(demo_folder, "ppt_info.txt")
                    tasks.append(executor.submit(self.download_and_save, ppt_info_path, ppt_info_local_path))
                    # 创建本地 audio 文件夹，并下载 audioCount.json
                    audio_folder_local = os.path.join(demo_folder, "audio")
                    os.makedirs(audio_folder_local, exist_ok=True)
                    audio_count_path = f"{DEMO_DIR}/{demo.id}/audio/audioCount.json"
                    audio_count_local_path = os.path.join(audio_folder_local, "audioCount.json")
                    tasks.append(executor.submit(self.download_and_save, audio_count_path, audio_count_local_path))
                    # 下载每个幻灯片的音频文件（如果存在）
                    slides = DemonstrationSlide.query.filter_by(demonstration_id=demo.id).all()
                    for slide in slides:
                        if slide.audio_path:
                            audio_filename = os.path.basename(slide.audio_path)
                            audio_local_path = os.path.join(audio_folder_local, audio_filename)
                            tasks.append(executor.submit(self.download_and_save, slide.audio_path, audio_local_path))

                # 等待所有下载任务完成
                for future in as_completed(tasks):
                    success, result = future.result()
                    if not success:
                        app_logger.warning(result)

            # 生成 ZIP 包（确定性 ZIP）
            base_name = os.path.join(tempfile.gettempdir(), "demonstrations_package")
            zip_path = base_name + ".zip"
            create_deterministic_zip(temp_dir, zip_path)
            shutil.rmtree(temp_dir)

            # 再次确保缓存目录存在（防止之前被删除）
            os.makedirs(BULK_PACKAGE_CACHE_DIR, exist_ok=True)
            shutil.copy(zip_path, cache_zip_path)
            logger.debug(f"Bulk package cached at {cache_zip_path}.")
            return True, cache_zip_path
        except Exception as e:
            logger.error(f"prepare_bulk_download_package error: {str(e)}", exc_info=True)
            return False, str(e)

# 创建全局实例以便于在应用中使用
demonstration_accessor = DemonstrationAccessor()
