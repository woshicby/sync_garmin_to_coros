#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量修正 FIT 文件名中的日期时间为文件内部记录的开始时间，
并同步更新 sync_whitelist.md 中的对应条目。

使用 garmin_fit_sdk 正确解析 FIT 文件，提取 session_mesgs.start_time，
统一使用 UTC+8 时区偏移转为本地时间。

⚠ 归档说明：时间提取逻辑已统一到 core/fit_parser.py，下载流程已内置该功能。
本文件仅留档参考，不建议继续使用。
"""

import os
import re
import sys
from datetime import datetime, timedelta

from garmin_fit_sdk import Decoder, Stream

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GARMIN_DIR = os.path.join(BASE_DIR, "downloads", "garmin")
COROS_DIR = os.path.join(BASE_DIR, "downloads", "coros")
KEEP_MERGED_DIR = os.path.join(BASE_DIR, "downloads", "KEEP_merged")
KEEP_PHONE_DIR = os.path.join(BASE_DIR, "downloads", "KEEP_phone")
WHITELIST_PATH = os.path.join(BASE_DIR, "config", "sync_whitelist.md")

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


def extract_fit_local_start_time(filepath):
    """从 FIT 文件中提取活动的本地开始时间

    时区逻辑：优先使用文件中的 local_timestamp 计算时区偏移，
    如果文件中没有则回退到 UTC+8。

    1. 优先从 session_mesgs 获取 start_time，加上时区偏移
    2. 回退：从 file_id_mesgs 获取 time_created，加上时区偏移

    Returns:
        datetime or None: 本地开始时间
    """
    try:
        stream = Stream.from_file(filepath)
        decoder = Decoder(stream)
        msgs, errors = decoder.read(
            convert_datetimes_to_dates=False,
            expand_sub_fields=True,
            expand_components=True,
            merge_heart_rates=False,
        )
    except Exception:
        return None

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


def rename_files_in_dir(dir_path):
    """重命名目录下的所有 FIT 文件，返回 {旧名: 新名} 映射"""
    rename_map = {}
    files = [f for f in os.listdir(dir_path) if f.endswith('.fit')]
    unchanged = 0

    for i, filename in enumerate(files, 1):
        filepath = os.path.join(dir_path, filename)

        start_time = extract_fit_local_start_time(filepath)
        if start_time is None:
            print(f"  [{i}/{len(files)}] 无法提取时间，跳过: {filename}", flush=True)
            continue

        new_date = start_time.strftime("%Y%m%d")
        new_time = start_time.strftime("%H%M%S")

        # 解析旧文件名，只替换日期和时间部分
        match = re.match(r"^(\d{8})-(\d{6})-(.+)$", filename)
        if not match:
            print(f"  [{i}/{len(files)}] 文件名格式不匹配，跳过: {filename}", flush=True)
            continue

        old_date = match.group(1)
        old_time = match.group(2)
        rest = match.group(3)

        if old_date == new_date and old_time == new_time:
            unchanged += 1
            if unchanged % 100 == 0:
                print(f"  [{i}/{len(files)}] 已检查 {unchanged} 个无需修改...", flush=True)
            continue

        new_filename = f"{new_date}-{new_time}-{rest}"
        new_filepath = os.path.join(dir_path, new_filename)

        # 检查目标文件是否已存在
        if os.path.exists(new_filepath):
            print(f"  [{i}/{len(files)}] 目标已存在，跳过: {filename} -> {new_filename}", flush=True)
            continue

        try:
            os.rename(filepath, new_filepath)
            rename_map[filename] = new_filename
            print(f"  [{i}/{len(files)}] {filename} -> {new_filename}", flush=True)
        except Exception as e:
            print(f"  [{i}/{len(files)}] 重命名失败: {filename} - {e}", flush=True)

    return rename_map


def update_whitelist(rename_map):
    """更新 whitelist 文件中的文件名引用"""
    if not rename_map or not os.path.exists(WHITELIST_PATH):
        return

    with open(WHITELIST_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    for old_name, new_name in rename_map.items():
        content = content.replace(old_name, new_name)

    if content != original:
        with open(WHITELIST_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n白名单文件已更新，共替换 {len(rename_map)} 个文件名引用")
    else:
        print("\n白名单文件无需更新")


def main():
    # Windows 控制台 UTF-8 输出
    if sys.platform == 'win32':
        os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    print("=" * 60)
    print("批量修正 FIT 文件名中的日期时间")
    print("=" * 60)

    total_renamed = {}

    print("\n处理 Garmin 文件...")
    garmin_map = rename_files_in_dir(GARMIN_DIR)
    total_renamed.update(garmin_map)
    print(f"Garmin: 重命名 {len(garmin_map)} 个文件")

    print("\n处理 Coros 文件...")
    coros_map = rename_files_in_dir(COROS_DIR)
    total_renamed.update(coros_map)
    print(f"Coros: 重命名 {len(coros_map)} 个文件")

    print("\n处理 KEEP_merged 文件...")
    keep_merged_map = rename_files_in_dir(KEEP_MERGED_DIR)
    total_renamed.update(keep_merged_map)
    print(f"KEEP_merged: 重命名 {len(keep_merged_map)} 个文件")

    print("\n处理 KEEP_phone 文件...")
    keep_phone_map = rename_files_in_dir(KEEP_PHONE_DIR)
    total_renamed.update(keep_phone_map)
    print(f"KEEP_phone: 重命名 {len(keep_phone_map)} 个文件")

    print(f"\n总计重命名 {len(total_renamed)} 个文件")

    print("\n更新白名单文件...")
    update_whitelist(total_renamed)

    print("\n完成！")


if __name__ == "__main__":
    main()
