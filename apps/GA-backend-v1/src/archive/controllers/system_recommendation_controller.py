"""
System recommendation controller module.
Handles API endpoints for system recommendations and suggestions.
"""
from flask import request, jsonify
from accessors.system_recommendation_accessor import SystemRecommandationAccessor
from utils.embedding_utils import EmbeddingUtils
from typing import Dict, List, Union, Tuple, Any
import requests
import os
import uuid

VECTOR_DB_NAME = 'WDK'
VECTOR_COLLECTION_NAME_FAQ = 'wdb'
VECTOR_COLLECTION_NAME_RS = 'recommendation_systems'

class SystemRecommendationController:
    @staticmethod
    def add() -> Tuple[Dict, int]:
        recommendation_id = str(uuid.uuid4())
        url = request.json.get('url', None)
        url_type = request.json.get('url_type', None)
        description = request.json.get('description', None)
        name = request.json.get('name', None)
        description_v = EmbeddingUtils.get_embedding(description)
        data = {
            "id": recommendation_id,
            "url": url,
            "url_type": url_type,
            "description": description,
            "name": name,
            "description_v": description_v,
        }
        result = SystemRecommandationAccessor.add(data)
        if result and result[0]:
            return_data = data.copy()
            return_data.pop('description_v', None)
            return jsonify(return_data), 201
        return jsonify({
            'error': 'Failed to add recommended choice', 
            'message': result[1] if result else 'Unknown error'
        }), 500
    
    @staticmethod
    def get_by_id(id) -> Tuple[Dict, int]:
        result = SystemRecommandationAccessor.get_by_id(id)
        return jsonify(result), 200 
    
    @staticmethod
    def list() -> Tuple[Dict, int]:
        result = SystemRecommandationAccessor.list()
        return jsonify(result), 200
    
    @staticmethod
    def update(id) -> Tuple[Dict, int]:
        url = request.json.get('url', None)
        url_type = request.json.get('url_type', None)
        description = request.json.get('description', None)
        name = request.json.get('name', None)
        description_v = EmbeddingUtils.get_embedding(description)
        data = {
            "id": id,
            "url": url,
            "url_type": url_type,
            "description": description,
            "name": name,
            "description_v": description_v,
        }
        result = SystemRecommandationAccessor.update(data)
        if result and result[0]:
            return_data = data.copy()
            return_data.pop('description_v', None)
            return jsonify(return_data), 200
        return jsonify({
            'error': 'Failed to update recommended choice', 
            'message': result[1] if result else 'Unknown error'
        }), 500
    
    @staticmethod
    def delete(id) -> Tuple[Dict, int]:
        result = SystemRecommandationAccessor.delete(id)
        return jsonify(result), 200
    
    @staticmethod
    def get_system_recommendation_by_description(json=None) -> List[Dict]:
        if json:
            message = json.get('message', None)
            topk = json.get('topK', 10)
        else:
            message = request.json.get('message', None)
            topk = request.json.get('topK', 10)
            
        description_v = EmbeddingUtils.get_embedding(message)
        result = SystemRecommandationAccessor.get_system_recommendation_by_description(description_v, topk)
        return result
    
    

