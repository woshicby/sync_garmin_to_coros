#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
活动下载服务

提供 Garmin 和 Coros 平台的活动下载功能。
"""

import time
import json
import logging
import re
import os
import zipfile
import io
from datetime import datetime, timedelta

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DIRS, SPORT_TYPE_MAPPING, CONFIG_FILES
from config_manager import get_garmin_config
from garmin_fit_sdk import Decoder, Stream

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

FIT_EPOCH = datetime(1989, 12, 31, 0, 0, 0)
# 默认时区偏移：UTC+8（中国时区），当 FIT 文件中无时区信息时使用
DEFAULT_TZ_OFFSET_SECONDS = 8 * 3600


def _get_tz_offset(msgs):
    """从 FIT 消息中获取时区偏移（秒）

    优先从 activity_mesgs 中的 local_timestamp 与 timestamp 差值获取。
    如果文件中没有时区信息，返回默认 UTC+8。

    Returns:
        int: 时区偏移秒数
    """
    if 'activity_mesgs' in msgs:
        for act in msgs['activity_mesgs']:
            ts = act.get('timestamp')
            local_ts = act.get('local_timestamp')
            if ts is not None and local_ts is not None:
                return local_ts - ts
    return DEFAULT_TZ_OFFSET_SECONDS


def _extract_fit_start_time(fit_data):
    """从 FIT 文件二进制数据中提取活动开始时间

    时区逻辑：优先使用文件中的 local_timestamp 计算时区偏移，
    如果文件中没有则回退到 UTC+8。

    Args:
        fit_data: FIT 文件的二进制数据

    Returns:
        datetime or None: 活动的本地开始时间
    """
    if not fit_data or len(fit_data) < 14:
        return None

    try:
        stream = Stream.from_byte_array(fit_data)
        decoder = Decoder(stream)
        msgs, errors = decoder.read(
            convert_datetimes_to_dates=False,
            expand_sub_fields=True,
            expand_components=True,
            merge_heart_rates=False,
        )

        tz_offset = _get_tz_offset(msgs)

        # 从 session_mesgs 获取 start_time
        if 'session_mesgs' in msgs:
            for sess in msgs['session_mesgs']:
                start_time = sess.get('start_time')
                if start_time is not None:
                    utc_dt = FIT_EPOCH + timedelta(seconds=start_time)
                    return utc_dt + timedelta(seconds=tz_offset)

        # 回退：从 file_id_mesgs 获取 time_created
        if 'file_id_mesgs' in msgs:
            for fid in msgs['file_id_mesgs']:
                time_created = fid.get('time_created')
                if time_created is not None:
                    utc_dt = FIT_EPOCH + timedelta(seconds=time_created)
                    return utc_dt + timedelta(seconds=tz_offset)

        return None

    except Exception as e:
        print(f"从 FIT 文件提取时间失败: {e}")
        return None


def get_activity_type(sport_type):
    """将 Coros 运动类型转换为与 Garmin 一致的名称"""
    return SPORT_TYPE_MAPPING.get(sport_type, "other")


def download_garmin_activities():
    """下载 Garmin 活动文件
    
    注意：不使用client.logout()主动登出，因为garminconnect提示这个步骤已被弃用，改为直接删除令牌文件来退出，但我们需要保留令牌以便下次自动复用。
    garminconnect 库会自动处理令牌刷新和更新。
    """
    from garminconnect import Garmin, GarminConnectAuthenticationError
    import garth
    
    download_folder = DIRS['garmin_downloads']
    os.makedirs(download_folder, exist_ok=True)
    
    client = _login_garmin()
    if not client:
        print("登录失败，程序退出")
        return False
    
    return _download_all_garmin_fit_files(client, download_folder)


def _login_garmin():
    """登录 Garmin Connect"""
    try:
        from garminconnect import Garmin, GarminConnectAuthenticationError
        import garth
        
        config_manager = get_garmin_config()
        config = config_manager.load()
        email = config.get('email')
        password = config.get('password')
        
        if not email or not password:
            email = input("请输入Garmin Connect邮箱: ")
            password = input("请输入Garmin Connect密码: ")
            
            config_manager.update({'email': email, 'password': password})
            config_manager.save()
        
        client = Garmin(
            email=email,
            password=password,
            is_cn=True,
            prompt_mfa=lambda: input("请输入Garmin Connect验证码（已发送到您的邮箱）: ")
        )
        
        try:
            tokenstore = DIRS['garmin_tokens']
            os.makedirs(tokenstore, exist_ok=True)
            
            has_token_files = os.path.exists(os.path.join(tokenstore, "oauth1_token.json")) and \
                             os.path.exists(os.path.join(tokenstore, "oauth2_token.json"))
            
            if has_token_files:
                client.login(tokenstore)
                print("登录成功！")
                return client
            else:
                client.login()
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


def _download_all_garmin_fit_files(client, download_folder):
    """下载所有 Garmin FIT 文件"""
    from garminconnect import Garmin
    try:
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
        
        existing_files = os.listdir(download_folder)
        activity_id_to_files = {}
        
        for filename in existing_files:
            if not filename.endswith('.fit'):
                continue
            
            id_match = re.search(r'(\d+)\.fit$', filename)
            if id_match:
                activity_id = int(id_match.group(1))
                if activity_id not in activity_id_to_files:
                    activity_id_to_files[activity_id] = []
                activity_id_to_files[activity_id].append(filename)
        
        print(f"已检查现有文件 ({len(existing_files)} 个)...")
        
        print("开始下载活动文件...")
        skip_count = 0
        download_count = 0
        last_was_skip = False
        for index, activity in enumerate(activities, 1):
            try:
                activity_id = activity['activityId']
                
                if activity_id in activity_id_to_files:
                    skip_count += 1
                    print(f"\r({index}/{len(activities)}) 检查活动中... 已跳过 {skip_count} 个", end="", flush=True)
                    last_was_skip = True
                    continue
                
                if last_was_skip:
                    print()
                    last_was_skip = False
                
                zip_data = client.download_activity(activity_id, Garmin.ActivityDownloadFormat.ORIGINAL)
                
                activity_type = "unknown"
                if 'activityType' in activity:
                    if isinstance(activity['activityType'], dict):
                        activity_type = activity['activityType'].get('typeKey', 'unknown')
                    elif isinstance(activity['activityType'], str):
                        activity_type = activity['activityType']
                
                activity_name = activity.get('activityName', 'unnamed')
                activity_name = re.sub(r'[\\/:*?"<>|]', '_', activity_name)
                activity_name = activity_name.replace(' ', '')
                
                with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zf:
                    for zip_filename in zf.namelist():
                        if zip_filename.endswith('.fit'):
                            fit_data = zf.read(zip_filename)
                            
                            # 优先从 FIT 文件内部提取开始时间
                            start_time = _extract_fit_start_time(fit_data)
                            
                            # 回退：FIT 解析失败时使用 API 元数据
                            if start_time is None:
                                start_time_str = activity.get('startTimeLocal') or activity.get('startTimeGMT', '')
                                if start_time_str:
                                    start_time_str = start_time_str.replace('Z', '').split('.')[0]
                                    try:
                                        start_time = datetime.fromisoformat(start_time_str)
                                    except ValueError:
                                        start_time = None
                            
                            if start_time is None:
                                print(f"({index}/{len(activities)}) 无法获取时间信息，跳过: activity_{activity_id}")
                                break
                            
                            date_part = start_time.strftime("%Y%m%d")
                            time_part = start_time.strftime("%H%M%S")
                            
                            new_filename = f"{date_part}-{time_part}-{activity_type}-{activity_name}-{activity_id}.fit"
                            fit_path = os.path.join(download_folder, new_filename)
                            
                            with open(fit_path, 'wb') as f:
                                f.write(fit_data)
                            
                            download_count += 1
                            print(f"({index}/{len(activities)}) 下载成功: {new_filename}")
                time.sleep(1)
            except Exception as e:
                print(f"({index}/{len(activities)}) 下载失败: activity_{activity_id} - {e}")
                time.sleep(2)
        
        if last_was_skip:
            print()
        
        if skip_count > 0:
            print(f"共跳过 {skip_count} 个已存在的活动")
        print(f"所有活动检查完成，新下载 {download_count} 个文件")
        return True
        
    except Exception as e:
        print(f"下载过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def download_coros_activities():
    """下载 Coros 活动文件"""
    import requests
    
    from clients.coros_client import login_coros
    
    download_folder = DIRS['coros_downloads']
    os.makedirs(download_folder, exist_ok=True)
    
    print("正在登录Coros账号...")
    client = login_coros()
    if not client:
        print("\n登录失败，程序已退出。")
        return False
    
    return _download_all_coros_fit_files(client, download_folder)


def _download_all_coros_fit_files(client, download_folder):
    """下载所有 Coros FIT 文件"""
    import requests
    
    try:
        client._check_token()
        
        print("开始获取所有活动...")
        activities = []
        size = 200
        page = 1
        
        while True:
            activity_url = f"{client.teamapi}/activity/query?size={size}&pageNumber={page}"
            
            headers = {
                "Accept": "application/json, text/plain, */*",
                "accesstoken": client.access_token,
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            }
            
            response = client.req.request('GET', activity_url, headers=headers)
            result = json.loads(response.data)
            
            if result['result'] != '0000':
                print(f"获取活动列表失败: {result['message']}")
                return False
            
            page_result = result['data']
            activities.extend(page_result['dataList'])
            
            total_page = page_result['totalPage']
            if page >= total_page:
                break
            
            page += 1
            time.sleep(0.5)

        if not activities:
            print("未找到任何活动")
            return True
        
        print(f"共找到 {len(activities)} 个活动")
        
        existing_files = os.listdir(download_folder)
        existing_activity_ids = set()

        for filename in existing_files:
            if not filename.endswith('.fit'):
                continue
            
            id_match = re.search(r'(\d+)\.fit$', filename)
            if id_match:
                existing_activity_ids.add(id_match.group(1))

        print("开始下载活动文件...")
        skip_count = 0
        download_count = 0
        last_was_skip = False
        for index, activity in enumerate(activities, 1):
            activity_id = activity.get('labelId')
            if not activity_id:
                if last_was_skip:
                    print()
                    last_was_skip = False
                print(f"({index}/{len(activities)}) 缺少活动ID，跳过")
                continue

            if str(activity_id) in existing_activity_ids:
                skip_count += 1
                print(f"\r({index}/{len(activities)}) 检查活动中... 已跳过 {skip_count} 个", end="", flush=True)
                last_was_skip = True
                continue

            if last_was_skip:
                print()
                last_was_skip = False

            try:
                sport_type = activity.get('sportType') or 100
                if sport_type == 65535:
                    sport_type = 100
                
                download_url = f"{client.teamapi}/activity/detail/download?labelId={activity_id}&sportType={sport_type}&fileType=4"
                
                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "accesstoken": client.access_token,
                    "Content-Type": "application/json;charset=UTF-8",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                }
                
                response = client.req.request('POST', download_url, headers=headers)
                download_result = json.loads(response.data)
                if download_result['result'] != '0000':
                    print(f"({index}/{len(activities)}) 获取下载URL失败: activity_{activity_id} sportType={sport_type} - {download_result['message']}")
                    continue
                
                fit_url = download_result['data']['fileUrl']
                
                # 先下载 FIT 数据到内存
                fit_data = None
                try:
                    headers = {"User-Agent": "Mozilla/5.0"}
                    download_response = requests.get(fit_url, headers=headers)
                    download_response.raise_for_status()
                    fit_data = download_response.content
                except Exception:
                    headers = {"User-Agent": "Mozilla/5.0"}
                    response_alt = client.req.request('GET', fit_url, headers=headers, preload_content=True)
                    fit_data = response_alt.data
                
                # 优先从 FIT 文件内部提取开始时间
                start_time = _extract_fit_start_time(fit_data) if fit_data else None
                
                # 回退：FIT 解析失败时使用 API 元数据
                if start_time is None:
                    begin_time = activity.get('startTime')
                    if begin_time:
                        start_time = datetime.fromtimestamp(begin_time)
                
                if start_time is None:
                    print(f"({index}/{len(activities)}) 无法获取时间信息，跳过")
                    continue
                
                date_part = start_time.strftime("%Y%m%d")
                time_part = start_time.strftime("%H%M%S")
                
                activity_type = get_activity_type(sport_type)
                
                new_filename = f"{date_part}-{time_part}-{activity_type}-{activity_id}.fit"
                fit_path = os.path.join(download_folder, new_filename)
                
                with open(fit_path, "wb") as f:
                    f.write(fit_data)

                print(f"({index}/{len(activities)}) 下载成功: {new_filename}")
                download_count += 1

                time.sleep(1)
            except Exception as e:
                print(f"({index}/{len(activities)}) 下载失败: activity_{activity_id} - {e}")
                time.sleep(2)
        
        if last_was_skip:
            print()
        if skip_count > 0:
            print(f"共跳过 {skip_count} 个已存在的活动")
        print(f"所有活动检查完成，新下载 {download_count} 个文件")
        return True

    except Exception as e:
        print(f"下载过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False
