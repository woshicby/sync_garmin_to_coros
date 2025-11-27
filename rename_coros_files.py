import os
import re
import analyze_activity_files

def main():
    # 首先运行分析脚本生成初始报告
    print("正在执行初始活动文件分析...")
    analyze_activity_files.main()

    # 读取不匹配的活动文件列表
    mismatched_file = os.path.join("reports", "mismatched_activities.txt")
    with open(mismatched_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 遍历每一组不匹配的文件信息（每4行一组）
    filtered_lines = [line.strip() for line in lines if line.strip() and line.strip() != "高驰和佳明活动类型不匹配的文件名单：" and not line.strip().startswith("总共有")]
    
    for i in range(0, len(filtered_lines), 4):
        if i + 3 >= len(filtered_lines):
            break  # 确保有完整的4行信息
            
        garmin_file_line = filtered_lines[i]
        coros_file_line = filtered_lines[i+1]
        garmin_type_line = filtered_lines[i+2]
        coros_type_line = filtered_lines[i+3]
        
        # 提取佳明文件名
        if not garmin_file_line.startswith("佳明文件: "):
            continue
        garmin_filename = garmin_file_line.split(": ")[1]
        
        # 提取高驰文件名
        if not coros_file_line.startswith("高驰文件: "):
            continue
        coros_filename = coros_file_line.split(": ")[1]
        
        # 提取佳明活动类型
        if not garmin_type_line.startswith("佳明活动类型: "):
            continue
        garmin_activity_type = garmin_type_line.split(": ")[1]

        # 构建高驰文件路径并检查存在性
        coros_file_path = os.path.join("downloads", "coros", coros_filename)
        if not os.path.exists(coros_file_path):
            print(f"高驰文件不存在：{coros_filename}")
            continue

        # 重命名高驰文件，替换活动类型为佳明的活动类型
        coros_parts = coros_filename.split("-")
        if len(coros_parts) < 3:
            continue
        
        coros_parts[2] = garmin_activity_type
        new_coros_filename = "-".join(coros_parts)
        new_coros_file_path = os.path.join("downloads", "coros", new_coros_filename)

        # 执行重命名
        try:
            os.rename(coros_file_path, new_coros_file_path)
            print(f"重命名成功：{coros_filename} → {new_coros_filename}")
        except Exception as e:
            print(f"重命名失败：{coros_filename} → {new_coros_filename}，错误：{e}")

    # 重命名完成后再次运行分析脚本生成最终报告
    print("\n正在执行修正后的活动文件分析...")
    analyze_activity_files.main()

    print("\n所有操作完成！分析结果已保存到 reports 文件夹中。")

if __name__ == "__main__":
    main()