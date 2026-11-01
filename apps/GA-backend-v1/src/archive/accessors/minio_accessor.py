"""
MinIO accessor module.
Provides functionality for interacting with MinIO object storage service.
"""
import os
from minio import Minio
from minio.error import S3Error
import logging
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
        """初始化MinIO客户端连接"""
        try:
            self.endpoint = os.getenv('MINIO_ENDPOINT', '')
            self.access_key = os.getenv('MINIO_ACCESS_KEY', 'aisixadmin')
            self.secret_key = os.getenv('MINIO_SECRET_KEY', 'qazwsxedc')
            self.secure = os.getenv('MINIO_SECURE', 'False').lower() == 'true'
            self.default_bucket = os.getenv('MINIO_DEFAULT_BUCKET', 'systemlinkage')

            self.client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure
            )

            # 确保默认桶存在
            self._ensure_bucket_exists(self.default_bucket)

            logger.info(f"MinIO connection initialized with endpoint: {self.endpoint}")
        except Exception as e:
            logger.error(f"Failed to initialize MinIO connection: {str(e)}")
            self.client = None

    def _ensure_bucket_exists(self, bucket_name: str) -> None:
        """确保指定的桶存在，如不存在则创建"""
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info(f"Bucket '{bucket_name}' created successfully")
        except S3Error as e:
            logger.error(f"Error checking/creating bucket '{bucket_name}': {str(e)}")
            raise

    def upload_file(self, file_data: Union[bytes, BinaryIO], object_name: str, bucket_name: str = None, content_type: str = None) -> Tuple[bool, Union[Dict[str, str], str]]:
        """
        上传文件到MinIO服务器

        Args:
            file_data: 文件数据（字节流或文件对象）
            object_name: MinIO中的对象名称
            bucket_name: 存储桶名称，默认使用配置的默认桶
            content_type: 文件的MIME类型，默认None（由MinIO自动检测）

        Returns:
            tuple: (success, result)，success是布尔值，result是成功时的对象信息或失败时的错误信息
        """
        if not bucket_name:
            bucket_name = self.default_bucket

        try:
            if not self.client:
                raise RuntimeError("MinIO client not initialized")

            # 确保桶存在
            self._ensure_bucket_exists(bucket_name)

            # 处理文件数据
            file_size = 0
            if hasattr(file_data, 'read'):  # 如果是文件对象
                file_data.seek(0, 2)  # 移动到文件末尾
                file_size = file_data.tell()  # 获取文件大小
                file_data.seek(0)  # 移回文件开头
            else:  # 如果是字节数据
                file_size = len(file_data)

            result = self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=content_type
            )

            return True, {
                'bucket_name': result.bucket_name,
                'object_name': result.object_name,
                'etag': result.etag,
                'version_id': result.version_id
            }
        except S3Error as e:
            logger.error(f"S3 error uploading file '{object_name}': {str(e)}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Error uploading file '{object_name}': {str(e)}")
            return False, str(e)

    def download_file(self, object_name: str, bucket_name: str = None) -> Tuple[bool, Union[bytes, str]]:
        """
        从MinIO服务器下载文件

        Args:
            object_name: MinIO中的对象名称
            bucket_name: 存储桶名称，默认使用配置的默认桶

        Returns:
            tuple: (success, result)，success是布尔值，result是成功时的文件数据或失败时的错误信息
        """
        if not bucket_name:
            bucket_name = self.default_bucket

        try:
            if not self.client:
                raise RuntimeError("MinIO client not initialized")

            response = self.client.get_object(
                bucket_name=bucket_name,
                object_name=object_name
            )

            data = response.read()
            response.close()
            response.release_conn()

            return True, data
        except S3Error as e:
            logger.error(f"S3 error downloading file '{object_name}': {str(e)}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Error downloading file '{object_name}': {str(e)}")
            return False, str(e)

    def get_file_url(self, object_name: str, bucket_name: str = None) -> Tuple[bool, str]:
        """
        获取文件的绝对路径，如果URL中含有host.docker.internal则替换为localhost

        Args:
            object_name: MinIO中的对象名称
            bucket_name: 存储桶名称，默认使用配置的默认桶
            expires: URL的过期时间，默认1小时

        Returns:
            tuple: (success, result)，success是布尔值，result是成功时的URL或失败时的错误信息
        """
        if not bucket_name:
            bucket_name = self.default_bucket

        try:
            if not self.client:
                raise Exception("MinIO client not initialized")

            # 确保对象存在
            self.client.stat_object(bucket_name, object_name)
            # 获取 MinIO 中文件的绝对路径
            arr = ['h', 't', 't', 'p']
            file_url = f"{''.join(arr)}://{self.endpoint}/{bucket_name}/{object_name}"
            # 如果 URL 中包含 host.docker.internal, 替换为 localhost
            if "HOST_DOCKER_INTERNAL" in file_url:
                file_url = file_url.replace("HOST_DOCKER_INTERNAL", "LOCALHOST")

            return True, file_url
        except S3Error as e:
            logger.error(f"S3 error getting URL for file '{object_name}': {str(e)}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Error getting URL for file '{object_name}': {str(e)}")
            return False, str(e)

    def list_files(self, prefix: str = '', recursive: bool = True, bucket_name: str = None) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """
        列出MinIO中的文件

        Args:
            prefix: 文件前缀过滤
            recursive: 是否递归查找子目录
            bucket_name: 存储桶名称，默认使用配置的默认桶

        Returns:
            tuple: (success, result)，success是布尔值，result是成功时的文件列表或失败时的错误信息
        """
        if not bucket_name:
            bucket_name = self.default_bucket

        try:
            if not self.client:
                raise RuntimeError("MinIO client not initialized")

            # 确保桶存在
            self._ensure_bucket_exists(bucket_name)

            objects = self.client.list_objects(
                bucket_name=bucket_name,
                prefix=prefix,
                recursive=recursive
            )

            files = []
            for obj in objects:
                files.append({
                    'object_name': obj.object_name,
                    'size': obj.size,
                    'last_modified': obj.last_modified,
                    'etag': obj.etag
                })

            return True, files
        except S3Error as e:
            logger.error(f"S3 error listing files: {str(e)}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            return False, str(e)

    def delete_file(self, object_name: str, bucket_name: str = None) -> Tuple[bool, str]:
        """
        删除MinIO中的文件

        Args:
            object_name: MinIO中的对象名称
            bucket_name: 存储桶名称，默认使用配置的默认桶

        Returns:
            tuple: (success, result)，success是布尔值，result是成功时的消息或失败时的错误信息
        """
        if not bucket_name:
            bucket_name = self.default_bucket

        try:
            if not self.client:
                raise RuntimeError("MinIO client not initialized")

            self.client.remove_object(
                bucket_name=bucket_name,
                object_name=object_name
            )

            return True, f"Object '{object_name}' deleted successfully"
        except S3Error as e:
            logger.error(f"S3 error deleting file '{object_name}': {str(e)}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Error deleting file '{object_name}': {str(e)}")
            return False, str(e)

    def copy_file(self, source_object: str, target_object: str, source_bucket: str = None, target_bucket: str = None) -> Tuple[bool, Union[Dict[str, str], str]]:
        """
        在MinIO中复制文件

        Args:
            source_object: 源对象名称
            target_object: 目标对象名称
            source_bucket: 源存储桶名称，默认使用配置的默认桶
            target_bucket: 目标存储桶名称，默认使用源桶

        Returns:
            tuple: (success, result)，success是布尔值，result是成功时的消息或失败时的错误信息
        """
        if not source_bucket:
            source_bucket = self.default_bucket
        if not target_bucket:
            target_bucket = source_bucket

        try:
            if not self.client:
                raise RuntimeError("MinIO client not initialized")

            # 确保源对象存在
            self.client.stat_object(source_bucket, source_object)

            # 确保目标桶存在
            self._ensure_bucket_exists(target_bucket)

            result = self.client.copy_object(
                bucket_name=target_bucket,
                object_name=target_object,
                source=f"{source_bucket}/{source_object}"
            )

            return True, {
                'bucket_name': result.bucket_name,
                'object_name': result.object_name,
                'etag': result.etag,
                'version_id': result.version_id
            }
        except S3Error as e:
            logger.error(f"S3 error copying file '{source_object}' to '{target_object}': {str(e)}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Error copying file '{source_object}' to '{target_object}': {str(e)}")
            return False, str(e)


# 创建全局实例以便于在应用中使用
minio_accessor = MinioAccessor()
