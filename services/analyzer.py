#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
活动分析服务

提供 Garmin 和 Coros 活动文件的对比分析功能。
"""

import os
import re
import datetime
import json

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    DIRS, CONFIG_FILES, REPORT_FILES, 
    AUTO_WHITELIST_TYPES, TYPE_COMMENTS, NORMAL_SPORT_TYPES
)


def analyze_activities():
    """分析活动文件，找出 Garmin 独有的活动"""
    result_folder = DIRS['reports']
    os.makedirs(result_folder, exist_ok=True)
    
    whitelist = _load_whitelist()
    
    garmin_files = _get_garmin_files_info()
    coros_files = _get_coros_files_info()
    
    garmin_datetimes = {file["datetime"]: file for file in garmin_files}
    coros_datetimes = {file["datetime"]: file for file in coros_files}
    
    duplicates = _find_duplicate_activities(garmin_files, coros_files)
    
    _generate_mismatched_report(duplicates, result_folder)
    _generate_coros_only_report(coros_files, garmin_datetimes, whitelist, result_folder)
    _generate_garmin_only_report(garmin_files, coros_datetimes, whitelist, result_folder)
    _generate_analysis_report(garmin_files, coros_files, duplicates, result_folder)


def _load_whitelist():
    """加载白名单配置"""
    whitelist = {'garmin': set(), 'coros': set()}
    whitelist_path = CONFIG_FILES['sync_whitelist']
    
    if os.path.exists(whitelist_path):
        try:
            with open(whitelist_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '.fit' in line:
                            words = line.split()
                            fit_files = [word for word in words if word.endswith('.fit')]
                            
                            if fit_files:
                                whitelist['garmin'].add(fit_files[0])
                                for coros_filename in fit_files[1:]:
                                    whitelist['coros'].add(coros_filename)
            
            total_entries = len(whitelist['garmin']) + len(whitelist['coros'])
            print(f"已加载白名单配置，佳明白名单 {len(whitelist['garmin'])} 项，高驰白名单 {len(whitelist['coros'])} 项，总共 {total_entries} 个跳过项")
        except Exception as e:
            print(f"加载白名单配置失败: {str(e)}")
    
    return whitelist


def _add_to_whitelist(filename):
    """将指定的活动文件添加到白名单中"""
    whitelist_path = CONFIG_FILES['sync_whitelist']
    
    existing_entries = set()
    if os.path.exists(whitelist_path):
        try:
            with open(whitelist_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '.fit' in line:
                            words = line.split()
                            for word in words:
                                if word.endswith('.fit'):
                                    existing_entries.add(word)
                                    break
        except Exception as e:
            print(f"读取白名单文件失败: {str(e)}")
    
    if filename in existing_entries:
        return
    
    sport_type = "other"
    match = re.match(r"^\d{8}-\d{6}-(\w+)-", filename)
    if match:
        sport_type = match.group(1)
    
    comment = TYPE_COMMENTS.get(sport_type, "# 其他类型文件")
    
    has_comment = False
    comment_section_start = -1
    if os.path.exists(whitelist_path):
        with open(whitelist_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if comment in line:
                    has_comment = True
                    comment_section_start = i
                    break
    
    try:
        if not os.path.exists(whitelist_path):
            os.makedirs(os.path.dirname(whitelist_path), exist_ok=True)
            with open(whitelist_path, 'w', encoding='utf-8') as f:
                f.write('# 同步白名单配置\n')
                f.write('# 格式：佳明活动文件名 高驰活动文件名\n')
                f.write('# 高驰导入失败的文件\n')
                f.write(comment + '\n')
                f.write(filename + '\n')
        else:
            if not has_comment:
                with open(whitelist_path, 'a', encoding='utf-8') as f:
                    f.write('\n' + comment + '\n')
                    f.write(filename + '\n')
            else:
                with open(whitelist_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                comment_end = comment_section_start
                for i in range(comment_section_start + 1, len(lines)):
                    if lines[i].strip().startswith('#') or not lines[i].strip():
                        comment_end = i
                        break
                else:
                    comment_end = len(lines)
                
                lines.insert(comment_end, filename + '\n')
                
                with open(whitelist_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
        
        print(f"已将 {filename} 添加到白名单")
    except Exception as e:
        print(f"添加文件到白名单失败: {str(e)}")


def _get_garmin_files_info():
    """获取佳明下载文件的信息"""
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
    """获取高驰下载文件的信息"""
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


def _find_duplicate_activities(garmin_files, coros_files):
    """根据日期和时间查找重复活动"""
    duplicates = []
    
    garmin_datetime_map = {file["datetime"]: file for file in garmin_files}
    
    for coros_file in coros_files:
        coros_dt = coros_file["datetime"]
        if coros_dt in garmin_datetime_map:
            garmin_file = garmin_datetime_map[coros_dt]
            duplicates.append((garmin_file, coros_file))
    
    return duplicates


def _generate_mismatched_report(duplicates, result_folder):
    """生成活动类型不匹配报告"""
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


def _generate_coros_only_report(coros_files, garmin_datetimes, whitelist, result_folder):
    """生成高驰独有活动报告"""
    coros_only_output = []
    walking_count = 0
    
    filtered_coros_files = []
    for file in coros_files:
        if file["datetime"] not in garmin_datetimes:
            if file["sport_type"] == "walking":
                _add_to_whitelist(file["filename"])
                walking_count += 1
            elif file["filename"] not in whitelist['coros']:
                filtered_coros_files.append(file)
    
    coros_only_count = len(filtered_coros_files)
    coros_only_output.append(f"高驰有佳明没有的活动名单：")
    coros_only_output.append(f"总共有 {coros_only_count} 个这样的活动（{walking_count} 个walking类型活动已添加到白名单）")
    coros_only_output.append("")
    
    for file in filtered_coros_files:
        coros_only_output.append(f"文件名: {file['filename']}")
        coros_only_output.append(f"日期时间: {file['datetime'].strftime('%Y-%m-%d %H:%M:%S')}")
        coros_only_output.append(f"活动类型: {file['sport_type']}")
        coros_only_output.append("")
    
    with open(REPORT_FILES['coros_only'], "w", encoding="utf-8") as f:
        for line in coros_only_output:
            f.write(line + "\n")


def _generate_garmin_only_report(garmin_files, coros_datetimes, whitelist, result_folder):
    """生成佳明独有活动报告"""
    garmin_only_output = []
    walking_count = 0
    indoor_climbing_count = 0
    bouldering_count = 0
    
    filtered_garmin_files = []
    for file in garmin_files:
        if file["datetime"] not in coros_datetimes:
            if file["sport_type"] in AUTO_WHITELIST_TYPES:
                _add_to_whitelist(file["filename"])
                if file["sport_type"] == "walking":
                    walking_count += 1
                elif file["sport_type"] == "indoor_climbing":
                    indoor_climbing_count += 1
                elif file["sport_type"] == "bouldering":
                    bouldering_count += 1
            elif file["filename"] not in whitelist['garmin']:
                filtered_garmin_files.append(file)
    
    garmin_only_count = len(filtered_garmin_files)
    garmin_only_output.append(f"佳明有高驰没有的活动名单：")
    garmin_only_output.append(f"总共有 {garmin_only_count} 个这样的活动（{walking_count} 个walking、{indoor_climbing_count} 个indoor_climbing、{bouldering_count} 个bouldering类型活动已添加到白名单）")
    garmin_only_output.append("")
    
    for file in filtered_garmin_files:
        garmin_only_output.append(f"文件名: {file['filename']}")
        garmin_only_output.append(f"日期时间: {file['datetime'].strftime('%Y-%m-%d %H:%M:%S')}")
        garmin_only_output.append(f"活动类型: {file['sport_type']}")
        garmin_only_output.append("")
    
    with open(REPORT_FILES['garmin_only'], "w", encoding="utf-8") as f:
        for line in garmin_only_output:
            f.write(line + "\n")


def _generate_analysis_report(garmin_files, coros_files, duplicates, result_folder):
    """生成综合分析报告"""
    output = []
    output.append("正在分析佳明和高驰的活动文件...")
    output.append(f"\n佳明下载文件数: {len(garmin_files)}")
    output.append(f"高驰下载文件数: {len(coros_files)}")
    
    mismatched_count = len([(g, c) for g, c in duplicates if g['sport_type'] != c['sport_type']])
    output.append(f"\n高驰和佳明活动类型不匹配: {mismatched_count}")
    
    abnormal_files = [f for f in coros_files 
                     if not f["sport_type"].startswith("type_") 
                     and f["sport_type"] not in NORMAL_SPORT_TYPES]
    
    if abnormal_files:
        output.append(f"\n找到 {len(abnormal_files)} 个高驰活动类型异常文件")
    else:
        output.append(f"\n所有高驰活动类型正常")
    
    output.append("\n高驰活动类型分布：")
    sport_type_count = {}
    for file in coros_files:
        sport_type = file["sport_type"]
        sport_type_count[sport_type] = sport_type_count.get(sport_type, 0) + 1
    
    for sport_type, count in sorted(sport_type_count.items(), key=lambda x: x[1], reverse=True):
        output.append(f"  {sport_type}: {count}")
    
    with open(REPORT_FILES['analysis'], "w", encoding="utf-8") as f:
        for line in output:
            f.write(line + "\n")
    
    print(f"\n分析完成！结果已保存到 {result_folder} 目录")
