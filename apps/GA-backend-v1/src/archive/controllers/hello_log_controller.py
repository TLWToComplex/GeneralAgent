"""
Hello log controller module.
Handles API endpoints for tracking and retrieving system greeting interactions.
"""
from flask import request, jsonify
from flask_jwt_extended import jwt_required
from typing import Dict, List, Any, Union, Tuple
from accessors.hello_log_accessor import HelloLog  # 确保导入HelloLog模型


class HelloLogController:

    @staticmethod
    def add_log_records() -> Tuple[Union[Dict, List], int]:
        data = request.json
        codes = data.get('codes', [])  # 获取代码数组
        if not codes:
            return jsonify({'error': 'No codes provided'}), 400

        result, response = HelloLog.add_log_records(codes)

        if result:
            return jsonify([record.to_dict() for record in response]), 201
        else:
            return jsonify({'error': response}), 500

    @staticmethod
    @jwt_required()
    def get_logs_by_code() -> Tuple[Union[Dict, List], int]:
        code = request.args.get('code', type=int)
        result, logs = HelloLog.get_logs_by_code(code)

        if result:
            return jsonify([log.to_dict() for log in logs]), 200
        else:
            return jsonify({'error': logs}), 500
