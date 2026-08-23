#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Keep 历史活动批量上传工具

将 Keep 运动 App 的历史活动（FIT 文件）批量上传到 Garmin 和 Coros 两个平台。

结构：
- _upload_to_coros: 单个文件上传到 Coros（压缩 → MD5 → OSS → 导入接口）
- upload_keep_activities: 主流程（扫描 → 登录 → 逐文件双平台上传 → 报告）
- 登录复用 core.downloader._login_garmin 与 core.syncer._init_coros_client
"""

import os
import re
import sys
import time
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import DIRS, STS_CONFIG
from core.oss_client import get_oss_client, calculate_md5_file
from core.downloader import _login_garmin
from core.syncer import _init_coros_client

# Keep 文件中文运动类型 → 英文类型映射
# 实际目录中出现的类型：行走 / 健身 / 跑步 / 骑行 / 瑜伽
KEEP_TYPE_MAP = {
    "步行": "walking",
    "行走": "walking",
    "徒步": "hiking",
    "跑步": "running",
    "骑行": "cycling",
    "健身": "strength_training",
    "瑜伽": "yoga",
}

# Keep 历史活动所在目录（merged = 手环合并数据, phone = 手机记录）
KEEP_DIRS = [
    os.path.join(DIRS['downloads'], 'KEEP_merged'),
    os.path.join(DIRS['downloads'], 'KEEP_phone'),
]
REPORT_FILE = os.path.join(DIRS['reports'], 'others_upload_report.txt')


def _collect_keep_files():
    """扫描所有 Keep 目录, 收集 FIT 文件

    Returns:
        list: [(file_path, filename), ...] 全部 Keep 活动文件
    """
    files = []
    for keep_dir in KEEP_DIRS:
        if not os.path.exists(keep_dir):
            print(f"⚠ Keep 目录不存在: {keep_dir}")
            continue
        for filename in sorted(os.listdir(keep_dir)):
            if filename.endswith('.fit'):
                files.append((os.path.join(keep_dir, filename), filename))
    return files


# ══════════════════════════════════════════════════════════════
# 单个文件上传到 Coros
# ══════════════════════════════════════════════════════════════
def _upload_to_coros(coros_client, file_path, filename):
    """上传单个文件到 Coros

    流程：压缩为 zip → 计算 MD5 → 上传 OSS → 调用高驰导入接口

    Args:
        coros_client: 已登录的 CorosClient
        file_path: 本地 FIT 文件路径
        filename: 目标文件名

    Returns:
        bool: 是否上传成功
    """
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


# ══════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════
def upload_keep_activities():
    """批量上传 Keep 活动到 Garmin 和 Coros

    流程：扫描 Keep 目录 → 统计类型 → 登录两个平台 → 逐文件双平台上传
    → 生成报告（reports/others_upload_report.txt）

    Returns:
        bool: 是否执行成功
    """
    print("=" * 60)
    print("Keep 历史活动批量上传工具")
    print("=" * 60)

    # 扫描 Keep 文件（合并所有 Keep 目录）
    keep_files = _collect_keep_files()
    if not keep_files:
        print("未找到任何 Keep 活动文件")
        return False

    print(f"\n找到 {len(keep_files)} 个 Keep 活动文件")

    # 统计类型分布
    type_counts = {}
    for _, f in keep_files:
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

    for i, (file_path, filename) in enumerate(keep_files):
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