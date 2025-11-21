import os
import json
import urllib3
import hashlib
import certifi

# 用于阿里云OSS
import oss2
from oss2 import SizedFileAdapter, determine_part_size
from oss2.models import PartInfo

# 用于AWS S3
import boto3
from boto3.s3.transfer import TransferConfig

# 工具函数用于解码凭证
from utils import decode_oss_credentials as decode_credentials

class StsTokenError(Exception):
    """初始化STS Token错误异常"""
    def __init__(self, status):
        super(StsTokenError, self).__init__(status)
        self.status = status

class OssClientError(Exception):
    """OSS客户端错误异常"""
    def __init__(self, status):
        super(OssClientError, self).__init__(status)
        self.status = status

class AliOssClient:
    """阿里云OSS客户端"""
    def __init__(self, bucket="coros-oss", service="aliyun", app_id="1660188068672619112", sign="9AD4AA35AAFEE6BB1E847A76848D58DF", v=2):
        self.bucket = bucket
        self.service = service
        self.app_id = app_id
        self.sign = sign
        self.security_token = None
        self.access_key_id = None
        self.access_key_secret = None
        self.req = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        self.client = None
        self.v = v
        self.init_client()

    def init_client(self):
        """初始化OSS客户端，获取STS Token"""
        sts_token_url = f"https://faq.coros.com/openapi/oss/sts?bucket={self.bucket}&service={self.service}&app_id={self.app_id}&sign={self.sign}&v={self.v}"

        response = self.req.request('GET', sts_token_url)
        sts_token_response = json.loads(response.data)
        
        if sts_token_response["code"] != 200:
            raise StsTokenError("获取阿里云OSS STS Token异常")
            
        credentials = sts_token_response["data"]["credentials"]
        credients_json = decode_credentials(credentials)

        self.security_token = credients_json["SecurityToken"]
        self.access_key_id = credients_json["AccessKeyId"]
        self.access_key_secret = credients_json["AccessKeySecret"]

        auth = oss2.StsAuth(self.access_key_id, self.access_key_secret, self.security_token)
        self.client = oss2.Bucket(auth, "https://oss-cn-beijing.aliyuncs.com", self.bucket)
    
    def multipart_upload(self, file_path, file_name):
        """分片上传文件到阿里云OSS"""
        key = f"fit_zip/{file_name}"
        print(f"开始上传文件到阿里云OSS: {file_name}")
        
        # 初始化分片上传
        init_multipart_upload_result = self.client.init_multipart_upload(key)
        if init_multipart_upload_result.status != 200:
            raise OssClientError("初始化阿里云分片上传异常")
            
        upload_id = init_multipart_upload_result.upload_id
        total_size = os.path.getsize(file_path)
        # 确定分片大小
        part_size = determine_part_size(total_size, preferred_size=1024 * 1024)  # 1MB分片
        parts = []

        # 逐个上传分片
        with open(file_path, 'rb') as fileobj:
            part_number = 1
            offset = 0
            while offset < total_size:
                num_to_upload = min(part_size, total_size - offset)
                # 调用SizedFileAdapter生成新的文件对象，重新计算起始追加位置
                result = self.client.upload_part(key, upload_id, part_number,
                                              SizedFileAdapter(fileobj, num_to_upload))
                parts.append(PartInfo(part_number, result.etag))
                
                offset += num_to_upload
                part_number += 1

        # 完成分片上传
        headers = dict()
        # 如需设置文件访问权限ACL等额外参数，可以在这里添加
        self.client.complete_multipart_upload(key, upload_id, parts, headers=headers)
        print(f"文件上传完成，key: {key}")
        return key

class AwsOssClient:
    """AWS S3客户端"""
    def __init__(self, bucket="eu-coros", service="aws", app_id="1660188068672619112", sign="877571111A1EE5316E4B590103D4B5B3", v=2):
        self.bucket = bucket
        self.service = service
        self.app_id = app_id
        self.sign = sign
        self.credentials = None
        self.access_key_id = None
        self.access_key_secret = None
        self.req = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        self.v = v
        self.client = None
        self.init_client()
    
    def init_client(self):
        """初始化S3客户端，获取STS Token"""
        sts_token_url = f"https://faq.coros.com/openapi/oss/sts?bucket={self.bucket}&service={self.service}&app_id={self.app_id}&sign={self.sign}&v={self.v}"

        response = self.req.request('GET', sts_token_url)
        sts_token_response = json.loads(response.data)
        
        if sts_token_response["code"] != 200:
            raise StsTokenError("获取AWS OSS STS Token异常")

        credentials = sts_token_response["data"]["credentials"]
        self.credentials = credentials
        self.v = sts_token_response["data"]["v"]
        
        credients_json = decode_credentials(credentials)
        
        self.client = boto3.client(
            "s3",
            aws_access_key_id=credients_json["AccessKeyId"],
            aws_secret_access_key=credients_json["SecretAccessKey"],
            aws_session_token=credients_json["SessionToken"],
            endpoint_url='https://s3.eu-central-1.amazonaws.com',
        )

    def multipart_upload(self, file_path, file_name):
        """分片上传文件到AWS S3"""
        key = f"fit_zip/{file_name}"
        print(f"开始上传文件到AWS S3: {file_name}")
        
        # 配置上传选项
        config = TransferConfig(
            multipart_threshold=1024 * 1024 * 5,  # 分片上传的阈值（5MB）
            max_concurrency=4,                   # 并发数
            multipart_chunksize=1024 * 1024 * 5,  # 分片大小（5MB）
            use_threads=True                     # 使用多线程
        )

        # 执行上传
        self.client.upload_file(
            file_path,
            Bucket=self.bucket,
            Key=key,
            Config=config
        )
        print(f"文件上传完成，key: {key}")
        return key

def get_oss_client(bucket, service, region_id=2, access_token=None):
    """根据服务类型获取对应的OSS客户端
    
    Args:
        bucket: OSS存储桶名称
        service: 服务类型 ('aliyun' 或 'aws')
        region_id: 区域ID (1: 国际区, 2: 中国区, 3: 欧洲区)
        access_token: 访问令牌（预留参数）
        
    Returns:
        OSS客户端实例
    """
    if service == 'aliyun' or region_id == 2:
        return AliOssClient(bucket=bucket)
    else:
        return AwsOssClient(bucket=bucket)

def calculate_md5_file(file_path):
    """计算文件的MD5值
    
    Args:
        file_path: 文件路径
        
    Returns:
        计算得到的MD5字符串
    """
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()