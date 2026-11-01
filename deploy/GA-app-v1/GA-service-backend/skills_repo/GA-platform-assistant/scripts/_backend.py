"""共享 HTTP 工具：封装对后台 admin_server 的调用。

沙盒内默认通过后台地址访问宿主机的 admin_server。
环境变量：
    BACKEND_URL    后台基础地址
    USER_NAME      默认 'admin'
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional


DEFAULT_BACKEND_URL = "http://host.docker.internal:8038"
DEFAULT_USER_NAME = "admin"


def get_backend_url() -> str:
    return (os.getenv("BACKEND_URL") or DEFAULT_BACKEND_URL).rstrip("/")


def get_user_name() -> str:
    return os.getenv("USER_NAME") or DEFAULT_USER_NAME


def _build_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {get_user_name()}",
        "Content-Type": "application/json",
    }


def http_get(path: str, params: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Dict[str, Any]:
    base = get_backend_url()
    query = ""
    if params:
        # 过滤 None / 空字符串
        clean = {k: v for k, v in params.items() if v not in (None, "", [])}
        if clean:
            query = "?" + urllib.parse.urlencode(clean, doseq=True)
    url = f"{base}{path}{query}"
    req = urllib.request.Request(url, headers=_build_headers(), method="GET")
    return _do_request(req, timeout)


def http_post(path: str, body: Optional[Dict[str, Any]] = None, timeout: int = 60) -> Dict[str, Any]:
    base = get_backend_url()
    url = f"{base}{path}"
    payload = json.dumps(body or {}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=_build_headers(), method="POST")
    return _do_request(req, timeout)


def _do_request(req: urllib.request.Request, timeout: int) -> Dict[str, Any]:
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return {"raw": data}
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass
        die(f"后台返回 HTTP {e.code}: {body or e.reason} | url={req.full_url}")
    except urllib.error.URLError as e:
        die(f"无法连接后台 ({e.reason})：请确认 BACKEND_URL，当前值 {get_backend_url()}")
    except Exception as e:
        die(f"调用后台异常: {e}")


def die(msg: str, code: int = 1) -> None:
    print(json.dumps({"error": msg}, ensure_ascii=False))
    sys.exit(code)


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))
