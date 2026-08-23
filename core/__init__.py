#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core 包：项目核心逻辑

- downloader: Garmin / Coros 活动下载
- analyzer:   活动差异分析
- syncer:      Garmin ↔ Coros 同步上传
- coros_client: Coros 平台客户端
- oss_client:  OSS / S3 存储客户端
- fit_parser:  FIT 文件解析工具
- config:      路径常量与配置管理
"""

from .downloader import download_garmin_activities, download_coros_activities
from .analyzer import analyze_activities
from .syncer import sync_activities, sync_coros_to_garmin

__all__ = [
    'download_garmin_activities',
    'download_coros_activities',
    'analyze_activities',
    'sync_activities',
    'sync_coros_to_garmin',
]
