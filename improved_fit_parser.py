import os
import struct
from datetime import datetime, timedelta

"""
improved_fit_parser.py

本模块提供了FIT文件解析功能，主要用于从Garmin和Coros设备生成的FIT活动文件中提取时间戳信息。

主要功能：
- 将FIT时间戳转换为标准datetime对象
- 扫描二进制数据中的时间戳候选值
- 分析FIT文件并提取关键时间信息
- 比较不同来源FIT文件的时间戳差异

依赖模块：
- os: 文件操作相关功能
- struct: 用于解析二进制数据
- datetime: 时间处理功能
"""

# FIT文件的基础时间纪元（基准时间点）
# FIT文件格式使用1989年12月31日作为时间戳计算的起点
FIT_EPOCH = datetime(1989, 12, 31, 0, 0, 0)

def fit_timestamp_to_datetime(timestamp):
    """
    将FIT格式的时间戳转换为Python datetime对象
    
    参数:
        timestamp (int): FIT格式的时间戳（秒数）
    
    返回:
        datetime or None: 转换后的datetime对象，如果时间戳无效则返回None
    
    说明:
        FIT格式使用自1989年12月31日以来的秒数作为时间戳
    """
    # 检查时间戳是否有效（非零且不超过32位无符号整数最大值）
    if timestamp == 0 or timestamp > 2**32 - 1:
        return None
    # 将秒数转换为datetime对象
    return FIT_EPOCH + timedelta(seconds=timestamp)

def find_timestamp_candidates(data):
    """
    在二进制数据中查找可能的FIT时间戳值
    
    参数:
        data (bytes): 要扫描的二进制数据
    
    返回:
        list: 包含(time_pos, timestamp, datetime_obj)元组的列表，按时间排序
    
    处理逻辑:
        1. 定义合理的时间戳范围（2000-2030年）
        2. 扫描所有可能的4字节序列
        3. 尝试解析为小端序4字节无符号整数
        4. 验证时间戳是否在合理范围内
        5. 将有效时间戳转换为datetime对象并存储
        6. 按时间顺序排序结果
    """
    candidates = []
    
    # 定义合理的时间戳范围（2000-2030年对应的FIT时间戳值）
    min_timestamp = (datetime(2000, 1, 1) - FIT_EPOCH).total_seconds()
    max_timestamp = (datetime(2030, 1, 1) - FIT_EPOCH).total_seconds()
    
    # 扫描所有可能的4字节序列（时间戳通常为4字节）
    for i in range(len(data) - 3):
        try:
            # 尝试解析为小端序4字节无符号整数（FIT格式使用小端序）
            timestamp = struct.unpack_from('<I', data, i)[0]
            
            # 检查是否在合理的时间范围内
            if min_timestamp <= timestamp <= max_timestamp:
                dt = fit_timestamp_to_datetime(timestamp)
                if dt:
                    # 存储位置、原始时间戳和转换后的datetime对象
                    candidates.append((i, timestamp, dt))
        except:
            # 忽略解析错误，继续扫描
            pass
    
    # 按datetime对象排序，便于后续分析时间序列
    candidates.sort(key=lambda x: x[2])
    return candidates

