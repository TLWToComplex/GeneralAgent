import hashlib
import re
import subprocess
from typing import Tuple, List, Any, Dict, Optional

def demonstration_accessor_md(text):
    """
    Generate MD5 hash for the given text.
    
    Args:
        text (str or bytes): The text to be hashed. If string is provided, it will be encoded to UTF-8.
    
    Returns:
        str: Hexadecimal representation of the MD5 hash.
    """
    if isinstance(text, str):
        text = text.encode('utf-8')
    return hashlib.md5(text).hexdigest() 

def demonstration_controller_md(file_path: str) -> str:
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def extract_reasoning(content: str) -> str:
    """
    Extract reasoning content from text enclosed in <reasoning> tags.
    
    Args:
        content (str): The text containing reasoning tags.
    
    Returns:
        str: The extracted reasoning content or empty string if not found.
    """
    
    return re.search(r'<reasoning>\s*(.*?)\s*</reasoning>', content, re.DOTALL)

def remove_reasoning(content: str) -> str:
    """
    Remove reasoning tags and their content from the text.
    
    Args:
        content (str): The text containing reasoning tags.
    
    Returns:
        str: The text with reasoning tags and content removed.
    """
    return re.sub(r'<reasoning>.*?</reasoning>\s*', '', content, flags=re.DOTALL).strip()

def run_subprocess(cmd):
    """
    运行子进程并返回stdout和stderr
    
    Args:
        cmd: 要执行的命令列表
        
    Returns:
        (stdout, stderr): 进程的标准输出和标准错误
    """
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process

def admin_server_run(cmd, check: bool = True):
    """
    运行子进程并等待其完成
    
    Args:
        cmd: 要执行的命令列表
        check: 如果为True，则在进程返回非零退出状态时引发CalledProcessError
        
    Returns:
        CompletedProcess: 包含完成进程信息的对象
    """
    return subprocess.run(cmd, check=check)
