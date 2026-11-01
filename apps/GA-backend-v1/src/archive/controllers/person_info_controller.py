"""
Person info controller module.
Handles API endpoints for person information management.
"""
from flask import request, jsonify
from typing import Dict, List, Union, Tuple, Any
from accessors.person_info_accessor import PersonInfo

class PersonInfoController:

    @staticmethod
    def add_person() -> Tuple[Dict, int]:
        data = request.json
        result, person_info_or_error = PersonInfo.add_person(data)
        if result:
            return jsonify(person_info_or_error), 201
        else:
            return jsonify({'error': 'Failed to add person', 'message': person_info_or_error}), 500

    @staticmethod
    def list_persons() -> Tuple[Dict, int]:
        skip = request.args.get('skip', default=0, type=int)
        take = request.args.get('take', default=100, type=int)
        result, persons_or_error = PersonInfo.list_persons(skip, take)
        if result:
            return jsonify(persons_or_error), 200
        else:
            return jsonify({'error': 'Failed to list persons', 'message': persons_or_error}), 500

    @staticmethod
    def get_persons_by_codes() -> Tuple[Dict, int]:
        codes_str = request.args.get('codes', '')
        if codes_str:
            try:
                codes = [int(code) for code in codes_str.split(',') if code.strip()]
            except ValueError:
                return jsonify({'error': 'Invalid code format, codes should be integers'}), 400

            result, persons_or_error = PersonInfo.get_persons_by_codes(codes)
            if result:
                return jsonify(persons_or_error), 200
            else:
                return jsonify({'error': 'Failed to list persons by codes', 'message': persons_or_error}), 500
        else:
            return jsonify({'error': 'No codes provided'}), 400

    @staticmethod
    def get_person(person_id) -> Tuple[Dict, int]:
        result, person_or_error = PersonInfo.get_person(person_id)
        if result:
            return jsonify(person_or_error), 200
        else:
            return jsonify({'error': 'Person not found', 'message': person_or_error}), 404

    @staticmethod
    def get_person_by_code(code) -> Tuple[Dict, int]:
        result, person_or_error = PersonInfo.get_person_by_code(code)
        if result:
            return jsonify(person_or_error), 200
        else:
            return jsonify({'error': 'Failed to get person by code', 'message': person_or_error}), 404

    @staticmethod
    def query_person() -> Tuple[Dict, int]:
        name = request.args.get('name', default='', type=str)
        skip = request.args.get('skip', default=0, type=int)
        take = request.args.get('take', default=1000, type=int)
        code_prefix = request.args.get('code', default='', type=str)

        if not name and not code_prefix:
            return jsonify({'error': 'Query must include either a "name" or a "code" parameter.'}), 400

        result, persons_or_error = PersonInfo.query_person(name, code_prefix, skip, take)
        if result:
            return jsonify(persons_or_error), 200
        else:
            return jsonify({'error': 'Failed to query persons', 'message': persons_or_error}), 500

    @staticmethod
    def update_person(person_id) -> Tuple[Dict, int]:
        update_data = request.json
        result, person_info_or_message = PersonInfo.update_person(person_id, update_data)
        if result:
            return jsonify(person_info_or_message), 200
        else:
            return jsonify({'error': 'Failed to update person', 'message': person_info_or_message}), 500

    @staticmethod
    def delete_person(person_id) -> Tuple[Dict, int]:
        result, message = PersonInfo.delete_person(person_id)
        if result:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': 'Failed to delete person', 'message': message}), 500
