"""
Text-to-Speech controller module.
Handles API endpoints for text-to-speech conversion and management.
"""
from flask import request, jsonify, Response
from accessors.tts_accessor import TTS
from controllers.minio_controller import MinioController
import os
from typing import Dict, Any, Tuple, Union, List, Optional
file_sever_ip = os.getenv("FILE_SERVER_BASE")
audio_bucket = os.getenv('AUDIO_BUCKET', 'audioseed')

class TTSController:
    AUDIO_BUCKET = audio_bucket

    @staticmethod
    def _serialize_tts(tts: Any) -> Dict[str, Any]:
        """将 TTS 对象转换为可序列化的字典"""
        # 处理 audio_url，去掉预签名部分
        audio_url = tts.audio_url
        if audio_url and '?' in audio_url:
            audio_url = audio_url.split('?')[0]

        return {
            'id': tts.id,
            'name': tts.name,
            'prompt': tts.prompt,
            'descriptions': tts.descriptions,
            'audio_url': audio_url,
            'virtual_human_tts_status': tts.virtual_human_tts_status,
            'offline_synthesis_tts_status': tts.offline_synthesis_tts_status,
            'is_need_training': tts.is_need_training,
            'virtual_human_tts_model_path': tts.virtual_human_tts_model_path,
            'offline_synthesis_tts_model_path': tts.offline_synthesis_tts_model_path,
            'created_at': tts.created_at.isoformat() if tts.created_at else None,
            'updated_at': tts.updated_at.isoformat() if tts.updated_at else None
        }

    @staticmethod
    def create_tts() -> Tuple[Response, int]:
        try:
            # 处理文件上传
            if 'file' in request.files:
                file = request.files['file']
                if file.filename == '':
                    return jsonify({'error': 'No selected file'}), 400

                # 上传文件到 Minio，指定桶名和原始文件名
                request.form = request.form.copy()  # 创建表单数据的副本
                request.form['bucket'] = TTSController.AUDIO_BUCKET  # 添加桶名参数
                request.form['object_name'] = file.filename  # 使用原始文件名
                response = MinioController.upload_file()
                print(response)
                if response[1] != 200:
                    return response
                result = response[0].json['data']
                object_name = result.get('object_name', file.filename)
                audio_url = f"{file_sever_ip}/files/{TTSController.AUDIO_BUCKET}/{object_name}"
            else:
                audio_url = None

            # 获取其他表单数据
            data = {
                'name': request.form.get('name'),
                'prompt': request.form.get('prompt'),
                'descriptions': request.form.get('descriptions'),
                'audio_url': audio_url,
                'virtual_human_tts_status': request.form.get('virtual_human_tts_status', 'false').lower() == 'true',
                'offline_synthesis_tts_status': request.form.get('offline_synthesis_tts_status', 'false').lower() == 'true',
                'is_need_training': request.form.get('is_need_training', 'false').lower() == 'true',
                'virtual_human_tts_model_path': request.form.get('virtual_human_tts_model_path'),
                'offline_synthesis_tts_model_path': request.form.get('offline_synthesis_tts_model_path')
            }

            if not data['name']:
                return jsonify({'error': 'Name is required'}), 400

            success, result = TTS.create(data)
            if success:
                return jsonify(TTSController._serialize_tts(result)), 201
            return jsonify({'error': str(result)}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @staticmethod
    def get_tts(id: int) -> Tuple[Response, int]:
        success, result = TTS.get_by_id(id)
        if success:
            return jsonify(TTSController._serialize_tts(result)), 200
        return jsonify({'error': str(result)}), 404

    @staticmethod
    def list_tts() -> Tuple[Response, int]:
        success, result = TTS.list_all()
        if success:
            return jsonify([TTSController._serialize_tts(item) for item in result]), 200
        return jsonify({'error': str(result)}), 500

    @staticmethod
    def update_tts(id: int) -> Tuple[Response, int]:
        try:
            # 首先获取现有的 TTS 记录
            success, existing_tts = TTS.get_by_id(id)
            if not success:
                return jsonify({'error': str(existing_tts)}), 404

            data = {}
            old_audio_url = existing_tts.audio_url

            # 处理文件上传
            if 'file' in request.files:
                file = request.files['file']
                if file.filename != '':
                    # 先删除旧文件
                    if old_audio_url:
                        print(f"Deleting old file: {old_audio_url}")  # 打印要删除的文件 URL
                        TTSController._delete_minio_file(old_audio_url)

                    # 上传新文件到 Minio，使用原始文件名
                    request.form = request.form.copy()
                    request.form['bucket'] = TTSController.AUDIO_BUCKET
                    request.form['object_name'] = file.filename  # 使用原始文件名
                    response = MinioController.upload_file()
                    if response[1] != 200:
                        return response

                    # 获取上传后的文件名，构建永久的公共访问 URL
                    result = response[0].json['data']
                    object_name = result.get('object_name', file.filename)
                    data['audio_url'] = f"http://localhost:9000/{TTSController.AUDIO_BUCKET}/{object_name}"

            # 获取其他表单数据
            for field in ['name', 'prompt', 'descriptions', 'virtual_human_tts_status',
                         'offline_synthesis_tts_status', 'is_need_training',
                         'virtual_human_tts_model_path', 'offline_synthesis_tts_model_path']:
                if field in request.form:
                    value = request.form[field]
                    if field in ['virtual_human_tts_status', 'offline_synthesis_tts_status', 'is_need_training']:
                        value = value.lower() == 'true'
                    data[field] = value

            if not data:
                return jsonify({'error': 'No data provided'}), 400

            success, result = TTS.update(id, data)
            if success:
                return jsonify(TTSController._serialize_tts(result)), 200
            return jsonify({'error': str(result)}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @staticmethod
    def delete_tts(id: int) -> Tuple[Response, int]:
        try:
            # 首先获取要删除的 TTS 记录
            success, tts = TTS.get_by_id(id)
            if not success:
                return jsonify({'error': str(tts)}), 404

            # 检查是否需要训练
            if tts.is_need_training:
                return jsonify({'error': '默认音色不能删除'}), 400

            # 检查是否是激活的虚拟人 TTS
            if tts.virtual_human_tts_status:
                return jsonify({'error': '激活状态的虚拟人音色不能删除'}), 400

            # 删除 Minio 中的文件
            TTSController._delete_minio_file(tts.audio_url)

            # 删除数据库记录
            success, result = TTS.delete(id)
            if success:
                return jsonify({'message': result}), 200
            return jsonify({'error': str(result)}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @staticmethod
    def _delete_minio_file(url: Optional[str]) -> None:
        """删除 Minio 中的文件"""
        if not url:
            return
        try:
            # 从 URL 中提取文件名
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            path = parsed_url.path.lstrip('/')
            if path.startswith(f"{TTSController.AUDIO_BUCKET}/"):
                path = path[len(f"{TTSController.AUDIO_BUCKET}/"):]

            if path:
                # 设置删除文件所需的参数
                request.args = {'bucket': TTSController.AUDIO_BUCKET}
                print(f"Deleting file: {path}")
                response = MinioController.delete_file(path)
                print(f"Delete response: {response}")
                if response[1] != 200:
                    print(f"Failed to delete file: {path}, response: {response}")
        except Exception as e:
            print(f"Error deleting file: {str(e)}")

    @staticmethod
    def toggle_virtual_human_tts_status(id: int) -> Tuple[Response, int]:
        """切换 virtual_human_tts_status 状态"""
        try:
            # 首先获取要更新的记录
            success, tts = TTS.get_by_id(id)
            if not success:
                return jsonify({'error': str(tts)}), 404

            # 如果当前记录已经是 true，则不允许切换为 false
            if tts.virtual_human_tts_status:
                return jsonify({'error': '当前记录已经是激活状态'}), 200

            # 先将所有记录的状态设置为 false
            success, _ = TTS.update_all({'virtual_human_tts_status': False})
            if not success:
                return jsonify({'error': '更新所有记录状态失败'}), 500

            # 将当前记录的状态设置为 true
            success, result = TTS.update(id, {'virtual_human_tts_status': True})
            if success:
                return jsonify(TTSController._serialize_tts(result)), 200
            return jsonify({'error': str(result)}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @staticmethod
    def toggle_offline_synthesis_tts_status(id: int) -> Tuple[Response, int]:
        """切换 offline_synthesis_tts_status 状态"""
        try:
            # 首先获取要更新的记录
            success, tts = TTS.get_by_id(id)
            if not success:
                return jsonify({'error': str(tts)}), 404

            # 如果当前记录已经是 true，则不允许切换为 false
            if tts.offline_synthesis_tts_status:
                return jsonify({'error': '当前记录已经是激活状态'}), 200

            # 先将所有记录的状态设置为 false
            success, _ = TTS.update_all({'offline_synthesis_tts_status': False})
            if not success:
                return jsonify({'error': '更新所有记录状态失败'}), 500

            # 将当前记录的状态设置为 true
            success, result = TTS.update(id, {'offline_synthesis_tts_status': True})
            if success:
                return jsonify(TTSController._serialize_tts(result)), 200
            return jsonify({'error': str(result)}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @staticmethod
    def get_active_virtual_human_tts() -> Tuple[Response, int]:
        """获取激活的虚拟人 TTS"""
        try:
            success, result = TTS.get_by_status('virtual_human_tts_status')
            if success:
                if result is None:
                    return jsonify({'message': '没有激活的虚拟人音色'}), 404
                return jsonify(TTSController._serialize_tts(result)), 200
            return jsonify({'error': str(result)}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @staticmethod
    def get_active_offline_synthesis_tts() -> Tuple[Response, int]:
        """获取激活的离线合成 TTS"""
        try:
            success, result = TTS.get_by_status('offline_synthesis_tts_status')
            if success:
                if result is None:
                    return jsonify({'message': '没有激活的离线合成音色'}), 404
                return jsonify(TTSController._serialize_tts(result)), 200
            return jsonify({'error': str(result)}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500

