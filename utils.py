import base64
import json
import urllib3
import certifi
import os
import hashlib
import struct

# 从配置文件加载配置
def load_config(config_file):
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# 解码Coros OSS凭证
def decode_credentials(encoded_str):
    """解码Coros返回的OSS凭证字符串
    
    Args:
        encoded_str: 编码后的凭证字符串
        
    Returns:
        dict: 解码后的凭证字典
    """
    try:
        # 移除可能的前缀
        if encoded_str.startswith('oss,'):
            encoded_str = encoded_str[4:]
        
        # Base64解码
        decoded_bytes = base64.b64decode(encoded_str)
        
        # 转换为字符串并解析JSON
        decoded_str = decoded_bytes.decode('utf-8')
        return json.loads(decoded_str)
        
    except Exception as e:
        print(f"解码凭证失败: {str(e)}")
        # 如果解码失败，尝试另一种解码方式
        try:
            # 尝试直接解析（如果已经是JSON格式）
            return json.loads(encoded_str)
        except:
            # 返回空字典
            return {}

# 计算文件的MD5值
def calculate_file_md5(file_path):
    """计算文件的MD5值
    
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


def decode_oss_credentials(credient):
    salt = "9y78gpoERW4lBNYL"  # 盐值
    
    # 第一步：去除盐（salt）部分
    encode_credient = credient.replace(salt, '')
    
    # 第二步：Base64 解码
    credients = base64.b64decode(encode_credient).decode('utf-8')  # 解码后的内容转成 utf-8 字符串
    
    return json.loads(credients)


def get_oss_sts_token(bucket, service, app_id, sign, v=2, access_token=None):
    sts_token_url = f"https://faq.coros.com/openapi/oss/sts?bucket={bucket}&service={service}&app_id={app_id}&sign={sign}&v={v}"
    
    # 设置请求头，包括访问令牌
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
    
    def upload_file(self, file_path, file_name):
        raise NotImplementedError("upload_file方法必须被子类实现")


try:
    import oss2
    from oss2 import SizedFileAdapter, determine_part_size
    from oss2.models import PartInfo
    
    class AliOssClient(OssClient):
        def __init__(self, bucket="coros-oss", service="aliyun", app_id="1660188068672619112", sign="9AD4AA35AAFEE6BB1E847A76848D58DF", v=2, access_token=None):
            super().__init__(bucket, service, app_id, sign, v, access_token)
            self.init_client()
        
        def init_client(self):
            self.credentials = get_oss_sts_token(self.bucket, self.service, self.app_id, self.sign, self.v, self.access_token)
            auth = oss2.StsAuth(self.credentials["AccessKeyId"], self.credentials["AccessKeySecret"], self.credentials["SecurityToken"])
            self.client = oss2.Bucket(auth, "https://oss-cn-beijing.aliyuncs.com", self.bucket)
        
        def upload_file(self, file_path, file_name):
            key = f"fit_zip/{file_name}"
            init_multipart_upload_result = self.client.init_multipart_upload(key)
            if init_multipart_upload_result.status != 200:
                raise Exception("初始化阿里云分片上传异常")
            
            upload_id = init_multipart_upload_result.upload_id
            total_size = os.path.getsize(file_path)
            part_size = determine_part_size(total_size, preferred_size=1024 * 1024)
            parts = []
            
            with open(file_path, 'rb') as fileobj:
                part_number = 1
                offset = 0
                while offset < total_size:
                    num_to_upload = min(part_size, total_size - offset)
                    result = self.client.upload_part(key, upload_id, part_number, SizedFileAdapter(fileobj, num_to_upload))
                    parts.append(PartInfo(part_number, result.etag))
                    offset += num_to_upload
                    part_number += 1
            
            r = self.client.complete_multipart_upload(key, upload_id, parts)
            return key
except ImportError:
    # 如果没有安装oss2库，就跳过阿里云OSS客户端的实现
    pass


try:
    import boto3
    from boto3.s3.transfer import TransferConfig
    
    class AwsOssClient(OssClient):
        def __init__(self, bucket="eu-coros", service="aws", app_id="1660188068672619112", sign="877571111A1EE5316E4B590103D4B5B3", v=2, access_token=None):
            super().__init__(bucket, service, app_id, sign, v, access_token)
            self.init_client()
        
        def init_client(self):
            self.credentials = get_oss_sts_token(self.bucket, self.service, self.app_id, self.sign, self.v, self.access_token)
            self.client = boto3.client(
                "s3",
                aws_access_key_id=self.credentials["AccessKeyId"],
                aws_secret_access_key=self.credentials["SecretAccessKey"],
                aws_session_token=self.credentials["SessionToken"],
                endpoint_url='https://s3.eu-central-1.amazonaws.com',
            )
        
        def upload_file(self, file_path, file_name):
            config = TransferConfig(
                multipart_threshold=1024 * 1024 * 5,  # 分片上传的阈值（5MB）
                max_concurrency=4,                   # 并发数
                multipart_chunksize=1024 * 1024 * 5,  # 分片大小（5MB）
                use_threads=True                     # 使用多线程
            )
            
            self.client.upload_file(
                file_path,
                Bucket=self.bucket,
                Key=f"fit_zip/{file_name}",
                Config=config
            )
            return f"fit_zip/{file_name}"
except ImportError:
    # 如果没有安装boto3库，就跳过AWS OSS客户端的实现
    pass


def get_oss_client(bucket, service, app_id=None, sign=None, v=2, access_token=None):
    # 获取OSS配置和参数
    config_file_path = os.path.join(os.path.dirname(__file__), "config", "oss_config.json")
    if not os.path.exists(config_file_path):
        raise Exception("未找到OSS配置文件")

    with open(config_file_path, 'r') as f:
        oss_config = json.load(f)

    # 使用配置文件中的app_id和sign作为默认值，如果参数中提供了则覆盖
    if app_id is None:
        app_id = oss_config.get("appId", "")
    if sign is None:
        sign = oss_config.get("sign", "")

    if service == "aliyun":
        try:
            return AliOssClient(bucket, service, app_id=app_id, sign=sign, v=v, access_token=access_token)
        except NameError:
            raise Exception("未安装oss2库，无法使用阿里云OSS客户端")
    elif service == "aws":
        try:
            return AwsOssClient(bucket, service, app_id=app_id, sign=sign, v=v, access_token=access_token)
        except NameError:
            raise Exception("未安装boto3库，无法使用AWS OSS客户端")
    else:
        raise Exception(f"不支持的OSS服务类型: {service}")