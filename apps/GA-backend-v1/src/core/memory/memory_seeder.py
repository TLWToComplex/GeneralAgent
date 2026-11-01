"""
记忆种子模块 - 为 deepagent 的每个用户首次对话创建初始记忆文件。

仅在文件不存在时写入，已有进化内容不会被覆盖。
目录结构：{base}/{agent_uuid}/{user_uuid}/{filename}
其中 {base} 取自 container_path（主容器视角）：种子写入与管理接口读写均走这里。
volume mount 源路径（宿主机视角）由调用方单独使用 host_path 拼装。
"""
import logging
import os
import shutil
from typing import Dict, List, Optional
from src.accessors.ai_user_accessor import AIUser
from src.utils.config_manager import config_manager

logger = logging.getLogger(__name__)


# AGENTS.md 种子模板：核心身份 + 三个文件的职责说明
# MemoryMiddleware 会在 system prompt 中以 <agent_memory> 标签注入这些内容
_AGENTS_MD_SEED = """## 核心身份

你是一个具备记忆能力的 DeepAgent。你的记忆通过文件系统持久化，由三个 markdown 文件组成。

## 记忆文件职责

记忆系统包含三个文件，请严格按其职责使用 `edit_file` 工具更新对应文件：

- `AGENTS.md`（本文件）：身份、行为准则、自我进化规则。当你发现更好的通用工作方法时更新。
- `preferences.md`：用户的主观偏好。当用户表达对格式、语言、风格、工具使用方式的偏好时更新。
- `knowledge.md`：客观知识与经验教训。当你学到新的领域知识、踩坑教训或可复用的事实时更新。

## 行为准则

- 优先使用 `/workspace/skills_repo/` 下已有技能完成任务，避免重复造轮子。
- 涉及 Word/PPT/Excel 文档读写时必须使用对应技能。
- 工作目录始终是 `/workspace`，所有产出文件保存到 `/workspace`，不要保存到 `/workspace/temp`。
- 用户上传的临时文件位于 `/workspace/temp`，使用完整路径访问。

## 自我进化原则

- 当用户给出反馈（无论好坏）时，先把"为什么"沉淀到对应记忆文件，再回应用户。
- 当用户明确要求"记住"某事时，立即调用 `edit_file` 写入对应文件，再继续后续动作。
- 不要记录敏感信息（API Key、密码、token、个人身份信息）。
- 不要记录一次性、临时性的信息（如"今天我心情不好"、"现在几点"）。
"""


_PREFERENCES_MD_SEED = """## 用户信息及偏好记录

本文件保存用户的基本信息，记录并更新用户的主观偏好。当用户表达对输出格式、语言、风格、工具使用方式的倾向时，使用 `edit_file` 在对应小节追加或更新条目。以用户最近一次表达的偏好为准，当用户表达了对应的新偏好时，需要更新为新偏好。

### 用户信息
- 用户姓名：{realname}

### 输出格式偏好
（暂无记录）

### 语言与风格偏好
（暂无记录）

### 工具与流程偏好
（暂无记录）
"""


_KNOWLEDGE_MD_SEED = """## 知识与经验

本文件记录并更新错误教训、可复用经验。使用 `edit_file` 在对应小节追加或更新条目。以学到的最新的正确的知识和经验为准，当学到新知识或经验时，需要更新为新内容。

### 错误教训
（暂无记录）

### 可复用经验
（暂无记录）
"""


_SEED_TEMPLATES: Dict[str, str] = {
    "AGENTS.md": _AGENTS_MD_SEED,
    "preferences.md": _PREFERENCES_MD_SEED,
    "knowledge.md": _KNOWLEDGE_MD_SEED,
}


def get_user_memory_dir(agent_uuid: str, user_uuid: str) -> str:
    """获取主容器内某 agent + 用户的记忆目录绝对路径（用于种子写入与管理接口读写）。"""
    container_base = config_manager.get_memory_container_path()
    return os.path.join(container_base, agent_uuid, user_uuid)


def get_user_memory_host_dir(agent_uuid: str, user_uuid: str) -> str:
    """获取宿主机视角下某 agent + 用户的记忆目录绝对路径（用于沙盒子容器 -v 挂载源）。"""
    host_base = config_manager.get_memory_host_path()
    return os.path.join(host_base, agent_uuid, user_uuid)


def seed_initial_memories(
    agent_uuid: str,
    user_uuid: str,
    file_names: Optional[List[str]] = None,
    overwrite: bool = False,
) -> str:
    """
    为指定 agent + 用户创建初始记忆文件（仅当文件不存在时写入）。

    Args:
        agent_uuid: Agent UUID
        user_uuid: 用户 UUID（来自 AIUser.uuid，从 JWT 解析）
        file_names: 要创建的文件清单，默认使用配置中的全量清单
        overwrite: 是否覆盖已存在的文件（用于 /aiMemory/clear 重置场景）

    Returns:
        创建的目录绝对路径
    """
    if not agent_uuid or not user_uuid:
        raise ValueError("agent_uuid 与 user_uuid 均不能为空")

    user = AIUser.query.filter_by(uuid=user_uuid).first()
    if not user:
        realname = "未知"
    else:
        realname = user.realname or "未知"

    agent_memory_dir = get_user_memory_dir(agent_uuid, user_uuid)
    os.makedirs(agent_memory_dir, exist_ok=True)

    files = file_names if file_names is not None else config_manager.get_memory_files()
    for filename in files:
        # 未在模板表中的文件，写入空内容（保证 MemoryMiddleware 能 read 到）
        template = _SEED_TEMPLATES.get(filename) or ""
        filepath = os.path.join(agent_memory_dir, filename)
        if not overwrite and os.path.exists(filepath):
            continue
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(template.format(realname=realname))
            logger.info(f"已写入记忆种子: {filepath}")
        except Exception as e:
            logger.error(f"写入记忆种子失败 {filepath}: {e}")
            raise

    return agent_memory_dir


def reset_memories(agent_uuid: str, user_uuid: str) -> str:
    """
    清空指定 agent + 用户的所有记忆文件，并重写为初始种子。
    """
    return seed_initial_memories(agent_uuid, user_uuid, overwrite=True)


def delete_agent_memory(agent_uuid: str) -> Optional[str]:
    """
    删除指定 agent 的全部记忆目录（含所有用户的子目录）。
    在 agent 删除时调用，避免遗留孤儿记忆数据。

    Args:
        agent_uuid: Agent UUID

    Returns:
        被删除的目录绝对路径；目录不存在或配置未启用时返回 None。
    """

    if not agent_uuid:
        return None

    if not config_manager.get_memory_enabled(agent_uuid):
        return None

    container_base = config_manager.get_memory_container_path()
    if not container_base:
        return None

    agent_dir = os.path.join(container_base, agent_uuid)
    if not os.path.isdir(agent_dir):
        logger.info(f"Agent 记忆目录不存在，跳过删除: {agent_dir}")
        return None

    try:
        shutil.rmtree(agent_dir)
        logger.info(f"已删除 agent 记忆目录: {agent_dir}")
        return agent_dir
    except Exception as e:
        logger.error(f"删除 agent 记忆目录失败 {agent_dir}: {e}")
        raise
