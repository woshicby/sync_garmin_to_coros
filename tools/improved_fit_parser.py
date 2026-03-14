#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FIT 文件解析工具

本模块提供了FIT文件解析功能，主要用于从Garmin和Coros设备生成的FIT活动文件中提取时间戳信息。

主要功能：
- 将FIT时间戳转换为标准datetime对象
- 扫描二进制数据中的时间戳候选值
- 分析FIT文件并提取关键时间信息
- 比较不同来源FIT文件的时间戳差异
"""

import os
import struct
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DIRS

FIT_EPOCH = datetime(1989, 12, 31, 0, 0, 0)


def fit_timestamp_to_datetime(timestamp):
    """将FIT格式的时间戳转换为Python datetime对象
    
    Args:
        timestamp: FIT格式的时间戳（秒数）
        
    Returns:
        datetime or None: 转换后的datetime对象，如果时间戳无效则返回None
    """
    if timestamp == 0 or timestamp > 2**32 - 1:
        return None
    return FIT_EPOCH + timedelta(seconds=timestamp)


def find_timestamp_candidates(data):
    """在二进制数据中查找可能的FIT时间戳值
    
    Args:
        data: 要扫描的二进制数据
        
    Returns:
        list: 包含(time_pos, timestamp, datetime_obj)元组的列表，按时间排序
    """
    candidates = []
    
    min_timestamp = (datetime(2000, 1, 1) - FIT_EPOCH).total_seconds()
    max_timestamp = (datetime(2030, 1, 1) - FIT_EPOCH).total_seconds()
    
    for i in range(len(data) - 3):
        try:
            timestamp = struct.unpack_from('<I', data, i)[0]
            
            if min_timestamp <= timestamp <= max_timestamp:
                dt = fit_timestamp_to_datetime(timestamp)
                if dt:
                    candidates.append((i, timestamp, dt))
        except:
            pass
    
    candidates.sort(key=lambda x: x[2])
    return candidates


def analyze_fit_file(file_path):
    """分析FIT文件，提取可能的时间戳信息和活动时间范围
    
    Args:
        file_path: FIT文件的路径
        
    Returns:
        dict: 包含文件分析结果的字典
    """
    result = {
        'file_path': file_path,
        'file_size': os.path.getsize(file_path),
        'timestamp_candidates': [],
        'first_valid_timestamp': None,
        'last_valid_timestamp': None,
        'likely_start_time': None,
        'likely_end_time': None
    }
    
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
            
            if b'.FIT' not in data[:30]:
                print(f"警告: {file_path} 可能不是有效的FIT文件")
                return result
            
            result['timestamp_candidates'] = find_timestamp_candidates(data)
            
            if result['timestamp_candidates']:
                first_timestamps = result['timestamp_candidates'][:5]
                last_timestamps = result['timestamp_candidates'][-5:]
                
                result['first_valid_timestamp'] = first_timestamps[0][2]
                result['last_valid_timestamp'] = last_timestamps[-1][2]
                
                file_name = os.path.basename(file_path)
                print(f"文件名: {file_name}")
                
                try:
                    date_part = file_name.split('-')[0]
                    time_part = file_name.split('-')[1]
                    
                    if len(date_part) == 8 and len(time_part) == 6:
                        file_datetime = datetime.strptime(date_part + time_part, '%Y%m%d%H%M%S')
                        print(f"从文件名解析的时间: {file_datetime}")
                        
                        closest_timestamp = None
                        min_diff = None
                        
                        for i, ts, dt in result['timestamp_candidates']:
                            diff = abs((dt - file_datetime).total_seconds())
                            if min_diff is None or diff < min_diff:
                                min_diff = diff
                                closest_timestamp = dt
                        
                        if closest_timestamp:
                            print(f"最接近文件名时间的时间戳: {closest_timestamp} (差异: {min_diff}秒)")
                            result['likely_start_time'] = closest_timestamp
                except Exception as e:
                    print(f"从文件名解析时间失败: {e}")
                    result['likely_start_time'] = result['first_valid_timestamp']
                    result['likely_end_time'] = result['last_valid_timestamp']
                
                print(f"找到 {len(result['timestamp_candidates'])} 个有效时间戳候选")
                print("前5个时间戳:")
                for i, (pos, ts, dt) in enumerate(first_timestamps[:5]):
                    print(f"  {i+1}. 位置: {pos}, 时间戳: {ts}, 时间: {dt}")
                
                print("后5个时间戳:")
                for i, (pos, ts, dt) in enumerate(last_timestamps[:5]):
                    print(f"  {i+1}. 位置: {pos}, 时间戳: {ts}, 时间: {dt}")
            else:
                print("未找到有效的时间戳")
                
    except Exception as e:
        print(f"读取文件时出错: {str(e)}")
    
    return result


def compare_files():
    """比较两个FIT文件（Garmin和Coros）的时间戳信息"""
    coros_file = "20240711-200746-indoor_cardio-461899280647487495.fit"
    garmin_file = "20240711-200700-strength_training-核心力量训练-391040389.fit"
    
    coros_path = os.path.join(DIRS['coros_downloads'], coros_file)
    garmin_path = os.path.join(DIRS['garmin_downloads'], garmin_file)
    
    print("=== 分析高驰FIT文件 ===")
    coros_result = analyze_fit_file(coros_path)
    
    print("\n=== 分析佳明FIT文件 ===")
    garmin_result = analyze_fit_file(garmin_path)
    
    print("\n=== 时间戳比较结果 ===")
    
    if coros_result['likely_start_time'] and garmin_result['likely_start_time']:
        print(f"高驰文件可能的开始时间: {coros_result['likely_start_time']}")
        print(f"佳明文件可能的开始时间: {garmin_result['likely_start_time']}")
        time_diff = abs(coros_result['likely_start_time'] - garmin_result['likely_start_time'])
        print(f"开始时间差异: {time_diff}")
    else:
        print("无法确定两个文件的开始时间")
    
    print("\n=== 所有有效时间戳的范围 ===")
    print(f"高驰文件 - 第一个时间戳: {coros_result['first_valid_timestamp']}")
    print(f"高驰文件 - 最后一个时间戳: {coros_result['last_valid_timestamp']}")
    print(f"佳明文件 - 第一个时间戳: {garmin_result['first_valid_timestamp']}")
    print(f"佳明文件 - 最后一个时间戳: {garmin_result['last_valid_timestamp']}")
    
    print(f"\n高驰文件找到 {len(coros_result['timestamp_candidates'])} 个时间戳候选")
    print(f"佳明文件找到 {len(garmin_result['timestamp_candidates'])} 个时间戳候选")
    
    if len(coros_result['timestamp_candidates']) > 0 and len(garmin_result['timestamp_candidates']) > 0:
        coros_timestamps = [ts for _, ts, _ in coros_result['timestamp_candidates'][:10]]
        garmin_timestamps = [ts for _, ts, _ in garmin_result['timestamp_candidates'][:10]]
        
        if coros_timestamps == garmin_timestamps:
            print("\n两个文件的前10个时间戳值完全相同！")
        else:
            print("\n两个文件的时间戳值存在差异")
    
    try:
        coros_name = os.path.basename(coros_path)
        garmin_name = os.path.basename(garmin_path)
        
        coros_date = coros_name.split('-')[0]
        coros_time = coros_name.split('-')[1]
        coros_dt = datetime.strptime(coros_date + coros_time, '%Y%m%d%H%M%S')
        
        garmin_date = garmin_name.split('-')[0]
        garmin_time = garmin_name.split('-')[1]
        garmin_dt = datetime.strptime(garmin_date + garmin_time, '%Y%m%d%H%M%S')
        
        print(f"\n=== 文件名中的时间比较 ===")
        print(f"高驰文件名时间: {coros_dt}")
        print(f"佳明文件名时间: {garmin_dt}")
        name_time_diff = abs(coros_dt - garmin_dt)
        print(f"文件名时间差异: {name_time_diff}")
        
    except Exception as e:
        print(f"从文件名提取时间失败: {e}")


if __name__ == "__main__":
    compare_files()
