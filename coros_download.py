import time
import json
import logging
import base64
import binascii
import re
import os
import zipfile
import io
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from coros_client import login_coros, CorosClient, CorosLoginError

# 设置日志级别为DEBUG
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Coros sportType 到 Garmin activityType 的映射
# Coros sportType 到 Garmin activityType 的映射
sport_type_mapping = {
    100: "running",
    101: "treadmill_running",
    104: "hiking",
    200: "cycling",  # roal_biking也是200
    300: "swimming",
    400: "walking",
    402: "indoor_cardio",  # breathwork也是402
    500: "hiking",
    600: "strength_training",
    700: "yoga",
    800: "rowing",
    900: "elliptical",
    1000: "other",
    10001: "multi_sport", 
}

def get_activity_type(sport_type):
    """将 Coros 运动类型转换为与 Garmin 一致的名称"""
    return sport_type_mapping.get(sport_type, "other")


# 配置相关函数已从coros_client导入，不再需要自己实现



# 配置相关函数已从coros_client导入，不再需要自己实现



# login_coros函数已从coros_client导入，不再需要自己实现



def download_all_fit_files(client, download_folder):
    """
    下载所有fit文件
    """
    try:
        # 确保客户端已登录
        client._check_token()
        
        # 创建下载目录
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)
            print(f"创建目录: {download_folder}")

        # 获取所有活动
        print("开始获取所有活动...")
        activities = []
        size = 200
        page = 1
        
        while True:
            # 获取活动列表
            activity_url = f"{client.teamapi}/activity/query?size={size}&pageNumber={page}"
            
            # 使用CorosClient的req属性发送请求（urllib3）
            headers = {
                "Accept": "application/json, text/plain, */*",
                "accesstoken": client.access_token,
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.39 Safari/537.36",
            }
            
            response = client.req.request('GET', activity_url, headers=headers)
            result = json.loads(response.data)
            
            if result['result'] != '0000':
                print(f"获取活动列表失败: {result['message']}")
                return False
            
            page_result = result['data']
            activities.extend(page_result['dataList'])
            
            total_page = page_result['totalPage']
            if page >= total_page:
                break
            
            page += 1
            time.sleep(0.5)  # 避免请求过快

        if not activities:
            print("未找到任何活动")
            return True
        
        print(f"共找到 {len(activities)} 个活动")
        # 保存不同sportType的活动样本（仅保存sport_type_mapping中未找到的类型）
        if activities:
            # 创建保存样本的文件夹
            sample_folder = "activity_samples"
            if not os.path.exists(sample_folder):
                os.makedirs(sample_folder)
            
            sport_type_samples = {}
            saved_samples_count = 0
            max_samples = 10  # 最多保存10个不同类型
            
            for activity in activities:
                sport_type = activity.get('sportType')
                if sport_type and sport_type not in sport_type_samples:
                    # 检查该运动类型是否不在映射表中
                    if sport_type not in sport_type_mapping:
                        sport_type_samples[sport_type] = activity
                        # 保存样本文件到指定文件夹
                        sample_file_path = os.path.join(sample_folder, f"activity_sample_{sport_type}.json")
                        with open(sample_file_path, "w", encoding="utf-8") as f:
                            json.dump(activity, f, indent=2, ensure_ascii=False)
                        saved_samples_count += 1
                    
                    if len(sport_type_samples) >= max_samples:  # 最多保存10个不同类型
                        break
            
            if saved_samples_count > 0:
                print(f"已保存 {saved_samples_count} 个不同未映射sportType的活动样本到 {sample_folder} 文件夹")
            else:
                print("所有活动类型均已在sport_type_mapping中定义，未保存任何样本")

        # 创建活动ID到活动对象的映射（使用字符串键以便与文件提取的activity_id匹配）
        activity_id_to_activity = {str(activity.get('labelId')): activity for activity in activities if activity.get('labelId')}

        # 检查现有文件
        existing_files = os.listdir(download_folder)
        existing_activity_ids = set()

        for filename in existing_files:
            if not filename.endswith('.fit'):
                continue
            
            # 从文件名末尾提取活动ID（支持新旧格式）
            activity_id = None
            id_match = re.search(r'(\d+)\.fit$', filename)
            if id_match:
                activity_id = id_match.group(1)
            
            if activity_id:
                existing_activity_ids.add(activity_id)

        # 下载活动文件（仅下载未存在的）
        print("开始下载未存在的活动文件...")
        for index, activity in enumerate(activities, 1):
            activity_id = activity.get('labelId')
            if not activity_id:
                print(f"({index}/{len(activities)}) 缺少活动ID，跳过")
                continue

            # 检查是否已下载
            if str(activity_id) in existing_activity_ids:
                print(f"({index}/{len(activities)}) 活动已存在，跳过下载: {activity_id}")
                continue

            try:
                # 获取活动类型
                sport_type = activity.get('sportType', 100)
                
                # 获取下载URL
                download_url = f"{client.teamapi}/activity/detail/download?labelId={activity_id}&sportType={sport_type}&fileType=4"
                
                # 使用CorosClient发送POST请求
                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "accesstoken": client.access_token,
                    "Content-Type": "application/json;charset=UTF-8",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.39 Safari/537.36",
                }
                
                response = client.req.request('POST', download_url, headers=headers)
                download_result = json.loads(response.data)
                if download_result['result'] != '0000':
                    print(f"({index}/{len(activities)}) 获取下载URL失败: activity_{activity_id} - {download_result['message']}")
                    continue
                
                fit_url = download_result['data']['fileUrl']
                
                # 构建新文件名
                begin_time = activity.get('startTime')
                if not begin_time:
                    print(f"({index}/{len(activities)}) 缺少时间信息，跳过")
                    continue
                
                dt = datetime.fromtimestamp(begin_time)
                date_part = dt.strftime("%Y%m%d")
                time_part = dt.strftime("%H%M%S")
                
                activity_type = get_activity_type(sport_type)
                
                new_filename = f"{date_part}-{time_part}-{activity_type}-{activity_id}.fit"
                fit_path = os.path.join(download_folder, new_filename)
                
                # 下载FIT文件 - 使用requests库直接下载，因为urllib3流式下载较为复杂
                try:
                    # 使用requests库下载文件
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.39 Safari/537.36",
                    }
                    download_response = requests.get(fit_url, stream=True, headers=headers)
                    download_response.raise_for_status()

                    # 保存文件
                    with open(fit_path, "wb") as f:
                        for chunk in download_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                except Exception:
                    # 如果requests下载失败，尝试使用urllib3下载
                    print(f"({index}/{len(activities)}) requests下载失败，尝试使用urllib3下载...")
                    
                    # 使用urllib3下载文件
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.39 Safari/537.36",
                    }
                    response = client.req.request('GET', fit_url, headers=headers, preload_content=False)
                    
                    with open(fit_path, "wb") as f:
                        for chunk in response.stream(8192):
                            if chunk:
                                f.write(chunk)
                    response.release_conn()

                print(f"({index}/{len(activities)}) 下载成功: {new_filename}")

                time.sleep(1)  # 避免请求过快
            except requests.exceptions.RequestException as e:
                activity_id_str = f"activity_{activity_id}" if 'activity_id' in locals() else "unknown_activity"
                print(f"({index}/{len(activities)}) 下载失败 (网络错误): {activity_id_str} - {e}")
                time.sleep(2)  # 失败后稍作等待
            except Exception as e:
                activity_id_str = f"activity_{activity_id}" if 'activity_id' in locals() else "unknown_activity"
                print(f"({index}/{len(activities)}) 下载失败: {activity_id_str} - {e}")
                import traceback
                traceback.print_exc()
                time.sleep(2)  # 失败后稍作等待

        print("所有FIT文件下载完成！")
        return True

    except requests.exceptions.RequestException as e:
        print(f"下载过程中出现网络错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"下载过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False



def main():
    """
    主函数
    """
    # 配置信息
    download_folder = "downloads/coros"

    # 登录
    print("正在登录Coros账号...")
    client = login_coros()
    if not client:
        print("\n登录失败，程序已退出。")
        print("提示：请检查您的网络连接、账号密码是否正确，或尝试等待一段时间后再重试。")
        return
    
    # 确保下载目录存在
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    # 下载所有fit文件
    try:
        success = download_all_fit_files(client, download_folder)
        if success:
            print("所有文件下载完成！")
        else:
            print("文件下载失败")
    except Exception as e:
        print(f"程序执行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # CorosClient使用urllib3，无需额外关闭操作
        pass



if __name__ == "__main__":
    main()