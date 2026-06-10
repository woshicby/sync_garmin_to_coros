#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Keep 历史活动批量上传工具

将 downloads/keep 目录中的古老 Keep 运动记录批量上传到 Garmin 和 Coros 两个平台。
"""

import os
import re
import sys
import time
import json
import tempfile
import zipfile
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DIRS, STS_CONFIG, OSS_APP_ID, OSS_SIGN
from config_manager import get_garmin_config, get_coros_config
from clients.coros_client import CorosClient
from storage.oss_client import get_oss_client, calculate_md5_file

# Keep 文件中文运动类型 → 英文类型映射
KEEP_TYPE_MAP = {
    "步行": "walking",
    "徒步": "hiking",
    "跑步": "running",
    "骑行": "cycling",
}

KEEP_DIR = os.path.join(DIRS['downloads'], 'others')
REPORT_FILE = os.path.join(DIRS['reports'], 'others_upload_report.txt')


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

        tokenstore = DIRS['garmin_tokens']
        os.makedirs(tokenstore, exist_ok=True)

        has_token_files = os.path.exists(os.path.join(tokenstore, "oauth1_token.json")) and \
                         os.path.exists(os.path.join(tokenstore, "oauth2_token.json"))

        if has_token_files:
            client.login(tokenstore)
            print("Garmin 登录成功！")
        else:
            client.login()
            client.garth.dump(tokenstore)
            print("Garmin 登录成功！令牌已保存。")

        return client
    except Exception as e:
        print(f"Garmin 登录失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def _init_coros_client():
    """初始化 Coros 客户端"""
    try:
        config_manager = get_coros_config()
        config = config_manager.load()
        email = config.get("email", "")
        password = config.get("password", "")

        print(f"已加载Coros配置，邮箱: {email}")

        coros_client = CorosClient(email, password)
        coros_client._check_token()
        print(f"Coros 登录成功！用户ID: {coros_client.user_id}, 区域ID: {coros_client.region_id}")

        return coros_client
    except Exception as e:
        print(f"Coros 客户端初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def _upload_to_coros(coros_client, file_path, filename):
    """上传单个文件到 Coros"""
    user_id = coros_client.user_id
    region_id = coros_client.region_id

    bucket = STS_CONFIG.get(region_id, STS_CONFIG[2])['bucket']
    service = STS_CONFIG.get(region_id, STS_CONFIG[2])['service']

    temp_zip_path = None
    try:
        # 压缩为 zip
        temp_zip_path = tempfile.mktemp(suffix='.zip')
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(file_path, os.path.basename(file_path))

        zip_size = os.path.getsize(temp_zip_path)
        file_md5 = calculate_md5_file(temp_zip_path)

        oss_client = get_oss_client(bucket, service, access_token=coros_client.access_token)
        zip_filename = f"{user_id}/{file_md5}.zip"
        oss_client.multipart_upload(temp_zip_path, zip_filename)

        standard_oss_key = f"fit_zip/{user_id}/{file_md5}.zip"

        result = coros_client.upload_activity(
            oss_object=standard_oss_key,
            md5=file_md5,
            file_name=f"{filename}.zip",
            size=zip_size
        )

        return result
    except Exception as e:
        print(f"  Coros 上传异常: {str(e)}")
        return False
    finally:
        if temp_zip_path and os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)


def upload_keep_activities():
    """批量上传 Keep 活动到 Garmin 和 Coros"""
    print("=" * 60)
    print("Keep 历史活动批量上传工具")
    print("=" * 60)

    # 扫描 Keep 文件
    if not os.path.exists(KEEP_DIR):
        print(f"错误: Keep 目录不存在: {KEEP_DIR}")
        return False

    keep_files = sorted([f for f in os.listdir(KEEP_DIR) if f.endswith('.fit')])
    if not keep_files:
        print("未找到任何 Keep 活动文件")
        return False

    print(f"\n找到 {len(keep_files)} 个 Keep 活动文件")

    # 统计类型分布
    type_counts = {}
    for f in keep_files:
        match = re.match(r'^\d{8}-\d{6}-(\w+)', f)
        if match:
            cn_type = match.group(1)
            en_type = KEEP_TYPE_MAP.get(cn_type, cn_type)
            type_counts[en_type] = type_counts.get(en_type, 0) + 1

    print("文件类型分布:")
    for t, c in sorted(type_counts.items()):
        print(f"  - {t}: {c} 个")

    # 登录 Garmin
    print("\n" + "-" * 40)
    print("正在登录 Garmin...")
    garmin_client = _login_garmin()
    if not garmin_client:
        print("Garmin 登录失败，无法继续")
        return False

    # 登录 Coros
    print("\n正在登录 Coros...")
    coros_client = _init_coros_client()
    if not coros_client:
        print("Coros 登录失败，无法继续")
        return False

    # 开始上传
    print("\n" + "=" * 60)
    print("开始批量上传...")
    print("=" * 60)

    results = []
    garmin_success = 0
    garmin_fail = 0
    coros_success = 0
    coros_fail = 0

    total = len(keep_files)
    start_time = time.time()

    for i, filename in enumerate(keep_files):
        file_path = os.path.join(KEEP_DIR, filename)

        match = re.match(r'^(\d{8}-\d{6})-(\w+)', filename)
        cn_type = match.group(2) if match else "未知"
        en_type = KEEP_TYPE_MAP.get(cn_type, cn_type)

        progress = f"[{i+1}/{total}]"
        elapsed = time.time() - start_time
        avg_time = elapsed / (i + 1) if i > 0 else 0
        eta = avg_time * (total - i - 1)
        eta_str = f"{int(eta // 60)}分{int(eta % 60)}秒" if eta > 0 else "即将完成"

        print(f"\n{progress} {filename} ({en_type}) [预计剩余: {eta_str}]")

        # 上传到 Garmin
        garmin_ok = False
        try:
            garmin_client.upload_activity(file_path)
            garmin_ok = True
            garmin_success += 1
            print(f"  Garmin   ✅ 上传成功")
        except Exception as e:
            garmin_fail += 1
            error_msg = str(e)
            # 截断过长的错误信息
            if len(error_msg) > 100:
                error_msg = error_msg[:100] + "..."
            print(f"  Garmin   ❌ 上传失败: {error_msg}")

        # 上传到 Coros
        coros_ok = _upload_to_coros(coros_client, file_path, filename)
        if coros_ok:
            coros_success += 1
            print(f"  Coros    ✅ 上传成功")
        else:
            coros_fail += 1
            print(f"  Coros    ❌ 上传失败")

        results.append({
            'filename': filename,
            'type': en_type,
            'garmin': garmin_ok,
            'coros': coros_ok
        })

        # 速率限制
        time.sleep(1.5)

    # 生成报告
    total_time = time.time() - start_time
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("Keep 历史活动批量上传报告\n")
        f.write(f"上传时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"总耗时: {int(total_time // 60)}分{int(total_time % 60)}秒\n\n")
        f.write(f"总文件数: {total}\n")
        f.write(f"Garmin 上传成功: {garmin_success} / 失败: {garmin_fail}\n")
        f.write(f"Coros 上传成功: {coros_success} / 失败: {coros_fail}\n\n")

        # 失败记录
        garmin_failed = [r for r in results if not r['garmin']]
        coros_failed = [r for r in results if not r['coros']]

        if garmin_failed:
            f.write(f"Garmin 上传失败 ({len(garmin_failed)} 个):\n")
            for r in garmin_failed:
                f.write(f"  - {r['filename']} ({r['type']})\n")
            f.write("\n")

        if coros_failed:
            f.write(f"Coros 上传失败 ({len(coros_failed)} 个):\n")
            for r in coros_failed:
                f.write(f"  - {r['filename']} ({r['type']})\n")
            f.write("\n")

        # 全部成功记录
        f.write("详细记录:\n")
        for r in results:
            g_status = "✅" if r['garmin'] else "❌"
            c_status = "✅" if r['coros'] else "❌"
            f.write(f"  Garmin:{g_status} Coros:{c_status} {r['filename']} ({r['type']})\n")

    # 控制台摘要
    print("\n" + "=" * 60)
    print("📊 上传完成！")
    print(f"总文件数: {total}")
    print(f"总耗时: {int(total_time // 60)}分{int(total_time % 60)}秒")
    print(f"Garmin: ✅ {garmin_success} / ❌ {garmin_fail}")
    print(f"Coros:  ✅ {coros_success} / ❌ {coros_fail}")
    print(f"📄 详细报告已保存到: {os.path.abspath(REPORT_FILE)}")
    print("=" * 60)

    return True


if __name__ == '__main__':
    upload_keep_activities()