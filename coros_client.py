import urllib3
import json
import hashlib
import certifi
import os
import time
import base64
import binascii
import logging

# 设置日志级别为DEBUG
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def load_config():
    """
    加载配置文件
    """
    config_file = "config/coros_config.json"
    try:
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            # 解密密码
            if "password" in config and config["password"]:
                config["password"] = base64.b64decode(config["password"]).decode("utf-8")
            return config
    except (json.JSONDecodeError, binascii.Error, UnicodeDecodeError) as e:
        print(f"配置文件解析错误，将使用空配置: {e}")
    return {}

def save_config(config):
    """
    保存配置文件
    """
    config_file = "config/coros_config.json"
    # 加密密码
    if "password" in config and config["password"]:
        config["password"] = base64.b64encode(config["password"].encode("utf-8")).decode("utf-8")
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def login_coros():
    """
    登录Coros账户并返回CorosClient实例
    """
    max_attempts = 3  # 最大重试次数
    attempt = 0
    
    while attempt < max_attempts:
        try:
            # 获取用户配置
            config = load_config()
            email = config.get('email')
            password = config.get('password')

            # 处理密码
            password_str = None
            # 检查密码是否存在且非空
            if password and password.strip():
                try:
                    # 处理base64填充问题
                    password_padded = password + '=' * ((4 - len(password) % 4) % 4)
                    password_str = base64.b64decode(password_padded).decode('utf-8')
                except (binascii.Error, UnicodeDecodeError):
                    # 如果解密失败，可能是旧版配置文件保存的是明文密码
                    print("检测到旧版配置文件，正在更新密码存储格式...")
                    password_str = password

            # 如果邮箱不存在或密码不存在/为空，则提示用户输入
            if not email or not password_str or not password_str.strip():
                print("Coros配置不完整，需要补充信息...")
                # 保留现有邮箱（如果有）
                if not email:
                    email = input("请输入Coros邮箱: ")
                else:
                    print(f"使用已保存的邮箱: {email}")
                
                # 总是提示输入密码
                password_str = input("请输入Coros密码: ")
                
                # 保存到配置文件
                config['email'] = email
                config['password'] = base64.b64encode(password_str.encode('utf-8')).decode('utf-8')  # 简单加密
                save_config(config)
                print("配置已保存")
            
            # 创建CorosClient实例
            client = CorosClient(email, password_str)
            
            # 尝试登录
            try:
                client.login()
                return client
            except CorosLoginError as e:
                error_msg = str(e)
                # 处理密码错误次数过多的情况
                if "Password error times exceeds limitation" in error_msg:
                    print("\n错误: 密码错误次数过多，账号已被临时锁定！")
                    print("建议等待30分钟后再尝试登录。")
                    # 清除配置文件中的密码，避免再次自动尝试错误密码
                    current_config = load_config()
                    if 'password' in current_config:
                        del current_config['password']
                        save_config(current_config)
                        print("已清除配置文件中的密码信息。")
                    return None
                else:
                    # 其他登录错误
                    attempt += 1
                    remaining_attempts = max_attempts - attempt
                    print(f"登录失败: {error_msg}")
                    print(f"剩余尝试次数: {remaining_attempts}")
                    
                    # 清除配置文件中的密码
                    current_config = load_config()
                    if 'password' in current_config:
                        del current_config['password']
                        save_config(current_config)
                    
                    # 提示用户重新输入密码
                    if remaining_attempts > 0:
                        print("\n请重新输入密码：")
                        # 保留邮箱，只重新输入密码
                        password_str = input("请输入Coros密码: ")
                        # 更新配置文件
                        config['email'] = email
                        config['password'] = base64.b64encode(password_str.encode('utf-8')).decode('utf-8')
                        save_config(config)
                    else:
                        print("已达到最大尝试次数，请稍后再试。")
                        return None
            
        except Exception as e:
            print(f"登录过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
            # 清除密码以便下次重新输入
            current_config = load_config()
            if 'password' in current_config:
                del current_config['password']
                save_config(current_config)
            attempt += 1
            if attempt < max_attempts:
                print(f"\n尝试重新登录 (剩余{max_attempts - attempt}次)...")
            else:
                print("已达到最大尝试次数，请稍后再试。")
                return None
    
    return None

# 区域配置
REGIONCONFIG = {
    1: {
        "teamapi": "https://teamapi.coros.com"
    },
    2: {
        "teamapi": "https://teamcnapi.coros.com"
    },
    3: {
        "teamapi": "https://teameuapi.coros.com"
    }
}

# STS配置
STS_CONFIG = {
    1: {
        'bucket': 'coros-s3',
        'service': 'aws'
    },
    2: {
        'bucket': 'coros-oss',
        'service': 'aliyun'
    },
    3: {
        'bucket': 'eu-coros',
        'service': 'aws'
    }
}

class CorosLoginError(Exception):
    """Coros登录错误异常"""
    def __init__(self, status):
        super(CorosLoginError, self).__init__(status)
        self.status = status

class CorosActivityUploadError(Exception):
    """Coros活动上传错误异常"""
    def __init__(self, status):
        super(CorosActivityUploadError, self).__init__(status)
        self.status = status

class CorosClient:
    """Coros API客户端"""
    
    def __init__(self, email, password):
        """初始化Coros客户端
        
        Args:
            email: Coros账号邮箱
            password: Coros账号密码
        """
        # 参数验证
        if not email or not isinstance(email, str):
            raise ValueError("邮箱不能为空，且必须是字符串类型")
        if not password or not isinstance(password, str):
            raise ValueError("密码不能为空，且必须是字符串类型")
        
        self.email = email
        self.password = password
        
        # 初始化HTTP客户端
        try:
            self.req = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        except Exception as e:
            print(f"初始化HTTP客户端失败: {e}")
            # 使用不验证证书的方式作为后备方案
            self.req = urllib3.PoolManager(cert_reqs='CERT_NONE')
            print("已切换到不验证SSL证书的模式")
        
        # 初始化属性
        self.access_token = None
        self.user_id = None
        self.region_id = None
        self.teamapi = None
        self.token_expire_time = None
        
        # 尝试从文件加载已保存的token
        try:
            self._load_token()
        except Exception as e:
            print(f"加载token失败: {e}")
            # 继续执行，稍后会在需要时重新登录
    
    def login(self):
        """登录Coros账号
        
        Returns:
            bool: 登录成功返回True，失败抛出异常
            
        Raises:
            CorosLoginError: 登录失败时抛出
        """
        # 默认使用中国区登录URL
        login_url = "https://teamcnapi.coros.com/account/login"

        login_data = {
            "account": self.email,
            "pwd": hashlib.md5(self.password.encode()).hexdigest(),  # MD5加密密码
            "accountType": 2,
        }
        
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.39 Safari/537.36",
            "referer": "https://teamcnapi.coros.com/",
            "origin": "https://teamcnapi.coros.com/",
        }

        login_body = json.dumps(login_data)
        response = self.req.request('POST', login_url, body=login_body, headers=headers)

        login_response = json.loads(response.data)
        login_result = login_response["result"]
        
        if login_result != "0000":
            raise CorosLoginError(f"Coros登录异常: {login_response['message']}")

        # 登录成功，保存必要信息
        self.access_token = login_response["data"]["accessToken"]
        self.user_id = login_response["data"]["userId"]
        self.region_id = login_response["data"]["regionId"]
        self.teamapi = REGIONCONFIG[self.region_id]['teamapi']
        
        # 设置token过期时间（假设token有效期为24小时）
        self.token_expire_time = int(time.time()) + 24 * 3600
        
        # 保存token到文件
        self._save_token()
        
        print(f"登录成功! 用户ID: {self.user_id}, 区域ID: {self.region_id}")
        return True
    
    def _save_token(self):
        """保存token信息到文件"""
        try:
            # 创建token目录
            token_dir = "tokens/coros"
            if not os.path.exists(token_dir):
                os.makedirs(token_dir)
            
            # 生成唯一的token文件名（基于邮箱）
            email_hash = hashlib.md5(self.email.encode()).hexdigest()
            token_file = os.path.join(token_dir, f"token_{email_hash}.json")
            
            # 保存token信息
            token_data = {
                "access_token": self.access_token,
                "user_id": self.user_id,
                "region_id": self.region_id,
                "teamapi": self.teamapi,
                "expire_time": self.token_expire_time,
                "save_time": int(time.time())
            }
            
            with open(token_file, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, ensure_ascii=False, indent=2)
            
            print(f"Token已保存到: {token_file}")
            
        except Exception as e:
            print(f"保存Token失败: {str(e)}")
    
    def _load_token(self):
        """从文件加载token信息"""
        try:
            # 生成唯一的token文件名（基于邮箱）
            email_hash = hashlib.md5(self.email.encode()).hexdigest()
            token_file = os.path.join("tokens/coros", f"token_{email_hash}.json")
            
            if not os.path.exists(token_file):
                print("未找到保存的Token文件")
                return False
            
            # 读取token信息
            with open(token_file, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            
            # 检查token是否过期
            current_time = int(time.time())
            if token_data.get('expire_time', 0) < current_time:
                print("Token已过期，需要重新登录")
                # 删除过期的token文件
                os.remove(token_file)
                return False
            
            # 加载token信息
            self.access_token = token_data['access_token']
            self.user_id = token_data['user_id']
            self.region_id = token_data['region_id']
            self.teamapi = token_data['teamapi']
            self.token_expire_time = token_data['expire_time']
            
            remaining_time = (self.token_expire_time - current_time) // 3600
            print(f"成功加载Token，剩余有效期: {remaining_time} 小时")
            return True
            
        except Exception as e:
            print(f"加载Token失败: {str(e)}")
            return False
    
    def upload_activity(self, oss_object, md5, file_name, size):
        """
        上传活动到Coros
        
        Args:
            oss_object: OSS对象路径
            md5: 文件的MD5值
            file_name: 原始文件名
            size: 文件大小
            
        Returns:
            bool: 上传成功返回True，失败返回False
        """
        # 检查并确保登录状态 - 登录失败时直接抛出异常，不再重试
        self._check_token()

        upload_url = f"{self.teamapi}/activity/fit/import"

        headers = {
            "Accept": "application/json, text/plain, */*",
            "accesstoken": self.access_token,
            # 移除Content-Type，让urllib3自动处理multipart/form-data
        }
    
        try:
            # 获取区域对应的配置
            bucket = STS_CONFIG[self.region_id]["bucket"]
            # 映射服务名称：阿里云→oss，其他→s3
            service_name = STS_CONFIG[self.region_id]["service"]
            serviceName = 'oss' if service_name == 'aliyun' else 's3'
            
            # 构建请求数据，包装在jsonParameter中
            data = {
                "source": 1,
                "timezone": 32,  # 固定时区参数
                "bucket": bucket,
                "md5": md5,
                "size": size,
                "object": oss_object,
                "serviceName": serviceName,
                "oriFileName": file_name
            }
            
            # 将数据转换为JSON字符串，作为jsonParameter的值
            json_parameter = json.dumps(data)
            
            # 构建表单数据
            fields = {
                'jsonParameter': json_parameter
            }
            
            # 发送请求 - 使用fields参数发送表单数据
            response = self.req.request(
                method='POST',
                url=upload_url,
                fields=fields,  # 使用fields发送表单数据
                headers=headers
            )
            
            # 解析响应
            upload_response = json.loads(response.data)
            
            # 检查上传结果
            if upload_response.get("result") == "0000":
                print(f"活动上传成功: {file_name}")
                return True
            else:
                error_msg = upload_response.get("message", "未知错误")
                print(f"活动上传失败: {error_msg}")
                return False
                
        except Exception as err:
            print(f"上传过程中发生错误: {str(err)}")
            return False
    
    def get_activities(self, size=200, page=1):
        """获取活动列表
        
        Args:
            size: 每页大小
            page: 页码
            
        Returns:
            dict: 活动列表数据
        """
        self._check_token()
        activitys_url = f"{self.teamapi}/activity/query?size={size}&pageNumber={page}"
        
        headers = {
            "Accept": "application/json, text/plain, */*",
            "accesstoken": self.access_token,
        }
        
        try:
            response = self.req.request(
                method='GET',
                url=activitys_url,
                headers=headers
            )
            return json.loads(response.data)
        except Exception as err:
            print(f"获取活动列表失败: {str(err)}")
            return None
    
    def get_all_activities(self):
        """获取所有活动
        
        Returns:
            list: 所有活动列表
        """
        all_activities = []
        size = 200
        page = 1
        
        while True:
            activities = self.get_activities(size, page)
            if not activities or 'data' not in activities:
                break
                
            total_page = activities['data'].get('totalPage', 0)
            if total_page >= page:
                all_activities.extend(activities['data'].get('dataList', []))
            else:
                break
                
            page += 1
            
        print(f"总共获取到 {len(all_activities)} 个活动")
        return all_activities
    
    def download_activity(self, activity_id, sport_type):
        """下载活动文件
        
        Args:
            activity_id: 活动ID
            sport_type: 运动类型
            
        Returns:
            urllib3.response.HTTPResponse: 响应对象
        """
        self._check_token()
        
        # 获取下载链接
        get_download_url = f"{self.teamapi}/activity/detail/download?labelId={activity_id}&sportType={sport_type}&fileType=4"
        
        headers = {
            "Accept": "application/json, text/plain, */*",
            "accesstoken": self.access_token,
        }
        
        try:
            # 先获取下载URL
            response = self.req.request(
                method='POST',
                url=get_download_url,
                headers=headers
            )
            
            response_json = json.loads(response.data)
            download_url = response_json['data']['fileUrl']
            
            # 下载文件
            return self.req.request(
                method='GET',
                url=download_url,
                headers=headers
            )
            
        except Exception as err:
            print(f"下载活动失败: {str(err)}")
            return None
    
    def _check_token(self):
        """检查并确保Token有效"""
        current_time = int(time.time())
        
        # 如果没有token或者token已过期，重新登录
        # 登录失败时直接抛出异常，不再重试
        if not self.access_token or (self.token_expire_time and self.token_expire_time < current_time):
            # 直接调用login，登录失败时会抛出CorosLoginError异常
            self.login()

# 登录功能已经在文件前面的login_coros函数中实现