"""
System recommendation accessor module.
Manages database operations for system recommendations and suggestions.
"""
from pymilvus import Collection, db, MilvusClient, connections
import os
from typing import Dict, Any, Tuple, List, Union, Optional
VECTOR_DB_NAME = "WDK"
VECTOR_COLLECTION_NAME_RS = "recommendation_systems"
MILVUS_URL = os.getenv('MILVUS_URL', '') 
if os.getenv('VECTOR_DB_TYPE', '') == 'milvus':
    root_client = MilvusClient(
        uri=MILVUS_URL,
        token="root:Milvus"
    )

    connections.connect(
        user=os.getenv('MILVUS_USER', 'aisix'),
        password=os.getenv('MILVUS_PASSWORD', '123456'),
        uri=MILVUS_URL
    )

    db.using_database(VECTOR_DB_NAME)
    collection = Collection(VECTOR_COLLECTION_NAME_RS)

class SystemRecommandationAccessor:

    @classmethod
    def add(cls, data: dict) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        try:
            collection.insert(data)
            return True, "Success"
        except Exception as e:
            return False, {"code": 400, "message": str(e)}
        
    @classmethod
    def get_by_id(cls, id: str) -> Optional[Dict[str, Any]]:
        query_result = collection.query(
            expr=f"id == '{id}'",
            output_fields=["id", "name", "description", "url", "url_type"]
        )
        if query_result:
            return query_result[0]
        else:
            return None
        
    @classmethod
    def list(cls) -> Optional[List[Dict[str, Any]]]:
        query_result = collection.query(
            expr="",
            output_fields=["id", "name", "description", "url", "url_type"],
            limit=16000,
            consistency_level="Strong"
        )
        if not query_result:
            return None
            
        # 使用字典来合并相同系统的数据
        merged_results = {}
        for item in query_result:
            # 使用name、url和url_type的组合作为键
            key = f"{item['name']}_{item['url']}_{item['url_type']}"
            if key not in merged_results:
                merged_results[key] = {
                    "description": [item['description']],
                    "id": [item['id']],
                    "name": item['name'],
                    "url": item['url'],
                    "url_type": item['url_type']
                }
            else:
                merged_results[key]['description'].append(item['description'])
                merged_results[key]['id'].append(item['id'])
        
        # 将字典转换为列表
        return list(merged_results.values())
        
    @classmethod
    def update(cls, data: dict) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        try:
            collection.upsert(data)
            return True, "Success"
        except Exception as e:
            return False, {"code": 400, "message": str(e)}
    
    @classmethod
    def delete(cls, id: str) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        try:
            collection.delete(
                expr=f"id == '{id}'"
            )
            return True, "Success"
        except Exception as e:
            return False, {"code": 400, "message": str(e)}

    @classmethod
    def get_system_recommendation_by_description(cls, description_v: list, topk: int) -> Dict[str, Any]:
        search_params = {
                "metric_type": "L2",
                "offset": 0,
                "ignore_growing": False,
                "params": {
                    "nprobe": 10
                }
            }
        query_result = collection.search(
            data = [description_v],
            anns_field = "description_v",
            param = search_params,
            output_fields = ["id", "description", "name", "url", "url_type"],
            limit = int(topk),
        )
        
        classified_results = {
            "xt": [],  # 系统
            "mx": [],  # 模型
            "pk": [],  # 配块
            "mk": [],  # 模块
            "cp": []   # 产品
        }
        
        # 使用字典来合并相同系统的数据
        merged_results = {}
        
        # 处理查询结果
        for hits in query_result:
            for hit in hits:
                # 获取相似度分数
                score = hit.score if hasattr(hit, 'score') else 0.0
                
                name = str(hit.entity.get("name")) if hit.entity.get("name") else ""
                url = str(hit.entity.get("url")) if hit.entity.get("url") else ""
                url_type = str(hit.entity.get("url_type")) if hit.entity.get("url_type") else ""
                # 使用name、url和url_type的组合作为键
                key = f"{name}_{url}_{url_type}"
                
                if key not in merged_results:
                    merged_results[key] = {
                        "id": str(hit.entity.get("id")) if hit.entity.get("id") else "",
                        "mc": name,
                        "ms": str(hit.entity.get("description")) if hit.entity.get("description") else "",
                        "xtUrl": url,
                        "type": url_type,
                        "score": max(0, float(1 - score))
                    }
                else:
                    # 更新最高相似度分数
                    merged_results[key]['score'] = max(merged_results[key]['score'], max(0, float(1 - score)))
        
        # 根据type分类
        for result in merged_results.values():
            type_value = result["type"].lower()
            if "系统" in type_value:
                classified_results["xt"].append(result)
            elif "模型" in type_value:
                classified_results["mx"].append(result)
            elif "配块" in type_value:
                classified_results["pk"].append(result)
            elif "模块" in type_value:
                classified_results["mk"].append(result)
            elif "产品" in type_value:
                classified_results["cp"].append(result)
        
        # 对每个分类的结果按照分数从高到低排序
        for category in classified_results:
            classified_results[category].sort(key=lambda x: x['score'], reverse=True)
        
        return {
            "code": 200,
            "message": "操作成功",
            "data": classified_results
        }
