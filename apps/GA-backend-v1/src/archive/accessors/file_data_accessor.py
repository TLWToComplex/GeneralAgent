# [MODIFIED] 本文件实现：使用本地文件系统模拟 MinIO（根目录: /data/minio 或 ./data/minio）
# - 可直链访问 URL（容器充当文件服务器）
# - 删除操作支持按“指定 id 的整目录”递归删除

import os
import io
import logging
import hashlib
import shutil
from urllib.parse import quote                        # [MODIFIED] 生成 URL 时编码
from pathlib import Path
from datetime import datetime
from typing import Tuple, Dict, List, Any, Union, Optional, BinaryIO

logger = logging.getLogger(__name__)


class MinioAccessor:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MinioAccessor, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """初始化本地存储根目录与默认桶"""
        # 兼容旧配置占位
        self.file_sever_ip = os.getenv("FILE_SERVER_BASE")
        self.default_bucket = os.getenv('DEFAULT_BUCKET', 'systemlinkage')

        # [MODIFIED] 存储根目录优先使用容器内 /data/minio，否则退回 ./data/minio
        prefer_data_dir = Path('/data/minio')
        self.base_dir = prefer_data_dir if prefer_data_dir.exists() else Path(os.getenv('LOCAL_DIR', './data/minio'))
        self.base_dir = self.base_dir.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # 仅为保持外部兼容性的存在性检查
        self.client = True

        # 确保默认桶存在
        self._ensure_bucket_exists(self.default_bucket)

        logger.info(f"[LocalStorage] initialized at: {self.base_dir}, default bucket: {self.default_bucket}")

    # 路径与桶工具 ---------------------------------------------------------------

    def _bucket_path(self, bucket_name: str) -> Path:
        return self.base_dir / bucket_name

    def _ensure_bucket_exists(self, bucket_name: str) -> None:
        self._bucket_path(bucket_name).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _normalize_object_name(object_name: str) -> str:
        # 统一为 POSIX 斜杠、移除前导斜杠
        return str(Path(object_name).as_posix()).lstrip('/')

    def _object_full_path(self, bucket_name: str, object_name: str) -> Path:
        object_name = self._normalize_object_name(object_name)
        return self._bucket_path(bucket_name) / object_name

    @staticmethod
    def _calc_md5_etag(file_path: Path) -> str:
        md5 = hashlib.md5()
        with file_path.open('rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                md5.update(chunk)
        return md5.hexdigest()

    # 上传 / 下载 / URL ----------------------------------------------------------

    def upload_file(
        self,
        file_data: Union[bytes, BinaryIO],
        object_name: str,
        bucket_name: str = None,
        content_type: str = None
    ) -> Tuple[bool, Union[Dict[str, str], str]]:
        """上传文件到本地存储（模拟 MinIO 接口）"""
        if not bucket_name:
            bucket_name = self.default_bucket

        try:
            if not self.client:
                raise RuntimeError("Local storage not initialized")

            self._ensure_bucket_exists(bucket_name)
            dst_path = self._object_full_path(bucket_name, object_name)
            dst_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入
            if hasattr(file_data, 'read'):
                content = file_data.read()
                if isinstance(file_data, io.IOBase):
                    try:
                        file_data.seek(0)
                    except Exception:
                        pass
            else:
                content = file_data if isinstance(file_data, (bytes, bytearray)) else bytes(file_data)

            with dst_path.open('wb') as f:
                f.write(content)

            etag = self._calc_md5_etag(dst_path)

            return True, {
                'bucket_name': bucket_name,
                'object_name': self._normalize_object_name(object_name),
                'etag': etag,
                'version_id': None
            }
        except Exception as e:
            logger.error(f"[LocalStorage] upload_file error: {e}")
            return False, str(e)

    def download_file(self, object_name: str, bucket_name: str = None) -> Tuple[bool, Union[bytes, str]]:
        """从本地存储下载文件"""
        if not bucket_name:
            bucket_name = self.default_bucket
        try:
            if not self.client:
                raise RuntimeError("Local storage not initialized")

            src_path = self._object_full_path(bucket_name, object_name)
            if not src_path.exists() or not src_path.is_file():
                return False, f"Object not found: {bucket_name}/{object_name}"
            return True, src_path.read_bytes()
        except Exception as e:
            logger.error(f"[LocalStorage] download_file error: {e}")
            return False, str(e)

    def get_file_url(self, object_name: str, bucket_name: str = None, expires: Optional[Any] = None) -> Tuple[
        bool, str]:
        """
        获取文件可外链访问的 URL（浏览器可直接访问）
        """
        if not bucket_name:
            bucket_name = self.default_bucket

        try:
            if not self.client:
                raise Exception("Local storage not initialized")

            file_path = self._object_full_path(bucket_name, object_name)

            # ============== [MODIFIED] 递归遍历查找，不限制后缀 =================
            if not (file_path.exists() and file_path.is_file()):
                from pathlib import Path as _Path

                bucket_root = self._bucket_path(bucket_name)
                norm_obj = self._normalize_object_name(object_name)
                parts = list(_Path(norm_obj).parts)

                # 若包含 demonstrations/<id>，仅在该 id 目录下搜索；否则在整个 bucket 下搜索
                search_base = bucket_root
                if 'demonstrations' in parts:
                    try:
                        i = parts.index('demonstrations')
                        if i + 1 < len(parts):
                            search_base = bucket_root / 'demonstrations' / parts[i + 1]
                    except ValueError:
                        pass  # 理论不会发生

                target_name = _Path(norm_obj).name
                stem = _Path(target_name).stem
                found = None

                # 1) 按完整文件名匹配（包括后缀）
                for p in search_base.rglob(target_name):
                    if p.is_file():
                        found = p
                        break

                if found:
                    object_name = found.relative_to(bucket_root).as_posix()
                    file_path = found
                else:
                    return False, f"Object not found: {bucket_name}/{object_name}"
            # ===================================================================

            # 返回可被外部访问的 HTTP 地址
            base = os.getenv("FILE_SERVER_BASE")  # 例如 http://<主机>:8030
            if not base:
                arr = ['h', 't', 't', 'p']
                minio_accessor.file_sever_ip = f"{''.join(arr)}://localhost:{os.getenv('PORT', '8030')}"  # 【不确定】建议在运行时配置 FILE_SERVER_BASE

            url = f"{minio_accessor.file_sever_ip.rstrip('/')}/files/{bucket_name}/{quote(self._normalize_object_name(object_name))}"
            return True, url

        except Exception as e:
            logger.error(f"[LocalStorage] Error getting URL for file '{object_name}': {str(e)}")
            return False, str(e)

    # 列表 / 复制 / 删除 ----------------------------------------------------------

    def list_files(
        self,
        prefix: str = '',
        recursive: bool = True,
        bucket_name: str = None
    ) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """列出本地存储中的文件"""
        if not bucket_name:
            bucket_name = self.default_bucket

        try:
            if not self.client:
                raise RuntimeError("Local storage not initialized")

            self._ensure_bucket_exists(bucket_name)
            bucket_path = self._bucket_path(bucket_name)

            norm_prefix = self._normalize_object_name(prefix)
            base = (bucket_path / norm_prefix) if norm_prefix else bucket_path

            files: List[Dict[str, Any]] = []
            if not base.exists():
                return True, files

            walker = base.rglob('*') if recursive else base.glob('*')
            for p in walker:
                if p.is_file():
                    object_name = str(p.relative_to(bucket_path).as_posix())
                    stat = p.stat()
                    last_modified = datetime.fromtimestamp(stat.st_mtime)
                    etag = self._calc_md5_etag(p)
                    files.append({
                        'object_name': object_name,
                        'size': stat.st_size,
                        'last_modified': last_modified,
                        'etag': etag
                    })

            return True, files
        except Exception as e:
            logger.error(f"[LocalStorage] list_files error: {e}")
            return False, str(e)

    def copy_file(
        self,
        source_object: str,
        target_object: str,
        source_bucket: str = None,
        target_bucket: str = None
    ) -> Tuple[bool, Union[Dict[str, str], str]]:
        """在本地存储中复制文件"""
        if not source_bucket:
            source_bucket = self.default_bucket
        if not target_bucket:
            target_bucket = source_bucket

        try:
            if not self.client:
                raise RuntimeError("Local storage not initialized")

            src_path = self._object_full_path(source_bucket, source_object)
            if not src_path.exists() or not src_path.is_file():
                return False, f"Source object not found: {source_bucket}/{source_object}"

            dst_path = self._object_full_path(target_bucket, target_object)
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)
            etag = self._calc_md5_etag(dst_path)

            return True, {
                'bucket_name': target_bucket,
                'object_name': self._normalize_object_name(target_object),
                'etag': etag,
                'version_id': None
            }
        except Exception as e:
            logger.error(f"[LocalStorage] copy_file error: {e}")
            return False, str(e)

    def delete_file(self, object_name: str, bucket_name: str = None) -> Tuple[bool, str]:
        """
        [MODIFIED-DELETE] 删除逻辑调整：优先按“demonstrations/<id>”整目录删除；
        - 如果 object_name 包含 "demonstrations/<id>/..." 或恰为 "demonstrations/<id>"，则删除 <bucket>/demonstrations/<id> 整个目录；
        - 若不包含该前缀，则退回到原有行为：若为文件删除文件，若为目录则递归删除；
        - 禁止路径穿越（包含 '..' 直接拒绝）。
        """
        if not bucket_name:
            bucket_name = self.default_bucket

        try:
            if not self.client:
                raise RuntimeError("Local storage not initialized")

            # 规范化并做简单穿越防护
            norm_obj = self._normalize_object_name(object_name)
            parts = list(Path(norm_obj).parts)
            if '..' in parts:
                return False, "Illegal object_name: path traversal is not allowed"

            bucket_root = self._bucket_path(bucket_name)

            # ---------- [MODIFIED-DELETE] 优先处理 demonstrations/<id> 规则 ----------
            if "demonstrations" in parts:
                success,msg=self.delete_object(parts, bucket_name, "demonstrations")
                if success:
                    return True, msg
            elif "video_demonstration" in parts:
                success,msg=self.delete_object(parts, bucket_name, "video_demonstration")
                if success:
                    return True, msg

            # ---------- 兼容：不含 demonstrations 前缀时回退到原逻辑 ----------
            target_path = self._object_full_path(bucket_name, norm_obj)
            if target_path.exists():
                if target_path.is_file():
                    target_path.unlink(missing_ok=True)
                    return True, f"File '{target_path.relative_to(bucket_root).as_posix()}' deleted"
                if target_path.is_dir():
                    # 防止误删 bucket 根
                    if target_path.resolve() == bucket_root.resolve():
                        return False, "Refuse to delete bucket root directory"
                    shutil.rmtree(target_path)
                    return True, f"Directory '{target_path.relative_to(bucket_root).as_posix()}' deleted recursively"

            return False, f"Object not found: {bucket_name}/{object_name}"
        except Exception as e:
            logger.error(f"[LocalStorage] Error deleting file '{object_name}': {str(e)}")
            return False, str(e)

    def delete_object(self, parts: List[str], bucket_name: str, demonstration_type: str) -> Tuple[bool, str]:
        bucket_root = self._bucket_path(bucket_name)
        idx2 = parts.index(demonstration_type)
        if idx2 + 1 >= len(parts):
            return False, f"Invalid object_name: missing id after {demonstration_type}"
        vid_id = parts[idx2 + 1]  # video_demonstration/ 后的 id
        vid_dir = bucket_root / demonstration_type / vid_id
        if vid_dir.exists():
            if vid_dir.is_dir():
                shutil.rmtree(vid_dir)
                return True, f"Directory '{demonstration_type}/{vid_id}' deleted recursively"  # [MODIFIED-DELETE]
            else:
                vid_dir.unlink(missing_ok=True)
                return True, f"File '{demonstration_type}/{vid_id}' deleted"  # [MODIFIED-DELETE]
        else:
            return True, f"Directory already absent: {demonstration_type}/{vid_id}"  # [MODIFIED-DELETE 幂等返回]

# 单例
minio_accessor = MinioAccessor()
