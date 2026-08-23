#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Garmin 和 Coros 双向活动同步工具

主入口程序，协调整个同步流程：
1. 下载 Garmin 和 Coros 活动文件
2. 分析活动差异
3. 同步 Garmin 独有活动到 Coros
4. 同步 Coros 独有活动到 Garmin
5. 重新下载：再次拉取两边活动列表，把刚上传到对方平台的新活动
   下载到对应文件夹（Garmin 侧出现刚上传的高驰活动，反之亦然）
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import ensure_directories
from core import (
    download_garmin_activities,
    download_coros_activities,
    analyze_activities,
    sync_activities,
    sync_coros_to_garmin,
)


def _download_with_retry(label, download_fn):
    """下载活动文件，失败时提供重试/继续/退出选项

    Args:
        label: 平台名称（如 "Garmin" / "Coros"），用于提示
        download_fn: 下载函数，返回 True 表示成功

    Returns:
        bool: True 表示有可用文件（下载成功或用户选择继续）
    """
    if download_fn():
        return True

    print(f"❌ {label} 活动下载失败（常见原因：登录失败或网络问题）。")
    while True:
        choice = input(f"请选择: [1] 重试下载  [2] 继续用现有本地文件（{label}新活动可能缺失）  [其他] 退出: ").strip()
        if choice == "1":
            print(f"正在重新下载{label}活动...")
            if download_fn():
                return True
            print(f"❌ {label} 重试仍然失败。")
            continue
        if choice == "2":
            print(f"⚠ 继续使用现有本地文件，{label} 新活动可能缺失。")
            return False
        print("已退出。")
        sys.exit(1)


def _step(num, total, title):
    """打印步骤标题"""
    print(f"\n{'═' * 56}")
    print(f"  Step {num}/{total}  {title}")
    print(f"{'─' * 56}")


def main():
    """主函数"""
    ensure_directories()

    print("═" * 56)
    print("  Garmin ↔ Coros 双向活动同步工具")
    print("═" * 56)

    _step(1, 5, "下载活动文件")
    _download_with_retry("Coros", download_coros_activities)
    _download_with_retry("Garmin", download_garmin_activities)

    _step(2, 5, "分析活动差异")
    analyze_activities()

    _step(3, 5, "同步佳明活动到高驰")
    garmin_to_coros_count = sync_activities()

    _step(4, 5, "同步高驰活动到佳明")
    coros_to_garmin_count = sync_coros_to_garmin()

    total_uploaded = garmin_to_coros_count + coros_to_garmin_count

    _step(5, 5, "上传后重新下载")
    if total_uploaded > 0:
        print(f"本次共上传 {total_uploaded} 个文件，重新下载...")
        if not download_coros_activities():
            print("⚠ Coros 重新下载失败，本次上传的文件可能未出现在本地。")
        if not download_garmin_activities():
            print("⚠ Garmin 重新下载失败，本次上传的文件可能未出现在本地。")
    else:
        print("本次无新上传文件，跳过重新下载")

    print(f"\n{'═' * 56}")
    print("  ✅ 所有操作完成！")
    print("═" * 56)


if __name__ == "__main__":
    main()
