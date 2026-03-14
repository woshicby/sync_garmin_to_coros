#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
活动同步服务

提供将 Garmin 活动同步到 Coros 的功能。
"""

import os
import re
import json
import time
import tempfile
import zipfile

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DIRS, STS_CONFIG, REPORT_FILES
from config_manager import get_coros_config
from clients.coros_client import CorosClient
from storage.oss_client import get_oss_client, calculate_md5_file


def sync_activities():
    """同步 Garmin 活动到 Coros"""
    print("开始同步佳明活动到高驰...")
    
    coros_client = _init_coros_client()
    if not coros_client:
        print("错误: Coros客户端初始化失败，无法进行上传")
        return False
    
    activities_to_upload = _load_activities_to_upload()
    
    if not activities_to_upload:
        print("没有需要上传的佳明活动")
        return True
    
    print(f"正在上传 {len(activities_to_upload)} 个佳明活动到高驰...")
    
    return _upload_activities(coros_client, activities_to_upload)


def _init_coros_client():
    """初始化 Coros 客户端"""
    try:
        config_manager = get_coros_config()
        config = config_manager.load()
        
        email = config.get("email", "")
        password = config.get("password", "")
        
        print(f"已加载Coros配置，邮箱: {email}")
        
        coros_client = CorosClient(email, password)
        print("Coros客户端已创建，将自动使用保存的token或在需要时登录")
        
        print("正在验证登录状态...")
        coros_client._check_token()
        user_id = coros_client.user_id
        region_id = coros_client.region_id
        print(f"登录状态验证成功！用户ID: {user_id}, 区域ID: {region_id}")
        
        return coros_client
    except Exception as e:
        print(f"初始化Coros客户端失败: {str(e)}")
        return None


def _load_activities_to_upload():
    """加载需要上传的活动列表"""
    garmin_only_file = REPORT_FILES['garmin_only']
    garmin_files_dir = DIRS['garmin_downloads']
    activities_to_upload = []

    if os.path.exists(garmin_only_file):
        with open(garmin_only_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        index = 0
        while index < len(lines):
            line = lines[index].strip()
            if line.startswith("文件名:"):
                filename = line.split(":", 1)[1].strip()
                if index + 2 < len(lines):
                    date_time_line = lines[index + 1].strip()
                    sport_type_line = lines[index + 2].strip()
                    date_time_str = date_time_line.split(":", 1)[1].strip()
                    activities_to_upload.append((filename, date_time_line, sport_type_line, date_time_str))
                    index += 4
                else:
                    index += 1
            else:
                index += 1
        
        activities_to_upload.sort(key=lambda x: x[3])
        activities_to_upload = [(item[0], item[1], item[2]) for item in activities_to_upload]

    return activities_to_upload


def _upload_activities(coros_client, activities_to_upload):
    """上传活动文件"""
    garmin_files_dir = DIRS['garmin_downloads']
    
    report_lines = []
    report_lines.append("同步佳明活动到高驰报告\n")
    report_lines.append(f"同步时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append(f"待上传活动数量: {len(activities_to_upload)}\n\n")
    
    upload_success_count = 0
    upload_failure_count = 0
    
    user_id = coros_client.user_id
    region_id = coros_client.region_id
    
    total_files = len(activities_to_upload)
    for i, (filename, date_time_line, sport_type_line) in enumerate(activities_to_upload):
        progress_info = f"[{i+1}/{total_files}] {filename}"
        print(f"🔄 正在处理: {progress_info}")
        
        file_path = os.path.join(garmin_files_dir, filename)
        
        if not os.path.exists(file_path):
            report_lines.append(f"文件不存在: {file_path}\n")
            upload_failure_count += 1
            print(f"❌ {progress_info} - 文件不存在")
            continue
        
        try:
            bucket = STS_CONFIG.get(region_id, STS_CONFIG[2])['bucket']
            service = STS_CONFIG.get(region_id, STS_CONFIG[2])['service']
            serviceName = 'oss' if service == 'aliyun' else 's3'
            
            temp_zip_path = tempfile.mktemp(suffix='.zip')
            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(file_path, os.path.basename(file_path))

            try:
                zip_size = os.path.getsize(temp_zip_path)
                file_md5 = calculate_md5_file(temp_zip_path)

                oss_client = get_oss_client(bucket, service, region_id, coros_client.access_token)
                
                zip_filename = f"{user_id}/{file_md5}.zip"
                
                oss_key = oss_client.multipart_upload(temp_zip_path, zip_filename)
                file_size = zip_size

                standard_oss_key = f"fit_zip/{user_id}/{file_md5}.zip"
                
                upload_result = coros_client.upload_activity(
                    oss_object=standard_oss_key,
                    md5=file_md5,
                    file_name=f"{os.path.basename(file_path)}.zip",
                    size=file_size
                )
            finally:
                if temp_zip_path and os.path.exists(temp_zip_path):
                    os.remove(temp_zip_path)
            
            if upload_result:
                activity_time = date_time_line.split(':', 1)[1].strip()
                report_lines.append(f"✅ 上传成功: {filename} - {activity_time}\n")
                upload_success_count += 1
                print(f"✅ {progress_info} - 📊 活动导入成功")
            else:
                activity_time = date_time_line.split(':', 1)[1].strip()
                report_lines.append(f"❌ 上传失败(API错误): {filename} - {activity_time}\n")
                upload_failure_count += 1
                print(f"❌ {progress_info} - ❌ API错误: 导入失败")
            
            time.sleep(1)
        except Exception as e:
            activity_time = date_time_line.split(':', 1)[1].strip()
            report_lines.append(f"❌ 上传失败(异常): {filename} - {activity_time} - {str(e)}\n")
            upload_failure_count += 1
            print(f"❌ {progress_info} - ⚠️ 异常错误: {str(e)}")
            time.sleep(2)
    
    report_lines.append(f"\n上传结果统计:\n")
    report_lines.append(f"成功上传: {upload_success_count} 个\n")
    report_lines.append(f"上传失败: {upload_failure_count} 个\n")
    report_lines.append(f"总活动数: {len(activities_to_upload)} 个\n")
    
    report_file = REPORT_FILES['sync_report']
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"同步时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"总活动数: {len(activities_to_upload)}\n")
        f.write(f"成功上传: {upload_success_count}\n")
        f.write(f"上传失败: {upload_failure_count}\n\n")
        f.writelines(report_lines)
    
    print("\n" + "="*50)
    print("📊 同步报告摘要:")
    print(f"📋 总计: {len(activities_to_upload)} 个活动")
    print(f"✅ 成功: {upload_success_count} 个活动")
    print(f"❌ 失败: {upload_failure_count} 个活动")
    print(f"📄 同步报告已保存到: {os.path.abspath(report_file)}")
    print("="*50)
    print(f"💡 同步完成!")
    
    return True
