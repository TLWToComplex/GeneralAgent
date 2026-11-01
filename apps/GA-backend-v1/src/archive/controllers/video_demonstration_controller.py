"""
Video demonstration controller module.
Handles API endpoints for video demonstration uploads and management.
"""
from flask import request, jsonify, send_file, Response
from typing import Tuple, Union, Dict, Any
from accessors.database import db
from accessors.video_demonstration_accessor import video_demonstration_accessor

class VideoDemonstrationController:
    @staticmethod
    def create_video_demonstration() -> Tuple[Response, int]:
        try:
            if 'file' not in request.files:
                return jsonify({'success': False, 'message': '没有找到视频文件'}), 400
            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'message': '未选择视频文件'}), 400

            name = request.form.get('name')
            if not name:
                return jsonify({'success': False, 'message': '视频演示名称为必填项'}), 400

            description = request.form.get('description', '')
            # trigger 可以是逗号分隔字符串或者 JSON 数组（前端自行传入）
            trigger_data = request.form.get('trigger')
            if not trigger_data:
                return jsonify({'success': False, 'message': '触发词为必填项'}), 400

            # 获取 reply 字段，默认为 "好的。"
            reply = request.form.get('reply', '好的。')

            # 调用 accessor 创建视频演示工程
            success, result = video_demonstration_accessor.create_video_demonstration(
                name=name,
                description=description,
                trigger_data=trigger_data,
                file_data=file,
                original_filename=file.filename,
                reply=reply
            )
            if success:
                return jsonify({'success': True, 'data': result}), 200
            else:
                return jsonify({'success': False, 'message': result}), 500

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def update_video_demonstration(demo_id: int) -> Tuple[Response, int]:
        try:
            name = request.form.get('name')
            if not name:
                return jsonify({'success': False, 'message': '视频演示名称为必填项'}), 400
            description = request.form.get('description', '')
            trigger_data = request.form.get('trigger')
            if not trigger_data:
                return jsonify({'success': False, 'message': '触发词为必填项'}), 400

            # 获取 reply 字段，默认为 "好的。"
            reply = request.form.get('reply', '好的。')

            file_data = None
            original_filename = None
            if 'file' in request.files:
                file_data = request.files['file']
                if file_data.filename:
                    original_filename = file_data.filename
                else:
                    file_data = None

            success, result = video_demonstration_accessor.update_video_demonstration(
                demo_id=demo_id,
                name=name,
                description=description,
                trigger_data=trigger_data,
                reply=reply,
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
    def get_video_demonstration(demo_id: int) -> Tuple[Response, int]:
        try:
            success, result = video_demonstration_accessor.get_video_demonstration(demo_id)
            if success:
                return jsonify({'success': True, 'data': result}), 200
            else:
                return jsonify({'success': False, 'message': result}), 404
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def list_video_demonstrations() -> Tuple[Response, int]:
        try:
            success, result = video_demonstration_accessor.list_video_demonstrations()
            if success:
                return jsonify({'success': True, 'data': result}), 200
            else:
                return jsonify({'success': False, 'message': result}), 500
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def delete_video_demonstration(demo_id: int) -> Tuple[Response, int]:
        try:
            success, result = video_demonstration_accessor.delete_video_demonstration(demo_id)
            if success:
                return jsonify({'success': True, 'message': result}), 200
            else:
                return jsonify({'success': False, 'message': result}), 404
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def download_video(demo_id: int) -> Union[Response, Tuple[Response, int]]:
        """
        根据请求参数中的 demo_id 下载视频文件的压缩包（ZIP格式），
        参考 download_package 的实现方式。
        """
        try:
            success, result = video_demonstration_accessor.prepare_download_video_package_by_id(demo_id)
            if not success:
                return jsonify({'success': False, 'message': result}), 500

            zip_path = result

            # 从数据库获取视频演示工程名称，用于生成下载包文件名
            from accessors.video_demonstration_accessor import VideoDemonstration
            video_demo = VideoDemonstration.query.get(demo_id)
            filename = f"{video_demo.name.replace(' ', '_')}_video_package.zip" if video_demo else f"video_{demo_id}_package.zip"

            return send_file(
                zip_path,
                mimetype='application/zip',
                as_attachment=True,
                download_name=filename,
                max_age=0
            )
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
