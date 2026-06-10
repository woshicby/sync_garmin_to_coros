#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Garmin 和 Coros 双向活动同步工具

主入口程序，协调整个同步流程：
1. 下载 Garmin 和 Coros 活动文件
2. 分析活动差异
3. 同步 Garmin 独有活动到 Coros
4. 同步 Coros 独有活动到 Garmin
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ensure_directories
from services import (
    download_garmin_activities,
    download_coros_activities,
    analyze_activities,
    sync_activities,
    sync_coros_to_garmin
)


def main():
    """主函数"""
    ensure_directories()
    
    print("="*50)
    print("Garmin ↔ Coros 双向活动同步工具")
    print("="*50)
    
    print("\n📥 Step 1: 下载活动文件...")
    print("正在下载Coros活动...")
    download_coros_activities()
    
    print("\n正在下载Garmin活动...")
    download_garmin_activities()
    
    print("\n📊 Step 2: 分析活动文件...")
    analyze_activities()
    
    print("\n📤 Step 3: 同步佳明活动到高驰...")
    garmin_to_coros_count = sync_activities()
    
    print("\n📤 Step 4: 同步高驰活动到佳明...")
    coros_to_garmin_count = sync_coros_to_garmin()

    total_uploaded = garmin_to_coros_count + coros_to_garmin_count
    if total_uploaded > 0:
        print(f"\n📤 Step 5: 本次共上传 {total_uploaded} 个文件，重新下载...")
        print("正在下载Coros活动...")
        download_coros_activities()
        
        print("\n正在下载Garmin活动...")
        download_garmin_activities()
    else:
        print(f"\n📤 Step 5: 本次无新上传文件，跳过重新下载")
    
    print("\n✅ 所有操作完成！")


if __name__ == "__main__":
    main()
