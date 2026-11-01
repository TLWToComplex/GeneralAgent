"""
Prompt controller module.
Handles API endpoints for AI prompt management.
"""
from flask import request, jsonify
from typing import Dict, List, Union, Tuple, Any
from accessors.prompt_accessor import Prompt
from accessors.prompt_group_accessor import PromptGroup

class PromptController:

    @staticmethod
    def add_prompt() -> Tuple[Dict, int]:
        data = request.json
        result, prompt_info_or_error = Prompt.add_prompt(data)
        if result:
            return jsonify(prompt_info_or_error), 201
        else:
            return jsonify({'error': 'Failed to add prompt', 'message': prompt_info_or_error}), 500

    @staticmethod
    def list_prompts() -> Tuple[Dict, int]:
        skip = request.args.get('skip', default=0, type=int)
        result, prompts_or_error = Prompt.list_prompts(skip)
        if result:
            # 如果没有找到prompts，则返回空数组
            return jsonify(prompts_or_error), 200
        else:
            # 如果发生异常，则返回错误信息
            return jsonify({'error': 'Failed to list prompts', 'message': prompts_or_error}), 500

    @staticmethod
    def list_prompts_by_group_id(group_id) -> Tuple[Dict, int]:
        skip = request.args.get('skip', default=0, type=int)
        result, prompts_or_error = Prompt.list_prompts_by_group_id(group_id, skip)
        if result:
            return jsonify(prompts_or_error), 200
        else:
            return jsonify({'error': 'Failed to list prompts by group id', 'message': prompts_or_error}), 500

    @staticmethod
    def list_prompts_by_group_name(group_name) -> Tuple[Dict, int]:
        result, group_id_or_error = PromptGroup.get_group_id_by_name(group_name)
        if result:
            skip = request.args.get('skip', default=0, type=int)
            result, prompts_or_error = Prompt.list_prompts_by_group_id(group_id_or_error, skip)
            if result:
                return jsonify(prompts_or_error), 200
            else:
                return jsonify({'error': 'Failed to list prompts by group id', 'message': prompts_or_error}), 500
        else:
            return jsonify([]), 200

    @staticmethod
    def get_prompt(prompt_id) -> Tuple[Dict, int]:
        result, prompt_or_error = Prompt.get_prompt(prompt_id)
        if result:
            return jsonify(prompt_or_error), 200
        else:
            return jsonify({'error': 'Prompt not found', 'message': prompt_or_error}), 404

    @staticmethod
    def update_prompt(prompt_id) -> Tuple[Dict, int]:
        update_data = request.json
        result, prompt_info_or_message = Prompt.update_prompt(prompt_id, update_data)
        if result:
            return jsonify(prompt_info_or_message), 200
        else:
            return jsonify({'error': 'Failed to update prompt', 'message': prompt_info_or_message}), 500

    @staticmethod
    def delete_prompt(prompt_id) -> Tuple[Dict, int]:
        result, message = Prompt.delete_prompt(prompt_id)
        if result:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': 'Failed to delete prompt', 'message': message}), 500

    @staticmethod
    def get_prompt_by_code(code) -> Tuple[Dict, int]:
        result, prompt_or_error = Prompt.get_prompt_by_code(code)
        if result:
            return jsonify(prompt_or_error), 200
        else:
            return jsonify({'error': 'Prompt with specified code not found', 'message': prompt_or_error}), 404

