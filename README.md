# Garmin Connect 活动下载与 Coros 同步工具

一个强大的工具，用于从 Garmin Connect 下载活动数据并自动同步到 Coros 平台，实现跨平台运动数据管理。

> **重要说明：本工具仅支持国服 Garmin Connect，使用时请不要挂梯子或使用 VPN，否则可能导致登录失败或无法正常下载活动数据。**

## 功能特性

### Garmin 活动下载功能
- 自动登录 Garmin Connect 平台（支持 MFA 验证码）
- 批量加载并保存活动数据信息
- 自动下载活动的 .fit 文件（支持断点续传）
- 按照统一命名规范保存活动文件

### Coros 同步功能
- 自动登录 Coros 平台
- 智能分析 Garmin 和 Coros 活动，找出 Garmin 独有活动
- 按日期排序，有序上传活动文件到 Coros
- 过滤掉特定活动类型（如 walking）
- 支持白名单配置，手动指定需要跳过的活动对
- 生成详细的同步报告
- 支持文件存储服务（阿里云 OSS/AWS S3）

### 活动分析功能
- 比较 Garmin 和 Coros 活动数据
- 识别活动类型不匹配的情况
- 生成三种分析报告：
  - 活动类型不匹配报告
  - Coros 独有活动报告
  - Garmin 独有活动报告
- 统计 Coros 活动类型分布

## 安装依赖

使用以下命令安装所需依赖：

```bash
pip install -r requirements.txt
```

主要依赖包包括：
- garminconnect
- requests
- urllib3
- python-dotenv
- cryptography

## 配置说明

1. 首次运行前，请确保在 `config` 目录下创建以下配置文件：

   此外，您可以创建可选的白名单配置文件：

   **config/sync_whitelist.txt** (用于指定需要跳过的活动对):
   ```
   # 同步白名单配置文件
   # 格式：佳明活动完整文件名 高驰活动ID
   # 每行表示一对需要跳过的活动
   # 示例：
   20230711-174102-multi_sport-莆田市复合运动-251417157.fit 473383235099852802
   ```
   
   **白名单使用方法：**
   1. 当您已经手动将某个Garmin活动上传到Coros，或者希望跳过特定活动的自动同步时使用
   2. 格式必须严格遵守：Garmin活动文件名 + 空格 + Coros活动ID
   3. 可以通过分析报告（`analysis_results/sync_report.txt`）获取已同步活动的对应关系
   4. 白名单中的活动对将在同步过程中被自动跳过，避免重复上传
   5. 注释行以#开头，不会被程序解析

   主要配置文件:

   **config/garmin_config.json**:
   ```json
   {
     "email": "your_garmin_email@example.com",
     "password": "base64_encoded_password"
   }
   ```

   **config/coros_config.json**:
   ```json
   {
     "email": "your_coros_email@example.com",
     "password": "base64_encoded_password"
   }
   ```

   **config/oss_config.json** (用于文件存储):
   ```json
   {
     "appId": "your_app_id",
     "sign": "your_sign_key"
   }
   ```

2. 密码存储说明：
   - 密码以 base64 编码形式存储，程序会自动进行解码
   - 出于安全考虑，请勿直接以明文形式保存密码

## 使用方法

### 1. 主同步功能

运行主程序进行 Garmin 到 Coros 的活动同步：

```bash
python sync_garmin_to_coros.py
```

同步过程将自动：
- 下载 Garmin 活动
- 下载 Coros 活动
- 分析并找出需要同步的活动
- 按日期排序上传到 Coros
- 生成同步报告

### 2. Garmin 活动下载

单独下载 Garmin 活动：

```bash
python garmin_download.py
```

### 3. 活动分析

分析已下载的活动文件：

```bash
python analyze_activity_files.py
```

分析结果将保存在 `analysis_results` 目录下。

## 注意事项

1. **重要：本工具仅支持国服 Garmin Connect，使用时请不要挂梯子或使用 VPN**
2. 首次运行时，如果启用了 MFA，程序会提示输入验证码
3. 程序会自动管理登录令牌，避免频繁登录
4. 同步过程中会自动跳过已存在于 Coros 的活动
5. walking 类型的活动默认会被过滤，不会上传到 Coros
6. 白名单中的活动对将被自动跳过，适合处理已手动处理或特殊情况的活动
7. 请确保网络连接稳定，特别是在批量下载或上传活动时
8. 活动文件将按统一格式命名，包含日期、时间、活动类型、名称和ID

## 技术说明

- 使用 garminconnect 库与 Garmin Connect API 交互
- 使用 urllib3 库与 Coros API 交互
- 使用 requests 库处理 HTTP 请求
- 支持中国区域的 Garmin Connect 和 Coros 平台
- 支持多种存储服务：阿里云 OSS 和 AWS S3

## 文件结构

- `sync_garmin_to_coros.py`: 主程序，实现数据同步功能
- `garmin_download.py`: Garmin 活动下载功能
- `coros_client.py`: Coros API 客户端
- `analyze_activity_files.py`: 活动文件分析工具
- `config/`: 配置文件目录
- `downloads/`: 下载的活动文件目录
- `analysis_results/`: 分析结果目录

## 更新日志

- v1.0.0: 初始版本，添加 Garmin 活动下载功能
- v1.1.0: 添加 Coros 活动同步功能
- v1.2.0: 添加活动分析和报告生成功能
- v1.3.0: 优化同步逻辑，添加文件存储支持
- v1.4.0: 添加活动白名单功能，支持手动指定需要跳过的活动对

## 许可证

本项目仅供个人学习和使用，请勿用于商业目的。

## 免责声明

使用本工具时，请遵守 Garmin Connect 和 Coros 平台的服务条款。本工具的使用可能违反相关平台的 API 使用政策，使用者需自行承担风险。