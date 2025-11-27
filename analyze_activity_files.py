#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_activity_files.py

本模块提供了Garmin和Coros活动文件的全面分析功能，支持以下核心功能：

主要功能：
- 加载和管理活动白名单，用于筛选和标记活动
- 分析FIT格式的活动文件元数据，提取关键信息（时间、类型、设备等）
- 识别和标记重复的活动
- 生成详细的活动统计报告（按日期、类型、设备等维度）
- 添加walking类型活动到白名单
- 检测高驰活动类型异常

使用场景：
- 活动数据的批量管理和整理
- 跨设备（Garmin和Coros）活动数据的比较和同步
- 活动历史的统计分析和趋势观察
- 重复活动的检测和清理

依赖模块：
- os: 文件和目录操作
- re: 正则表达式操作
- datetime: 日期和时间处理
- json: JSON数据处理
"""

import os
import re
import datetime
import json

def load_whitelist():
    """加载白名单配置，返回佳明和高驰的活动白名单
    
    从配置文件中读取白名单，支持佳明和高驰两种设备的文件配置。
    文件格式每行可包含一个或多个.fit文件，第一个被视为佳明文件，
    其余被视为对应的高驰文件。支持#开头的注释行。
    
    Returns:
        dict: 包含'garmin'和'coros'两个键的字典，每个键对应一个文件名集合
    """
    whitelist = {
        'garmin': set(),
        'coros': set()
    }
    whitelist_path = os.path.join('config', 'sync_whitelist.txt')
    if os.path.exists(whitelist_path):
        try:
            with open(whitelist_path, 'r', encoding='utf-8') as f:
                for line in f:
                    # 跳过注释行和空行
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 处理格式，提取所有.fit结尾的文件名
                        if '.fit' in line:
                            words = line.split()
                            fit_files = []
                            # 收集所有.fit结尾的文件名
                            for word in words:
                                if word.endswith('.fit'):
                                    fit_files.append(word)
                            
                            # 处理收集到的.fit文件
                            if fit_files:
                                # 第一个作为佳明文件名
                                whitelist['garmin'].add(fit_files[0])
                                # 其余的作为高驰文件名（可能有多个，但通常只有一个或没有）
                                for coros_filename in fit_files[1:]:
                                    whitelist['coros'].add(coros_filename)
            total_entries = len(whitelist['garmin']) + len(whitelist['coros'])
            print(f"已加载白名单配置，佳明白名单 {len(whitelist['garmin'])} 项，高驰白名单 {len(whitelist['coros'])} 项，总共 {total_entries} 个跳过项")
        except Exception as e:
            print(f"加载白名单配置失败: {str(e)}")
    return whitelist

def add_to_whitelist(filename, is_garmin=True):
    """将指定的活动文件添加到白名单中
    
    将给定的文件名添加到同步白名单配置文件中。如果文件不存在，
    会创建新文件并添加适当的注释说明。如果文件已存在，会检查是否
    已有walking类型注释区域，如果没有则添加，然后将文件插入到
    适当位置。
    
    Args:
        filename (str): 要添加到白名单的文件名
        is_garmin (bool): 是否为佳明文件，默认为True
    """
    whitelist_path = os.path.join('config', 'sync_whitelist.txt')
    
    # 首先检查文件是否已存在
    existing_entries = set()
    if os.path.exists(whitelist_path):
        try:
            with open(whitelist_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 提取文件名并添加到集合中进行去重检查
                        if '.fit' in line:
                            words = line.split()
                            for word in words:
                                if word.endswith('.fit'):
                                    existing_entries.add(word)
                                    break
        except Exception as e:
            print(f"读取白名单文件失败: {str(e)}")
    
    # 检查文件名是否已经在白名单中
    if filename in existing_entries:
        return  # 文件已存在，不重复添加
    
    # 检查并确保有walking类型注释
    has_walking_comment = False
    walking_section_start = -1
    if os.path.exists(whitelist_path):
        with open(whitelist_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if '# walking类型文件' in line:
                    has_walking_comment = True
                    walking_section_start = i
                    break
    
    # 追加或插入walking文件
    try:
        if not os.path.exists(whitelist_path):
            # 文件不存在，创建新文件
            with open(whitelist_path, 'w', encoding='utf-8') as f:
                f.write('# 同步白名单配置\n')
                f.write('# 格式：佳明活动文件名 高驰活动文件名\n')
                f.write('# 或者：佳明活动文件名 \n')
                f.write('# 格式：佳明活动文件名 \n')
                f.write('# 高驰导入失败的文件\n')
                f.write('# walking类型文件\n')
                f.write(filename + '\n')
        else:
            # 文件存在，需要追加或插入
            if not has_walking_comment:
                # 没有walking类型注释，直接追加
                with open(whitelist_path, 'a', encoding='utf-8') as f:
                    f.write('\n# walking类型文件\n')
                    f.write(filename + '\n')
            else:
                # 有walking类型注释，读取文件后插入到walking部分之后
                with open(whitelist_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # 找到walking部分的结束位置
                walking_end = walking_section_start
                for i in range(walking_section_start + 1, len(lines)):
                    # 如果遇到新的注释行或文件末尾，则结束
                    if lines[i].strip().startswith('#') or not lines[i].strip():
                        walking_end = i
                        break
                else:
                    # 如果没有遇到新的注释，则在文件末尾添加
                    walking_end = len(lines)
                
                # 在walking部分末尾插入新的文件名
                lines.insert(walking_end, filename + '\n')
                
                # 写回文件
                with open(whitelist_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
        
        print(f"已将 {filename} 添加到白名单")
    except Exception as e:
        print(f"添加文件到白名单失败: {str(e)}")

def get_garmin_files_info():
    """获取佳明下载文件的信息
    
    扫描佳明下载目录中的所有.fit文件，解析文件名提取活动信息，
    包括日期时间、活动类型、活动名称和活动ID。
    
    Returns:
        list: 包含佳明活动文件信息的字典列表，每个字典包含文件名、
              datetime对象、活动类型、活动名称和活动ID
    """
    # 使用相对路径，相对于项目根目录
    garmin_dir = "downloads\garmin"
    garmin_files = []
    
    if not os.path.exists(garmin_dir):
        return garmin_files
    
    for filename in os.listdir(garmin_dir):
        if filename.endswith(".fit"):
            # 解析佳明文件名格式：日期-时间-活动类型-活动名称-活动ID.fit
            match = re.match(r"^(\d{8})-(\d{6})-(\w+)-(.*)-(\d+)\.fit$", filename)
            if match:
                date_str = match.group(1)
                time_str = match.group(2)
                sport_type = match.group(3)
                activity_name = match.group(4)
                activity_id = match.group(5)
                
                # 转换为datetime对象
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

def get_coros_files_info():
    """获取高驰下载文件的信息
    
    扫描高驰下载目录中的所有.fit文件，解析文件名提取活动信息，
    包括日期时间、活动类型和活动ID。
    
    Returns:
        list: 包含高驰活动文件信息的字典列表，每个字典包含文件名、
              datetime对象、活动类型和活动ID
    """
    # 使用相对路径，相对于项目根目录
    coros_dir = "downloads\coros"
    coros_files = []
    
    if not os.path.exists(coros_dir):
        return coros_files
    
    for filename in os.listdir(coros_dir):
        if filename.endswith(".fit"):
            # 解析高驰文件名格式：日期-时间-活动类型-活动ID.fit
            match = re.match(r"^(\d{8})-(\d{6})-(\w+)-(\d+)\.fit$", filename)
            if match:
                date_str = match.group(1)
                time_str = match.group(2)
                sport_type = match.group(3)
                activity_id = match.group(4)
                
                # 转换为datetime对象
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

def find_duplicate_activities(garmin_files, coros_files):
    """根据日期和时间查找重复活动
    
    通过比较活动的日期和时间，识别在佳明和高驰设备上记录的相同活动。
    创建佳明活动的datetime映射，然后遍历高驰活动进行匹配。
    
    Args:
        garmin_files (list): 佳明活动文件信息列表
        coros_files (list): 高驰活动文件信息列表
        
    Returns:
        list: 重复活动对的列表，每个元素是一个包含(garmin_file, coros_file)的元组
    """
    duplicates = []
    
    # 创建佳明活动的datetime映射
    garmin_datetime_map = {file["datetime"]: file for file in garmin_files}
    
    for coros_file in coros_files:
        coros_dt = coros_file["datetime"]
        if coros_dt in garmin_datetime_map:
            garmin_file = garmin_datetime_map[coros_dt]
            duplicates.append((garmin_file, coros_file))
    
    return duplicates

def check_coros_sport_types(coros_files):
    """
    检查高驰活动类型是否存在异常
    
    功能：
        识别可能存在命名问题的高驰活动类型，帮助发现异常数据
    
    参数：
        coros_files (list): 高驰活动文件信息列表，每个元素为包含活动信息的字典
    
    返回：
        list: 包含异常活动类型的文件信息列表
    
    判定逻辑：
        - 正常活动类型："running", "walking", "cycling", "hiking", "yoga"
        - 也接受以"type_"开头的活动类型
        - 其他类型被视为异常
    """
    # 定义已知的正常活动类型集合
    normal_sport_types = {"running", "walking", "cycling", "hiking", "yoga"}
    abnormal_files = []
    
    # 遍历所有高驰文件，检查活动类型
    for file in coros_files:
        sport_type = file["sport_type"]
        # 检查是否为异常类型（不是正常类型且不以type_开头）
        if not sport_type.startswith("type_") and sport_type not in normal_sport_types:
            abnormal_files.append(file)
    
    return abnormal_files

def get_coros_activity_samples():
    """
    获取高驰活动样本数据
    
    功能：
        从activity_sample.json文件中读取并返回高驰活动的样本数据，
        用于分析和参考高驰活动的数据结构和格式
    
    返回：
        dict or None: 如果文件存在，返回解析后的JSON数据（字典格式）;
                     如果文件不存在，返回None
    
    数据用途：
        样本数据通常用于测试解析函数、分析高驰API返回的数据格式，
        以及调试与高驰活动数据相关的功能
    """
    # 检查样本数据文件是否存在
    if os.path.exists("activity_sample.json"):
        # 以UTF-8编码打开并读取JSON文件
        with open("activity_sample.json", "r", encoding="utf-8") as f:
            # 解析JSON数据并返回
            return json.load(f)
    # 如果文件不存在，返回None
    return None

def main():
    """活动文件分析主函数
    
    执行以下主要功能:
    1. 创建分析结果文件夹
    2. 加载白名单配置
    3. 扫描并获取佳明和高驰活动文件信息
    4. 查找重复活动并识别活动类型不匹配情况
    5. 处理walking类型活动并添加到白名单
    6. 生成四个分析结果文件:
       - mismatched_activities.txt: 活动类型不匹配的文件名单
       - coros_only_activities.txt: 高驰独有活动名单
       - garmin_only_activities.txt: 佳明独有活动名单
       - analysis_result.txt: 总体分析报告
    """
    # 创建分析结果文件夹
    result_folder = "reports"
    if not os.path.exists(result_folder):
        os.makedirs(result_folder)
    
    # 加载白名单
    whitelist = load_whitelist()
    
    # 获取所有文件信息
    garmin_files = get_garmin_files_info()
    coros_files = get_coros_files_info()
    
    # 获取 datetime 集合用于判断活动是否存在
    garmin_datetimes = {file["datetime"] for file in garmin_files}
    coros_datetimes = {file["datetime"] for file in coros_files}
    
    # 查找重复活动
    duplicates = find_duplicate_activities(garmin_files, coros_files)
    
    # 生成四个结果文件
    
    # 1. 生成高驰和佳明活动不匹配的文件名单
    mismatched_output = []
    mismatched_count = len([(g, c) for g, c in duplicates if g['sport_type'] != c['sport_type']])
    mismatched_output.append(f"高驰和佳明活动类型不匹配的文件名单：")
    mismatched_output.append(f"总共有 {mismatched_count} 个不匹配的活动")
    mismatched_output.append("")
    
    # 遍历所有重复活动，筛选类型不匹配的活动
    if duplicates:
        for garmin_file, coros_file in duplicates:
            if garmin_file['sport_type'] != coros_file['sport_type']:
                mismatched_output.append(f"佳明文件: {garmin_file['filename']}")
                mismatched_output.append(f"高驰文件: {coros_file['filename']}")
                mismatched_output.append(f"佳明活动类型: {garmin_file['sport_type']}")
                mismatched_output.append(f"高驰活动类型: {coros_file['sport_type']}")
                mismatched_output.append("")
    
    # 写入不匹配活动报告文件
    with open(os.path.join(result_folder, "mismatched_activities.txt"), "w", encoding="utf-8") as f:
        for line in mismatched_output:
            f.write(line + "\n")
    
    # 2. 生成高驰有佳明没有的活动名单（排除白名单中的文件和walking类型）
    coros_only_output = []
    walking_count = 0
    
    # 计算不包含白名单且非walking类型的数量
    filtered_coros_files = []
    for file in coros_files:
        if file["datetime"] not in garmin_datetimes:
            if file["sport_type"] == "walking":
                # walking类型活动添加到白名单
                add_to_whitelist(file["filename"], is_garmin=False)
                walking_count += 1
            elif file["filename"] not in whitelist['coros']:
                filtered_coros_files.append(file)
    
    # 写入高驰独有活动统计信息
    coros_only_count = len(filtered_coros_files)
    coros_only_output.append(f"高驰有佳明没有的活动名单：")
    coros_only_output.append(f"总共有 {coros_only_count} 个这样的活动（{walking_count} 个walking类型活动已添加到白名单）")
    coros_only_output.append("")
    
    # 写入高驰独有活动详细信息
    for file in filtered_coros_files:
        coros_only_output.append(f"文件名: {file['filename']}")
        coros_only_output.append(f"日期时间: {file['datetime'].strftime('%Y-%m-%d %H:%M:%S')}")
        coros_only_output.append(f"活动类型: {file['sport_type']}")
        coros_only_output.append("")
    
    # 写入高驰独有活动报告文件
    with open(os.path.join(result_folder, "coros_only_activities.txt"), "w", encoding="utf-8") as f:
        for line in coros_only_output:
            f.write(line + "\n")
    
    # 3. 生成佳明有高驰没有的活动名单（排除白名单中的文件和walking类型）
    garmin_only_output = []
    walking_count = 0
    
    # 计算不包含白名单且非walking类型的数量
    filtered_garmin_files = []
    for file in garmin_files:
        if file["datetime"] not in coros_datetimes:
            if file["sport_type"] == "walking":
                # walking类型活动添加到白名单
                add_to_whitelist(file["filename"], is_garmin=True)
                walking_count += 1
            elif file["filename"] not in whitelist['garmin']:
                filtered_garmin_files.append(file)
    
    # 写入佳明独有活动统计信息
    garmin_only_count = len(filtered_garmin_files)
    garmin_only_output.append(f"佳明有高驰没有的活动名单：")
    garmin_only_output.append(f"总共有 {garmin_only_count} 个这样的活动（{walking_count} 个walking类型活动已添加到白名单）")
    garmin_only_output.append("")
    
    # 写入佳明独有活动详细信息
    for file in filtered_garmin_files:
        garmin_only_output.append(f"文件名: {file['filename']}")
        garmin_only_output.append(f"日期时间: {file['datetime'].strftime('%Y-%m-%d %H:%M:%S')}")
        garmin_only_output.append(f"活动类型: {file['sport_type']}")
        garmin_only_output.append("")
    
    # 写入佳明独有活动报告文件
    with open(os.path.join(result_folder, "garmin_only_activities.txt"), "w", encoding="utf-8") as f:
        for line in garmin_only_output:
            f.write(line + "\n")
    
    # 4. 生成综合分析结果报告
    output = []
    output.append("正在分析佳明和高驰的活动文件...")
    output.append(f"\n佳明下载文件数: {len(garmin_files)}")
    output.append(f"高驰下载文件数: {len(coros_files)}")
    
    # 添加不匹配和独有活动统计
    output.append(f"\n高驰和佳明活动类型不匹配: {mismatched_count}")
    output.append(f"高驰有佳明没有: {coros_only_count}")
    output.append(f"佳明有高驰没有: {garmin_only_count}")
    
    # 检查高驰活动类型异常
    abnormal_files = check_coros_sport_types(coros_files)
    if abnormal_files:
        output.append(f"\n找到 {len(abnormal_files)} 个高驰活动类型异常文件")
    else:
        output.append(f"\n所有高驰活动类型正常")
    
    # 统计高驰活动类型分布
    output.append("\n高驰活动类型分布：")
    sport_type_count = {}
    for file in coros_files:
        sport_type = file["sport_type"]
        sport_type_count[sport_type] = sport_type_count.get(sport_type, 0) + 1
    
    # 按活动类型排序输出统计信息
    for sport_type, count in sorted(sport_type_count.items()):
        output.append(f"  {sport_type}: {count}")
    
    # 添加完成信息和结果文件说明
    output.append("\n分析完成！")
    output.append(f"\n详细结果已保存到：")
    output.append(f"  - mismatched_activities.txt: 高驰和佳明活动不匹配的文件名单")
    output.append(f"  - coros_only_activities.txt: 高驰有佳明没有的活动名单")
    output.append(f"  - garmin_only_activities.txt: 佳明有高驰没有的活动名单")
    
    # 写入综合分析报告文件
    with open(os.path.join(result_folder, "analysis_result.txt"), "w", encoding="utf-8") as f:
        for line in output:
            if line is not None:
                f.write(str(line) + "\n")
    
    # 输出分析完成信息到控制台
    print(f"分析结果已保存到 {os.path.join(result_folder, 'analysis_result.txt')} 文件中")
    print(f"三个详细结果文件已生成在 {result_folder} 文件夹中")
def analyze_main():
    """分析模块的入口函数，被主程序调用
    
    此函数是为了与主程序的调用约定保持一致，直接调用main函数。
    """
    main()


if __name__ == "__main__":
    # 模块独立运行时的入口点
    main()