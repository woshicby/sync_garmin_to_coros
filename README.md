# Garmin Connect 与 Coros 双向活动同步工具

## 语言切换 / Language Switch / 言語切り替え

[![中文](https://img.shields.io/badge/中文-Chinese-red)](#garmin-connect-与-coros-双向活动同步工具)
[![English](https://img.shields.io/badge/English-%E8%8B%B1%E6%96%87-blue)](#garmin-connect-and-coros-bidirectional-activity-sync-tool)
[![日本語](https://img.shields.io/badge/日本語-Japanese-green)](#garmin-connect-と-coros-の双向アクティビティ同期ツール)

> **注意：英文和日语版本内容由AI生成，可能存在翻译误差，请以中文版本为准。**
>
> **Note: English and Japanese versions are AI-generated and may contain translation errors. Please refer to the Chinese version for accuracy.**
>
> **注意：英語版と日本語版はAIによって生成されており、翻訳エラーが含まれている可能性があります。正確性については、中国語版を参照してください。**

一个强大的工具，实现 Garmin Connect 和 Coros 平台之间的双向活动同步，自动管理跨平台运动数据。

> **重要说明：本工具仅支持国服 Garmin Connect，使用时请不要挂梯子或使用 VPN，否则可能导致登录失败或无法正常下载活动数据。**
> **gitignore里已经设置好忽略密码和凭证，但若要将本地使用的代码上传到git，请再次确认是否修改过。若有修改，请及时更新gitignore文件。**

## 功能特性

### 双向同步功能
- 自动登录 Garmin Connect 和 Coros 平台
- 智能分析两个平台的活动数据
- 找出各平台独有活动并同步到另一方
- 支持多区域配置（国际区、中国区、欧洲区）
- 按日期排序，有序上传活动文件
- 过滤掉特定活动类型（如 walking、indoor_climbing、bouldering）
- 支持白名单配置，手动指定需要跳过的活动对
- 生成详细的同步报告
- 支持多种文件存储服务（阿里云 OSS、AWS S3）

### 活动下载功能
- 自动登录 Garmin Connect 平台（支持 MFA 验证码）
- 批量加载并保存活动数据信息
- 自动下载活动的 .fit 文件（支持断点续传）
- 从 FIT 文件内部提取精确的开始时间（使用 garmin_fit_sdk），统一 UTC+8 时区
- 按照统一命名规范保存活动文件

### 活动分析功能
- 比较 Garmin 和 Coros 活动数据
- 识别活动类型不匹配的情况
- 生成三种分析报告：
  - 活动类型不匹配报告
  - Coros 独有活动报告
  - Garmin 独有活动报告
- 统计活动类型分布

### 辅助工具
- **FIT 文件名修正工具**：批量将 FIT 文件名中的日期时间修正为文件内部记录的开始时间，并同步更新白名单
- **Coros 文件重命名工具**：根据 Garmin 活动类型修正 Coros 文件的活动类型名称
- **Keep 历史活动上传工具**：批量上传 Keep 运动记录到 Garmin 和 Coros
- **FIT 文件解析工具**：解析 FIT 文件并提取时间戳信息

## 安装依赖

使用以下命令安装所需依赖：

```bash
pip install -r requirements.txt
```

主要依赖包包括：
- garminconnect
- garth
- garmin-fit-sdk（FIT 文件解析）
- urllib3
- certifi
- requests
- oss2 (中国区用户必须)
- boto3 (国际区/欧洲区用户必须)

## 项目结构

```
sync_garmin_to_coros/
├── clients/                    # API 客户端模块
│   ├── __init__.py
│   └── coros_client.py         # Coros API 客户端
├── services/                   # 业务服务模块
│   ├── __init__.py
│   ├── downloader.py           # 活动下载服务（含 FIT 时间提取）
│   ├── analyzer.py             # 活动分析服务
│   └── syncer.py               # 活动同步服务
├── storage/                    # 存储模块
│   ├── __init__.py
│   └── oss_client.py           # OSS 文件上传
├── tools/                      # 辅助工具
│   ├── __init__.py
│   ├── rename_fit_files.py     # FIT 文件名时间修正工具
│   ├── rename_coros_files.py   # Coros 文件活动类型修正工具
│   ├── improved_fit_parser.py  # FIT 解析工具
│   └── upload_activities.py    # Keep 历史活动批量上传工具
├── config/                     # 配置文件目录（gitignore）
│   └── sync_whitelist.md       # 同步白名单
├── downloads/                  # 下载的活动文件（gitignore）
│   ├── garmin/                 # Garmin 活动文件
│   ├── coros/                  # Coros 活动文件
│   ├── KEEP_merged/            # Keep 合并活动文件
│   └── KEEP_phone/             # Keep 手机活动文件
├── reports/                    # 分析报告目录（gitignore）
├── tokens/                     # 登录令牌目录（gitignore）
│   ├── garmin/                 # Garmin 令牌
│   └── coros/                  # Coros 令牌
├── config.py                   # 统一配置文件
├── config_manager.py           # 配置管理器
├── main.py                     # 主入口程序
├── requirements.txt            # 依赖列表
├── LICENSE
└── README.md
```

## 配置说明

### 区域配置

本工具支持以下区域配置：
- **国际区**: 适用于全球大部分地区
- **中国区**: 适用于中国大陆地区
- **欧洲区**: 适用于欧洲地区用户

不同区域使用不同的API地址和存储服务：
- 国际区: 使用 AWS S3 存储服务
- 中国区: 使用阿里云 OSS 存储服务
- 欧洲区: 使用 AWS S3 存储服务

### 配置文件

1. 首次运行前，程序会自动创建所需的配置文件和目录结构。

2. 配置文件位置：
   - `config/garmin_config.json`: Garmin Connect 登录配置
   - `config/coros_config.json`: Coros 登录配置
   - `config/sync_whitelist.md`: 同步白名单配置（可选）

3. 配置文件格式：

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

   **config/sync_whitelist.md** (用于指定需要跳过的活动对):
   ```
   # 同步白名单配置文件
   # 格式：佳明活动完整文件名 高驰活动完整文件名
   # 每行表示一对需要跳过的活动
   # 示例：
   20230711-174102-multi_sport-莆田市复合运动-256118606.fit 20230711-175127-running-461428804292739075.fit

   # walking类型文件会自动添加到此处
   20230815-080000-walking-日常步行-123456789.fit
   ```

4. 密码/凭证存储说明：
   - 密码以 base64 编码形式存储，程序会自动进行解码
   - 出于安全考虑，请勿直接以明文形式保存密码
   - 首次运行时，程序会提示输入邮箱和密码，并自动加密保存

## 使用方法

### 1. 主同步功能

运行主程序进行 Garmin 和 Coros 的双向活动同步：

```bash
python main.py
```

同步过程将自动：
- 下载 Garmin 活动
- 下载 Coros 活动
- 分析并找出需要同步的活动
- 按日期排序上传到对方平台
- 生成同步报告

### 2. 单独使用各模块

```python
# 下载 Garmin 活动
from services import download_garmin_activities
download_garmin_activities()

# 下载 Coros 活动
from services import download_coros_activities
download_coros_activities()

# 分析活动
from services import analyze_activities
analyze_activities()

# 同步活动
from services import sync_activities
sync_activities()
```

### 3. 使用辅助工具

```bash
# 修正 FIT 文件名中的日期时间为文件内部记录的开始时间
python tools/rename_fit_files.py

# 重命名 Coros 文件（修正活动类型不匹配）
python tools/rename_coros_files.py

# 解析 FIT 文件
python tools/improved_fit_parser.py

# 批量上传 Keep 历史活动到 Garmin 和 Coros
python tools/upload_activities.py
```

## FIT 文件时间提取说明

本工具使用 `garmin_fit_sdk` 从 FIT 文件中精确提取活动开始时间，统一使用 **UTC+8** 时区偏移转为本地时间。

提取逻辑：
1. 优先从 `session_mesgs.start_time` 获取 UTC 开始时间
2. 回退：从 `file_id_mesgs.time_created` 获取 UTC 时间
3. 加上 UTC+8（28800 秒）时区偏移得到本地时间
4. 用于文件命名：`YYYYMMDD-HHMMSS-活动类型-活动名称-ID.fit`

下载服务（`downloader.py`）在下载 FIT 文件时自动使用此逻辑命名文件，确保文件名中的时间与 FIT 文件内部记录一致。

## 注意事项

1. **重要：本工具仅支持国服 Garmin Connect，使用时请不要挂梯子或使用 VPN**
2. 首次运行时，如果启用了 MFA，程序会提示输入验证码
3. 程序会自动管理登录令牌，避免频繁登录
4. 同步过程中会自动跳过已存在于对方平台的活动
5. walking、indoor_climbing、bouldering 类型的活动默认会被过滤，不会上传
6. 白名单中的活动对将被自动跳过，适合处理已手动处理或特殊情况的活动
7. 请确保网络连接稳定，特别是在批量下载或上传活动时
8. 活动文件将按统一格式命名，包含日期、时间、活动类型、名称和ID

## 技术说明

- 使用 garminconnect 库与 Garmin Connect API 交互
- 使用 urllib3 库与 Coros API 交互
- 使用 garmin-fit-sdk 解析 FIT 文件，提取精确的开始时间
- 使用 requests 库处理 HTTP 请求
- 支持多区域的 Garmin Connect 和 Coros 平台
- 支持多种存储服务：阿里云 OSS 和 AWS S3

## 更新日志

- v1.0.0: 初始版本，添加 Garmin 活动下载功能
- v1.1.0: 添加 Coros 活动同步功能
- v1.2.0: 添加活动分析和报告生成功能
- v1.3.0: 优化同步逻辑，添加文件存储支持
- v1.4.0: 添加活动白名单功能，支持手动指定需要跳过的活动对
- v1.5.0: 支持多区域配置（国际区、中国区、欧洲区）
- v1.6.0: 更新依赖库，优化登录流程
- v2.0.0: 重构项目结构，模块化设计，统一配置管理
- v2.1.0: 优化活动同步逻辑，白名单文件改为md格式，增强报告统计信息，改进多项运动文件处理流程
- v2.2.0: 使用 garmin-fit-sdk 替代手动解析 FIT 文件，统一 UTC+8 时区偏移；下载时从 FIT 文件内部提取开始时间命名文件；新增 FIT 文件名时间修正工具；新增 Keep 历史活动批量上传工具

## 许可证

本项目仅供个人学习和使用，请勿用于商业目的。

## 免责声明

使用本工具时，请遵守 Garmin Connect 和 Coros 平台的服务条款。本工具的使用可能违反相关平台的 API 使用政策，使用者需自行承担风险。

---

# Garmin Connect and Coros Bidirectional Activity Sync Tool

A powerful tool for bidirectional synchronization of activity data between Garmin Connect and Coros platforms, enabling cross-platform sports data management.

> **Important Note: This tool only supports the Chinese region Garmin Connect. Please do not use a VPN or proxy when using this tool, as it may cause login failures or prevent normal download of activity data.**
> **The gitignore file is already configured to ignore passwords and credentials, but if you want to upload locally used code to git, please double-check if you have modified it. If so, please update the gitignore file in a timely manner.**

## Features

### Bidirectional Sync Function
- Automatic login to Garmin Connect and Coros platforms
- Intelligent analysis of activity data from both platforms
- Find exclusive activities from each platform and sync to the other
- Support for multiple regions: International, Chinese, and European regions
- Date-sorted, sequential upload of activity files
- Filtering of specific activity types (such as walking, indoor_climbing, bouldering)
- Support for whitelist configuration to manually specify activity pairs to skip
- Generation of detailed sync reports
- Support for multiple file storage services (Alibaba Cloud OSS for China region, AWS S3 for International/European regions)

### Activity Download Function
- Automatic login to Garmin Connect platform (supports MFA verification code)
- Batch loading and saving of activity data information
- Automatic download of activity .fit files (supports resumable downloads)
- Extract precise start time from FIT files using garmin_fit_sdk, with unified UTC+8 timezone
- Saving activity files according to a unified naming convention

### Activity Analysis Function
- Compare Garmin and Coros activity data
- Identify cases of mismatched activity types
- Generate three types of analysis reports:
  - Activity type mismatch report
  - Coros-only activities report
  - Garmin-only activities report
- Statistics on activity type distribution

### Utility Tools
- **FIT Filename Correction Tool**: Batch correct date/time in FIT filenames to match internal start time, and sync whitelist
- **Coros File Rename Tool**: Fix Coros file activity type names based on Garmin activity types
- **Keep Activity Upload Tool**: Batch upload Keep historical activities to Garmin and Coros
- **FIT File Parser**: Parse FIT files and extract timestamp information

## Installation

Install the required dependencies using the following command:

```bash
pip install -r requirements.txt
```

Main dependency packages include:
- garminconnect
- garth
- garmin-fit-sdk (FIT file parsing)
- urllib3
- certifi
- requests
- oss2 (required for Chinese region)
- boto3 (required for International/European region)

## Project Structure

```
sync_garmin_to_coros/
├── clients/                    # API client module
│   ├── __init__.py
│   └── coros_client.py         # Coros API client
├── services/                   # Business service module
│   ├── __init__.py
│   ├── downloader.py           # Activity download service (with FIT time extraction)
│   ├── analyzer.py             # Activity analysis service
│   └── syncer.py               # Activity sync service
├── storage/                    # Storage module
│   ├── __init__.py
│   └── oss_client.py           # OSS file upload
├── tools/                      # Utility tools
│   ├── __init__.py
│   ├── rename_fit_files.py     # FIT filename time correction tool
│   ├── rename_coros_files.py   # Coros file activity type correction tool
│   ├── improved_fit_parser.py  # FIT parser tool
│   └── upload_activities.py    # Keep historical activity batch upload tool
├── config/                     # Configuration files (gitignore)
│   └── sync_whitelist.md       # Sync whitelist
├── downloads/                  # Downloaded activity files (gitignore)
│   ├── garmin/                 # Garmin activity files
│   ├── coros/                  # Coros activity files
│   ├── KEEP_merged/            # Keep merged activity files
│   └── KEEP_phone/             # Keep phone activity files
├── reports/                    # Analysis reports (gitignore)
├── tokens/                     # Login tokens (gitignore)
│   ├── garmin/                 # Garmin tokens
│   └── coros/                  # Coros tokens
├── config.py                   # Unified configuration
├── config_manager.py           # Configuration manager
├── main.py                     # Main entry point
├── requirements.txt            # Dependencies
├── LICENSE
└── README.md
```

## Configuration Instructions

### Regional Configuration

The tool supports three regions with different API endpoints and storage services:

| Region | Garmin API | Coros API | Storage Service |
|--------|------------|-----------|----------------|
| International | connectapi.garmin.com | teamapi.coros.com | AWS S3 |
| Chinese | connectapi.garmin.cn | teamapi.coros.com.cn | Alibaba Cloud OSS |
| European | connectapi.garmin.eu | teamapi.coros.com | AWS S3 |

### Configuration Files

1. Before running for the first time, the program will automatically create the required directory structure.

2. Configuration file locations:
   - `config/garmin_config.json`: Garmin Connect login configuration
   - `config/coros_config.json`: Coros login configuration
   - `config/sync_whitelist.md`: Sync whitelist configuration (optional)

3. Configuration file format:

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

   **config/sync_whitelist.md** (for specifying activity pairs to skip):
   ```
   # Sync whitelist configuration file
   # Format: Garmin activity full filename Coros activity full filename
   # Each line represents a pair of activities to skip
   # Example:
   20230711-174102-multi_sport-莆田市复合运动-256118606.fit 20230711-175127-running-461428804292739075.fit
   ```

4. Password/Credential Storage Instructions:
   - Passwords are stored in base64 encoded format, and the program will automatically decode them
   - For security reasons, please do not save passwords in plain text format

## Usage

### 1. Main Sync Function

Run the main program for Garmin and Coros bidirectional activity sync:

```bash
python main.py
```

The sync process will automatically:
- Download Garmin activities
- Download Coros activities
- Analyze and find activities that need to be synced
- Upload to the other platform in date order
- Generate sync report

### 2. Using Individual Modules

```python
# Download Garmin activities
from services import download_garmin_activities
download_garmin_activities()

# Download Coros activities
from services import download_coros_activities
download_coros_activities()

# Analyze activities
from services import analyze_activities
analyze_activities()

# Sync activities
from services import sync_activities
sync_activities()
```

### 3. Using Utility Tools

```bash
# Correct date/time in FIT filenames to match internal start time
python tools/rename_fit_files.py

# Rename Coros files (fix activity type mismatch)
python tools/rename_coros_files.py

# Parse FIT files
python tools/improved_fit_parser.py

# Batch upload Keep historical activities to Garmin and Coros
python tools/upload_activities.py
```

## FIT File Time Extraction

This tool uses `garmin_fit_sdk` to precisely extract activity start times from FIT files, with a unified **UTC+8** timezone offset for local time conversion.

Extraction logic:
1. Priority: Get UTC start time from `session_mesgs.start_time`
2. Fallback: Get UTC time from `file_id_mesgs.time_created`
3. Add UTC+8 (28800 seconds) timezone offset to get local time
4. Used for file naming: `YYYYMMDD-HHMMSS-activity_type-activity_name-ID.fit`

The download service (`downloader.py`) automatically uses this logic when downloading FIT files, ensuring the filename time matches the internal FIT file record.

## Notes

1. **Important: This tool only supports the Chinese region Garmin Connect. Please do not use a VPN or proxy when using this tool**
2. On first run, if MFA is enabled, the program will prompt for a verification code
3. The program will automatically manage login tokens to avoid frequent logins
4. The sync process will automatically skip activities already existing on the other platform
5. Activities of type walking, indoor_climbing, bouldering are filtered by default and will not be uploaded
6. Activity pairs in the whitelist will be automatically skipped, suitable for handling manually processed or special case activities
7. Please ensure a stable network connection, especially when batch downloading or uploading activities
8. Activity files will be named according to a unified format, including date, time, activity type, name, and ID

## Technical Notes

- Uses garminconnect library to interact with Garmin Connect API
- Uses urllib3 library to interact with Coros API
- Uses garmin-fit-sdk to parse FIT files and extract precise start times
- Uses requests library to handle HTTP requests
- Supports multiple regions: International, Chinese, and European regions
- Supports multiple storage services: Alibaba Cloud OSS and AWS S3

## Changelog

- v1.0.0: Initial version, added Garmin activity download functionality
- v1.1.0: Added Coros activity sync functionality
- v1.2.0: Added activity analysis and report generation functionality
- v1.3.0: Optimized sync logic, added file storage support
- v1.4.0: Added activity whitelist functionality, supporting manual specification of activity pairs to skip
- v1.5.0: Added multiple region support (International, Chinese, European)
- v1.6.0: Updated dependencies, optimized login flow
- v2.0.0: Refactored project structure, modular design, unified configuration management
- v2.1.0: Optimized activity sync logic, changed whitelist file to md format, enhanced report statistics, improved multi-sport file processing
- v2.2.0: Replaced manual FIT parsing with garmin-fit-sdk, unified UTC+8 timezone offset; extract start time from FIT file for naming during download; added FIT filename time correction tool; added Keep historical activity batch upload tool

## License

This project is for personal learning and use only, please do not use it for commercial purposes.

## Disclaimer

When using this tool, please comply with the terms of service of Garmin Connect and Coros platforms. The use of this tool may violate the API usage policies of relevant platforms, and users should assume the risk themselves.

---

# Garmin Connect と Coros の双向アクティビティ同期ツール

Garmin Connect と Coros プラットフォーム間のアクティビティデータの双向同期を実現する強力なツールです。クロスプラットフォームのスポーツデータ管理を可能にします。

> **重要な注意事項：このツールは中国地域のGarmin Connectのみをサポートしています。VPN やプロキシを使用しないでください。ログインに失敗したり、アクティビティデータの正常なダウンロードが妨げられたりする可能性があります。**
> **gitignore ファイルはすでにパスワードと認証情報を無視するように設定されていますが、ローカルで使用しているコードを git にアップロードする場合は、変更されていないか再度確認してください。変更されている場合は、gitignore ファイルを適時更新してください。**

## 機能特性

### 双方向同期機能
- Garmin Connect と Coros プラットフォームへの自動ログイン
- 両プラットフォームのアクティビティデータのインテリジェント分析
- 各プラットフォームの独占アクティビティを見つけ、もう一方に同期
- 複数の地域をサポート：国際版、中国版、欧州版
- 日付でソートし、順序ててアクティビティファイルをアップロード
- 特定のアクティビティタイプ（walking、indoor_climbing、bouldering など）をフィルタリング
- ホワイトリスト設定をサポートし、スキップするアクティビティペアを手動で指定
- 詳細な同期レポートの生成
- 複数のファイルストレージサービスをサポート：中国地域は Alibaba Cloud OSS、国際/欧州地域は AWS S3

### アクティビティダウンロード機能
- Garmin Connect プラットフォームへの自動ログイン（MFA 検証コードに対応）
- アクティビティデータ情報の一括読み込みと保存
- アクティビティの .fit ファイルの自動ダウンロード（再開可能なダウンロードに対応）
- garmin_fit_sdk を使用してFIT ファイルから正確な開始時刻を抽出、統一 UTC+8 タイムゾーン
- 統一された命名規則に従ってアクティビティファイルを保存

### アクティビティ分析機能
- Garmin と Coros のアクティビティデータを比較
- アクティビティタイプが一致しないケースを特定
- 3種類の分析レポートを生成：
  - アクティビティタイプ不一致レポート
  - Coros 独占アクティビティレポート
  - Garmin 独占アクティビティレポート
- アクティビティタイプ分布の統計

### ユーティリティツール
- **FIT ファイル名修正ツール**: FIT ファイル名の日時を内部記録の開始時刻に一括修正し、ホワイトリストを同期更新
- **Coros ファイル名変更ツール**: Garmin アクティビティタイプに基づいて Coros ファイルのアクティビティタイプ名を修正
- **Keep アクティビティアップロードツール**: Keep の履歴アクティビティを Garmin と Coros に一括アップロード
- **FIT ファイルパーサー**: FIT ファイルを解析しタイムスタンプ情報を抽出

## インストール

以下のコマンドで必要な依存パッケージをインストールしてください：

```bash
pip install -r requirements.txt
```

主な依存パッケージ：
- garminconnect
- garth
- garmin-fit-sdk（FIT ファイル解析）
- urllib3
- certifi
- requests
- oss2（中国地域ユーザー必須）
- boto3（国際/欧州地域ユーザー必須）

## プロジェクト構造

```
sync_garmin_to_coros/
├── clients/                    # API クライアントモジュール
│   ├── __init__.py
│   └── coros_client.py         # Coros API クライアント
├── services/                   # ビジネスサービスモジュール
│   ├── __init__.py
│   ├── downloader.py           # アクティビティダウンロードサービス（FIT 時間抽出含む）
│   ├── analyzer.py             # アクティビティ分析サービス
│   └── syncer.py               # アクティビティ同期サービス
├── storage/                    # ストレージモジュール
│   ├── __init__.py
│   └── oss_client.py           # OSS ファイルアップロード
├── tools/                      # ユーティリティツール
│   ├── __init__.py
│   ├── rename_fit_files.py     # FIT ファイル名時間修正ツール
│   ├── rename_coros_files.py   # Coros ファイルアクティビティタイプ修正ツール
│   ├── improved_fit_parser.py  # FIT パーサーツール
│   └── upload_activities.py    # Keep 履歴アクティビティ一括アップロードツール
├── config/                     # 設定ファイルディレクトリ（gitignore）
│   └── sync_whitelist.md       # 同期ホワイトリスト
├── downloads/                  # ダウンロードしたアクティビティファイル（gitignore）
│   ├── garmin/                 # Garmin アクティビティファイル
│   ├── coros/                  # Coros アクティビティファイル
│   ├── KEEP_merged/            # Keep 統合アクティビティファイル
│   └── KEEP_phone/             # Keep スマートフォンアクティビティファイル
├── reports/                    # 分析レポート（gitignore）
├── tokens/                     # ログイントークン（gitignore）
│   ├── garmin/                 # Garmin トークン
│   └── coros/                  # Coros トークン
├── config.py                   # 統一設定
├── config_manager.py           # 設定マネージャー
├── main.py                     # メインエントリポイント
├── requirements.txt            # 依存関係
├── LICENSE
└── README.md
```

## 設定説明

### 地域設定

このツールは3つの地域をサポートしています：

| 地域 | Garmin API | Coros API | ストレージサービス |
|------|------------|-----------|------------------|
| 国際 | connectapi.garmin.com | teamapi.coros.com | AWS S3 |
| 中国 | connectapi.garmin.cn | teamapi.coros.com.cn | Alibaba Cloud OSS |
| 欧州 | connectapi.garmin.eu | teamapi.coros.com | AWS S3 |

### 設定ファイル

1. 初回実行前に、プログラムが必要なディレクトリ構造を自動作成します。

2. 設定ファイルの場所：
   - `config/garmin_config.json`: Garmin Connect ログイン設定
   - `config/coros_config.json`: Coros ログイン設定
   - `config/sync_whitelist.md`: 同期ホワイトリスト設定（オプション）

3. 設定ファイルの形式：

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

   **config/sync_whitelist.md**（スキップするアクティビティペアを指定）:
   ```
   # 同期ホワイトリスト設定ファイル
   # 形式：Garmin アクティビティ完全ファイル名 Coros アクティビティ完全ファイル名
   # 各行はスキップするアクティビティペアを表します
   # 例：
   20230711-174102-multi_sport-莆田市复合运动-256118606.fit 20230711-175127-running-461428804292739075.fit
   ```

4. パスワード/認証情報の保存について：
   - パスワードは base64 エンコード形式で保存され、プログラムが自動的にデコードします
   - セキュリティ上の理由から、パスワードを平文で保存しないでください

## 使用方法

### 1. メイン同期機能

メインプログラムを実行して Garmin と Coros の双方向アクティビティ同期を行います：

```bash
python main.py
```

同期プロセスは自動的に：
- Garmin アクティビティをダウンロード
- Coros アクティビティをダウンロード
- 同期が必要なアクティビティを分析して特定
- 日付順で相手プラットフォームにアップロード
- 同期レポートを生成

### 2. 個別モジュールの使用

```python
# Garmin アクティビティをダウンロード
from services import download_garmin_activities
download_garmin_activities()

# Coros アクティビティをダウンロード
from services import download_coros_activities
download_coros_activities()

# アクティビティを分析
from services import analyze_activities
analyze_activities()

# アクティビティを同期
from services import sync_activities
sync_activities()
```

### 3. ユーティリティツールの使用

```bash
# FIT ファイル名の日時を内部記録の開始時刻に修正
python tools/rename_fit_files.py

# Coros ファイルの名前を変更（アクティビティタイプの不一致を修正）
python tools/rename_coros_files.py

# FIT ファイルを解析
python tools/improved_fit_parser.py

# Keep 履歴アクティビティを Garmin と Coros に一括アップロード
python tools/upload_activities.py
```

## FIT ファイル時間抽出について

このツールは `garmin_fit_sdk` を使用して FIT ファイルからアクティビティの開始時刻を正確に抽出し、統一された **UTC+8** タイムゾーンオフセットでローカル時刻に変換します。

抽出ロジック：
1. 優先：`session_mesgs.start_time` から UTC 開始時刻を取得
2. フォールバック：`file_id_mesgs.time_created` から UTC 時刻を取得
3. UTC+8（28800秒）のタイムゾーンオフセットを加算してローカル時刻を取得
4. ファイル命名に使用：`YYYYMMDD-HHMMSS-アクティビティタイプ-アクティビティ名-ID.fit`

ダウンロードサービス（`downloader.py`）は、FIT ファイルのダウンロード時にこのロジックを自動的に使用してファイルに名前を付け、ファイル名の時刻が FIT ファイルの内部記録と一致することを保証します。

## 注意事項

1. **重要：このツールは中国地域のGarmin Connectのみをサポートしています。VPN やプロキシを使用しないでください**
2. 初回実行時、MFA が有効な場合、検証コードの入力が求められます
3. プログラムはログイントークンを自動管理し、頻繁なログインを回避します
4. 同期プロセスは、相手プラットフォームに既存のアクティビティを自動的にスキップします
5. walking、indoor_climbing、bouldering タイプのアクティビティはデフォルトでフィルタリングされ、アップロードされません
6. ホワイトリスト内のアクティビティペアは自動的にスキップされます
7. バッチダウンロードまたはアップロード時に安定したネットワーク接続を確保してください
8. アクティビティファイルは統一形式で命名されます：日付、時刻、アクティビティタイプ、名前、ID を含む

## 技術説明

- garminconnect ライブラリを使用して Garmin Connect API と通信
- urllib3 ライブラリを使用して Coros API と通信
- garmin-fit-sdk を使用して FIT ファイルを解析し、正確な開始時刻を抽出
- requests ライブラリを使用して HTTP リクエストを処理
- 複数の地域をサポート：国際版、中国版、欧州版
- 複数のストレージサービスをサポート：Alibaba Cloud OSS と AWS S3

## 更新履歴

- v1.0.0: 初期バージョン、Garmin アクティビティダウンロード機能を追加
- v1.1.0: Coros アクティビティ同期機能を追加
- v1.2.0: アクティビティ分析とレポート生成機能を追加
- v1.3.0: 同期ロジックを最適化、ファイルストレージサポートを追加
- v1.4.0: アクティビティホワイトリスト機能を追加
- v1.5.0: 複数地域サポートを追加（国際、中国、欧州）
- v1.6.0: 依存関係を更新、ログインフローを最適化
- v2.0.0: プロジェクト構造をリファクタリング、モジュラー設計、統一設定管理
- v2.1.0: アクティビティ同期ロジックを最適化、ホワイトリストファイルを md 形式に変更、レポート統計を強化、マルチスポートファイル処理を改善
- v2.2.0: 手動 FIT 解析を garmin-fit-sdk に置き換え、UTC+8 タイムゾーンオフセットを統一；ダウンロード時に FIT ファイルから開始時刻を抽出して命名；FIT ファイル名時間修正ツールを追加；Keep 履歴アクティビティ一括アップロードツールを追加

## ライセンス

このプロジェクトは個人の学習と使用のみを目的としています。商用目的で使用しないでください。

## 免責事項

このツールを使用する際は、Garmin Connect および Coros プラットフォームの利用規約を遵守してください。このツールの使用は、関連プラットフォームの API 使用ポリシーに違反する可能性があり、ユーザー自身のリスクで使用してください。
