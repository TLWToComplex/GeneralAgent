"""
HTTP client utility module.
Provides HTTP client functions for making API requests to external services.
"""
import requests
import os
from typing import Dict, Any, Optional, Union, List, Tuple
VLM_URLS = os.getenv('VLM_URLS', '')
F1_SERVICE = os.getenv('F1_SERVICE','')
K1_SERVICE = os.getenv('K1_SERVICE', '')
RERANK_URLS = os.getenv('RERANK_URLS', '')


def _handle_response(response: requests.Response) -> Optional[Union[Dict[str, Any], str]]:
    """
    处理HTTP响应。
    :param response: requests库返回的响应对象。
    :return: 响应的JSON数据或文本。
    """
    try:
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP错误: {http_err}")
        return None
    except ValueError:
        return response.text
    except Exception as err:
        print(f"其他错误: {err}")
        return None 


service_mapping = {
    "f1_service": F1_SERVICE,
    "k1_service": K1_SERVICE,
    "vlm_service": VLM_URLS,
    "rerank_service": RERANK_URLS
}


def _build_url(service_name: str, endpoint: str) -> str:
    """
    构建完整的请求URL，自动根据服务名选择对应的IP地址。
    :param service_name: 服务名称，用于查找对应的IP地址。
    :param endpoint: 请求的API端点。
    :return: 完整的URL。
    """
    base_url = service_mapping.get(service_name)
    if not base_url:
        raise ValueError(f"未找到服务 {service_name} 对应的IP地址。")
    return f"{base_url}{endpoint}"


class HTTPClient:
    def __init__(self, headers: Optional[Dict[str, str]] = None):
        """
        初始化HTTP客户端，不再需要base_url，改为通过服务映射自动管理。
        :param headers: 默认的请求头，可选。
        """
        self.headers = headers if headers else {}

    def get(self, service_name: str, endpoint: str, params: Optional[Dict[str, Any]] = None, 
            headers: Optional[Dict[str, str]] = None) -> Optional[Union[Dict[str, Any], str]]:
        """
        发送GET请求。
        :param service_name: 服务名称，用于自动选择对应的IP地址。
        :param endpoint: API端点。
        :param params: 请求参数，可选。
        :param headers: 请求头，可选。
        :return: 响应对象。
        """
        url = _build_url(service_name, endpoint)
        response = requests.get(url, params=params, headers=headers or self.headers)
        return _handle_response(response)

    def post(self, service_name: str, endpoint: str, data: Any = None, json: Any = None, 
             headers: Optional[Dict[str, str]] = None) -> Optional[Union[Dict[str, Any], str]]:
        """
        发送POST请求。
        :param service_name: 服务名称，用于自动选择对应的IP地址。
        :param endpoint: API端点。
        :param data: 请求体，使用表单数据格式（可选）。
        :param json: 请求体，使用JSON格式（可选）。
        :param headers: 请求头，可选。
        :return: 响应对象。
        """
        url = _build_url(service_name, endpoint)
        response = requests.post(url, data=data, json=json, headers=headers or self.headers)
        return _handle_response(response)

    def put(self, service_name: str, endpoint: str, data: Any = None, json: Any = None, 
            headers: Optional[Dict[str, str]] = None) -> Optional[Union[Dict[str, Any], str]]:
        """
        发送PUT请求。
        :param service_name: 服务名称，用于自动选择对应的IP地址。
        :param endpoint: API端点。
        :param data: 请求体，使用表单数据格式（可选）。
        :param json: 请求体，使用JSON格式（可选）。
        :param headers: 请求头，可选。
        :return: 响应对象。
        """
        url = _build_url(service_name, endpoint)
        response = requests.put(url, data=data, json=json, headers=headers or self.headers)
        return _handle_response(response)

    def delete(self, service_name: str, endpoint: str, 
               headers: Optional[Dict[str, str]] = None) -> Optional[Union[Dict[str, Any], str]]:
        """
        发送DELETE请求。
        :param service_name: 服务名称，用于自动选择对应的IP地址。
        :param endpoint: API端点。
        :param headers: 请求头，可选。
        :return: 响应对象。
        """
        url = _build_url(service_name, endpoint)
        response = requests.delete(url, headers=headers or self.headers)
        return _handle_response(response)
