#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSS 存储客户端

提供阿里云 OSS 和 AWS S3 的文件上传功能：
- calculate_md5_file: 计算文件 MD5（上传完整性校验）
- decode_oss_credentials / get_oss_sts_token: 获取并解析 STS 临时凭据
- OssClient: 分片上传客户端
"""

import os
import json
import urllib3
import hashlib
import certifi
import base64

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import OSS_APP_ID, OSS_SIGN, OSS_SALT


def calculate_md5_file(file_path):
    """计算文件 MD5 值（分块读取，用于大文件上传校验）

    Args:
        file_path: 文件路径

    Returns:
        str: 计算得到的MD5字符串
    """
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def decode_oss_credentials(credential):
    """解码OSS凭证
    
    Args:
        credential: 编码后的凭证字符串
        
    Returns:
        dict: 解码后的凭证字典
    """
    encode_credential = credential.replace(OSS_SALT, '')
    credentials = base64.b64decode(encode_credential).decode('utf-8')
    return json.loads(credentials)


def get_oss_sts_token(bucket, service, app_id, sign, v=2, access_token=None):
    """获取OSS STS Token
    
    Args:
        bucket: 存储桶名称
        service: 服务类型 (aliyun/aws)
        app_id: 应用ID
        sign: 签名
        v: 版本号
        access_token: 访问令牌
        
    Returns:
        dict: STS凭证
    """
    sts_token_url = f"https://faq.coros.com/openapi/oss/sts?bucket={bucket}&service={service}&app_id={app_id}&sign={sign}&v={v}"
    
    headers = {}
    if access_token:
        headers['accesstoken'] = access_token
    
    req = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
    response = req.request('GET', sts_token_url, headers=headers)
    
    sts_token_response = json.loads(response.data)
    if sts_token_response["code"] != 200:
        raise Exception(f"获取OSS STS Token异常: {sts_token_response}")
    
    credentials = sts_token_response["data"]["credentials"]
    return decode_oss_credentials(credentials)


class OssClient:
    """OSS客户端基类"""
    
    def __init__(self, bucket, service, app_id, sign, v=2, access_token=None):
        self.bucket = bucket
        self.service = service
        self.app_id = app_id
        self.sign = sign
        self.v = v
        self.access_token = access_token
        self.client = None
        self.credentials = None
    
    def init_client(self):
        raise NotImplementedError("init_client方法必须被子类实现")
    
    def multipart_upload(self, file_path, file_name):
        raise NotImplementedError("multipart_upload方法必须被子类实现")


try:
    import oss2
    from oss2 import SizedFileAdapter, determine_part_size
    from oss2.models import PartInfo
    
    class AliOssClient(OssClient):
        """阿里云OSS客户端"""
        
        def __init__(self, bucket="coros-oss", service="aliyun", app_id=None, sign=None, v=2, access_token=None):
            app_id = app_id or OSS_APP_ID
            sign = sign or OSS_SIGN['aliyun']
            super().__init__(bucket, service, app_id, sign, v, access_token)
            self.init_client()
        
        def init_client(self):
            self.credentials = get_oss_sts_token(
                self.bucket, self.service, self.app_id, self.sign, self.v, self.access_token
            )
            auth = oss2.StsAuth(
                self.credentials["AccessKeyId"],
                self.credentials["AccessKeySecret"],
                self.credentials["SecurityToken"]
            )
            self.client = oss2.Bucket(auth, "https://oss-cn-beijing.aliyuncs.com", self.bucket)
        
        def multipart_upload(self, file_path, file_name):
            """分片上传文件"""
            key = f"fit_zip/{file_name}"
            init_result = self.client.init_multipart_upload(key)
            if init_result.status != 200:
                raise Exception("初始化阿里云分片上传异常")
            
            upload_id = init_result.upload_id
            total_size = os.path.getsize(file_path)
            part_size = determine_part_size(total_size, preferred_size=1024 * 1024)
            parts = []
            
            with open(file_path, 'rb') as fileobj:
                part_number = 1
                offset = 0
                while offset < total_size:
                    num_to_upload = min(part_size, total_size - offset)
                    result = self.client.upload_part(
                        key, upload_id, part_number, SizedFileAdapter(fileobj, num_to_upload)
                    )
                    parts.append(PartInfo(part_number, result.etag))
                    offset += num_to_upload
                    part_number += 1
            
            self.client.complete_multipart_upload(key, upload_id, parts)
            return key

except ImportError:
    pass


try:
    import boto3
    from boto3.s3.transfer import TransferConfig
    
    class AwsOssClient(OssClient):
        """AWS S3客户端"""
        
        def __init__(self, bucket="eu-coros", service="aws", app_id=None, sign=None, v=2, access_token=None):
            app_id = app_id or OSS_APP_ID
            sign = sign or OSS_SIGN['aws']
            super().__init__(bucket, service, app_id, sign, v, access_token)
            self.init_client()
        
        def init_client(self):
            self.credentials = get_oss_sts_token(
                self.bucket, self.service, self.app_id, self.sign, self.v, self.access_token
            )
            self.client = boto3.client(
                "s3",
                aws_access_key_id=self.credentials["AccessKeyId"],
                aws_secret_access_key=self.credentials["SecretAccessKey"],
                aws_session_token=self.credentials["SessionToken"],
                endpoint_url='https://s3.eu-central-1.amazonaws.com',
            )
        
        def multipart_upload(self, file_path, file_name):
            """分片上传文件"""
            config = TransferConfig(
                multipart_threshold=1024 * 1024 * 5,
                max_concurrency=4,
                multipart_chunksize=1024 * 1024 * 5,
                use_threads=True
            )
            
            self.client.upload_file(
                file_path,
                Bucket=self.bucket,
                Key=f"fit_zip/{file_name}",
                Config=config
            )
            return f"fit_zip/{file_name}"

except ImportError:
    pass


def get_oss_client(bucket, service, app_id=None, sign=None, v=2, access_token=None):
    """获取OSS客户端实例
    
    Args:
        bucket: 存储桶名称
        service: 服务类型 (aliyun/aws)
        app_id: 应用ID
        sign: 签名
        v: 版本号
        access_token: 访问令牌
        
    Returns:
        OssClient: OSS客户端实例
    """
    if service == "aliyun":
        try:
            return AliOssClient(bucket, service, app_id=app_id, sign=sign, v=v, access_token=access_token)
        except NameError:
            raise Exception("未安装oss2库，无法使用阿里云OSS客户端")
    elif service == "aws":
        try:
            return AwsOssClient(bucket, service, app_id=app_id, sign=sign, v=v, access_token=access_token)
        except NameError:
            raise Exception("未安装boto3库，无法使用AWS S3客户端")
    else:
        raise Exception(f"不支持的OSS服务类型: {service}")
