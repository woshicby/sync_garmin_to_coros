#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重命名 Coros 活动文件工具

根据 Garmin 活动类型重命名 Coros 活动文件，使活动类型一致。
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.analyzer import analyze_activities
from config import DIRS, REPORT_FILES


def main():
    print("正在执行初始活动文件分析...")
    analyze_activities()

    mismatched_file = REPORT_FILES['mismatched']
    with open(mismatched_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    filtered_lines = [line.strip() for line in lines if line.strip() and line.strip() != "高驰和佳明活动类型不匹配的文件名单：" and not line.strip().startswith("总共有")]
    
    for i in range(0, len(filtered_lines), 4):
        if i + 3 >= len(filtered_lines):
            break
            
        garmin_file_line = filtered_lines[i]
        coros_file_line = filtered_lines[i+1]
        garmin_type_line = filtered_lines[i+2]
        coros_type_line = filtered_lines[i+3]
        
        if not garmin_file_line.startswith("佳明文件: "):
            continue
        garmin_filename = garmin_file_line.split(": ")[1]
        
        if not coros_file_line.startswith("高驰文件: "):
            continue
        coros_filename = coros_file_line.split(": ")[1]
        
        if not garmin_type_line.startswith("佳明活动类型: "):
            continue
        garmin_activity_type = garmin_type_line.split(": ")[1]

        coros_file_path = os.path.join(DIRS['coros_downloads'], coros_filename)
        if not os.path.exists(coros_file_path):
            print(f"高驰文件不存在：{coros_filename}")
            continue

        coros_parts = coros_filename.split("-")
        if len(coros_parts) < 3:
            continue
        
        coros_parts[2] = garmin_activity_type
        new_coros_filename = "-".join(coros_parts)
        new_coros_file_path = os.path.join(DIRS['coros_downloads'], new_coros_filename)

        try:
            os.rename(coros_file_path, new_coros_file_path)
            print(f"重命名成功：{coros_filename} → {new_coros_filename}")
        except Exception as e:
            print(f"重命名失败：{coros_filename} → {new_coros_filename}，错误：{e}")

    print("\n正在执行修正后的活动文件分析...")
    analyze_activities()

    print("\n所有操作完成！分析结果已保存到 reports 文件夹中。")


if __name__ == "__main__":
    main()
