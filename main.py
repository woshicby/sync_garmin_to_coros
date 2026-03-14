#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Garmin Connect 活动同步到 Coros 平台

主入口程序，协调整个同步流程：
1. 下载 Garmin 和 Coros 活动文件
2. 分析活动差异
3. 同步 Garmin 独有活动到 Coros
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ensure_directories
from services import (
    download_garmin_activities,
    download_coros_activities,
    analyze_activities,
    sync_activities
)


def main():
    """主函数"""
    ensure_directories()
    
    print("="*50)
    print("Garmin → Coros 活动同步工具")
    print("="*50)
    
    print("\n📥 Step 1: 下载活动文件...")
    print("正在下载Coros活动...")
    download_coros_activities()
    
    print("\n正在下载Garmin活动...")
    download_garmin_activities()
    
    print("\n📊 Step 2: 分析活动文件...")
    analyze_activities()
    
    print("\n📤 Step 3: 同步活动...")
    sync_activities()
    
    print("\n✅ 所有操作完成！")


if __name__ == "__main__":
    main()
