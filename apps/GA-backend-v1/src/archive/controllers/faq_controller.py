"""
FAQ controller module.
Manages API endpoints for frequently asked questions and their answers.
"""
from flask import request, jsonify, Response
from accessors.faq_accessor import Faq
from datetime import datetime
from utils.embedding_utils import EmbeddingUtils
from typing import Tuple, Dict, Any, List, Union, Optional
import requests
import os
import uuid

# 向量数据库配置
VECTOR_DB_TYPE = os.getenv('VECTOR_DB_TYPE', 'milvus')

class FaqController:

    @staticmethod
    def qa_add() -> Tuple[Response, int]:
        question = request.json.get('question', None)
        answer = request.json.get('answer', None)
        tags = request.json.get('tags', None)
        create_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        faq_id = str(uuid.uuid4())
        question_v = EmbeddingUtils.get_embedding(question)

        faq_data = {
                "id": faq_id,
                "question_v": question_v,
                "question": question,
                "answer": answer,
                "tags": tags if VECTOR_DB_TYPE == 'milvus' else ','.join(tags),
                "create_date": create_date,
                "update_date": ""
            }

        # 根据数据库类型构建不同的查询表达式
        if VECTOR_DB_TYPE == 'milvus':
            expr = f"question == \"{question}\""  # Milvus使用引号
        else:  # hippo
            expr = f"question == {question}"  # Hippo不使用引号
            
        existing_questions = Faq.check_question_exists(expr)
        if existing_questions and len(existing_questions[1]) > 0:
            return jsonify({'error': 'Failed to add faq', 'message': '问题已存在，不能重复添加'}), 500
        
        # 添加FAQ
        result = Faq.add_faq(faq_data)
        if result and result[0]:
            return jsonify({'id': faq_id}), 201
        return jsonify({'error': 'Failed to add faq', 'message': result[1] if result else 'Unknown error'}), 500

    @staticmethod
    def qa_get_list():
        try:
            # 调用accessor获取FAQ列表
            data = Faq.get_faq_list()
            
            # 检查返回结果
            if isinstance(data, dict) and "error" in data:
                return jsonify(data), 500
            elif isinstance(data, list):
                return jsonify(data), 200
            else:
                return jsonify({"error": "Invalid response format"}), 500
                
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def qa_get_by_id(id):
        try:
            data = Faq.get_faq_by_id(id)
            if isinstance(data, dict) and "error" in data:
                return jsonify(data), 404 if data["error"] == "FAQ not found" else 500
            elif isinstance(data, dict):
                return jsonify(data), 200
            else:
                return jsonify({"error": "Invalid response format"}), 500
                
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def qa_delete(id):
        # 删除FAQ
        result = Faq.delete_faq(id)
        if result and result[0]:
            return jsonify({"message": "FAQ deleted successfully"}), 200
        else:
            return jsonify({'error': 'Failed to delete faq', 'message': result[1] if result else 'Unknown error'}), 500

    @staticmethod
    def qa_update(id):
        question = request.json.get('question', None)
        answer = request.json.get('answer', None)
        tags = request.json.get('tags', None)
        update_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        question_v = EmbeddingUtils.get_embedding(question)

        update_data = {
                "id": id,
                "question_v": question_v,
                "question": question,
                "answer": answer,
                "tags": tags if VECTOR_DB_TYPE == 'milvus' else ','.join(tags),
                "create_date": update_date,
                "update_date": update_date
            }

        # 根据数据库类型构建不同的查询表达式
        if VECTOR_DB_TYPE == 'milvus':
            expr = f"question == \"{question}\" and id !=\"{id}\""  # Milvus使用引号
        else:  # hippo
            expr = f"question == {question} and id != {id}"  # Hippo不使用引号
            
        existing_questions,value = Faq.check_question_exists(expr)

        if value and len(value) > 0:
            return jsonify({'error': 'Failed to add faq', 'message': '问题已存在，不能重复添加'}), 500

        # 更新FAQ
        result = Faq.upsert_faq(update_data)
        if result and result[0]:
            return jsonify({"message": "FAQ updated successfully"}), 200
        else:
            return jsonify({'error': 'Failed to update faq', 'message': result[1] if result else 'Unknown error'}), 500

    @staticmethod
    def qa_get_by_question(question: str = None, topk: int = None, tags: list = None) -> Tuple[Response, int]:
        if question is None or topk is None:
            question = request.json.get('question', None)
            topk = request.json.get('topk', None)
            tags = request.json.get('tags', None)

        question_v = EmbeddingUtils.get_embedding(question)
        
        # 构建tags查询表达式（仅Milvus需要）
        expr = ""
        if VECTOR_DB_TYPE == 'milvus' and tags:
            if isinstance(tags, list):
                # 将列表转换为字符串格式
                tags_str = ", ".join([f"'{tag}'" for tag in tags])
                expr = f"array_contains_any(tags, [{tags_str}])"
            else:
                # 单个tag的情况
                expr = f"array_contains(tags, '{tags}')"
        if VECTOR_DB_TYPE == 'hippo':
            if tags:
                expr = f"tags in {tags}"
            else:
                expr = ""
        # 查询FAQ
        data = Faq.get_qa_by_question(question_v, topk, expr)
        if isinstance(data, dict) and "error" in data:
            return jsonify(data), 500
        elif isinstance(data, list):
            # 直接返回格式化后的结果
            return data
        else:
            return jsonify({"error": "Invalid response format"}), 500
