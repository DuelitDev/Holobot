# -*- coding: utf-8 -*-
# botlib/sys/manager/storage.py

from boto3 import client as s3
from botlib.sys.config import Config
from os import makedirs
from os.path import dirname
from os.path import exists as file_exists
from os.path import join as path_combine

_CACHE_PATH = path_combine(Config.get("BASE_PATH"), Config.get("CACHE_PATH"))
_BUCKET_NAME = Config.get("AWS_S3_NAME")


class StorageManager:
    """
    A class that manages file IO to a service using AWS S3.
    """
    _instance = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        # single-ton pattern
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # single-ton
        if self._initialized:
            return
        self._initialized = True
        self._s3 = s3("s3", aws_access_key_id=Config.get("AWS_PUBLIC_KEY"),
                      aws_secret_access_key=Config.get("AWS_PRIVATE_KEY"),
                      region_name=Config.get("AWS_REGION"))

    @staticmethod
    def format_key_to_url(key: str) -> str:
        """
        Get url for object.

        :param key: object key
        :return: url
        """
        return "https://s3-{}.amazonaws.com/{}/{}".format(
            Config.get("AWS_REGION"), _BUCKET_NAME, key)

    @staticmethod
    def _is_cached(key: str) -> bool:
        """
        Check if the object is stored in storage.

        :param key: object key
        :return: bool
        """
        if file_exists(path_combine(_CACHE_PATH, key)):
            return True
        return False

    def _caching(self, key: str, data: bytes, force: bool = False):
        """
        Cache object to EBS storage.

        :param key: object key
        :param data: object body
        :param force: If True, cache again even if already cached
        """
        if self._is_cached(key) and not force:
            return
        path = path_combine(_CACHE_PATH, key)
        makedirs(dirname(path), exist_ok=True)
        with open(path, "wb") as file:
            file.write(data)

    def _get_cache(self, key: str) -> bytes:
        """
        Get cached object from EBS storage.

        :param key: object key
        :return: object body
        """
        if not self._is_cached(key):
            raise RuntimeError(f"{key} was not cached.")
        with open(path_combine(_CACHE_PATH, key), "rb") as file:
            return file.read()

    def get(self, key: str, cache: bool = False) -> bytes:
        """
        Get object from S3 Bucket.

        :param key: object key
        :param cache: If True, cache objects to EBS storage
        :return: object body
        """
        if self._is_cached(key):
            return self._get_cache(key)
        resp = self._s3.get_object(Bucket=_BUCKET_NAME, Key=key)
        data = resp["Body"].read()
        if cache:
            self._caching(key, data)
        return data

    def get_to_file(self, key: str) -> str:
        """
        Get object file path.

        :param key: object key
        :return: file path
        """
        if not self._is_cached(key):
            resp = self._s3.get_object(Bucket=_BUCKET_NAME, Key=key)
            data = resp["Body"].read()
            self._caching(key, data)
        return path_combine(_CACHE_PATH, key)

    def put(self, key: str, data: str | bytes):
        """
        Put object to S3 Bucket.

        :param key: object key
        :param data: object body
        """
        if isinstance(data, str):
            data = data.encode("utf-8")
        self._s3.put_object(Bucket=_BUCKET_NAME, Key=key, Body=data)

    def put_from_file(self, key: str, path: str):
        """
        Put object from file path

        :param key: object key
        :param path: file path
        """
        with open(path, "rb") as file:
            self.put(key, file.read())

    def exists(self, key: str) -> bool:
        """
        Checks whether an object exists.

        :param key: object key
        :return: bool
        """
        try:
            self._s3.get_object(Bucket=_BUCKET_NAME, Key=key)
            return True
        except Exception as e:
            if hasattr(e, "response"):
                if e.response["ResponseMetadata"]["HTTPStatusCode"] == 404:
                    return False
            raise e
