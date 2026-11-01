"""
Deepagent文件控制器模块。
处理Deepagent相关文件上传、下载等业务逻辑。
"""
import logging
import os
import tarfile
import zipfile
import posixpath
import json
import urllib.parse
from typing import Dict, Optional
from src.controllers.sandbox_controller import sandbox_controller
from src.utils.config_manager import config_manager

logger = logging.getLogger(__name__)


class DeepagentFileController:
    """
    Deepagent文件控制器类，处理文件上传、下载等业务逻辑
    """

    @staticmethod
    def upload_file_to_sandbox(
        session_thread_id: str,
        file_content: bytes,
        filename: str,
        turn_id: str
    ) -> Dict:
        """
        上传文件到沙盒的临时目录

        Args:
            session_thread_id: 会话线程 ID
            file_content: 文件内容
            filename: 文件名
            turn_id: 对话轮次 ID

        Returns:
            包含上传结果的字典
        """
        try:
            # 获取沙盒后端（会自动创建）
            target_backend = sandbox_controller.get_sandbox_backend(session_thread_id)

            # 从配置获取临时文件目录
            temp_dir = config_manager.get_temp_dir()

            # 生成临时文件路径（使用 posixpath 确保使用正斜杠，适配 Docker 容器的 Linux 环境）
            temp_file_path = posixpath.join(temp_dir, filename)

            # 确保临时目录存在（使用绝对路径）
            temp_dir_abs = f"/workspace/{temp_dir}"  # 在 Docker 容器中的绝对路径
            try:
                # 尝试创建临时目录（使用双引号包裹路径，处理特殊字符）
                logger.info(f"创建临时目录: mkdir -p \"{temp_dir_abs}\"")
                target_backend.execute(f"mkdir -p \"{temp_dir_abs}\"")
            except Exception as e:
                logger.warning(f"Failed to create temp directory: {e}")

            # 写入文件
            try:
                # 直接使用 upload_files 方法上传二进制文件
                logger.info(f"开始上传文件到: {temp_file_path}, 文件大小: {len(file_content)}")
                target_backend.upload_files([(temp_file_path, file_content)])
                logger.info(f"文件上传完成")

                # 验证文件是否真的上传成功
                verify_cmd = f"test -f '/workspace/{temp_file_path}' && echo 'File exists' || echo 'File not found'"
                verify_response = target_backend.execute(verify_cmd)
                logger.info(f"文件验证结果: {verify_response.output}")

                # 列出 temp 目录的内容
                list_cmd = f"ls -la '/workspace/{temp_dir}'"
                list_response = target_backend.execute(list_cmd)
                logger.info(f"temp 目录内容:\n{list_response.output}")
            except Exception as e:
                logger.error(f"Failed to upload file: {e}")
                raise

            logger.info(f"File uploaded successfully: {temp_file_path}")

            # 额外在宿主机/主服务的 input 目录中再存一份（供对话记录等本地逻辑读取）
            base_dir = config_manager.get_file_container_path()
            input_dir = os.path.join(base_dir, str(session_thread_id), "input")
            os.makedirs(input_dir, exist_ok=True)

            # 同名文件存在时追加序号，避免覆盖已有文件
            save_name = filename
            stem, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(os.path.join(input_dir, save_name)):
                save_name = f"{stem}({counter}){ext}"
                counter += 1

            local_path = os.path.join(input_dir, save_name)
            with open(local_path, 'wb') as f_out:
                f_out.write(file_content)
            logger.info(f"File saved to input dir: {local_path}")

            # 生成下载链接并更新上传记录 JSON 文件
            download_url = (
                f"http://<server_host>:<server_port>"
                f"/aiFileProcessor/download"
                f"?file_path={urllib.parse.quote(local_path)}"
            )

            turn_key = str(turn_id or '')
            if turn_key:
                json_path = os.path.join(base_dir, str(session_thread_id), "upload_records.json")
                upload_records = {}
                if os.path.exists(json_path):
                    with open(json_path, 'r', encoding='utf-8') as jf:
                        upload_records = json.load(jf)

                saved_file_paths = [{"name": save_name, "path": download_url}]
                if turn_key in upload_records:
                    upload_records[turn_key].extend(saved_file_paths)
                else:
                    upload_records[turn_key] = saved_file_paths

                with open(json_path, 'w', encoding='utf-8') as jf:
                    json.dump(upload_records, jf, ensure_ascii=False, indent=4)

            return {
                "filename": filename,
                "temp_path": temp_file_path,
                "local_path": local_path,
                "size": len(file_content)
            }
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise

    @staticmethod
    def delete_file_from_sandbox(
        session_thread_id: str,
        filename: str
    ) -> Dict:
        """
        从沙盒的临时目录删除文件

        Args:
            session_thread_id: 会话线程 ID
            filename: 文件名

        Returns:
            包含删除结果的字典
        """
        try:
            # 获取沙盒后端（会自动创建）
            target_backend = sandbox_controller.get_sandbox_backend(session_thread_id)

            # 从配置获取临时文件目录
            temp_dir = config_manager.get_temp_dir()

            # 构建文件路径（使用 posixpath 确保使用正斜杠，适配 Docker 容器的 Linux 环境）
            file_path = posixpath.join(temp_dir, filename)

            delete_cmd = f"rm -f '{file_path}'"
            logger.info(f"执行删除命令: {delete_cmd}")

            response = target_backend.execute(delete_cmd)
            logger.info(f"删除命令执行结果: exit_code={response.exit_code}, output={response.output}")

            logger.info(f"File deleted successfully: {file_path}")

            return {
                "filename": filename,
                "message": "File deleted successfully"
            }
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            raise

    @staticmethod
    def upload_skill_package(
        file_content: bytes,
        filename: str,
        skill_name: str
    ) -> Dict:
        """
        上传并解析 skill 压缩包

        Args:
            file_content: 压缩包内容
            filename: 压缩包文件名
            skill_name: 技能名称（作为最终目录名）

        Returns:
            包含上传结果的字典
        """
        import shutil
        import uuid

        extract_temp_dir = None
        try:
            skills_path = config_manager.get_skills_path()
            if not os.path.exists(skills_path):
                os.makedirs(skills_path, exist_ok=True)

            temp_dir = os.path.join(skills_path, "temp")
            os.makedirs(temp_dir, exist_ok=True)

            # 生成唯一标识，避免并发上传时文件名冲突
            unique_id = str(uuid.uuid4())

            # 保存压缩包到临时文件（使用唯一文件名）
            temp_file = os.path.join(temp_dir, f"{unique_id}_{filename}")
            with open(temp_file, 'wb') as f:
                f.write(file_content)
            logger.info(f"temp_file package saved to: {temp_file}")

            # 先解压到独立的临时目录，避免覆盖已有技能文件
            extract_temp_dir = os.path.join(temp_dir, unique_id)
            os.makedirs(extract_temp_dir, exist_ok=True)

            # 解压到临时目录
            if filename.endswith('.tar') or filename.endswith('.tar.gz') or filename.endswith('.tgz'):
                with tarfile.open(temp_file, 'r:*') as tar:
                    tar.extractall(extract_temp_dir)
            elif filename.endswith('.zip'):
                with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                    zip_ref.extractall(extract_temp_dir)
            else:
                raise Exception("Unsupported file format. Only tar, tar.gz, tgz, and zip files are supported.")

            # 根据解压结果判断有无顶层目录，统一整理到 skill_name 目录下
            items = os.listdir(extract_temp_dir)
            if not items:
                raise Exception("Extracted archive is empty")

            folders = [i for i in items if os.path.isdir(os.path.join(extract_temp_dir, i))]

            if len(folders) == 1 and os.path.exists(os.path.join(extract_temp_dir, folders[0], 'SKILL.md')):
                # 情况1：只有一个文件夹且 SKILL.md 在其中 → 有顶层目录
                source_dir = os.path.join(extract_temp_dir, folders[0])
            elif os.path.exists(os.path.join(extract_temp_dir, 'SKILL.md')):
                # 情况2：多个文件/文件夹且 SKILL.md 在根层级 → 没有顶层目录
                source_dir = extract_temp_dir
            else:
                raise Exception("SKILL.md not found in extracted archive")

            # 移动到技能目录，以用户指定的 skill_name 命名
            target_dir = os.path.join(skills_path, skill_name)
            if os.path.exists(target_dir):
                raise Exception(f"Skill directory already exists: {skill_name}")

            shutil.move(source_dir, target_dir)

            # 清理临时文件
            os.remove(temp_file)
            shutil.rmtree(extract_temp_dir, ignore_errors=True)
            if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                os.rmdir(temp_dir)

            logger.info(f"Skill package uploaded and extracted successfully: {skill_name}")

            return {
                "skill_name": skill_name,
                "skill_path": target_dir,
                "message": f"Skill '{skill_name}' uploaded successfully"
            }
        except Exception as e:
            logger.error(f"Error uploading skill package: {e}")
            try:
                if 'temp_file' in locals() and os.path.exists(temp_file):
                    os.remove(temp_file)
                if extract_temp_dir and os.path.exists(extract_temp_dir):
                    shutil.rmtree(extract_temp_dir, ignore_errors=True)
                if 'temp_dir' in locals() and os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
            except:
                pass
            raise

    @staticmethod
    def list_workspace_files(
        session_thread_id: str,
        server_host: str = None,
        server_port: str = None,
    ) -> Dict:
        """列出沙箱 /workspace 目录下的所有文件（取持久化目录中的文件）。

        Args:
            session_thread_id: 会话线程 ID
            server_host: 文件下载服务 host（可选，提供时生成下载链接）
            server_port: 文件下载服务 port（可选）

        Returns:
            包含文件列表的字典
        """
        import urllib.parse
        container_path = config_manager.get_file_container_path()
        output_dir = os.path.join(container_path, str(session_thread_id), 'output')
        if not os.path.isdir(output_dir):
            return {
                "session_thread_id": session_thread_id,
                "files": [],
                "message": "输出目录不存在"
            }
        filenames = [
            f for f in os.listdir(output_dir)
            if os.path.isfile(os.path.join(output_dir, f))
        ]
        if not filenames:
            return {
                "session_thread_id": session_thread_id,
                "files": [],
                "message": "未生成文件"
            }

        files = []
        for fname in filenames:
            file_path = f"{container_path}/{session_thread_id}/output/{fname}"
            file_info = {
                "filename": fname,
                "download_url": (
                        f"http://{server_host}:{server_port}"
                        f"/aiFileProcessor/download"
                        f"?file_path={urllib.parse.quote(file_path)}"
                    )
            }
            files.append(file_info)

        files.sort(key=lambda f: f.get("filename", ""))
        logger.info(f"列出工作区文件: thread_id={session_thread_id}, count={len(files)}")

        return {
            "session_thread_id": session_thread_id,
            "files": files,
        }


# 全局Deepagent文件控制器实例
deepagent_file_controller = DeepagentFileController()
