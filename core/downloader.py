#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
活动下载服务

提供 Garmin 和 Coros 平台的活动下载功能。

结构：
- download_garmin_activities / _download_all_garmin_fit_files: Garmin 活动下载
- download_coros_activities / _download_all_coros_fit_files: Coros 活动下载
- _login_garmin: Garmin 登录（令牌优先，失效回退密码，可重试）
- get_activity_type: Coros sportType → 类型名映射
- _progress: 单行覆盖式进度显示
"""

import time
import json
import logging
import re
import os
import zipfile
import io
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import DIRS, SPORT_TYPE_MAPPING, CONFIG_FILES
from core.config import get_garmin_config
from core.fit_parser import extract_fit_start_time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# ══════════════════════════════════════════════════════════════
# 通用辅助
# ══════════════════════════════════════════════════════════════
def get_activity_type(sport_type):
    """将 Coros 运动类型转换为与 Garmin 一致的名称

    Args:
        sport_type: Coros 活动类型数字编码（见 SPORT_TYPE_MAPPING）

    Returns:
        str: 标准活动类型名，未映射时返回 "other"
    """
    return SPORT_TYPE_MAPPING.get(sport_type, "other")


def _progress(current, total, downloaded, skipped):
    """覆盖式单行进度显示（避免逐条刷屏）

    Args:
        current: 当前处理的序号（从 1 开始）
        total: 活动总数
        downloaded: 已成功下载数
        skipped: 已跳过（已存在）数
    """
    print(f"\r  进度 [{current}/{total}]  已下载 {downloaded}  |  已跳过 {skipped}", end="", flush=True)


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


# ══════════════════════════════════════════════════════════════
# Garmin 登录（令牌优先 → 密码兜底 → 可重试）
# ══════════════════════════════════════════════════════════════
def _login_garmin():
    """登录 Garmin Connect

    优先使用已保存的令牌登录；令牌失效或不存在时，
    回退到用户名/密码交互式登录（密码错误可重试）。

    Returns:
        Garmin client 或 None（登录失败/取消）
    """
    from garminconnect import Garmin, GarminConnectAuthenticationError
    import garth

    tokenstore = DIRS['garmin_tokens']
    os.makedirs(tokenstore, exist_ok=True)
    config_manager = get_garmin_config()
    config = config_manager.load()
    email = config.get('email', '')

    # ── 1. 优先尝试令牌登录 ──────────────────────────────
    has_token_files = os.path.exists(os.path.join(tokenstore, "oauth1_token.json")) and \
                      os.path.exists(os.path.join(tokenstore, "oauth2_token.json"))
    if has_token_files:
        try:
            client = Garmin(
                email=email,
                password=config.get('password', ''),
                is_cn=True,
                prompt_mfa=lambda: input("请输入Garmin Connect验证码（已发送到您的邮箱）: ")
            )
            client.login(tokenstore)
            print("登录成功！(使用已保存的令牌)")
            return client
        except GarminConnectAuthenticationError:
            print("⚠ 登录令牌已失效，需要重新输入用户名和密码登录。")
        except Exception as e:
            print(f"⚠ 令牌登录失败: {e}")

    # ── 2. 用户名/密码交互式登录（失败可重试）──────────────
    while True:
        try:
            if not email:
                email = input("请输入Garmin Connect邮箱: ").strip()
            password = input("请输入Garmin Connect密码: ").strip()
            if not email or not password:
                print("邮箱和密码不能为空，请重新输入。")
                continue

            client = Garmin(
                email=email,
                password=password,
                is_cn=True,
                prompt_mfa=lambda: input("请输入Garmin Connect验证码（已发送到您的邮箱）: ")
            )
            client.login()

            # 保存凭据与令牌，下次可直接令牌登录
            config_manager.update({'email': email, 'password': password})
            config_manager.save()
            client.garth.dump(tokenstore)
            print("登录成功！令牌已保存，下次将自动使用令牌登录。")
            return client

        except GarminConnectAuthenticationError:
            print("登录失败，用户名或密码错误，请重新输入。")
        except KeyboardInterrupt:
            print("\n已取消登录。")
            return None
        except (EOFError, StopIteration):
            print("\n输入中断，已取消登录。")
            return None
        except Exception as e:
            # 非认证错误（网络/接口变化等）不重试，避免死循环
            print(f"登录过程中出现错误: {e}")
            return None


# ══════════════════════════════════════════════════════════════
# Garmin 全量下载（分页拉取活动列表 → 逐个下载 FIT → 命名归档）
# ══════════════════════════════════════════════════════════════
def _download_all_garmin_fit_files(client, download_folder):
    """下载所有 Garmin FIT 文件

    Args:
        client: 已登录的 garminconnect 客户端
        download_folder: 下载保存目录（downloads/garmin）

    Returns:
        bool: 是否成功完成
    """
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
            if not (filename.endswith('.fit') or filename.endswith('.gpx')):
                continue
            
            id_match = re.search(r'(\d+)\.(fit|gpx)$', filename)
            if id_match:
                activity_id = int(id_match.group(1))
                if activity_id not in activity_id_to_files:
                    activity_id_to_files[activity_id] = []
                activity_id_to_files[activity_id].append(filename)
        
        print(f"已检查现有文件 ({len(existing_files)} 个)...")
        
        # 加载"无 FIT 文件"活动 ID 清单（如 GPX-only 的"其他"活动，避免每次重复下载）
        no_fit_ids = set()
        no_fit_path = CONFIG_FILES['garmin_no_fit']
        if os.path.exists(no_fit_path):
            with open(no_fit_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.isdigit():
                        no_fit_ids.add(int(line))
        if no_fit_ids:
            print(f"已加载 {len(no_fit_ids)} 个无 FIT 文件的活动 ID（将跳过）")
        
        # 统计需要下载的新活动（提前告知用户，避免看起来像卡住）
        existing_ids = set(activity_id_to_files.keys())
        new_activities = [a for a in activities
                          if a.get('activityId') not in existing_ids
                          and a.get('activityId') not in no_fit_ids]
        if not new_activities:
            print("没有新活动需要下载，全部已存在")
            return True
        print(f"发现 {len(new_activities)} 个新活动需要下载（{len(activities) - len(new_activities)} 个已存在将跳过）")
        print(f"预计耗时: 每个活动约 2-5 秒（含下载与限流间隔），总计约 {len(new_activities) * 3 // 60}-{len(new_activities) * 5 // 60} 分钟")
        
        print("开始下载活动文件...")
        skip_count = 0
        download_count = 0
        for index, activity in enumerate(activities, 1):
            try:
                activity_id = activity['activityId']
                
                if activity_id in activity_id_to_files:
                    skip_count += 1
                    _progress(index, len(activities), download_count, skip_count)
                    continue
                
                # 下载开始即更新进度（current 前进），避免看起来像卡住
                _progress(index, len(activities), download_count, skip_count)
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
                
                # 从 zip 中提取 FIT（优先）与 GPX（备用）
                fit_data = None
                gpx_data = None
                with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zf:
                    for zip_filename in zf.namelist():
                        if zip_filename.endswith('.fit') and fit_data is None:
                            fit_data = zf.read(zip_filename)
                        elif zip_filename.endswith('.gpx') and gpx_data is None:
                            gpx_data = zf.read(zip_filename)
                
                # 确定开始时间：FIT 内部提取优先，回退 API 元数据
                start_time = None
                if fit_data:
                    start_time = extract_fit_start_time(fit_data)
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
                elif fit_data:
                    # 有 FIT：按统一命名保存 .fit
                    date_part = start_time.strftime("%Y%m%d")
                    time_part = start_time.strftime("%H%M%S")
                    new_filename = f"{date_part}-{time_part}-{activity_type}-{activity_name}-{activity_id}.fit"
                    fit_path = os.path.join(download_folder, new_filename)
                    with open(fit_path, 'wb') as f:
                        f.write(fit_data)
                    download_count += 1
                    _progress(index, len(activities), download_count, skip_count)
                elif gpx_data:
                    # 无 FIT 只有 GPX（如"其他"活动）：保存 .gpx 归档
                    date_part = start_time.strftime("%Y%m%d")
                    time_part = start_time.strftime("%H%M%S")
                    new_filename = f"{date_part}-{time_part}-{activity_type}-{activity_name}-{activity_id}.gpx"
                    gpx_path = os.path.join(download_folder, new_filename)
                    with open(gpx_path, 'wb') as f:
                        f.write(gpx_data)
                    download_count += 1
                    _progress(index, len(activities), download_count, skip_count)
                    print(f"\n(保存 GPX: {new_filename})")
                else:
                    # zip 内既无 FIT 也无 GPX（异常）：记录 ID 到清单，避免下次重复下载
                    no_fit_ids.add(activity_id)
                    with open(no_fit_path, 'a', encoding='utf-8') as f:
                        f.write(f"{activity_id}\n")
                    print(f"\n⚠ 活动 {activity_id} zip 内无 FIT/GPX 文件，已记录跳过（共 {len(no_fit_ids)} 个）")
                time.sleep(1)
            except Exception as e:
                print(f"({index}/{len(activities)}) 下载失败: activity_{activity_id} - {e}")
                time.sleep(2)
        
        print()
        print(f"下载完成: 新下载 {download_count} 个, 跳过已有 {skip_count} 个")
        return True

    except Exception as e:
        print(f"下载过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False


# ══════════════════════════════════════════════════════════════
# Coros 活动下载
# ══════════════════════════════════════════════════════════════
def download_coros_activities():
    """下载 Coros 活动文件

    Returns:
        bool: 下载流程是否执行成功
    """
    import requests
    
    from core.coros_client import login_coros
    
    download_folder = DIRS['coros_downloads']
    os.makedirs(download_folder, exist_ok=True)
    
    print("正在登录Coros账号...")
    client = login_coros()
    if not client:
        print("\n登录失败，程序已退出。")
        return False
    
    return _download_all_coros_fit_files(client, download_folder)


# ══════════════════════════════════════════════════════════════
# Coros 全量下载（分页拉取 → 获取 OSS 下载 URL → 下载 FIT → 命名归档）
# ══════════════════════════════════════════════════════════════
def _download_all_coros_fit_files(client, download_folder):
    """下载所有 Coros FIT 文件

    Args:
        client: 已登录的 CorosClient
        download_folder: 下载保存目录（downloads/coros）

    Returns:
        bool: 是否成功完成
    """
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

        # 统计需要下载的新活动（提前告知用户）
        existing_ids = set(existing_activity_ids)
        new_activities = [a for a in activities if str(a.get('labelId')) not in existing_ids]
        if not new_activities:
            print("没有新活动需要下载，全部已存在")
            return True
        print(f"发现 {len(new_activities)} 个新活动需要下载（{len(activities) - len(new_activities)} 个已存在将跳过）")
        print(f"预计耗时: 每个活动约 2-5 秒（含下载与限流间隔），总计约 {len(new_activities) * 3 // 60}-{len(new_activities) * 5 // 60} 分钟")

        print("开始下载活动文件...")
        skip_count = 0
        download_count = 0
        for index, activity in enumerate(activities, 1):
            activity_id = activity.get('labelId')
            if not activity_id:
                print(f"({index}/{len(activities)}) 缺少活动ID，跳过")
                continue

            if str(activity_id) in existing_activity_ids:
                skip_count += 1
                _progress(index, len(activities), download_count, skip_count)
                continue

            # 下载开始即更新进度（current 前进），避免看起来像卡住
            _progress(index, len(activities), download_count, skip_count)
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
                start_time = extract_fit_start_time(fit_data) if fit_data else None
                
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

                download_count += 1
                _progress(index, len(activities), download_count, skip_count)

                time.sleep(1)
            except Exception as e:
                print(f"({index}/{len(activities)}) 下载失败: activity_{activity_id} - {e}")
                time.sleep(2)
        
        print()
        print(f"下载完成: 新下载 {download_count} 个, 跳过已有 {skip_count} 个")
        return True

    except Exception as e:
        print(f"下载过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False
