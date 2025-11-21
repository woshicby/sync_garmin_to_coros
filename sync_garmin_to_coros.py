#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
佳明活动同步到高驰平台的主程序

此模块是整个活动同步系统的核心控制器，负责协调整个同步流程，包括：
1. 下载最新的Coros和Garmin活动文件
2. 分析活动文件，找出Garmin独有的活动
3. 将Garmin独有的活动上传到Coros平台
4. 生成同步报告，记录上传结果和统计信息

依赖模块：
- coros_download: 负责下载高驰平台活动文件
- garmin_download: 负责下载佳明平台活动文件
- analyze_activity_files: 负责分析活动文件并找出差异
- coros_client: 负责与高驰API交互
- oss_client: 负责文件存储服务操作
"""

# 导入标准库
import os
import re
import json
import time
import base64
import tempfile
import zipfile

# 导入项目模块
from coros_download import main as coros_main  # 高驰活动下载功能
from garmin_download import main as garmin_main  # 佳明活动下载功能
from analyze_activity_files import main as analyze_main  # 活动文件分析功能
from coros_client import CorosClient  # 高驰API客户端
from oss_client import get_oss_client as new_get_oss_client, calculate_md5_file  # 文件存储服务客户端和MD5计算


# 区域配置 - 用于确定API访问地址
# 不同区域的用户需要访问对应的API服务
REGIONCONFIG = {
    1: {"teamapi": "https://teamapi.coros.com"},        # 国际区 - 适用于全球大部分地区
    2: {"teamapi": "https://teamcnapi.coros.com"},       # 中国区 - 适用于中国大陆地区
    3: {"teamapi": "https://teameuapi.coros.com"}        # 欧洲区 - 适用于欧洲地区用户
}


# STS配置 - 用于文件存储服务访问
# 不同区域使用不同的云存储服务
STS_CONFIG = {
    1: {'bucket': 'coros-s3', 'service': 'aws'},      # 国际区 - 使用AWS S3存储服务
    2: {'bucket': 'coros-oss', 'service': 'aliyun'},   # 中国区 - 使用阿里云OSS存储服务
    3: {'bucket': 'eu-coros', 'service': 'aws'}        # 欧洲区 - 使用AWS S3存储服务
}


def main():
    """主函数，执行佳明活动同步到高驰的完整流程
    
    实现了从佳明平台到高驰平台的活动数据同步，包括以下关键步骤：
    1. 下载最新的Coros和Garmin活动文件
    2. 分析活动文件，识别Garmin独有的活动
    3. 初始化高驰API客户端
    4. 解析需要上传的活动列表
    5. 执行活动文件上传
    6. 生成同步报告
    """
    print("开始同步佳明活动到高驰...")
    
    # Step 1: 下载最新的Coros和Garmin活动文件
    # 首先同步获取高驰平台的最新活动，确保数据完整
    print("正在下载Coros活动...")
    coros_main()  # 调用coros_download.py中的main函数下载高驰活动
    
    # 然后同步获取佳明平台的最新活动，用于后续分析比对
    print("正在下载Garmin活动...")
    garmin_main()  # 调用garmin_download.py中的main函数下载佳明活动
    
    # Step 2: 分析活动文件，找出Garmin独有的活动
    # 对两个平台的活动进行对比分析，识别需要同步的佳明独有活动
    print("正在分析活动文件...")
    analyze_main()  # 调用analyze_activity_files.py中的main函数分析活动文件
    
    # Step 3: 初始化Coros客户端
    # 预先创建CorosClient实例，用于后续与高驰API交互
    coros_client = None
    try:
        # 从配置文件读取用户凭据
        config_file = "config/coros_config.json"
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        email = config.get("email", "")
        password_encoded = config.get("password", "")
        
        print(f"已加载Coros配置，邮箱: {email}")
        
        # 尝试解码Base64编码的密码，增强安全性
        try:
            password = base64.b64decode(password_encoded).decode('utf-8')
            print(f"密码解码成功")
        except Exception as decode_error:
            print(f"密码解码失败: {str(decode_error)}")
            password = password_encoded  # 如果解码失败，直接使用原文
        
        # 创建客户端实例，自动尝试加载已保存的token
        coros_client = CorosClient(email, password)
        print("Coros客户端已创建，将自动使用保存的token或在需要时登录")
    except Exception as e:
        print(f"初始化Coros客户端失败: {str(e)}")
    
    # Step 4: 解析Garmin独有的活动列表文件
    # 从分析结果中获取需要上传的活动列表
    garmin_only_file = "analysis_results\\garmin_only_activities.txt"  # 分析结果文件路径
    garmin_files_dir = "downloads\\garmin"  # 佳明活动文件存储目录
    activities_to_upload = []  # 初始化待上传活动列表

    if os.path.exists(garmin_only_file):
        with open(garmin_only_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 解析文件内容，提取文件名、日期时间和活动类型信息
        index = 0
        while index < len(lines):
            line = lines[index].strip()
            if line.startswith("文件名:"):
                # 提取文件名
                filename = line.split(":", 1)[1].strip()
                # 检查后续行是否存在足够的信息
                if index + 2 < len(lines):
                    date_time_line = lines[index + 1].strip()
                    sport_type_line = lines[index + 2].strip()
                    # 提取日期时间字符串用于排序
                    date_time_str = date_time_line.split(":", 1)[1].strip()
                    activities_to_upload.append((filename, date_time_line, sport_type_line, date_time_str))
                    index += 4  # 跳过空行
                else:
                    index += 1
            else:
                index += 1
        
        # 按日期时间从早到晚排序（升序），确保活动按时间顺序上传
        activities_to_upload.sort(key=lambda x: x[3])
        # 移除临时添加的日期时间字符串，保持原有格式
        activities_to_upload = [(item[0], item[1], item[2]) for item in activities_to_upload]

    # 如果没有需要上传的活动，提前结束程序
    if not activities_to_upload:
        print("没有需要上传的佳明活动")
        return
    
    # Step 5: 准备上传活动文件
    print(f"正在上传 {len(activities_to_upload)} 个佳明活动到高驰...")
    
    # 确保Coros客户端已正确初始化
    if not coros_client:
        print("错误: Coros客户端初始化失败，无法进行上传")
        return
    
    # 首先验证登录状态，确保token有效
    try:
        print("正在验证登录状态...")
        coros_client._check_token()  # 检查并在必要时刷新token
        user_id = coros_client.user_id
        region_id = coros_client.region_id
        print(f"登录状态验证成功！用户ID: {user_id}, 区域ID: {region_id}")
    except Exception as login_error:
        print(f"登录验证失败: {str(login_error)}")
        print("无法继续上传活动，请检查您的账号和网络连接")
        return
    
    # Step 6: 准备同步报告数据结构
    report_lines = []  # 初始化报告内容列表
    report_lines.append("同步佳明活动到高驰报告\n")
    report_lines.append(f"同步时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append(f"待上传活动数量: {len(activities_to_upload)}\n\n")
    
    # 初始化上传统计计数器
    upload_success_count = 0  # 上传成功的活动数量
    upload_failure_count = 0  # 上传失败的活动数量
    
    # 遍历所有需要上传的活动文件
    total_files = len(activities_to_upload)
    for i, (filename, date_time_line, sport_type_line) in enumerate(activities_to_upload):
            
        # 显示当前处理的进度信息
            progress_info = f"[{i+1}/{total_files}] {filename}"
            print(f"🔄 正在处理: {progress_info}")
            
            # 构建完整的文件路径
            file_path = os.path.join(garmin_files_dir, filename)
            
            # 检查文件是否存在，避免后续操作出错
            if not os.path.exists(file_path):
                report_lines.append(f"文件不存在: {file_path}\n")
                upload_failure_count += 1
                print(f"❌ {progress_info} - 文件不存在")
                continue
            
            try:
                # 根据用户所在区域获取相应的存储服务配置
                bucket = STS_CONFIG.get(region_id, STS_CONFIG[2])['bucket']
                service = STS_CONFIG.get(region_id, STS_CONFIG[2])['service']
                # 映射服务名称：阿里云→oss，其他→s3
                serviceName = 'oss' if service == 'aliyun' else 's3'
                
                # 创建临时ZIP文件，将活动文件压缩成Coros平台要求的格式
                temp_zip_path = tempfile.mktemp(suffix='.zip')
                with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.write(file_path, os.path.basename(file_path))

                try:
                    # 计算ZIP文件的MD5值和文件大小，用于完整性校验
                    zip_size = os.path.getsize(temp_zip_path)
                    file_md5 = calculate_md5_file(temp_zip_path)

                    # 初始化OSS客户端，用于将文件上传到云存储
                    oss_client = new_get_oss_client(bucket, service, region_id, coros_client.access_token)
                    
                    # 生成基于MD5的文件名，避免重复上传
                    zip_filename = f"{user_id}/{file_md5}.zip"
                    
                    # 使用分片上传功能将文件上传到OSS/S3存储服务
                    oss_key = oss_client.multipart_upload(temp_zip_path, zip_filename)
                    file_size = zip_size

                    # 确保OSS路径格式符合Coros API要求的标准格式
                    standard_oss_key = f"fit_zip/{user_id}/{file_md5}.zip"
                    
                    # 调用Coros API完成活动上传流程
                    upload_result = coros_client.upload_activity(
                        oss_object=standard_oss_key,
                        md5=file_md5,
                        file_name=f"{os.path.basename(file_path)}.zip",
                        size=file_size
                    )
                finally:
                    # 确保清理临时文件，避免占用磁盘空间
                    if temp_zip_path and os.path.exists(temp_zip_path):
                        os.remove(temp_zip_path)
                
                # 处理上传结果
                if upload_result:
                    # 上传成功，记录成功信息
                    activity_time = date_time_line.split(':', 1)[1].strip()
                    report_lines.append(f"✅ 上传成功: {filename} - {activity_time}\n")
                    upload_success_count += 1
                    print(f"✅ {progress_info} - 📊 活动导入成功")
                else:
                    # 上传失败（API错误），记录失败信息
                    activity_time = date_time_line.split(':', 1)[1].strip()
                    report_lines.append(f"❌ 上传失败(API错误): {filename} - {activity_time}\n")
                    upload_failure_count += 1
                    print(f"❌ {progress_info} - ❌ API错误: 导入失败")
                
                time.sleep(1)  # 控制请求频率，避免触发API限流机制
            except Exception as e:
                # 捕获并记录上传过程中的异常
                activity_time = date_time_line.split(':', 1)[1].strip()
                report_lines.append(f"❌ 上传失败(异常): {filename} - {activity_time} - {str(e)}\n")
                upload_failure_count += 1
                print(f"❌ {progress_info} - ⚠️ 异常错误: {str(e)}")
                time.sleep(2)  # 失败后稍作等待，避免连续失败请求
    
    # Step 7: 生成并保存最终同步报告
    # 添加上传统计信息到报告
    report_lines.append(f"\n上传结果统计:\n")
    report_lines.append(f"成功上传: {upload_success_count} 个\n")
    report_lines.append(f"上传失败: {upload_failure_count} 个\n")
    report_lines.append(f"总活动数: {len(activities_to_upload)} 个\n")
    
    # 生成报告文件，保存到项目根目录
    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync_report.txt")
    with open(report_file, "w", encoding="utf-8") as f:
        # 写入基本统计信息
        f.write(f"同步时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"总活动数: {len(activities_to_upload)}\n")
        f.write(f"成功上传: {upload_success_count}\n")
        f.write(f"上传失败: {upload_failure_count}\n\n")
        # 写入详细的活动处理记录
        f.writelines(report_lines)
    
    # 打印格式化的同步报告摘要到控制台
    print("\n" + "="*50)
    print("📊 同步报告摘要:")
    print(f"📋 总计: {len(activities_to_upload)} 个活动")
    print(f"✅ 成功: {upload_success_count} 个活动")
    print(f"❌ 失败: {upload_failure_count} 个活动")
    print(f"📄 同步报告已保存到: {os.path.abspath(report_file)}")
    print("="*50)
    print(f"💡 同步完成!")


if __name__ == "__main__":
    # 程序入口点，当直接运行此文件时执行同步流程
    main()