def analyze_fit_file(file_path):
    """
    分析FIT文件，提取可能的时间戳信息和活动时间范围
    
    参数:
        file_path (str): FIT文件的路径
    
    返回:
        dict: 包含文件分析结果的字典，包括:
            - file_path: 文件路径
            - file_size: 文件大小
            - timestamp_candidates: 找到的时间戳候选列表
            - first_valid_timestamp: 第一个有效时间戳
            - last_valid_timestamp: 最后一个有效时间戳
            - likely_start_time: 可能的活动开始时间
            - likely_end_time: 可能的活动结束时间
    
    处理步骤:
        1. 初始化结果字典
        2. 验证文件是否为FIT格式（检查.FIT标记）
        3. 扫描文件中的所有可能时间戳
        4. 分析时间戳分布，确定活动时间范围
        5. 尝试从文件名提取时间信息作为参考
        6. 计算最可能的活动开始和结束时间
    """
    # 初始化结果字典，存储文件分析信息
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
        # 以二进制模式打开文件
        with open(file_path, 'rb') as f:
            # 读取整个文件内容
            data = f.read()
            
            # 验证是否为FIT文件（检查文件头部的.FIT标记）
            if b'.FIT' not in data[:30]:
                print(f"警告: {file_path} 可能不是有效的FIT文件")
                return result
            
            # 查找文件中所有可能的时间戳候选值
            result['timestamp_candidates'] = find_timestamp_candidates(data)
            
            # 如果找到有效的时间戳候选
            if result['timestamp_candidates']:
                # 提取前5个时间戳（通常包含开始时间）
                first_timestamps = result['timestamp_candidates'][:5]
                # 提取后5个时间戳（通常包含结束时间）
                last_timestamps = result['timestamp_candidates'][-5:]
                
                # 记录第一个和最后一个有效时间戳
                result['first_valid_timestamp'] = first_timestamps[0][2]
                result['last_valid_timestamp'] = last_timestamps[-1][2]
                
                # 尝试从文件名提取时间信息（假设文件名格式为YYYYMMDD-HHMMSS-...）
                file_name = os.path.basename(file_path)
                print(f"文件名: {file_name}")
                
                try:
                    # 尝试解析文件名中的日期和时间部分
                    date_part = file_name.split('-')[0]
                    time_part = file_name.split('-')[1]
                    
                    # 验证格式是否符合预期（8位日期，6位时间）
                    if len(date_part) == 8 and len(time_part) == 6:
                        file_datetime = datetime.strptime(date_part + time_part, '%Y%m%d%H%M%S')
                        print(f"从文件名解析的时间: {file_datetime}")
                        
                        # 找到文件中最接近文件名时间的时间戳
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
                    # 如果无法从文件名解析时间，则使用第一个和最后一个时间戳
                    result['likely_start_time'] = result['first_valid_timestamp']
                    result['likely_end_time'] = result['last_valid_timestamp']
                
                # 打印时间戳分析结果
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
    """
    比较两个FIT文件（Garmin和Coros）的时间戳信息
    
    功能:
        - 分析并比较来自不同设备的FIT文件
        - 提取并比较文件中的时间戳信息
        - 确定两个文件的时间戳是否匹配
        - 计算时间差异，帮助判断文件的关联性
    
    注意:
        本函数使用硬编码的示例文件路径，实际使用时需要根据具体情况修改
    """
    # 定义示例文件路径
    coros_file = "downloads/coros/20240711-200746-indoor_cardio-461899280647487495.fit"
    garmin_file = "downloads/garmin/20240711-200700-strength_training-核心力量训练-391040389.fit"
    
    # 获取文件的绝对路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    coros_path = os.path.join(base_dir, coros_file)
    garmin_path = os.path.join(base_dir, garmin_file)
    
    # 分析高驰(Coros)的FIT文件
    print("=== 分析高驰FIT文件 ===")
    coros_result = analyze_fit_file(coros_path)
    
    # 分析佳明(Garmin)的FIT文件
    print("\n=== 分析佳明FIT文件 ===")
    garmin_result = analyze_fit_file(garmin_path)
    
    # 比较两个文件的时间戳
    print("\n=== 时间戳比较结果 ===")
    
    # 比较可能的开始时间
    if coros_result['likely_start_time'] and garmin_result['likely_start_time']:
        print(f"高驰文件可能的开始时间: {coros_result['likely_start_time']}")
        print(f"佳明文件可能的开始时间: {garmin_result['likely_start_time']}")
        # 计算时间差异
        time_diff = abs(coros_result['likely_start_time'] - garmin_result['likely_start_time'])
        print(f"开始时间差异: {time_diff}")
    else:
        print("无法确定两个文件的开始时间")
    
    # 比较第一个和最后一个有效时间戳
    print("\n=== 所有有效时间戳的范围 ===")
    print(f"高驰文件 - 第一个时间戳: {coros_result['first_valid_timestamp']}")
    print(f"高驰文件 - 最后一个时间戳: {coros_result['last_valid_timestamp']}")
    print(f"佳明文件 - 第一个时间戳: {garmin_result['first_valid_timestamp']}")
    print(f"佳明文件 - 最后一个时间戳: {garmin_result['last_valid_timestamp']}")
    
    # 比较找到的时间戳候选数量
    print(f"\n高驰文件找到 {len(coros_result['timestamp_candidates'])} 个时间戳候选")
    print(f"佳明文件找到 {len(garmin_result['timestamp_candidates'])} 个时间戳候选")
    
    # 检查两个文件的时间戳值是否相同
    if len(coros_result['timestamp_candidates']) > 0 and len(garmin_result['timestamp_candidates']) > 0:
        # 提取前10个时间戳的值进行比较
        coros_timestamps = [ts for _, ts, _ in coros_result['timestamp_candidates'][:10]]
        garmin_timestamps = [ts for _, ts, _ in garmin_result['timestamp_candidates'][:10]]
        
        # 比较时间戳序列是否一致
        if coros_timestamps == garmin_timestamps:
            print("\n两个文件的前10个时间戳值完全相同！")
        else:
            print("\n两个文件的时间戳值存在差异")
    
    # 从文件名中提取时间并进行比较
    try:
        coros_name = os.path.basename(coros_path)
        garmin_name = os.path.basename(garmin_path)
        
        # 从高驰文件名提取时间
        coros_date = coros_name.split('-')[0]
        coros_time = coros_name.split('-')[1]
        coros_dt = datetime.strptime(coros_date + coros_time, '%Y%m%d%H%M%S')
        
        # 从佳明文件名提取时间
        garmin_date = garmin_name.split('-')[0]
        garmin_time = garmin_name.split('-')[1]
        garmin_dt = datetime.strptime(garmin_date + garmin_time, '%Y%m%d%H%M%S')
        
        # 比较文件名中的时间
        print(f"\n=== 文件名中的时间比较 ===")
        print(f"高驰文件名时间: {coros_dt}")
        print(f"佳明文件名时间: {garmin_dt}")
        name_time_diff = abs(coros_dt - garmin_dt)
        print(f"文件名时间差异: {name_time_diff}")
        
    except Exception as e:
        print(f"从文件名提取时间失败: {e}")

if __name__ == "__main__":
    compare_files()