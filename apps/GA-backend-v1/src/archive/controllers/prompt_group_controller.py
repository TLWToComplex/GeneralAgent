"""
Prompt group controller module.
Handles API endpoints for organizing and managing prompt groups.
"""
from flask import request, jsonify
from typing import Dict, Tuple
from accessors.prompt_group_accessor import PromptGroup

class PromptGroupController:
    @staticmethod
    def add_prompt_group() -> Tuple[Dict, int]:
        data = request.json
        result, group_info_or_error = PromptGroup.add_prompt_group(data)
        if result:
            return jsonify(group_info_or_error), 201
        else:
            return jsonify({'error': 'Failed to add prompt group', 'message': group_info_or_error}), 500

    @staticmethod
    def list_prompt_groups() -> Tuple[Dict, int]:
        result, groups_or_error = PromptGroup.list_prompt_groups_with_count()
        if result:
            return jsonify(groups_or_error), 200
        else:
            return jsonify({'error': 'Failed to list prompt groups', 'message': groups_or_error}), 500

    @staticmethod
    def get_prompt_group(group_id) -> Tuple[Dict, int]:
        result, group_or_error = PromptGroup.get_prompt_group(group_id)
        if result:
            return jsonify(group_or_error), 200
        else:
            return jsonify({'error': 'Prompt group not found', 'message': group_or_error}), 404

    @staticmethod
    def update_prompt_group(group_id) -> Tuple[Dict, int]:
        update_data = request.json
        result, group_info_or_message = PromptGroup.update_prompt_group(group_id, update_data) 
        if result: 
            return jsonify(group_info_or_message), 200 
        else: 
            return jsonify({'error': 'Failed to update prompt group', 'message': group_info_or_message}), 500

    @staticmethod
    def delete_prompt_group(group_id) -> Tuple[Dict, int]:
        result, message = PromptGroup.delete_prompt_group(group_id)
        if result:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': 'Failed to delete prompt group', 'message': message}), 500
