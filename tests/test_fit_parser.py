#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FIT 解析测试：用 downloads/garmin 真实文件验证时间提取"""

import os
from datetime import datetime

from core.fit_parser import extract_fit_start_time, get_tz_offset

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GARMIN_DIR = os.path.join(PROJECT_ROOT, 'downloads', 'garmin')


def _sample_fit_files(n=3):
    """取目录中最新的 n 个 FIT 文件"""
    files = sorted(f for f in os.listdir(GARMIN_DIR) if f.endswith('.fit'))
    assert files, "downloads/garmin 目录应有 FIT 文件（测试依赖真实数据）"
    return files[-n:]


def test_extract_fit_start_time_real_files():
    """真实 FIT 文件：提取的开始时间应与文件名日期一致（UTC+8）"""
    for filename in _sample_fit_files():
        path = os.path.join(GARMIN_DIR, filename)
        with open(path, 'rb') as f:
            data = f.read()

        dt = extract_fit_start_time(data)
        assert dt is not None, f"{filename} 应能提取到开始时间"
        assert isinstance(dt, datetime), f"{filename} 提取结果应为 datetime"

        date_part = filename[:8]
        assert dt.strftime('%Y%m%d') == date_part, \
            f"{filename} 提取时间 {dt} 与文件名日期 {date_part} 不一致"


def test_extract_fit_start_time_empty_input():
    """空/过短输入应返回 None 而非抛异常"""
    assert extract_fit_start_time(None) is None
    assert extract_fit_start_time(b'') is None
    assert extract_fit_start_time(b'1234567890123') is None


def test_get_tz_offset_default():
    """无时区信息时返回默认 UTC+8"""
    assert get_tz_offset({}) == 8 * 3600
    assert get_tz_offset({'activity_mesgs': []}) == 8 * 3600


def test_get_tz_offset_from_local_timestamp():
    """有 local_timestamp 时用其与 timestamp 的差值"""
    msgs = {
        'activity_mesgs': [
            {'timestamp': 1000, 'local_timestamp': 1000 + 8 * 3600},
        ]
    }
    assert get_tz_offset(msgs) == 8 * 3600
