"""
FAQ accessor module.
Manages database operations for frequently asked questions and their answers.
"""
from pymilvus import Collection, db, MilvusClient, connections
from transwarp_hippo_api.hippo_client import HippoClient, HippoField
from transwarp_hippo_api.hippo_type import HippoType, IndexType, MetricType
import os
from typing import List, Dict, Any, Tuple, Union

# 向量数据库配置
VECTOR_DB_TYPE = os.getenv('VECTOR_DB_TYPE', 'milvus')
VECTOR_DB_NAME = 'WDK'
VECTOR_COLLECTION_NAME_FAQ = 'wdb'

# Milvus配置
MILVUS_URL = os.getenv('MILVUS_URL', 'http://host.docker.internal:19530')
MILVUS_USER = os.getenv('MILVUS_USER', 'aisix')
MILVUS_PASSWORD = os.getenv('MILVUS_PASSWORD', '123456')

# Hippo配置
HIPPO_HOST = os.getenv('HIPPO_HOST', '')
HIPPO_PORT = os.getenv('HIPPO_PORT', '7788')
HIPPO_USERNAME = os.getenv('HIPPO_USERNAME','shiva')
HIPPO_PASSWORD = os.getenv('HIPPO_PASSWORD','shiva')

# 初始化连接
if VECTOR_DB_TYPE == 'milvus':
    connections.connect(
        user=MILVUS_USER,
        password=MILVUS_PASSWORD,
        uri=MILVUS_URL
    )
    # 切换到指定数据库
    db.using_database(VECTOR_DB_NAME)
    collection = Collection(VECTOR_COLLECTION_NAME_FAQ)
elif VECTOR_DB_TYPE == 'hippo':
    try:
        hippo_client = HippoClient([f"{HIPPO_HOST}:{HIPPO_PORT}"], username=HIPPO_USERNAME, pwd=HIPPO_PASSWORD)
        hippo_table = hippo_client.get_table(VECTOR_COLLECTION_NAME_FAQ, VECTOR_DB_NAME)
    except Exception as e:
        hippo_client = None
        hippo_table = None

