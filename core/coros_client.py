#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coros API 客户端

提供 Coros 平台的登录、活动管理和上传功能：
- login_coros: 交互式登录（保存 token）
- CorosClient: 核心客户端（登录 / token 持久化 / 上传 / 活动列表 / 下载）
- 异常类型：CorosLoginError / CorosActivityUploadError
"""

import urllib3
import json
import hashlib
import certifi
import os
import time
import logging

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import get_coros_config
from core.config import REGION_CONFIG, STS_CONFIG

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


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


def login_coros():
    """登录Coros账户并返回CorosClient实例"""
    max_attempts = 3
    attempt = 0
    
    while attempt < max_attempts:
        try:
            config_manager = get_coros_config()
            config = config_manager.load()
            email = config.get('email')
            password = config.get('password')

            if not email or not password or not password.strip():
                print("Coros配置不完整，需要补充信息...")
                if not email:
                    email = input("请输入Coros邮箱: ")
                else:
                    print(f"使用已保存的邮箱: {email}")
                
                password = input("请输入Coros密码: ")
                
                config_manager.update({'email': email, 'password': password})
                config_manager.save()
                print("配置已保存")
            
            client = CorosClient(email, password)
            
            try:
                client.login()
                return client
            except CorosLoginError as e:
                error_msg = str(e)
                if "Password error times exceeds limitation" in error_msg:
                    print("\n错误: 密码错误次数过多，账号已被临时锁定！")
                    print("建议等待30分钟后再尝试登录。")
                    config_manager.clear_password()
                    print("已清除配置文件中的密码信息。")
                    return None
                else:
                    attempt += 1
                    remaining_attempts = max_attempts - attempt
                    print(f"登录失败: {error_msg}")
                    print(f"剩余尝试次数: {remaining_attempts}")
                    
                    config_manager.clear_password()
                    
                    if remaining_attempts > 0:
                        print("\n请重新输入密码：")
                        password = input("请输入Coros密码: ")
                        config_manager.update({'email': email, 'password': password})
                        config_manager.save()
                    else:
                        print("已达到最大尝试次数，请稍后再试。")
                        return None
            
        except Exception as e:
            print(f"登录过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
            config_manager = get_coros_config()
            config_manager.clear_password()
            attempt += 1
            if attempt < max_attempts:
                print(f"\n尝试重新登录 (剩余{max_attempts - attempt}次)...")
            else:
                print("已达到最大尝试次数，请稍后再试。")
                return None
    
    return None


class CorosClient:
    """Coros API客户端"""
    
    def __init__(self, email, password):
        """初始化Coros客户端
        
        Args:
            email: Coros账号邮箱
            password: Coros账号密码
        """
        if not email or not isinstance(email, str):
            raise ValueError("邮箱不能为空，且必须是字符串类型")
        if not password or not isinstance(password, str):
            raise ValueError("密码不能为空，且必须是字符串类型")
        
        self.email = email
        self.password = password
        
        try:
            self.req = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        except Exception as e:
            print(f"初始化HTTP客户端失败: {e}")
            self.req = urllib3.PoolManager(cert_reqs='CERT_NONE')
            print("已切换到不验证SSL证书的模式")
        
        self.access_token = None
        self.user_id = None
        self.region_id = None
        self.teamapi = None
        self.token_expire_time = None
        
        try:
            self._load_token()
        except Exception as e:
            print(f"加载token失败: {e}")
    
    def login(self):
        """登录Coros账号"""
        login_url = "https://teamcnapi.coros.com/account/login"

        login_data = {
            "account": self.email,
            "pwd": hashlib.md5(self.password.encode()).hexdigest(),
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

        self.access_token = login_response["data"]["accessToken"]
        self.user_id = login_response["data"]["userId"]
        self.region_id = login_response["data"]["regionId"]
        self.teamapi = REGION_CONFIG[self.region_id]['teamapi']
        
        self.token_expire_time = int(time.time()) + 24 * 3600
        
        self._save_token()
        
        print(f"登录成功! 用户ID: {self.user_id}, 区域ID: {self.region_id}")
        return True
    
    def _save_token(self):
        """保存token信息到文件"""
        try:
            token_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tokens', 'coros')
            if not os.path.exists(token_dir):
                os.makedirs(token_dir)
            
            email_hash = hashlib.md5(self.email.encode()).hexdigest()
            token_file = os.path.join(token_dir, f"token_{email_hash}.json")
            
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
            token_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tokens', 'coros')
            email_hash = hashlib.md5(self.email.encode()).hexdigest()
            token_file = os.path.join(token_dir, f"token_{email_hash}.json")
            
            if not os.path.exists(token_file):
                print("未找到保存的Token文件")
                return False
            
            with open(token_file, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            
            current_time = int(time.time())
            if token_data.get('expire_time', 0) < current_time:
                print("Token已过期，需要重新登录")
                os.remove(token_file)
                return False
            
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
        """上传活动到Coros"""
        self._check_token()

        upload_url = f"{self.teamapi}/activity/fit/import"

        headers = {
            "Accept": "application/json, text/plain, */*",
            "accesstoken": self.access_token,
        }
    
        try:
            bucket = STS_CONFIG[self.region_id]["bucket"]
            service_name = STS_CONFIG[self.region_id]["service"]
            serviceName = 'oss' if service_name == 'aliyun' else 's3'
            
            data = {
                "source": 1,
                "timezone": 32,
                "bucket": bucket,
                "md5": md5,
                "size": size,
                "object": oss_object,
                "serviceName": serviceName,
                "oriFileName": file_name
            }
            
            json_parameter = json.dumps(data)
            
            fields = {
                'jsonParameter': json_parameter
            }
            
            response = self.req.request(
                method='POST',
                url=upload_url,
                fields=fields,
                headers=headers
            )
            
            upload_response = json.loads(response.data)
            
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
        """获取活动列表"""
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
        """获取所有活动"""
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
        """下载活动文件"""
        self._check_token()
        
        sport_type = sport_type or 100
        if sport_type == 65535:
            sport_type = 100
        
        get_download_url = f"{self.teamapi}/activity/detail/download?labelId={activity_id}&sportType={sport_type}&fileType=4"
        
        headers = {
            "Accept": "application/json, text/plain, */*",
            "accesstoken": self.access_token,
        }
        
        try:
            response = self.req.request(
                method='POST',
                url=get_download_url,
                headers=headers
            )
            
            response_json = json.loads(response.data)
            download_url = response_json['data']['fileUrl']
            
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
        
        if not self.access_token or (self.token_expire_time and self.token_expire_time < current_time):
            self.login()
