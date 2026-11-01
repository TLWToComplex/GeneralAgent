"""ORM 模型导出。

``Base.metadata`` 需要模型被导入后才完整，因此建表前请先 ``import app.models``。
"""
from app.models.dsh_instance import AIDshInstance
from app.models.password_history import AIPasswordHistory
from app.models.user import AIUser

__all__ = ["AIUser", "AIPasswordHistory", "AIDshInstance"]