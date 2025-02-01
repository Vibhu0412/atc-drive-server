from abc import ABC, abstractmethod
import os
from pathlib import Path
import boto3
from fastapi import UploadFile
import shutil
import aiofiles
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class BaseStorageManager(ABC):
    """Abstract base class for storage managers"""

    @abstractmethod
    async def create_folder(self, folder_name: str) -> str:
        pass

    @abstractmethod
    async def store_file(self, folder_name: str, file: UploadFile) -> str:
        pass

    @abstractmethod
    async def delete_folder(self, folder_name: str):
        pass

    @abstractmethod
    async def delete_file(self, file_path: str):
        pass


class LocalStorageManager(BaseStorageManager):
    def __init__(self):
        self.base_path = Path(os.getenv('LOCAL_STORAGE_PATH', 'storage'))
        self._ensure_base_path()

    def _ensure_base_path(self):
        """Ensure the base storage directory exists"""
        os.makedirs(self.base_path, exist_ok=True)

    def get_folder_path(self, folder_name: str) -> Path:
        """Generate physical folder path from folder name"""
        return self.base_path / folder_name

    async def create_folder(self, folder_name: str) -> str:
        """Create physical folder for the given folder name"""
        folder_path = self.get_folder_path(folder_name)
        os.makedirs(folder_path, exist_ok=True)
        return str(folder_path)

    async def store_file(self, folder_name: str, file: UploadFile) -> str:
        """Store a file in the appropriate folder"""
        folder_path = self.get_folder_path(folder_name)
        file_path = folder_path / file.filename

        async with aiofiles.open(file_path, 'wb') as out_file:
            while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                await out_file.write(content)

        return str(file_path)

    async def delete_folder(self, folder_name: str):
        """Delete a folder and all its contents"""
        folder_path = self.get_folder_path(folder_name)
        if folder_path.exists():
            shutil.rmtree(folder_path)

    async def delete_file(self, file_path: str):
        """Delete a specific file"""
        if os.path.exists(file_path):
            os.remove(file_path)


class S3StorageManager(BaseStorageManager):
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )
        self.bucket_name = os.getenv('S3_BUCKET_NAME')

    def get_folder_path(self, folder_name: str) -> str:
        """Generate S3 folder path from folder name"""
        return f"folders/{folder_name}/"

    async def create_folder(self, folder_name: str) -> str:
        """Create a folder in S3 (creates a placeholder object)"""
        folder_path = self.get_folder_path(folder_name)
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=folder_path
        )
        return folder_path

    async def store_file(self, folder_name: str, file: UploadFile) -> str:
        """Store a file in the appropriate S3 folder"""
        folder_path = self.get_folder_path(folder_name)
        file_key = f"{folder_path}{file.filename}"

        content = await file.read()

        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=file_key,
            Body=content
        )

        return file_key

    async def delete_folder(self, folder_name: str):
        """Delete a folder and all its contents from S3"""
        folder_path = self.get_folder_path(folder_name)

        paginator = self.s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=folder_path
        ):
            if 'Contents' in page:
                objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': objects_to_delete}
                )

    async def delete_file(self, file_path: str):
        """Delete a specific file from S3"""
        self.s3_client.delete_object(
            Bucket=self.bucket_name,
            Key=file_path
        )


def get_storage_manager() -> BaseStorageManager:
    """Factory function to get the appropriate storage manager based on environment"""
    env = os.getenv('ENVIRONMENT', 'DEV').upper()
    if env == 'DEV':
        return S3StorageManager()
    return LocalStorageManager()
