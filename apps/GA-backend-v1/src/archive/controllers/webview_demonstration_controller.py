"""
Webview demonstration controller module.
Handles API endpoints for web-based demonstration content management.
"""
from flask import request, jsonify, Response
from typing import Tuple, Dict, Any
from accessors.database import db
from accessors.webview_demonstration_accessor import webview_demonstration_accessor

class WebviewDemonstrationController:
    @staticmethod
    def create_webview_demonstration() -> Tuple[Response, int]:
        try:
            data = request.get_json(force=True)
            name = data.get('name')
            if not name:
                return jsonify({'success': False, 'message': '网页演示名称为必填项'}), 400
            description = data.get('description', '')
            trigger_data = data.get('trigger')
            if not trigger_data:
                return jsonify({'success': False, 'message': '触发词为必填项'}), 400
            url = data.get('url')
            if not url:
                return jsonify({'success': False, 'message': 'URL为必填项'}), 400
            reply = data.get('reply')
            if not reply:
                return jsonify({'success': False, 'message': '回复内容（reply）为必填项'}), 400
            success, result = webview_demonstration_accessor.create_webview_demonstration(
                name=name,
                description=description,
                trigger_data=trigger_data,
                url=url,
                reply=reply
            )
            if success:
                return jsonify({'success': True, 'data': result}), 200
            else:
                return jsonify({'success': False, 'message': result}), 500
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def update_webview_demonstration(demo_id: int) -> Tuple[Response, int]:
        try:
            data = request.get_json(force=True)
            name = data.get('name')
            if not name:
                return jsonify({'success': False, 'message': '网页演示名称为必填项'}), 400
            description = data.get('description', '')
            trigger_data = data.get('trigger')
            if not trigger_data:
                return jsonify({'success': False, 'message': '触发词为必填项'}), 400
            url = data.get('url')
            reply = data.get('reply')
            if not reply:
                return jsonify({'success': False, 'message': '回复内容（reply）为必填项'}), 400

            success, result = webview_demonstration_accessor.update_webview_demonstration(
                demo_id=demo_id,
                name=name,
                description=description,
                trigger_data=trigger_data,
                url=url,
                reply=reply
            )
            if success:
                return jsonify({'success': True, 'data': result}), 200
            else:
                return jsonify({'success': False, 'message': result}), 500
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def get_webview_demonstration(demo_id: int) -> Tuple[Response, int]:
        try:
            success, result = webview_demonstration_accessor.get_webview_demonstration(demo_id)
            if success:
                return jsonify({'success': True, 'data': result}), 200
            else:
                return jsonify({'success': False, 'message': result}), 404
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def list_webview_demonstrations() -> Tuple[Response, int]:
        try:
            success, result = webview_demonstration_accessor.list_webview_demonstrations()
            if success:
                return jsonify({'success': True, 'data': result}), 200
            else:
                return jsonify({'success': False, 'message': result}), 500
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def delete_webview_demonstration(demo_id: int) -> Tuple[Response, int]:
        try:
            success, result = webview_demonstration_accessor.delete_webview_demonstration(demo_id)
            if success:
                return jsonify({'success': True, 'message': result}), 200
            else:
                return jsonify({'success': False, 'message': result}), 404
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
