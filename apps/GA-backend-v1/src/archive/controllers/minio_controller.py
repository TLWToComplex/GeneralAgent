"""
MinIO controller module.
Manages API endpoints for file storage operations with MinIO service.
"""
import os
import io
import uuid
from datetime import timedelta
from typing import Dict, Tuple, Union, Any
from flask import request, jsonify, send_file
from accessors.file_data_accessor  import minio_accessor

class MinioController:
    @staticmethod
    def upload_file() -> Tuple[Dict, int]:
        try:
            if 'file' not in request.files:
                return jsonify({'success': False, 'message': 'No file part'}), 400

            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'message': 'No selected file'}), 400

            # 获取可选的自定义路径参数
            custom_path = request.form.get('path', '')
            # 获取可选的桶名参数
            bucket_name = request.form.get('bucket', None)

            # 生成唯一文件名
            file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            # 保留原始文件名选项
            preserve_filename = request.form.get('preserve_filename', 'false').lower() == 'true'

            if preserve_filename:
                object_name = file.filename
            else:
                object_name = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())

            # 如果有自定义路径，加到对象名前面
            if custom_path:
                # 确保路径以/结尾但不以/开头
                if not custom_path.endswith('/'):
                    custom_path = custom_path + '/'
                if custom_path.startswith('/'):
                    custom_path = custom_path[1:]
                object_name = f"{custom_path}{object_name}"

            # 上传文件
            success, result = minio_accessor.upload_file(
                file_data=file,
                object_name=object_name,
                bucket_name=bucket_name,
                content_type=file.content_type
            )

            if success:
                # 生成临时URL
                url_success, url = minio_accessor.get_file_url(
                    object_name=object_name,
                    bucket_name=bucket_name
                )
                if url_success:
                    result['url'] = url
                    # 添加原始文件名到结果中
                    result['original_filename'] = file.filename
                return jsonify({'success': True, 'data': result}), 200
            else:
                return jsonify({'success': False, 'message': result}), 500

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def download_file(object_name) -> Union[Any, Tuple[Dict, int]]:
        try:
            bucket_name = request.args.get('bucket', None)

            # 下载文件
            success, file_data = minio_accessor.download_file(
                object_name=object_name,
                bucket_name=bucket_name
            )

            if success:
                # 从对象名中获取文件名，如果有路径则去除路径部分
                filename = os.path.basename(object_name)

                # 创建内存文件对象
                file_obj = io.BytesIO(file_data)

                # 返回文件
                return send_file(
                    file_obj,
                    download_name=filename,
                    as_attachment=True
                )
            else:
                return jsonify({'success': False, 'message': file_data}), 404

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def list_files() -> Tuple[Dict, int]:
        try:
            bucket_name = request.args.get('bucket', None)
            prefix = request.args.get('prefix', '')
            recursive = request.args.get('recursive', 'true').lower() == 'true'

            # 列出文件
            success, files = minio_accessor.list_files(
                prefix=prefix,
                recursive=recursive,
                bucket_name=bucket_name
            )

            if success:
                return jsonify({'success': True, 'data': files}), 200
            else:
                return jsonify({'success': False, 'message': files}), 500

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def delete_file(object_name) -> Tuple[Dict, int]:
        try:
            bucket_name = request.args.get('bucket', None)

            # 删除文件
            success, message = minio_accessor.delete_file(
                object_name=object_name,
                bucket_name=bucket_name
            )

            if success:
                return jsonify({'success': True, 'message': message}), 200
            else:
                return jsonify({'success': False, 'message': message}), 500

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def get_file_url(object_name) -> Tuple[Dict, int]:
        try:
            bucket_name = request.args.get('bucket', None)
            hours = request.args.get('expires', '1')

            try:
                hours = int(hours)
            except ValueError:
                hours = 1

            # 生成临时URL
            success, url = minio_accessor.get_file_url(
                object_name=object_name,
                bucket_name=bucket_name,
                expires=timedelta(hours=hours)
            )

            if success:
                return jsonify({'success': True, 'data': {'url': url}}), 200
            else:
                return jsonify({'success': False, 'message': url}), 500

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

