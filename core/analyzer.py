#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
活动分析服务

提供 Garmin 和 Coros 活动文件的对比分析功能：
1. 扫描两个平台的本地下载目录，解析文件名中的日期时间与类型
2. 按日期时间匹配找出重复活动
3. 生成四类报告（类型不匹配 / Coros 独有 / Garmin 独有 / 统计摘要）
"""

import os
import re
import datetime
import json

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import (
    DIRS, CONFIG_FILES, REPORT_FILES, 
    TYPE_COMMENTS
)


# ══════════════════════════════════════════════════════════════
# 分析主入口
# ══════════════════════════════════════════════════════════════
def analyze_activities():
    """分析活动文件，生成差异报告

    流程：读取 Garmin/Coros 文件信息 → 找重复 → 生成 4 份报告
    （mismatched / coros_only / garmin_only / analysis）
    """
    result_folder = DIRS['reports']
    os.makedirs(result_folder, exist_ok=True)
    
    garmin_files = _get_garmin_files_info()
    coros_files = _get_coros_files_info()
    
    garmin_datetimes = {file["datetime"]: file for file in garmin_files}
    coros_datetimes = {file["datetime"]: file for file in coros_files}
    
    duplicates = _find_duplicate_activities(garmin_files, coros_files)
    
    _generate_mismatched_report(duplicates, result_folder)
    _generate_coros_only_report(coros_files, garmin_datetimes, result_folder)
    _generate_garmin_only_report(garmin_files, coros_datetimes, result_folder)
    _generate_analysis_report(garmin_files, coros_files, duplicates, result_folder)


# ══════════════════════════════════════════════════════════════
# 文件信息扫描
# ══════════════════════════════════════════════════════════════
def _get_garmin_files_info():
    """获取佳明下载文件的信息（解析文件名 → 日期时间/类型/路径）"""
    garmin_dir = DIRS['garmin_downloads']
    garmin_files = []
    
    if not os.path.exists(garmin_dir):
        return garmin_files
    
    for filename in os.listdir(garmin_dir):
        if filename.endswith(".fit"):
            match = re.match(r"^(\d{8})-(\d{6})-(\w+)-(.*)-(\d+)\.fit$", filename)
            if match:
                date_str = match.group(1)
                time_str = match.group(2)
                sport_type = match.group(3)
                activity_name = match.group(4)
                activity_id = match.group(5)
                
                try:
                    datetime_obj = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y%m%d %H%M%S")
                    garmin_files.append({
                        "filename": filename,
                        "datetime": datetime_obj,
                        "sport_type": sport_type,
                        "activity_name": activity_name,
                        "activity_id": activity_id
                    })
                except ValueError:
                    continue
    
    return garmin_files


def _get_coros_files_info():
    """获取高驰下载文件的信息（解析文件名 → 日期时间/类型/路径）"""
    coros_dir = DIRS['coros_downloads']
    coros_files = []
    
    if not os.path.exists(coros_dir):
        return coros_files
    
    for filename in os.listdir(coros_dir):
        if filename.endswith(".fit"):
            match = re.match(r"^(\d{8})-(\d{6})-(\w+)-(\d+)\.fit$", filename)
            if match:
                date_str = match.group(1)
                time_str = match.group(2)
                sport_type = match.group(3)
                activity_id = match.group(4)
                
                try:
                    datetime_obj = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y%m%d %H%M%S")
                    coros_files.append({
                        "filename": filename,
                        "datetime": datetime_obj,
                        "sport_type": sport_type,
                        "activity_id": activity_id
                    })
                except ValueError:
                    continue
    
    return coros_files


# ══════════════════════════════════════════════════════════════
# 重复匹配与报告生成
# ══════════════════════════════════════════════════════════════
def _find_duplicate_activities(garmin_files, coros_files):
    """根据日期和时间查找重复活动

    Args:
        garmin_files: Garmin 文件信息列表（含 "datetime" 键）
        coros_files: Coros 文件信息列表（含 "datetime" 键）

    Returns:
        list: [(garmin_file, coros_file), ...] 重复活动对
    """
    duplicates = []
    
    garmin_datetime_map = {file["datetime"]: file for file in garmin_files}
    
    for coros_file in coros_files:
        coros_dt = coros_file["datetime"]
        if coros_dt in garmin_datetime_map:
            garmin_file = garmin_datetime_map[coros_dt]
            duplicates.append((garmin_file, coros_file))
    
    return duplicates


def _generate_mismatched_report(duplicates, result_folder):
    """生成活动类型不匹配报告（同名活动但类型不同）"""
    mismatched_output = []
    mismatched_count = len([(g, c) for g, c in duplicates if g['sport_type'] != c['sport_type']])
    mismatched_output.append(f"高驰和佳明活动类型不匹配的文件名单：")
    mismatched_output.append(f"总共有 {mismatched_count} 个不匹配的活动")
    mismatched_output.append("")
    
    if duplicates:
        for garmin_file, coros_file in duplicates:
            if garmin_file['sport_type'] != coros_file['sport_type']:
                mismatched_output.append(f"佳明文件: {garmin_file['filename']}")
                mismatched_output.append(f"高驰文件: {coros_file['filename']}")
                mismatched_output.append(f"佳明活动类型: {garmin_file['sport_type']}")
                mismatched_output.append(f"高驰活动类型: {coros_file['sport_type']}")
                mismatched_output.append("")
    
    with open(REPORT_FILES['mismatched'], "w", encoding="utf-8") as f:
        for line in mismatched_output:
            f.write(line + "\n")


def _generate_coros_only_report(coros_files, garmin_datetimes, result_folder):
    """生成高驰独有活动报告（高驰有而佳明没有）"""
    coros_only_output = []
    
    coros_only_files = []
    for file in coros_files:
        if file["datetime"] not in garmin_datetimes:
            coros_only_files.append(file)
    
    coros_only_count = len(coros_only_files)
    coros_only_output.append(f"高驰有佳明没有的活动名单：")
    coros_only_output.append(f"总共有 {coros_only_count} 个这样的活动")
    coros_only_output.append("")
    
    for file in coros_only_files:
        coros_only_output.append(f"文件名: {file['filename']}")
        coros_only_output.append(f"日期时间: {file['datetime'].strftime('%Y-%m-%d %H:%M:%S')}")
        coros_only_output.append(f"活动类型: {file['sport_type']}")
        coros_only_output.append("")
    
    with open(REPORT_FILES['coros_only'], "w", encoding="utf-8") as f:
        for line in coros_only_output:
            f.write(line + "\n")


def _generate_garmin_only_report(garmin_files, coros_datetimes, result_folder):
    """生成佳明独有活动报告（佳明有而高驰没有，即待同步列表）"""
    garmin_only_output = []
    
    garmin_only_files = []
    for file in garmin_files:
        if file["datetime"] not in coros_datetimes:
            garmin_only_files.append(file)
    
    garmin_only_count = len(garmin_only_files)
    garmin_only_output.append(f"佳明有高驰没有的活动名单：")
    garmin_only_output.append(f"总共有 {garmin_only_count} 个这样的活动")
    garmin_only_output.append("")
    
    for file in garmin_only_files:
        garmin_only_output.append(f"文件名: {file['filename']}")
        garmin_only_output.append(f"日期时间: {file['datetime'].strftime('%Y-%m-%d %H:%M:%S')}")
        garmin_only_output.append(f"活动类型: {file['sport_type']}")
        garmin_only_output.append("")
    
    with open(REPORT_FILES['garmin_only'], "w", encoding="utf-8") as f:
        for line in garmin_only_output:
            f.write(line + "\n")


def _generate_analysis_report(garmin_files, coros_files, duplicates, result_folder):
    """生成分析摘要报告（文件数 / 匹配数 / 类型分布统计）"""
    output = []
    output.append("="*50)
    output.append("活动文件分析报告")
    output.append("="*50)
    
    output.append(f"\n【文件统计】")
    output.append(f"佳明下载文件数: {len(garmin_files)}")
    output.append(f"高驰下载文件数: {len(coros_files)}")
    
    garmin_matched = set()
    coros_matched = set()
    mismatched_count = 0
    for garmin_file, coros_file in duplicates:
        garmin_matched.add(garmin_file['filename'])
        coros_matched.add(coros_file['filename'])
        if garmin_file['sport_type'] != coros_file['sport_type']:
            mismatched_count += 1
    
    garmin_unmatched_count = len(garmin_files) - len(garmin_matched)
    coros_unmatched_count = len(coros_files) - len(coros_matched)
    
    output.append(f"\n【匹配统计】")
    output.append(f"佳明和高驰匹配文件: {len(duplicates)} 对")
    output.append(f"  - 类型匹配: {len(duplicates) - mismatched_count} 对")
    output.append(f"  - 类型不匹配: {mismatched_count} 对")
    output.append(f"佳明未匹配文件: {garmin_unmatched_count} 个")
    output.append(f"高驰未匹配文件: {coros_unmatched_count} 个")
    
    garmin_type_count = {}
    for file in garmin_files:
        sport_type = file["sport_type"]
        garmin_type_count[sport_type] = garmin_type_count.get(sport_type, 0) + 1
    
    output.append(f"\n【佳明活动类型分布】")
    for sport_type, count in sorted(garmin_type_count.items(), key=lambda x: x[1], reverse=True):
        output.append(f"  {sport_type}: {count}")
    
    coros_type_count = {}
    for file in coros_files:
        sport_type = file["sport_type"]
        coros_type_count[sport_type] = coros_type_count.get(sport_type, 0) + 1
    
    output.append(f"\n【高驰活动类型分布】")
    for sport_type, count in sorted(coros_type_count.items(), key=lambda x: x[1], reverse=True):
        output.append(f"  {sport_type}: {count}")
    
    with open(REPORT_FILES['analysis'], "w", encoding="utf-8") as f:
        for line in output:
            f.write(line + "\n")
    
    print(f"\n分析完成！结果已保存到 {result_folder} 目录")
