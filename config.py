#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置常量模块

集中管理项目中使用的所有常量配置。
"""

import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DIRS = {
    'config': os.path.join(BASE_DIR, 'config'),
    'downloads': os.path.join(BASE_DIR, 'downloads'),
    'garmin_downloads': os.path.join(BASE_DIR, 'downloads', 'garmin'),
    'coros_downloads': os.path.join(BASE_DIR, 'downloads', 'coros'),
    'reports': os.path.join(BASE_DIR, 'reports'),
    'tokens': os.path.join(BASE_DIR, 'tokens'),
    'garmin_tokens': os.path.join(BASE_DIR, 'tokens', 'garmin'),
    'coros_tokens': os.path.join(BASE_DIR, 'tokens', 'coros'),
}

REGION_CONFIG = {
    1: {"teamapi": "https://teamapi.coros.com"},
    2: {"teamapi": "https://teamcnapi.coros.com"},
    3: {"teamapi": "https://teameuapi.coros.com"},
}

STS_CONFIG = {
    1: {'bucket': 'coros-s3', 'service': 'aws'},
    2: {'bucket': 'coros-oss', 'service': 'aliyun'},
    3: {'bucket': 'eu-coros', 'service': 'aws'},
}

SPORT_TYPE_MAPPING = {
    100: "running",
    101: "treadmill_running",
    102: "cycling",
    104: "hiking",
    200: "cycling",
    300: "swimming",
    400: "walking",
    402: "indoor_cardio",
    500: "hiking",
    600: "strength_training",
    700: "yoga",
    800: "rowing",
    900: "elliptical",
    1000: "other",
    10001: "multi_sport",
}

SKIP_UPLOAD_TYPES = {"walking", "indoor_climbing", "bouldering"}

TYPE_COMMENTS = {
    "walking": "## 步行类型文件",
    "indoor_climbing": "## 室内攀岩类型文件",
    "bouldering": "## 抱石类型文件",
    "multi_sport": "## 多项运动类型文件",
    "running": "## 跑步类型文件",
    "cycling": "## 骑行类型文件",
    "strength_training": "## 力量训练类型文件",
    "yoga": "## 瑜伽类型文件",
    "hiking": "## 徒步类型文件",
    "boating_v2": "## 划船类型文件",
}

OSS_APP_ID = "1660188068672619112"
OSS_SIGN = {
    'aliyun': "9AD4AA35AAFEE6BB1E847A76848D58DF",
    'aws': "877571111A1EE5316E4B590103D4B5B3",
}

OSS_SALT = "9y78gpoERW4lBNYL"

CONFIG_FILES = {
    'garmin': os.path.join(DIRS['config'], 'garmin_config.json'),
    'coros': os.path.join(DIRS['config'], 'coros_config.json'),
    'oss': os.path.join(DIRS['config'], 'oss_config.json'),
    'sync_whitelist': os.path.join(DIRS['config'], 'sync_whitelist.md'),
}

REPORT_FILES = {
    'garmin_only': os.path.join(DIRS['reports'], 'garmin_only_activities.txt'),
    'coros_only': os.path.join(DIRS['reports'], 'coros_only_activities.txt'),
    'mismatched': os.path.join(DIRS['reports'], 'mismatched_activities.txt'),
    'sync_report': os.path.join(DIRS['reports'], 'sync_report.txt'),
    'analysis': os.path.join(DIRS['reports'], 'analysis_result.txt'),
}


def ensure_directories():
    """确保所有必要的目录都存在"""
    for dir_path in DIRS.values():
        os.makedirs(dir_path, exist_ok=True)
