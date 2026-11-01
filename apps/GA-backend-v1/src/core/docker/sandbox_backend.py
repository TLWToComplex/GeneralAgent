"""
Docker沙盒后端模块。
提供在Docker容器中执行命令和文件操作的后端实现。
"""
import logging
import os
import tarfile
import io
from typing import List, Union
from deepagents.backends import FilesystemBackend
from deepagents.backends.protocol import FileInfo, FileDownloadResponse, FileUploadResponse, WriteResult, SandboxBackendProtocol, ExecuteResponse
try:
    from deepagents.backends.protocol import LsResult
except ImportError:
    # deepagents < 0.5.0 doesn't have LsResult
    from dataclasses import dataclass
    @dataclass
    class LsResult:  # type: ignore[no-redef]
        error: str | None = None
        entries: list | None = None
from deepagents.backends.utils import format_content_with_line_numbers, check_empty_content
from src.utils.config_manager import config_manager
from src.core.docker.container_manager import container_manager
from src.accessors.ai_agent_accessor import AIAgent
from src.accessors.ai_skill_accessor import AISkill
from src.accessors.ai_user_accessor import AIUser

logger = logging.getLogger(__name__)


class DockerSandboxBackend(FilesystemBackend, SandboxBackendProtocol):
    """
    A backend that executes commands and file operations in a Docker container.
    Overrides FilesystemBackend methods to ensure all operations happen in the container.
    """
    def __init__(self,
                 image: str = "skill-agent:latest",
                 container_name: str = "skill-agent-sandbox",
                 work_dir: str = "/workspace",
                 mount_skills: bool = True,
                 agent_uuid: str = None,
                 user_uuid: str = None,
                 skill_replacements: dict = None,
                 user_token: str = None,
                 session_thread_id: str = None):
        # Initialize parent with local path for compatibility, but we will override methods
        try:
            super().__init__(root_dir=".")
        except Exception:
            pass

        self.image = image
        self.container_name = container_name
        self.work_dir = work_dir
        self.mount_skills = mount_skills
        self.agent_uuid = agent_uuid
        self.user_uuid = user_uuid
        self.session_thread_id = session_thread_id
        # skill folder_name -> additional_info dict, 用于 skill.md 占位符替换
        self._skill_replacements: dict = skill_replacements or {}
        # 容器环境变量
        self._environment = config_manager.get_sandbox_env(agent_uuid=self.agent_uuid)
        success, user_data = AIUser.get_user(uuid=self.user_uuid)
        if success and user_data:
            self._environment["USER_NAME"] = user_data.get("username")
        if self._environment.get("USER_TOKEN", ""):
            self._environment["USER_TOKEN"] = user_token
        # 内网镜像源模式（package_mode='mirror'）：把 pip/npm 内网源注入容器环境变量，
        # 使模型可按需 pip install / npm install -g（提示词第 6 条会相应声明可从内网源安装）。
        # 注意：apt 源写在文件里（/etc/apt/sources.list），运行时不能用 env 切换，
        #       需构建镜像时用 --build-arg APT_MIRROR=<内网> 指定；此处只注入 pip/npm。
        if (config_manager.get_package_mode() or "").strip().lower() == "mirror":
            from urllib.parse import urlparse
            _pip_url = (config_manager.get_pip_mirror_url() or "").strip()
            if _pip_url:
                self._environment["PIP_INDEX_URL"] = _pip_url
                # 内网源常为 http，需同时声明 trusted host，否则 pip 会拒绝连接
                _pip_host = urlparse(_pip_url).hostname
                if _pip_host:
                    self._environment["PIP_TRUSTED_HOST"] = _pip_host
            _npm_url = (config_manager.get_npm_mirror_url() or "").strip()
            if _npm_url:
                # npm 读取 npm_config_registry 环境变量，优先级高于镜像内 `npm config set registry`
                self._environment["npm_config_registry"] = _npm_url
        logger.info(
            f"DockerSandboxBackend init: work_dir={self.work_dir}, container={self.container_name}, "
            f"image={self.image}, agent_uuid={self.agent_uuid}, user_uuid={self.user_uuid}, environment={self._environment}"
        )
        self.container = self._get_or_create_container()

    def _apply_skill_replacements(self, path: str, content: str) -> str:
        """对 skill 目录下的文件内容进行 {{key}} 占位符替换。"""
        if not self._skill_replacements:
            return content

        sandbox_skills_path = config_manager.get_skills_sandbox_path()
        normalized_path = path if path.startswith('/') else f"/{path}"

        for folder_name, replacements in self._skill_replacements.items():
            skill_dir = f"{sandbox_skills_path.rstrip('/')}/{folder_name}"
            if normalized_path.startswith(skill_dir):
                if isinstance(replacements, dict):
                    for key, value in replacements.items():
                        placeholder = f"{{{{{key}}}}}"
                        content = content.replace(placeholder, str(value))
                break

        return content

    @staticmethod
    def _get_skill_folder_names(skill_uuids: List) -> List[str]:
        """将 skill uuid 列表转换为沙盒中的技能路径列表

        如果 skill_uuids 为空，返回空列表
        """

        if not skill_uuids:
            return []

        folder_names = []
        # 批量查询技能记录，避免 N+1 查询问题
        for skill_record in AISkill.query.filter(AISkill.uuid.in_(skill_uuids)).all():
            if skill_record.folder_name:
                folder_names.append(skill_record.folder_name)

        if not folder_names:
            return []

        return folder_names

    def _get_or_create_container(self):
        # 准备挂载卷
        volumes = {}
        if self.mount_skills:
            # 获取宿主机的 skills_repo 路径（统一通过配置或环境变量传入）
            skills_path = config_manager.get_host_skills_path()

            if not skills_path:
                # 未配置 host_path 时，fallback 到本地路径
                skills_path = os.path.abspath(config_manager.get_skills_path())
                logger.warning(f"host_skills_path not configured, falling back to local path: {skills_path}")

            if skills_path:
                success, agent_data = AIAgent.get_agent(uuid=self.agent_uuid)
                if success and agent_data:
                    skill_uuids = agent_data.get("config", {}).get("skills") or []
                    skill_folder_names = self._get_skill_folder_names(skill_uuids)
                    for folder_name in skill_folder_names:
                        skill_path = os.path.join(skills_path, folder_name)
                        skill_sandbox_path = os.path.join(config_manager.get_skills_sandbox_path(), folder_name)
                        volumes[skill_path] = {'bind': skill_sandbox_path, 'mode': 'ro'}
                        logger.info(f"Mounting skills path: {skill_path} -> {skill_sandbox_path}")
                # container_mount_path = config_manager.get_skills_sandbox_path()
                # volumes[skills_path] = {'bind': container_mount_path, 'mode': 'ro'}
            else:
                logger.warning("Skills path not set, skipping mount.")

        # Per-user 记忆挂载：仅当 agent_uuid + user_uuid 都存在时启用
        # 是否实际加载到 system prompt 由 agent_init_service 中的 memory_enabled 判断（受 agent_type 控制）
        # host_path 与 container_path 角色分离：
        #   - container_path：主容器内种子写入位置（os.makedirs/open 走这里）
        #   - host_path：宿主机 Docker daemon 创建沙盒子容器时使用的挂载源
        if config_manager.get_memory_enabled(self.agent_uuid) and self.agent_uuid and self.user_uuid:
            try:
                from src.core.memory.memory_seeder import (
                    seed_initial_memories,
                    get_user_memory_host_dir,
                )
                memory_host_base = config_manager.get_memory_host_path()
                memory_container_base = config_manager.get_memory_container_path()
                if memory_host_base and memory_container_base:
                    # 在主容器内写种子（仅在文件不存在时创建）
                    seed_initial_memories(self.agent_uuid, self.user_uuid)
                    # 沙盒挂载源用宿主机视角路径
                    memory_mount_source = get_user_memory_host_dir(self.agent_uuid, self.user_uuid)
                    memory_sandbox_path = config_manager.get_memory_sandbox_path()
                    volumes[memory_mount_source] = {'bind': memory_sandbox_path, 'mode': 'rw'}
                    logger.info(
                        f"Mounting memory: host={memory_mount_source} -> sandbox={memory_sandbox_path} (rw)"
                    )
                else:
                    logger.warning(
                        "memory host_path 或 container_path 未配置，跳过记忆挂载 "
                        f"(host_path={memory_host_base!r}, container_path={memory_container_base!r})"
                    )
            except Exception as e:
                logger.error(f"Failed to seed/mount memory directory: {e}", exc_info=True)

        output_file_host_dir = os.path.join(config_manager.get_file_host_path(), str(self.session_thread_id), "output")
        output_file_sandbox_dir = config_manager.get_file_sandbox_path()
        volumes[output_file_host_dir] = {'bind': output_file_sandbox_dir}

        # 使用容器管理器创建或获取容器
        container = container_manager.create_container(
            image_name=self.image,
            container_name=self.container_name,
            command="tail -f /dev/null",
            volumes=volumes,
            working_dir=self.work_dir,
            detach=True,
            auto_remove=False,
            environment=self._environment,
        )

        if container:
            logger.info(f"Container ready: {self.container_name}")
            # 验证沙盒容器内 skills 目录是否有效，无效则 fallback 复制
            sandbox_skills_path = config_manager.get_skills_sandbox_path()
            exit_code, output = container.exec_run(["bash", "-c", f"ls -A '{sandbox_skills_path}' 2>/dev/null"])
            if exit_code != 0 or not output.decode('utf-8').strip():
                logger.warning(f"Skills directory '{sandbox_skills_path}' is empty or not found in container, falling back to copy")
                if not self._copy_skills_to_container(container, sandbox_skills_path):
                    logger.error("Fallback copy of skills to container also failed!")
        else:
            logger.error(f"Failed to get or create container: {self.container_name}")

        return container

    def _copy_skills_to_container(self, container, container_mount_path: str) -> bool:
        """将宿主机的 skills_repo 目录复制到容器内（当卷挂载失败时的后备方案）"""
        try:
            skills_path = config_manager.get_skills_path()
            skills_path_abs = os.path.abspath(skills_path)
            if not os.path.isdir(skills_path_abs):
                logger.error(f"Local skills path does not exist: {skills_path_abs}")
                return False
            container.exec_run(["bash", "-c", f"mkdir -p '{container_mount_path}'"])
            for skill_name in os.listdir(skills_path_abs):
                skill_dir = os.path.join(skills_path_abs, skill_name)
                if not os.path.isdir(skill_dir):
                    continue
                tar_stream = io.BytesIO()
                with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                    for root, dirs, files in os.walk(skill_dir):
                        for fname in files:
                            fpath = os.path.join(root, fname)
                            arcname = os.path.relpath(fpath, skill_dir)
                            tar.add(fpath, arcname=arcname)
                tar_stream.seek(0)
                container.exec_run(["bash", "-c", f"mkdir -p '{container_mount_path}/{skill_name}'"])
                success = container.put_archive(path=f"{container_mount_path}/{skill_name}", data=tar_stream)
                if not success:
                    logger.error(f"Failed to copy skill '{skill_name}' to container")
                else:
                    logger.info(f"Copied skill '{skill_name}' to container")
            # 验证复制结果
            exit_code, output = container.exec_run(["bash", "-c", f"ls -A '{container_mount_path}' 2>/dev/null"])
            if exit_code == 0 and output.decode('utf-8').strip():
                logger.info(f"Skills copied successfully to '{container_mount_path}'")
                return True
            else:
                logger.error(f"Skills copy verification failed for '{container_mount_path}'")
                return False
        except Exception as e:
            logger.error(f"Error copying skills to container: {e}", exc_info=True)
            return False

    @property
    def id(self) -> str:
        return self.container.id

    def execute(self, command: str, timeout: int = None) -> ExecuteResponse:
        """Execute a shell command in the container."""
        wrapped_command = f"cd {self.work_dir} && {command}"
        exit_code, output = self.container.exec_run(
            cmd=["bash", "-c", wrapped_command]
        )
        result = output.decode('utf-8')
        if exit_code != 0:
            logger.error(f"Command failed (code {exit_code}): {result}")

        return ExecuteResponse(
            output=result,
            exit_code=exit_code
        )

    def _read_file_content(self, path: str, binary: bool = False) -> Union[str, bytes]:
        """Helper to read file content from container."""
        try:
            # 规范化工作目录路径，确保以 / 结尾
            normalized_work_dir = self.work_dir.rstrip('/') + '/'

            # 仅相对路径拼接工作目录；绝对路径原样透传。
            # 不要改写绝对路径：execute() 与 read() 运行在同一容器内，
            # 模型经 execute 写入 /tmp 等位置的文件是真实存在的，
            # 一旦拼成 /workspace/tmp/... 就会读不到（历史 bug）。
            if not path.startswith("/"):
                path = f"{normalized_work_dir}{path}"

            # Check if file exists first
            check_cmd = f"test -f '{path}'"
            exit_code, _ = self.container.exec_run(["bash", "-c", check_cmd])
            if exit_code != 0:
                raise FileNotFoundError(f"File not found: {path}")

            # Read file content using cat
            cat_cmd = ["cat", path]
            exit_code, output = self.container.exec_run(cat_cmd)

            if exit_code != 0:
                raise Exception(f"Failed to read file {path}: {output.decode('utf-8', errors='ignore')}")

            if binary:
                return output

            try:
                text = output.decode('utf-8')
                # 对 skill 目录下的文件进行 {{key}} 占位符替换
                text = self._apply_skill_replacements(path, text)
                return text
            except UnicodeDecodeError:
                #二进制文件（如 docx, xlsx, pdf 等）无法作为文本读取，返回提示
                import os
                ext = os.path.splitext(path)[1].lower()
                binary_extensions = {'.docx', '.xlsx', '.xls', '.pdf', '.pptx', '.doc', '.ppt', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.zip', '.rar', '.7z'}
                if ext in binary_extensions:
                    return f"[二进制文件: {os.path.basename(path)}，无法以文本方式读取，请使用对应的工具或Python脚本来处理]"
                raise ValueError("File content appears to be binary and cannot be read as text.")

        except Exception as e:
            if isinstance(e, (FileNotFoundError, ValueError)):
                logger.warning(f"Read file warning for {path}: {e}")
            else:
                logger.error(f"Error reading file {path}: {e}")
            raise

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        """Read file content with line numbers (overrides FilesystemBackend)."""
        try:
            content = self._read_file_content(file_path)

            empty_msg = check_empty_content(content)
            if empty_msg:
                return empty_msg

            lines = content.splitlines()
            start_idx = offset
            end_idx = min(start_idx + limit, len(lines))

            if start_idx >= len(lines):
                return f"Error: Line offset {offset} exceeds file length ({len(lines)} lines)"

            selected_lines = lines[start_idx:end_idx]
            return format_content_with_line_numbers(selected_lines, start_line=start_idx + 1)
        except Exception as e:
            logger.error(f"Error in read: {e}", exc_info=True)
            return f"Error reading file '{file_path}': {e}"

    def write(self, file_path: str, content: Union[str, List[str]]) -> WriteResult:
        """Write file to container (overrides FilesystemBackend)."""
        try:
            # 规范化工作目录路径，确保以 / 结尾
            normalized_work_dir = self.work_dir.rstrip('/') + '/'

            # 仅相对路径拼接工作目录；绝对路径原样透传（须与 _read_file_content 保持对称）
            target_path = file_path
            if not target_path.startswith("/"):
                target_path = f"{normalized_work_dir}{target_path}"

            # Convert content to string
            if isinstance(content, list):
                content = '\n'.join(content)

            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                data = content.encode('utf-8')
                tar_info = tarfile.TarInfo(name=os.path.basename(target_path))
                tar_info.size = len(data)
                tar.addfile(tar_info, io.BytesIO(data))

            tar_stream.seek(0)
            parent_dir = os.path.dirname(target_path)

            if parent_dir:
                # 使用双引号包裹路径，处理包含空格和特殊字符的路径
                self.execute(f"mkdir -p \"{parent_dir}\"")

            self.container.put_archive(
                path=parent_dir or self.work_dir,
                data=tar_stream
            )
            return WriteResult(path=file_path)
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            return WriteResult(error=str(e))

    def ls_info(self, path: str) -> List[FileInfo]:
        """List files in container (overrides FilesystemBackend)."""
        # 仅相对路径拼接工作目录；绝对路径原样透传（须与 _read_file_content 保持对称）
        target_path = path
        if not target_path.startswith("/"):
            if target_path == ".":
                target_path = self.work_dir
            else:
                target_path = f"{self.work_dir}/{target_path}"

        # 使用 ls -la 获取详细的文件列表
        ls_cmd = f"ls -la --color=never '{target_path}'"
        ls_response = self.execute(ls_cmd)

        if ls_response.exit_code != 0:
            logger.error(f"ls_info failed: {ls_response.output}")
            return []

        output = ls_response.output.strip()
        if not output:
            return []

        results: List[FileInfo] = []
        for line in output.splitlines():
            line = line.strip()

            # 跳过 total 行和 . / ..
            if not line or line.startswith('total'):
                continue
            if line.endswith(' .') or line.endswith(' ..'):
                continue

            try:
                parts = line.split()
                if len(parts) < 9:
                    continue

                perms = parts[0]
                is_dir = perms.startswith('d')

                # 获取文件名（从第9个字段开始，文件名可能包含空格）
                filename = ' '.join(parts[8:])

                if filename == '.' or filename == '..':
                    continue

                try:
                    size = int(parts[4])
                except (IndexError, ValueError):
                    size = 0

                modified = ' '.join(parts[5:8])

                display_path = filename + "/" if is_dir else filename

                if target_path != self.work_dir:
                    relative_path = target_path[len(self.work_dir):]
                    if relative_path.startswith("/"):
                        relative_path = relative_path[1:]
                    display_path = f"{relative_path}/{display_path}" if relative_path else display_path

                results.append({
                    "path": display_path,
                    "is_dir": is_dir,
                    "size": size,
                    "modified_at": modified
                })
            except Exception as e:
                logger.error(f"Error parsing ls line '{line}': {e}")

        results.sort(key=lambda x: x.get("path", ""))
        return results

    def download_files(self, paths: List[str]) -> List[FileDownloadResponse]:
        """Download files from container (overrides FilesystemBackend)."""
        responses = []
        logger.info(f"Downloading files: {paths}")
        for path in paths:
            try:
                # Read as binary
                content = self._read_file_content(path, binary=True)
                responses.append(FileDownloadResponse(
                    path=path,
                    content=content
                ))
            except Exception as e:
                logger.error(f"Error downloading file {path}: {e}")
                responses.append(FileDownloadResponse(
                    path=path,
                    error="file_not_found"
                ))
        return responses

    def upload_files(self, files: List[tuple]) -> List[FileUploadResponse]:
        """Upload files to container (overrides FilesystemBackend)."""
        responses = []
        for path, content in files:
            try:
                # Use write logic but for bytes
                # Handle absolute/relative paths
                target_path = path
                if not target_path.startswith("/"):
                    target_path = f"{self.work_dir}/{target_path}"

                # Convert content to bytes if needed
                if isinstance(content, str):
                    content_bytes = content.encode('utf-8')
                else:
                    content_bytes = content

                tar_stream = io.BytesIO()
                with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                    tar_info = tarfile.TarInfo(name=os.path.basename(target_path))
                    tar_info.size = len(content_bytes)
                    tar.addfile(tar_info, io.BytesIO(content_bytes))

                tar_stream.seek(0)
                parent_dir = os.path.dirname(target_path)

                if parent_dir:
                    # 使用双引号包裹路径，处理包含空格和特殊字符的路径
                    self.execute(f"mkdir -p \"{parent_dir}\"")

                self.container.put_archive(
                    path=parent_dir or self.work_dir,
                    data=tar_stream
                )

                responses.append(FileUploadResponse(
                    path=path
                ))
            except Exception as e:
                logger.error(f"Error uploading file {path}: {e}")
                responses.append(FileUploadResponse(
                    path=path,
                    error="invalid_path"
                ))
        return responses

    def close(self):
        """关闭后端并清理资源"""
        import threading
        if not self.container:
            return

        def _stop_and_remove():
            try:
                logger.info(f"停止容器: {self.container_name}")
                self.container.stop()
                logger.info(f"删除容器: {self.container_name}")
                self.container.remove()
            except Exception as e:
                err_msg = str(e)
                if "404" in err_msg or "No such container" in err_msg:
                    logger.info(f"容器已不存在，跳过清理: {self.container_name}")
                else:
                    logger.error(f"关闭容器失败: {e}")

        t = threading.Thread(target=_stop_and_remove, daemon=True)
        t.start()
        t.join(timeout=30)
        if t.is_alive():
            logger.warning(f"关闭容器超时，放弃等待: {self.container_name}")
        self.container = None

    def ls(self, path: str) -> 'LsResult':
        """List files (called by FilesystemMiddleware in deepagents >= 0.5.0)."""
        result = self.ls_info(path)
        return LsResult(entries=result)
