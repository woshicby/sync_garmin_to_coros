#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FIT 文件解析工具

统一处理 FIT 文件的开始时间提取（原分散在 downloader.py 与
tools/rename_fit_files.py 中的重复实现合并于此）。

时区逻辑：优先使用文件中的 local_timestamp 计算时区偏移，
如果文件中没有则回退到 UTC+8。
"""

from datetime import datetime, timedelta

from garmin_fit_sdk import Decoder, Stream

FIT_EPOCH = datetime(1989, 12, 31, 0, 0, 0)
# 默认时区偏移：UTC+8（中国时区），当 FIT 文件中无时区信息时使用
DEFAULT_TZ_OFFSET_SECONDS = 8 * 3600


def get_tz_offset(msgs):
    """从 FIT 消息中获取时区偏移（秒）

    优先从 activity_mesgs 中的 local_timestamp 与 timestamp 差值获取。
    如果文件中没有时区信息，返回默认 UTC+8。

    Args:
        msgs: garmin_fit_sdk Decoder 解析出的消息字典

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


def extract_fit_start_time(fit_data):
    """从 FIT 文件二进制数据中提取活动开始时间

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

        tz_offset = get_tz_offset(msgs)

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
