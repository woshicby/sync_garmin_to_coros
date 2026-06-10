#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
活动同步服务

提供 Garmin 和 Coros 双向活动同步功能。
"""

import os
import re
import json
import time
import tempfile
import zipfile

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DIRS, STS_CONFIG, REPORT_FILES, CONFIG_FILES, TYPE_COMMENTS, SKIP_UPLOAD_TYPES
from config_manager import get_coros_config, get_garmin_config
from clients.coros_client import CorosClient
from storage.oss_client import get_oss_client, calculate_md5_file


def _add_to_whitelist(filename, coros_filename=None, is_failed=False):
    """将指定的活动文件添加到白名单中
    
    Args:
        filename: 佳明活动文件名
        coros_filename: 高驰活动文件名（如果是时间不匹配的情况）
        is_failed: 是否是导入失败的情况
    """
    whitelist_path = CONFIG_FILES['sync_whitelist']
    
    existing_entries = set()
    if os.path.exists(whitelist_path):
        try:
            with open(whitelist_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '.fit' in line:
                            words = line.split()
                            for word in words:
                                if word.endswith('.fit'):
                                    existing_entries.add(word)
                                    break
        except Exception as e:
            print(f"读取白名单文件失败: {str(e)}")
    
    if filename in existing_entries:
        return
    
    sport_type = "other"
    match = re.match(r"^\d{8}-\d{6}-(\w+)-", filename)
    if match:
        sport_type = match.group(1)
    
    comment = TYPE_COMMENTS.get(sport_type, "## 其他类型文件") + ("（导入失败）" if is_failed else "")
    
    has_comment = False
    comment_section_start = -1
    if os.path.exists(whitelist_path):
        with open(whitelist_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if comment in line:
                    has_comment = True
                    comment_section_start = i
                    break
    
    entry_line = filename if is_failed else f"{filename} {coros_filename}"
    
    try:
        if not os.path.exists(whitelist_path):
            os.makedirs(os.path.dirname(whitelist_path), exist_ok=True)
            with open(whitelist_path, 'w', encoding='utf-8') as f:
                f.write('# 同步白名单配置文件\n')
                f.write('# 格式：佳明活动文件名 (高驰活动文件名)，每行表示一对需要跳过的活动\n')
                f.write('\n')
                f.write(comment + '\n')
                f.write(entry_line + '\n')
        else:
            if not has_comment:
                with open(whitelist_path, 'a', encoding='utf-8') as f:
                    f.write('\n' + comment + '\n')
                    f.write(entry_line + '\n')
            else:
                with open(whitelist_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                comment_end = comment_section_start
                for i in range(comment_section_start + 1, len(lines)):
                    if lines[i].strip().startswith('#') or not lines[i].strip():
                        comment_end = i
                        break
                else:
                    comment_end = len(lines)
                
                lines.insert(comment_end, entry_line + '\n')
                
                with open(whitelist_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
        
        print(f"已将 {filename} 添加到白名单")
    except Exception as e:
        print(f"添加文件到白名单失败: {str(e)}")


def sync_activities():
    """同步 Garmin 独有活动到 Coros"""
    print("开始同步佳明活动到高驰...")
    
    coros_client = _init_coros_client()
    if not coros_client:
        print("错误: Coros客户端初始化失败，无法进行上传")
        return 0
    
    activities_to_upload, garmin_only_count = _load_activities_to_upload()
    
    if not activities_to_upload:
        print("没有需要上传的佳明活动")
        return 0
    
    print(f"正在上传 {len(activities_to_upload)} 个佳明活动到高驰...")
    
    return _upload_activities(coros_client, activities_to_upload, garmin_only_count)


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


def _load_whitelist():
    """加载白名单中的佳明文件名"""
    whitelist_path = CONFIG_FILES['sync_whitelist']
    whitelist_garmin = set()
    
    if os.path.exists(whitelist_path):
        try:
            with open(whitelist_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '.fit' in line:
                            words = line.split()
                            for word in words:
                                if word.endswith('.fit'):
                                    whitelist_garmin.add(word)
                                    break
        except Exception as e:
            print(f"读取白名单文件失败: {str(e)}")
    
    return whitelist_garmin


def _load_activities_to_upload():
    """加载需要上传的活动列表"""
    garmin_only_file = REPORT_FILES['garmin_only']
    garmin_files_dir = DIRS['garmin_downloads']
    activities_to_upload = []
    garmin_only_count = 0
    
    whitelist_garmin = _load_whitelist()

    if os.path.exists(garmin_only_file):
        with open(garmin_only_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line in lines:
            if line.strip().startswith("总共有"):
                match = re.search(r'总共有 (\d+) 个', line)
                if match:
                    garmin_only_count = int(match.group(1))
                break
        
        index = 0
        while index < len(lines):
            line = lines[index].strip()
            if line.startswith("文件名:"):
                filename = line.split(":", 1)[1].strip()
                if filename in whitelist_garmin:
                    index += 4
                    continue
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

    return activities_to_upload, garmin_only_count


def _handle_multi_sport_whitelist(uploaded_files, coros_client):
    """处理上传成功的 multi_sport 文件白名单添加逻辑
    
    Args:
        uploaded_files: 上传成功的文件列表，每个元素是 (filename, date_time_line) 元组
        coros_client: Coros客户端
    """
    from datetime import datetime
    from services.downloader import download_coros_activities
    
    print("\n" + "="*50)
    print("📋 处理上传成功的多项运动文件...")
    print("正在重新下载高驰活动以匹配新上传的文件...")
    
    if not download_coros_activities():
        print("⚠️ 重新下载高驰活动失败，将所有上传的多项运动文件加入白名单")
        for filename, date_time_line in uploaded_files:
            _add_to_whitelist(filename)
        return
    
    coros_dir = DIRS['coros_downloads']
    coros_files = []
    for f in os.listdir(coros_dir):
        if f.endswith('.fit'):
            match = re.match(r'^(\d{8}-\d{6})-', f)
            if match:
                datetime_str = match.group(1)
                try:
                    dt = datetime.strptime(datetime_str, '%Y%m%d-%H%M%S')
                    coros_files.append({'filename': f, 'datetime': dt})
                except ValueError:
                    pass
    
    for filename, date_time_line in uploaded_files:
        date_time_str = date_time_line.split(':', 1)[1].strip()
        try:
            garmin_dt = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            print(f"⚠️ 无法解析时间: {date_time_str}，将 {filename} 加入白名单")
            _add_to_whitelist(filename)
            continue
        
        matched_coros = None
        min_diff = None
        for coros_file in coros_files:
            time_diff = abs((coros_file['datetime'] - garmin_dt).total_seconds())
            if time_diff <= 900:
                if min_diff is None or time_diff < min_diff:
                    min_diff = time_diff
                    matched_coros = coros_file['filename']
        
        if matched_coros:
            if min_diff == 0:
                print(f"✅ {filename} 与 {matched_coros} 时间完全匹配，无需加入白名单")
            else:
                print(f"✅ {filename} 匹配到高驰文件: {matched_coros} (时间差: {int(min_diff)}秒)")
                _add_to_whitelist(filename, coros_filename=matched_coros)
        else:
            print(f"⚠️ {filename} 未找到匹配的高驰文件，加入白名单")
            _add_to_whitelist(filename)
    
    print("="*50)


def _upload_activities(coros_client, activities_to_upload, garmin_only_count):
    """上传活动文件"""
    garmin_files_dir = DIRS['garmin_downloads']
    
    whitelist_skip_count = garmin_only_count - len(activities_to_upload)
    
    report_lines = []
    report_lines.append("同步佳明活动到高驰报告\n")
    report_lines.append(f"同步时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    upload_success_count = 0
    upload_failure_count = 0
    
    uploaded_multi_sport_files = []
    failed_files = []
    
    user_id = coros_client.user_id
    region_id = coros_client.region_id
    
    total_files = len(activities_to_upload)
    skip_count = 0
    skip_type_counts = {}
    for i, (filename, date_time_line, sport_type_line) in enumerate(activities_to_upload):
        progress_info = f"[{i+1}/{total_files}] {filename}"
        
        sport_type = sport_type_line.split(':', 1)[1].strip() if ':' in sport_type_line else ""
        if sport_type in SKIP_UPLOAD_TYPES:
            skip_count += 1
            skip_type_counts[sport_type] = skip_type_counts.get(sport_type, 0) + 1
            continue
        
        print(f"🔄 正在处理: {progress_info}")
        
        file_path = os.path.join(garmin_files_dir, filename)
        
        if not os.path.exists(file_path):
            report_lines.append(f"文件不存在: {file_path}\n")
            upload_failure_count += 1
            print(f"❌ {progress_info} - 文件不存在")
            failed_files.append((filename, sport_type))
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

                oss_client = get_oss_client(bucket, service, access_token=coros_client.access_token)
                
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
                
                if sport_type == "multi_sport":
                    uploaded_multi_sport_files.append((filename, date_time_line))
            else:
                activity_time = date_time_line.split(':', 1)[1].strip()
                report_lines.append(f"❌ 上传失败(API错误): {filename} - {activity_time}\n")
                upload_failure_count += 1
                print(f"❌ {progress_info} - ❌ API错误: 导入失败")
                failed_files.append((filename, sport_type))
            
            time.sleep(1)
        except Exception as e:
            activity_time = date_time_line.split(':', 1)[1].strip()
            report_lines.append(f"❌ 上传失败(异常): {filename} - {activity_time} - {str(e)}\n")
            upload_failure_count += 1
            print(f"❌ {progress_info} - ⚠️ 异常错误: {str(e)}")
            failed_files.append((filename, sport_type))
            time.sleep(2)
    
    for filename, sport_type in failed_files:
        _add_to_whitelist(filename, is_failed=True)
    
    if uploaded_multi_sport_files:
        _handle_multi_sport_whitelist(uploaded_multi_sport_files, coros_client)
    
    report_file = REPORT_FILES['sync_report']
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"同步时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"佳明有而高驰没有的活动: {garmin_only_count} 个\n")
        f.write(f"  - 白名单跳过: {whitelist_skip_count} 个\n")
        f.write(f"  - 类型跳过: {skip_count} 个\n")
        if skip_type_counts:
            for sport_type, count in sorted(skip_type_counts.items()):
                f.write(f"      • {sport_type}: {count} 个\n")
        f.write(f"  - 上传成功: {upload_success_count} 个\n")
        f.write(f"  - 上传失败: {upload_failure_count} 个\n\n")
        if report_lines:
            f.write("详细记录:\n")
            f.writelines(report_lines)
    
    print("\n" + "="*50)
    print("📊 同步报告摘要:")
    print(f"📋 佳明有而高驰没有的活动: {garmin_only_count} 个")
    print(f"⏭️ 白名单跳过: {whitelist_skip_count} 个")
    print(f"⏭️ 类型跳过: {skip_count} 个")
    if skip_type_counts:
        for sport_type, count in sorted(skip_type_counts.items()):
            print(f"   • {sport_type}: {count} 个")
    print(f"✅ 上传成功: {upload_success_count} 个")
    print(f"❌ 上传失败: {upload_failure_count} 个")
    print(f"📄 同步报告已保存到: {os.path.abspath(report_file)}")
    print("="*50)
    print(f"💡 同步完成!")
    
    return upload_success_count


def _load_coros_whitelist():
    """加载白名单中的高驰文件名"""
    whitelist_path = CONFIG_FILES['sync_whitelist']
    whitelist_coros = set()
    
    if os.path.exists(whitelist_path):
        try:
            with open(whitelist_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '.fit' in line:
                            words = line.split()
                            fit_files = [w for w in words if w.endswith('.fit')]
                            if len(fit_files) >= 1:
                                # 如果有第二个文件，那是高驰的文件；如果只有一个，就假设这个是需要跳过的
                                if len(fit_files) >= 2 and fit_files[1] != 'None':
                                    whitelist_coros.add(fit_files[1])
                                else:
                                    whitelist_coros.add(fit_files[0])
        except Exception as e:
            print(f"读取白名单文件失败: {str(e)}")
    
    return whitelist_coros


def _load_uploaded_files():
    """加载已上传文件记录"""
    uploaded_path = CONFIG_FILES['uploaded_files']
    uploaded = set()
    
    if os.path.exists(uploaded_path):
        try:
            with open(uploaded_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and line.endswith('.fit'):
                        uploaded.add(line)
        except Exception as e:
            print(f"读取已上传文件记录失败: {str(e)}")
    
    return uploaded


def _record_uploaded_file(filename):
    """记录一个已上传的文件"""
    uploaded_path = CONFIG_FILES['uploaded_files']
    try:
        os.makedirs(os.path.dirname(uploaded_path), exist_ok=True)
        with open(uploaded_path, 'a', encoding='utf-8') as f:
            f.write(filename + '\n')
    except Exception as e:
        print(f"记录已上传文件失败: {str(e)}")


def _check_duplicate_upload(filename, uploaded_set):
    """检查文件是否已上传过，如果是则移到白名单
    
    Returns:
        True 如果文件已上传过（已移到白名单），False 如果是新文件
    """
    if filename in uploaded_set:
        print(f"⚠️ {filename} 已在历史记录中上传过，移动到白名单")
        _add_to_whitelist(filename)
        return True
    return False


def sync_coros_to_garmin():
    """同步 Coros 独有活动到 Garmin"""
    from garminconnect import Garmin, GarminConnectAuthenticationError
    import garth
    
    print("开始同步高驰活动到佳明...")
    
    coros_only_file = REPORT_FILES['coros_only']
    coros_files_dir = DIRS['coros_downloads']
    
    if not os.path.exists(coros_only_file):
        print("没有高驰独有活动报告，跳过同步")
        return 0
    
    # 加载高驰独有活动列表
    coros_activities = []
    coros_only_count = 0
    
    with open(coros_only_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line in lines:
        if line.strip().startswith("总共有"):
            match = re.search(r'总共有 (\d+) 个', line)
            if match:
                coros_only_count = int(match.group(1))
            break
    
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if line.startswith("文件名:"):
            filename = line.split(":", 1)[1].strip()
            if index + 2 < len(lines):
                date_time_line = lines[index + 1].strip()
                sport_type_line = lines[index + 2].strip()
                date_time_str = date_time_line.split(":", 1)[1].strip()
                coros_activities.append((filename, date_time_str, sport_type_line))
                index += 4
            else:
                index += 1
        else:
            index += 1
    
    if not coros_activities:
        print("没有需要上传的高驰活动")
        return 0
    
    # 加载白名单（跳过已配对的高驰文件）
    whitelist_coros = _load_coros_whitelist()
    
    activities_to_upload = []
    whitelist_skip = 0
    for filename, date_time_str, sport_type_line in coros_activities:
        if filename in whitelist_coros:
            whitelist_skip += 1
            continue
        activities_to_upload.append((filename, date_time_str, sport_type_line))
    
    if not activities_to_upload:
        print(f"所有 {coros_only_count} 个高驰活动已在白名单中，无需上传")
        print("\n" + "="*50)
        print("📊 高驰→佳明 同步报告:")
        print(f"📋 高驰有而佳明没有的活动: {coros_only_count} 个")
        print(f"⏭️ 白名单跳过: {whitelist_skip} 个")
        print(f"✅ 上传成功: 0 个")
        print(f"❌ 上传失败: 0 个")
        print("="*50)
        return 0
    
    print(f"高驰独有活动: {coros_only_count} 个")
    print(f"白名单跳过: {whitelist_skip} 个")
    print(f"需要上传: {len(activities_to_upload)} 个")
    
    # 登录 Garmin
    print("\n正在登录 Garmin...")
    try:
        config_manager = get_garmin_config()
        config = config_manager.load()
        email = config.get('email')
        password = config.get('password')
        
        if not email or not password:
            print("Garmin 配置不完整，无法登录")
            return 0
        
        garmin_client = Garmin(
            email=email,
            password=password,
            is_cn=True,
            prompt_mfa=lambda: input("请输入Garmin Connect验证码（已发送到您的邮箱）: ")
        )
        
        tokenstore = DIRS['garmin_tokens']
        os.makedirs(tokenstore, exist_ok=True)
        
        has_token_files = os.path.exists(os.path.join(tokenstore, "oauth1_token.json")) and \
                         os.path.exists(os.path.join(tokenstore, "oauth2_token.json"))
        
        if has_token_files:
            garmin_client.login(tokenstore)
        else:
            garmin_client.login()
            garmin_client.garth.dump(tokenstore)
        
        print("Garmin 登录成功！")
    except Exception as e:
        print(f"Garmin 登录失败: {str(e)}")
        return 0
    
    # 上传活动
    print(f"\n正在上传 {len(activities_to_upload)} 个高驰活动到佳明...")
    
    report_lines = []
    report_lines.append("同步高驰活动到佳明报告\n")
    report_lines.append(f"同步时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    upload_success_count = 0
    upload_failure_count = 0
    
    total = len(activities_to_upload)
    for i, (filename, date_time_str, sport_type_line) in enumerate(activities_to_upload):
        file_path = os.path.join(coros_files_dir, filename)
        progress = f"[{i+1}/{total}] {filename}"
        
        if not os.path.exists(file_path):
            print(f"❌ {progress} - 文件不存在")
            report_lines.append(f"❌ 文件不存在: {filename}\n")
            upload_failure_count += 1
            continue
        
        try:
            print(f"🔄 正在上传: {progress}")
            resp = garmin_client.upload_activity(file_path)
            
            # 检查上传响应
            try:
                resp_json = resp.json()
                # 检查响应中是否有错误信息
                if isinstance(resp_json, dict):
                    detail = resp_json.get('detailedImportResult', {})
                    successes = detail.get('successes', [])
                    failures = detail.get('failures', [])
                    if failures:
                        upload_failure_count += 1
                        failure_msgs = [f.get('messages', [{}])[0].get('content', '') for f in failures]
                        print(f"❌ {progress} - {', '.join(failure_msgs)}")
                        report_lines.append(f"❌ {filename} - {date_time_str} - {', '.join(failure_msgs)}\n")
                    elif successes:
                        upload_success_count += 1
                        print(f"✅ {progress}")
                        report_lines.append(f"✅ {filename} - {date_time_str}\n")
                    else:
                        upload_success_count += 1
                        print(f"✅ {progress}")
                        report_lines.append(f"✅ {filename} - {date_time_str}\n")
                else:
                    upload_success_count += 1
                    print(f"✅ {progress}")
                    report_lines.append(f"✅ {filename} - {date_time_str}\n")
            except Exception:
                # 无法解析JSON，按HTTP状态码判断
                if resp.status_code in (200, 201, 204):
                    upload_success_count += 1
                    print(f"✅ {progress}")
                    report_lines.append(f"✅ {filename} - {date_time_str}\n")
                else:
                    upload_failure_count += 1
                    print(f"❌ {progress} - HTTP {resp.status_code}")
                    report_lines.append(f"❌ {filename} - {date_time_str} - HTTP {resp.status_code}\n")
        except Exception as e:
            upload_failure_count += 1
            error_msg = str(e)
            if len(error_msg) > 100:
                error_msg = error_msg[:100] + "..."
            print(f"❌ {progress} - {error_msg}")
            report_lines.append(f"❌ {filename} - {date_time_str} - {error_msg}\n")
        
        time.sleep(1)
    
    # 生成报告
    coros_to_garmin_report = os.path.join(os.path.dirname(REPORT_FILES['sync_report']), 'coros_to_garmin_report.txt')
    with open(coros_to_garmin_report, "w", encoding="utf-8") as f:
        f.write(f"同步时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"高驰有而佳明没有的活动: {coros_only_count} 个\n")
        f.write(f"  - 白名单跳过: {whitelist_skip} 个\n")
        f.write(f"  - 上传成功: {upload_success_count} 个\n")
        f.write(f"  - 上传失败: {upload_failure_count} 个\n\n")
        if report_lines:
            f.write("详细记录:\n")
            f.writelines(report_lines)
    
    print("\n" + "="*50)
    print("📊 高驰→佳明 同步报告:")
    print(f"📋 高驰有而佳明没有的活动: {coros_only_count} 个")
    print(f"⏭️ 白名单跳过: {whitelist_skip} 个")
    print(f"✅ 上传成功: {upload_success_count} 个")
    print(f"❌ 上传失败: {upload_failure_count} 个")
    print(f"📄 报告已保存到: {os.path.abspath(coros_to_garmin_report)}")
    print("="*50)
    
    return upload_success_count
