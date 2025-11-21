import time
import json
import logging
import base64
import binascii
import re
import os
import zipfile
import io
import sys
from datetime import datetime, timedelta
from garminconnect import Garmin, GarminConnectAuthenticationError
import garth


# 定义本地Garmin FIT文件目录
script_dir = os.path.dirname(os.path.abspath(__file__))
GARMIN_FIT_DIR = os.path.join(script_dir, "downloads", "garmin")

# 设置日志级别为DEBUG
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def load_config():
    """
    加载配置文件
    """ 
    config_file = "config/garmin_config.json"
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        # 解密密码
        if "password" in config and config["password"]:
            config["password"] = base64.b64decode(config["password"]).decode("utf-8")
        return config
    return {}


def save_config(config):
    """
    保存配置文件
    """
    config_file = "config/garmin_config.json"
    # 加密密码
    if "password" in config and config["password"]:
        config["password"] = base64.b64encode(config["password"].encode("utf-8")).decode("utf-8")
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def login_garmin():
    """
    使用garminconnect库登录Garmin Connect
    """
    try:
        # 获取用户配置
        config = load_config()
        email = config.get('email')
        password = config.get('password')
        
        # 处理密码
        password_str = None
        if password:
            try:
                # 处理base64填充问题
                password_padded = password + '=' * ((4 - len(password) % 4) % 4)
                password_str = base64.b64decode(password_padded).decode('utf-8')
            except (binascii.Error, UnicodeDecodeError):
                # 如果解密失败，可能是旧版配置文件保存的是明文密码
                print("检测到旧版配置文件，正在更新密码存储格式...")
                password_str = password
        
        if not email or not password_str:
            # 提示用户输入邮箱和密码
            email = input("请输入Garmin Connect邮箱: ")
            password_str = input("请输入Garmin Connect密码: ")
            
            # 保存到配置文件
            config['email'] = email
            config['password'] = base64.b64encode(password_str.encode('utf-8')).decode('utf-8')  # 简单加密
            save_config(config)
        
        # 创建Garmin实例并配置MFA提示
        client = Garmin(
            email=email,
            password=password_str,
            is_cn=True,
            prompt_mfa=lambda: input("请输入Garmin Connect验证码（已发送到您的邮箱）: ")
        )
        
        try:
            # 尝试登录（使用tokenstore目录保存认证令牌）
            tokenstore = "tokens/garmin"
            # 创建tokenstore目录如果不存在
            if not os.path.exists(tokenstore):
                os.makedirs(tokenstore)
            # 检查token文件是否存在
            has_token_files = os.path.exists(os.path.join(tokenstore, "oauth1_token.json")) and os.path.exists(os.path.join(tokenstore, "oauth2_token.json"))
            if has_token_files:
                # 尝试从tokenstore加载令牌登录
                client.login(tokenstore)
                print("登录成功！")
                return client
            else:
                # 首次登录：使用凭证登录并保存令牌
                client.login()  # 不传入tokenstore参数，使用凭证登录
                # 保存令牌到tokenstore
                client.garth.dump(tokenstore)
                print("登录成功！令牌已保存到tokenstore。")
                return client
        except GarminConnectAuthenticationError:
            print("登录失败，用户名或密码错误")
            return None
        except Exception as e:
            print(f"登录过程中出现错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
            
    except Exception as e:
        print(f"登录过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return None

def download_all_fit_files(client, download_folder):
    """
    下载所有fit文件
    """
    try:
        # 创建下载目录
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)
            print(f"创建目录: {download_folder}")
        
        # 获取所有活动
        print("开始获取所有活动...")
        activities = []
        start = 0
        limit = 100
        
        while True:
            print(f"正在获取第 {start} 到 {start + limit} 条活动...")
            batch = client.get_activities(start, limit)
            
            if not batch:
                break
            
            activities.extend(batch)
            start += limit
            
            if len(batch) < limit:
                break
        
        if not activities:
            print("未找到任何活动")
            return True
        
        # 下载每个活动的原始FIT文件（zip包）并解压
        print("开始下载FIT文件...")
        import zipfile
        import io
        
        # 先检查现有文件，建立活动ID到文件路径的映射
        existing_files = os.listdir(download_folder)
        activity_id_to_files = {}  # 活动ID到文件路径的映射
        
        for filename in existing_files:
            if not filename.endswith('.fit'):
                continue
            
            # 尝试从文件名中提取活动ID
            activity_id = None
            
            # 从文件名末尾提取活动ID（支持新旧格式）
            id_match = re.search(r'(\d+)\.fit$', filename)
            if id_match:
                activity_id = int(id_match.group(1))
            
            if activity_id is not None:
                if activity_id not in activity_id_to_files:
                    activity_id_to_files[activity_id] = []
                activity_id_to_files[activity_id].append(filename)
        
        # 保留原始文件，不进行重命名处理
        print(f"已检查现有文件 ({len(existing_files)} 个)...")
        
        # 下载新的活动文件
        print("开始下载新的活动文件...")
        for index, activity in enumerate(activities, 1):
            try:
                activity_id = activity['activityId']
                
                # 检查活动是否已存在
                if activity_id in activity_id_to_files:
                    print(f"({index}/{len(activities)}) 活动已存在，跳过下载: {activity_id}")
                    continue
                
                # 解析活动时间
                start_time_str = activity.get('startTimeLocal') or activity.get('startTimeGMT', '')
                if not start_time_str:
                    print(f"({index}/{len(activities)}) 缺少时间信息，跳过: activity_{activity_id}")
                    continue
                
                # 处理时间格式
                start_time_str = start_time_str.replace('Z', '').split('.')[0]  # 移除毫秒和时区后缀
                try:
                    start_time = datetime.fromisoformat(start_time_str)
                except ValueError:
                    print(f"({index}/{len(activities)}) 时间格式错误，跳过: activity_{activity_id}")
                    continue
                
                date_part = start_time.strftime("%Y%m%d")
                time_part = start_time.strftime("%H%M%S")
                
                # 获取活动类型
                activity_type = "unknown"
                if 'activityType' in activity:
                    if isinstance(activity['activityType'], dict):
                        activity_type = activity['activityType'].get('typeKey', 'unknown')
                    elif isinstance(activity['activityType'], str):
                        activity_type = activity['activityType']
                
                # 获取活动名称并清理文件名
                activity_name = activity.get('activityName', 'unnamed')
                activity_name = re.sub(r'[\\/:*?"<>|]', '_', activity_name)  # 移除无效字符
                activity_name = activity_name.replace(' ', '')  # 直接删除空格
                
                # 构建新文件名
                new_filename = f"{date_part}-{time_part}-{activity_type}-{activity_name}-{activity_id}.fit"
                fit_path = os.path.join(download_folder, new_filename)
                
                # 下载活动数据
                zip_data = client.download_activity(activity_id, Garmin.ActivityDownloadFormat.ORIGINAL)
                
                # 解压并提取FIT文件
                with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zf:
                    for filename in zf.namelist():
                        if filename.endswith('.fit'):
                            fit_data = zf.read(filename)
                            with open(fit_path, 'wb') as f:
                                f.write(fit_data)
                            
                            print(f"({index}/{len(activities)}) 下载成功: {new_filename}")
                time.sleep(1)  # 减少请求间隔以提高速度
            except Exception as e:
                print(f"({index}/{len(activity_ids)}) 下载失败: activity_{activity_id} - {e}")
                time.sleep(2)  # 失败后稍作等待
        
        print("所有FIT文件下载完成！")
        return True
        
    except Exception as e:
        print(f"下载过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """
    主函数
    """
    # 配置信息
    download_folder = GARMIN_FIT_DIR
    
    # 登录
    client = login_garmin()
    if not client:
        print("登录失败，程序退出")
        return
    
    # 下载所有fit文件
    try:
        success = download_all_fit_files(client, download_folder)
        if success:
            print("所有文件下载完成！")

        else:
            print("文件下载失败")
    finally:
        # 关闭会话
        client.logout()

if __name__ == "__main__":
    main()