class Faq():

    @classmethod
    def check_question_exists(cls, expr: str) -> Tuple[bool, Union[List[Dict[str, Any]], Dict[str, Any]]]:
        """
        检查问题是否已存在
        :param expr: 查询表达式，例如 'question == "问题内容"'
        :return: 匹配的问题列表，如果没有匹配则返回空列表
        """
        if not expr or not isinstance(expr, str):
            return False, {"code": 400, "message": "无效的查询表达式"}
        
        try:
            if VECTOR_DB_TYPE == 'milvus':
                results = collection.query(
                    expr=expr,
                    output_fields=["id", "question"],
                    limit=1,
                    consistency_level="Strong"
                )
                return True, results
            elif VECTOR_DB_TYPE == 'hippo':
                if hippo_table is None:
                    return False, {"code": 500, "message": "Hippo客户端未初始化"}
                
                query_result = hippo_table.query_scalar(
                    output_fields=["id", "question"],
                    expr=expr,
                    limit=1
                )
                
                results = []
                if query_result and isinstance(query_result, dict):
                    # Hippo返回列式格式，需要转换为行式格式
                    ids = query_result.get('id', [])
                    questions = query_result.get('question', [])
                    
                    # 转换为行式格式
                    for i in range(len(ids)):
                        results.append({
                            "id": ids[i] if i < len(ids) else "",
                            "question": questions[i] if i < len(questions) else ""
                        })
                
                return True, results
            else:
                return False, {"code": 500, "message": f"不支持的数据库类型: {VECTOR_DB_TYPE}"}
        except Exception as e:
            return False, {"code": 400, "message": str(e)}

    @classmethod
    def add_faq(cls, faq_data: dict) -> Tuple[bool, str]:
        try:
            if VECTOR_DB_TYPE == 'milvus':
                collection.insert(faq_data)
                return True, "Success"
            elif VECTOR_DB_TYPE == 'hippo':
                if hippo_table is None:
                    return False, "Hippo客户端未初始化"
                
                # Hippo使用列表格式：每个子列表代表一个字段的所有行数据
                insert_data = [
                    [faq_data["id"]],  # id字段
                    [faq_data["question_v"]],  # question_v字段  
                    [faq_data["question"]],  # question字段
                    [faq_data["answer"]],  # answer字段
                    [faq_data["tags"]],  # tags字段
                    [faq_data["create_date"]],  # create_date字段
                    [faq_data["update_date"]]  # update_date字段
                ]
                
                result = hippo_table.insert_rows(insert_data)
                if result:
                    return True, "Success"
                else:
                    return False, "插入失败"
        except Exception as e:
            return False, str(e)
        
    @classmethod
    def get_faq_list(cls) -> Union[List[Dict[str, Any]], Dict[str, str]]:
        try:
            if VECTOR_DB_TYPE == 'milvus':
                results = collection.query(
                    expr="", 
                    output_fields=["id", "question", "answer", "tags", "create_date"],
                    limit=16000,
                    consistency_level="Strong"
                )

                sorted_results = sorted(results, key=lambda x: x.get("create_date"), reverse=True)

                formatted_results = []
                for result in sorted_results:
                    formatted_results.append({
                        "id": str(result.get("id")),
                        "question": str(result.get("question", "")),
                        "answer": str(result.get("answer", "")),
                        "tags": list(result.get("tags", []))
                    })
                
                return formatted_results
            elif VECTOR_DB_TYPE == 'hippo':
                if hippo_table is None:
                    return {"error": "Hippo客户端未初始化"}
                
                query_result = hippo_table.query_scalar(
                    output_fields=["id", "question", "answer", "tags", "create_date"],
                    expr="",
                    limit=50000
                )
                
                formatted_results = []
                
                if query_result and isinstance(query_result, dict):
                    # Hippo返回列式格式，需要转换为行式格式
                    ids = query_result.get('id', [])
                    questions = query_result.get('question', [])
                    answers = query_result.get('answer', [])
                    tags_list = query_result.get('tags', [])
                    create_dates = query_result.get('create_date', [])
                    
                    # 获取最大长度，确保所有字段都处理
                    max_length = max(len(ids), len(questions), len(answers), len(tags_list), len(create_dates))
                    
                    # 转换为行式格式
                    for i in range(max_length):
                        # 处理tags：如果是字符串则分割为列表
                        tags = []
                        if i < len(tags_list) and tags_list[i]:
                            if isinstance(tags_list[i], str):
                                tags = [tag.strip() for tag in tags_list[i].split(',') if tag.strip()]
                            elif isinstance(tags_list[i], list):
                                tags = tags_list[i]
                        
                        # 构建结果字典
                        formatted_results.append({
                            "id": ids[i] if i < len(ids) else "",
                            "question": questions[i] if i < len(questions) else "",
                            "answer": answers[i] if i < len(answers) else "",
                            "tags": tags,
                            "create_date": create_dates[i] if i < len(create_dates) else ""
                        })
                    
                    # 按创建时间倒序排序
                    formatted_results.sort(key=lambda x: x.get("create_date", ""), reverse=True)

                return formatted_results
            
        except Exception as e:
            return {"error": str(e)}
        
    @classmethod
    def get_faq_by_id(cls, faq_id: str) -> Dict[str, Any]:
        try:
            if VECTOR_DB_TYPE == 'milvus':
                expr = f"id == \"{faq_id}\""
                
                results = collection.query(
                    expr=expr,
                    output_fields=["id", "question", "answer", "tags", "create_date"]
                )
                
                if not results:
                    return {"error": "FAQ not found"}
                
                result = results[0]
                formatted_result = {
                    "answer": str(result.get("answer", "")),
                    "id": str(result.get("id")),
                    "question": str(result.get("question", "")),
                    "tags": list(result.get("tags", []))
                }
                
                return formatted_result
            elif VECTOR_DB_TYPE == 'hippo':
                if hippo_table is None:
                    return {"error": "Hippo客户端未初始化"}
                
                expr = f"id == '{faq_id}'"
                query_result = hippo_table.query_scalar(
                    output_fields=["id", "question", "answer", "tags"],
                    limit=1,
                    expr=expr
                )
                
                if query_result and isinstance(query_result, dict):
                    # 检查是否有数据返回
                    ids = query_result.get('id', [])
                    if not ids or len(ids) == 0:
                        return {"error": "FAQ not found"}
                    
                    # 获取第一条记录的数据
                    questions = query_result.get('question', [])
                    answers = query_result.get('answer', [])
                    tags_list = query_result.get('tags', [])
                    
                    # 处理tags
                    tags = []
                    if len(tags_list) > 0 and tags_list[0]:
                        if isinstance(tags_list[0], str):
                            tags = [tag.strip() for tag in tags_list[0].split(',') if tag.strip()]
                        elif isinstance(tags_list[0], list):
                            tags = tags_list[0]
                    
                    result = {
                        "id": ids[0],
                        "question": questions[0] if len(questions) > 0 else "",
                        "answer": answers[0] if len(answers) > 0 else "",
                        "tags": tags
                    }
                    
                    return result
                else:
                    return {"error": "FAQ not found"}
            
        except Exception as e:
            return {"error": str(e)}

    @classmethod
    def delete_faq(cls, faq_id: str) -> Tuple[bool, str]:
        try:
            if VECTOR_DB_TYPE == 'milvus':
                expr = f"id == \"{faq_id}\""
                collection.delete(expr)
                return True, "Success"
            elif VECTOR_DB_TYPE == 'hippo':
                if hippo_table is None:
                    return False, "Hippo客户端未初始化"
                
                expr = f"id == '{faq_id}'"
                result = hippo_table.delete_rows_by_query(expr)
                
                if result:
                    return True, "Success"
                else:
                    return False, "删除失败"
        except Exception as e:
            return False, str(e)

    @classmethod
    def upsert_faq(cls, update_data: dict) -> Tuple[bool, str]:
        try:
            if VECTOR_DB_TYPE == 'milvus':
                collection.upsert(update_data)
                return True, "Success"
            elif VECTOR_DB_TYPE == 'hippo':
                if hippo_table is None:
                    return False, "Hippo客户端未初始化"
                
                # Hippo使用列表格式：每个子列表代表一个字段的所有行数据
                upsert_data = [
                    [update_data["id"]],  # id字段
                    [update_data["question_v"]],  # question_v字段  
                    [update_data["question"]],  # question字段
                    [update_data["answer"]],  # answer字段
                    [update_data["tags"]],  # tags字段
                    [update_data["create_date"]],  # create_date字段
                    [update_data["update_date"]]  # update_date字段
                ]
                
                result = hippo_table.upsert_rows(upsert_data)
                
                if result:
                    return True, "Success"
                else:
                    return False, "更新失败"
        except Exception as e:
            return False, str(e)

    @classmethod
    def get_qa_by_question(cls, question_v: list, topk: int, expr: str) -> Union[List[Dict[str, Any]], Dict[str, str]]:
        try:
            if VECTOR_DB_TYPE == 'milvus':
                search_params = {
                    "metric_type": "L2",
                    "offset": 0,
                    "ignore_growing": False,
                    "params": {
                        "nprobe": 10
                    }
                }

                topk = int(topk)

                results = collection.search(
                    data = [question_v],
                    anns_field = "question_v",
                    param = search_params,
                    expr = expr,
                    limit = topk,
                    output_fields = ["answer", "id", "question", "tags"]
                )
                
                formatted_results = []
                for hits in results:
                    for hit in hits:
                        question = str(hit.entity.get("question")) if hit.entity.get("question") else ""
                        id = str(hit.entity.get("id")) if hit.entity.get("id") else ""
                        answer = str(hit.entity.get("answer")) if hit.entity.get("answer") else ""
                        tags = list(hit.entity.get("tags")) if hit.entity.get("tags") else []
                        score = float(hit.score) if hit.score else 0.0
                        score_formatted = '{:.10f}'.format(score).rstrip('0').rstrip('.') if '.' in '{:.10f}'.format(score) else '{:.1f}'.format(score)
                        
                        formatted_results.append({
                            "answer": answer,
                            "id": id,
                            "question": question,
                            "scores": score_formatted,
                            "tags": tags,
                        })
                
                return formatted_results
            elif VECTOR_DB_TYPE == 'hippo':
                if hippo_table is None:
                    return {"error": "Hippo客户端未初始化"}
                search_result = hippo_table.query(
                    "question_v",
                    vectors=[question_v],
                    topk=topk,
                    output_fields=["id", "question", "answer", "tags"],
                    dsl=expr
                )
                
                formatted_results = []
                
                # 处理Hippo返回的格式：字典包含字段和对应的scores
                if search_result and isinstance(search_result, list) and len(search_result) > 0:
                    result_data = search_result[0]  # 取第一个结果集
                    
                    if isinstance(result_data, dict):
                        # 获取各字段的数据和评分
                        ids = result_data.get('id', [])
                        questions = result_data.get('question', [])
                        answers = result_data.get('answer', [])
                        tags_list = result_data.get('tags', [])
                        
                        # 获取评分，优先使用id%scores，如果没有则尝试其他字段的scores
                        scores = (result_data.get('id%scores', []) or 
                                result_data.get('question%scores', []) or
                                result_data.get('answer%scores', []) or
                                result_data.get('tags%scores', []))
                        
                        # 处理结果
                        for i in range(len(ids)):
                            # 处理tags
                            tags = []
                            if i < len(tags_list) and tags_list[i]:
                                if isinstance(tags_list[i], str):
                                    tags = [tag.strip() for tag in tags_list[i].split(',') if tag.strip()]
                                elif isinstance(tags_list[i], list):
                                    tags = tags_list[i]
                            
                            # 格式化评分
                            score = scores[i] if i < len(scores) else 0.0
                            score_formatted = '{:.10f}'.format(score).rstrip('0').rstrip('.') if '.' in '{:.10f}'.format(score) else '{:.1f}'.format(score)
                            
                            formatted_results.append({
                                "answer": answers[i] if i < len(answers) else "",
                                "id": ids[i] if i < len(ids) else "",
                                "question": questions[i] if i < len(questions) else "",
                                "scores": score_formatted,
                                "tags": tags
                            })
                
                return formatted_results
            
        except Exception as e:
            return {"error": str(e)}
