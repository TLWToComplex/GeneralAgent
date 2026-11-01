"""
Demonstration controller module.
Manages API endpoints for PowerPoint demonstration uploads, processing, and retrieval.
"""
import os
import uuid
import hashlib
from datetime import datetime
from flask import jsonify, request, send_file, Response
from typing import Tuple, Dict, Any, List, Union, Optional
from accessors.database import db
from accessors.demonstration_accessor import demonstration_accessor, Demonstration
from accessors.faq_accessor import Faq
from utils.embedding_utils import EmbeddingUtils
from utils.md5_utils import demonstration_controller_md

VECTOR_DB_TYPE = os.getenv('VECTOR_DB_TYPE', '')

class DemonstrationController:
    @staticmethod
    def create_demonstration() -> Tuple[Response, int]:
        try:
            if 'file' not in request.files:
                return jsonify({'success': False, 'message': 'No file part'}), 400
            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'message': 'No selected file'}), 400
            file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            if file_extension not in ['ppt', 'pptx']:
                return jsonify({'success': False, 'message': 'Only PPT and PPTX files are supported'}), 400
            name = request.form.get('name')
            if not name:
                return jsonify({'success': False, 'message': 'Demonstration name is required'}), 400
            description = request.form.get('description', '')
            mode = request.form.get('mode', '1')
            trigger_value = request.form.get('trigger')
            if not trigger_value:
                return jsonify({'success': False, 'message': 'Demonstration trigger is required'}), 400
            path_value = request.form.get('path', '')
            triggers = [t.strip() for t in trigger_value.split(',') if t.strip()]
            if not triggers:
                return jsonify({'success': False, 'message': '至少需要一个有效的触发词'}), 400
            faq_ids = []
            faq_details = []
            answer_value = path_value
            for t in triggers:
                question_v = EmbeddingUtils.get_embedding(t)
                if question_v is None:
                    return jsonify({'success': False, 'message': f'Failed to get embedding for trigger: {t}'}), 500
                new_faq_id = str(uuid.uuid4())
                faq_payload = {
                    "id": new_faq_id,
                    "question": t,
                    "question_v": question_v,
                    "answer": answer_value,
                    "tags": ["艾武模式"] if VECTOR_DB_TYPE == 'milvus' else ','.join(["艾武模式"]),
                    "create_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "update_date": ""
                }
                faq_success, faq_result = Faq.add_faq(faq_payload)
                if not faq_success:
                    return jsonify({'success': False, 'message': f'Failed to add FAQ for trigger {t}: {faq_result}'}), 500
                faq_ids.append(new_faq_id)
                faq_details.append((t, question_v, new_faq_id))
            faq_ids_str = ",".join(faq_ids)
            success, result = demonstration_accessor.create_demonstration(
                name=name,
                description=description,
                mode=mode,
                file_data=file,
                original_filename=file.filename,
                faq_id=faq_ids_str
            )
            if success:
                demo_id = result['id']
                if f"<{demo_id}>" not in answer_value:
                    if "StreamingAssets" in answer_value:
                        updated_answer = answer_value.replace("StreamingAssets", f"StreamingAssets<{demo_id}>")
                    else:
                        updated_answer = answer_value + f"<{demo_id}>"
                else:
                    updated_answer = answer_value
                update_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for (t, question_v, faq_id) in faq_details:
                    update_data = {
                        "id": faq_id,
                        "question": t,
                        "question_v": question_v,
                        "answer": updated_answer,
                        "tags": ["艾武模式"] if VECTOR_DB_TYPE == 'milvus' else ','.join(["艾武模式"]),
                        "create_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "update_date": update_date
                    }
                    faq_result = Faq.upsert_faq(update_data)
                    if not (faq_result and faq_result[0]):
                        return jsonify({
                            'success': False,
                            'message': f'Failed to update FAQ record for trigger {t}: '
                                       f'{faq_result[1] if faq_result else "未知错误"}'
                        }), 500
                return jsonify({'success': True, 'data': result}), 200
            else:
                return jsonify({'success': False, 'message': result}), 500
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def update_demonstration(demo_id: str) -> Tuple[Response, int]:
        try:
            name = request.form.get('name')
            if not name:
                return jsonify({'success': False, 'message': 'Demonstration name is required'}), 400
            description = request.form.get('description', '')
            mode = request.form.get('mode')
            if not mode:
                return jsonify({'success': False, 'message': 'Demonstration mode is required'}), 400
            trigger_value = request.form.get('trigger')
            if not trigger_value:
                return jsonify({'success': False, 'message': 'Demonstration trigger is required'}), 400
            path = request.form.get('path')
            if not path:
                return jsonify({'success': False, 'message': 'Demonstration path is required'}), 400
            file_data = None
            original_filename = None
            if 'file' in request.files:
                file_data = request.files['file']
                if file_data.filename:
                    original_filename = file_data.filename
                    file_extension = file_data.filename.rsplit('.', 1)[1].lower() if '.' in file_data.filename else ''
                    if file_extension not in ['ppt', 'pptx']:
                        return jsonify({'success': False, 'message': 'Only PPT and PPTX files are supported'}), 400
                else:
                    file_data = None
            success, result = demonstration_accessor.update_demonstration(
                demo_id=demo_id,
                name=name,
                description=description,
                mode=mode,
                trigger=trigger_value,
                path=path,
                file_data=file_data,
                original_filename=original_filename
            )
            if success:
                return jsonify({'success': True, 'data': result}), 200
            else:
                return jsonify({'success': False, 'message': result}), 500
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def get_demonstration(demo_id: str) -> Tuple[Response, int]:
        try:
            success, result = demonstration_accessor.get_demonstration(demo_id)
            if success:
                return jsonify({'success': True, 'data': result}), 200
            else:
                return jsonify({'success': False, 'message': result}), 404
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def list_demonstrations() -> Tuple[Response, int]:
        try:
            success, result = demonstration_accessor.list_demonstrations()
            if success:
                return jsonify({'success': True, 'data': result}), 200
            else:
                return jsonify({'success': False, 'message': result}), 500
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def delete_demonstration(demo_id: str) -> Tuple[Response, int]:
        try:
            success, result = demonstration_accessor.delete_demonstration(demo_id)
            if success:
                return jsonify({'success': True, 'message': result}), 200
            else:
                return jsonify({'success': False, 'message': result}), 404
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def get_demonstration_status(demo_id: str) -> Tuple[Response, int]:
        try:
            success, result = demonstration_accessor.get_demonstration(demo_id)
            if success:
                status_info = {
                    'id': result['id'],
                    'status': result['status'],
                    'total_slides': result['total_slides'],
                    'name': result['name'],
                    'updated_at': result['updated_at']
                }
                return jsonify({'success': True, 'data': status_info}), 200
            else:
                return jsonify({'success': False, 'message': result}), 404
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def retry_conversion(demo_id: str) -> Tuple[Response, int]:
        try:
            success, message = demonstration_accessor.retry_conversion(demo_id)
            if success:
                return jsonify({'success': True, 'message': 'Conversion restarted successfully'}), 200
            else:
                return jsonify({'success': False, 'message': message}), 500
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def retry_audio_synthesis(demo_id: str) -> Tuple[Response, int]:
        try:
            success, result = demonstration_accessor.retry_audio_synthesis(demo_id)
            if success:
                return jsonify({'success': True, 'message': '音频合成重启成功'}), 200
            else:
                return jsonify({'success': False, 'message': result}), 400
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def save_narrations(demo_id: str) -> Tuple[Response, int]:
        try:
            if not request.is_json:
                return jsonify({'success': False, 'message': 'Request must contain JSON data'}), 400
            data = request.get_json()
            narrations = data.get('narrations')
            if not narrations or not isinstance(narrations, list):
                return jsonify({'success': False, 'message': 'Invalid narrations format. Expected list of strings'}), 400
            success, result = demonstration_accessor.save_narrations(demo_id, narrations)
            if success:
                return jsonify({'success': True, 'data': result}), 200
            else:
                return jsonify({'success': False, 'message': result}), 500
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def update_slide_narration(demo_id: str, slide_number: int) -> Tuple[Response, int]:
        try:
            if not request.is_json:
                return jsonify({'success': False, 'message': 'Request must contain JSON data'}), 400
            data = request.get_json()
            narration = data.get('narration')
            if narration is None:
                return jsonify({'success': False, 'message': 'Narration content is required'}), 400
            try:
                slide_number = int(slide_number)
                if slide_number <= 0:
                    return jsonify({'success': False, 'message': 'Slide number must be positive'}), 400
            except ValueError:
                return jsonify({'success': False, 'message': 'Slide number must be an integer'}), 400
            success, result = demonstration_accessor.update_slide_narration(demo_id, slide_number, narration)
            if success:
                return jsonify({'success': True, 'data': result}), 200
            else:
                return jsonify({'success': False, 'message': result}), 500
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def download_package() -> Response:
        try:
            success, result = demonstration_accessor.prepare_bulk_download_package()
            if not success:
                return jsonify({'success': False, 'message': result}), 500
            zip_path = result
            etag = demonstration_controller_md(zip_path)
            if request.headers.get("If-None-Match") == etag:
                return "", 304
            filename = "demonstrations_package.zip"
            response = send_file(
                zip_path,
                mimetype='application/zip',
                as_attachment=True,
                download_name=filename,
                max_age=0
            )
            response.headers["ETag"] = etag
            return response
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def download_package_by_id(demo_id: str) -> Response:
        try:
            success, result = demonstration_accessor.prepare_download_package_by_id(demo_id)
            if not success:
                return jsonify({'success': False, 'message': result}), 500
            zip_path = result
            demo = Demonstration.query.get(demo_id)
            filename = f"{demo.name.replace(' ', '_')}_package.zip" if demo else f"presentation_{demo_id}.zip"
            return send_file(
                zip_path,
                mimetype='application/zip',
                as_attachment=True,
                download_name=filename,
                max_age=0
            )
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
