"""
Configuration controller module.
Handles API endpoints for system configuration management.
"""
from flask import jsonify, request, Response
from typing import Tuple

from accessors.configuration_accessor import Configuration

class ConfigurationController:

    @staticmethod
    def get_configurations() -> Tuple[Response, int]:
        result, data_or_error = Configuration.get_all_configurations()
        if result:
            return jsonify(data_or_error), 200
        else:
            return jsonify({'error': data_or_error}), 500

    @staticmethod
    def update_configuration() -> Tuple[Response, int]:
        data = request.json
        name = data.get('name')
        value = data.get('value')
        description = data.get('description', None)

        if not name or value is None:
            return jsonify({'error': 'Missing name or value.'}), 400

        result, data_or_error = Configuration.update_configuration(name, value, description)
        if result:
            return jsonify(data_or_error), 200
        else:
            return jsonify({'error': data_or_error}), 500

    @staticmethod
    def add_configuration() -> Tuple[Response, int]:
        data = request.json
        name = data.get('name')
        value = data.get('value')
        description = data.get('description', None)

        if not name or value is None:
            return jsonify({'error': 'Missing name or value.'}), 400

        result, data_or_error = Configuration.add_configuration(name, value, description)
        if result:
            return jsonify(data_or_error), 201
        else:
            return jsonify({'error': data_or_error}), 500

    @staticmethod
    def delete_configuration() -> Tuple[Response, int]:
        name = request.args.get('name')

        if not name:
            return jsonify({'error': 'Missing name.'}), 400

        result, data_or_error = Configuration.delete_configuration(name)
        if result:
            return jsonify({'message': data_or_error}), 200
        else:
            return jsonify({'error': data_or_error}), 500
