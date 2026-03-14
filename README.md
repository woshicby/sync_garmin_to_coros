# Garmin Connect 活动下载与 Coros 同步工具

## 语言切换 / Language Switch / 言語切り替え

[![中文](https://img.shields.io/badge/中文-Chinese-red)](#garmin-connect-活动下载与-coros-同步工具)
[![English](https://img.shields.io/badge/English-%E8%8B%B1%E6%96%87-blue)](#garmin-connect-activity-download-and-coros-sync-tool)
[![日本語](https://img.shields.io/badge/日本語-Japanese-green)](#garmin-connect-アクティビティダウンロードと-coros-同期ツール)

> **注意：英文和日语版本内容由AI生成，可能存在翻译误差，请以中文版本为准。**
> 
> **Note: English and Japanese versions are AI-generated and may contain translation errors. Please refer to the Chinese version for accuracy.**
> 
> **注意：英語版と日本語版はAIによって生成されており、翻訳エラーが含まれている可能性があります。正確性については、中国語版を参照してください。**

一个强大的工具，用于从 Garmin Connect 下载活动数据并自动同步到 Coros 平台，实现跨平台运动数据管理。

> **重要说明：本工具仅支持国服 Garmin Connect，使用时请不要挂梯子或使用 VPN，否则可能导致登录失败或无法正常下载活动数据。**
> **gitignore里已经设置好忽略密码和凭证，但若要将本地使用的代码上传到git，请再次确认是否修改过。若有修改，请及时更新gitignore文件。**

## 功能特性

### Garmin 活动下载功能
- 自动登录 Garmin Connect 平台（支持 MFA 验证码）
- 批量加载并保存活动数据信息
- 自动下载活动的 .fit 文件（支持断点续传）
- 按照统一命名规范保存活动文件

### Coros 同步功能
- 自动登录 Coros 平台
- 支持多区域配置（国际区、中国区、欧洲区）
- 智能分析 Garmin 和 Coros 活动，找出 Garmin 独有活动
- 按日期排序，有序上传活动文件到 Coros
- 过滤掉特定活动类型（如 walking、indoor_climbing、bouldering）
- 支持白名单配置，手动指定需要跳过的活动对
- 生成详细的同步报告
- 支持多种文件存储服务（阿里云 OSS、AWS S3）

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
│   ├── downloader.py           # 活动下载服务
│   ├── analyzer.py             # 活动分析服务
│   └── syncer.py               # 活动同步服务
├── storage/                    # 存储模块
│   ├── __init__.py
│   └── oss_client.py           # OSS 文件上传
├── tools/                      # 辅助工具
│   ├── __init__.py
│   ├── rename_coros_files.py   # 重命名工具
│   └── improved_fit_parser.py  # FIT 解析工具
├── config.py                   # 统一配置文件
├── config_manager.py           # 配置管理器
├── main.py                     # 主入口程序
├── requirements.txt            # 依赖列表
├── config/                     # 配置文件目录
├── downloads/                  # 下载的活动文件
│   ├── garmin/                 # Garmin 活动文件
│   └── coros/                  # Coros 活动文件
├── reports/                    # 分析报告目录
└── tokens/                     # 登录令牌目录
    ├── garmin/                 # Garmin 令牌
    └── coros/                  # Coros 令牌
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
   - `config/sync_whitelist.txt`: 同步白名单配置（可选）

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

   **config/sync_whitelist.txt** (用于指定需要跳过的活动对):
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

运行主程序进行 Garmin 到 Coros 的活动同步：

```bash
python main.py
```

同步过程将自动：
- 下载 Garmin 活动
- 下载 Coros 活动
- 分析并找出需要同步的活动
- 按日期排序上传到 Coros
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
# 重命名 Coros 文件（修正活动类型不匹配）
python tools/rename_coros_files.py

# 解析 FIT 文件
python tools/improved_fit_parser.py
```

## 注意事项

1. **重要：本工具仅支持国服 Garmin Connect，使用时请不要挂梯子或使用 VPN**
2. 首次运行时，如果启用了 MFA，程序会提示输入验证码
3. 程序会自动管理登录令牌，避免频繁登录
4. 同步过程中会自动跳过已存在于 Coros 的活动
5. walking、indoor_climbing、bouldering 类型的活动默认会被过滤，不会上传到 Coros
6. 白名单中的活动对将被自动跳过，适合处理已手动处理或特殊情况的活动
7. 请确保网络连接稳定，特别是在批量下载或上传活动时
8. 活动文件将按统一格式命名，包含日期、时间、活动类型、名称和ID

## 技术说明

- 使用 garminconnect 库与 Garmin Connect API 交互
- 使用 urllib3 库与 Coros API 交互
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

## 许可证

本项目仅供个人学习和使用，请勿用于商业目的。

## 免责声明

使用本工具时，请遵守 Garmin Connect 和 Coros 平台的服务条款。本工具的使用可能违反相关平台的 API 使用政策，使用者需自行承担风险。

---

# Garmin Connect Activity Download and Coros Sync Tool

A powerful tool for downloading activity data from Garmin Connect and automatically syncing it to the Coros platform, enabling cross-platform sports data management.

> **Important Note: This tool now supports multiple regions. Please do not use a VPN or proxy when using the Chinese region version, as it may cause login failures or prevent normal download of activity data.**
> **The gitignore file is already configured to ignore passwords and credentials, but if you want to upload locally used code to git, please double-check if you have modified it. If so, please update the gitignore file in a timely manner.**

## Features

### Garmin Activity Download
- Automatic login to Garmin Connect platform (supports MFA verification code)
- Batch loading and saving of activity data information
- Automatic download of activity .fit files (supports resumable downloads)
- Saving activity files according to a unified naming convention

### Coros Sync Function
- Automatic login to Coros platform
- Support for multiple regions: International, Chinese, and European regions
- Intelligent analysis of Garmin and Coros activities to find Garmin-exclusive activities
- Date-sorted, sequential upload of activity files to Coros
- Filtering of specific activity types (such as walking, indoor_climbing, bouldering)
- Support for whitelist configuration to manually specify activity pairs to skip
- Generation of detailed sync reports
- Support for multiple file storage services (Alibaba Cloud OSS for China region, AWS S3 for International/European regions)

### Activity Analysis Function
- Compare Garmin and Coros activity data
- Identify cases of mismatched activity types
- Generate three types of analysis reports:
  - Activity type mismatch report
  - Coros-only activities report
  - Garmin-only activities report
- Statistics on Coros activity type distribution

## Installation

Install the required dependencies using the following command:

```bash
pip install -r requirements.txt
```

Main dependency packages include:
- garminconnect
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
│   ├── downloader.py           # Activity download service
│   ├── analyzer.py             # Activity analysis service
│   └── syncer.py               # Activity sync service
├── storage/                    # Storage module
│   ├── __init__.py
│   └── oss_client.py           # OSS file upload
├── tools/                      # Utility tools
│   ├── __init__.py
│   ├── rename_coros_files.py   # Rename tool
│   └── improved_fit_parser.py  # FIT parser tool
├── config.py                   # Unified configuration
├── config_manager.py           # Configuration manager
├── main.py                     # Main entry point
├── requirements.txt            # Dependencies
├── config/                     # Configuration files
├── downloads/                  # Downloaded activity files
│   ├── garmin/                 # Garmin activity files
│   └── coros/                  # Coros activity files
├── reports/                    # Analysis reports
└── tokens/                     # Login tokens
    ├── garmin/                 # Garmin tokens
    └── coros/                  # Coros tokens
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
   - `config/sync_whitelist.txt`: Sync whitelist configuration (optional)

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

   **config/sync_whitelist.txt** (for specifying activity pairs to skip):
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

Run the main program for Garmin to Coros activity sync:

```bash
python main.py
```

The sync process will automatically:
- Download Garmin activities
- Download Coros activities
- Analyze and find activities that need to be synced
- Upload to Coros in date order
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
# Rename Coros files (fix activity type mismatch)
python tools/rename_coros_files.py

# Parse FIT files
python tools/improved_fit_parser.py
```

## Notes

1. **Important: For the Chinese region version, please do not use a VPN or proxy when using this tool**
2. On first run, if MFA is enabled, the program will prompt for a verification code
3. The program will automatically manage login tokens to avoid frequent logins
4. The sync process will automatically skip activities already existing in Coros
5. Activities of type walking, indoor_climbing, bouldering are filtered by default and will not be uploaded to Coros
6. Activity pairs in the whitelist will be automatically skipped, suitable for handling manually processed or special case activities
7. Please ensure a stable network connection, especially when batch downloading or uploading activities
8. Activity files will be named according to a unified format, including date, time, activity type, name, and ID

## Technical Notes

- Uses garminconnect library to interact with Garmin Connect API
- Uses urllib3 library to interact with Coros API
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

## License

This project is for personal learning and use only, please do not use it for commercial purposes.

## Disclaimer

When using this tool, please comply with the terms of service of Garmin Connect and Coros platforms. The use of this tool may violate the API usage policies of relevant platforms, and users should assume the risk themselves.

---

# Garmin Connect アクティビティダウンロードと Coros 同期ツール

Garmin Connect からアクティビティデータをダウンロードし、自動的に Coros プラットフォームに同期する強力なツールです。クロスプラットフォームのスポーツデータ管理を実現します。

> **重要な注意事項：このツールは複数の地域をサポートしています。中国地域版を使用する場合は、VPN やプロキシを使用しないでください。そうしないと、ログインに失敗したり、アクティビティデータの正常なダウンロードが妨げられたりする可能性があります。**
> **gitignore ファイルはすでにパスワードと認証情報を無視するように設定されていますが、ローカルで使用しているコードを git にアップロードする場合は、変更されていないか再度確認してください。変更されている場合は、gitignore ファイルを適時更新してください。**

## 機能特性

### Garmin アクティビティダウンロード機能
- Garmin Connect プラットフォームへの自動ログイン（MFA 検証コードに対応）
- アクティビティデータ情報の一括読み込みと保存
- アクティビティの .fit ファイルの自動ダウンロード（再開可能なダウンロードに対応）
- 統一された命名規則に従ってアクティビティファイルを保存

### Coros 同期機能
- Coros プラットフォームへの自動ログイン
- 複数の地域をサポート：国際版、中国版、欧州版
- Garmin と Coros のアクティビティをインテリジェントに分析し、Garmin 独占のアクティビティを見つける
- 日付でソートし、順序立ててアクティビティファイルを Coros にアップロード
- 特定のアクティビティタイプ（walking、indoor_climbing、bouldering など）をフィルタリング
- ホワイトリスト設定をサポートし、スキップするアクティビティペアを手動で指定
- 詳細な同期レポートの生成
- 複数のファイルストレージサービスをサポート：中国地域は Alibaba Cloud OSS、国際/欧州地域は AWS S3

### アクティビティ分析機能
- Garmin と Coros のアクティビティデータを比較
- アクティビティタイプが一致しないケースを特定
- 3種類の分析レポートを生成：
  - アクティビティタイプ不一致レポート
  - Coros 独占アクティビティレポート
  - Garmin 独占アクティビティレポート
- Coros アクティビティタイプ分布の統計

## 依存関係のインストール

以下のコマンドを使用して、必要な依存関係をインストールします：

```bash
pip install -r requirements.txt
```

主な依存パッケージは以下の通りです：
- garminconnect
- urllib3
- certifi
- requests
- oss2 (中国地域ユーザー必須)
- boto3 (国際/欧州地域ユーザー必須)

## プロジェクト構造

```
sync_garmin_to_coros/
├── clients/                    # API クライアントモジュール
│   ├── __init__.py
│   └── coros_client.py         # Coros API クライアント
├── services/                   # ビジネスサービスモジュール
│   ├── __init__.py
│   ├── downloader.py           # アクティビティダウンロードサービス
│   ├── analyzer.py             # アクティビティ分析サービス
│   └── syncer.py               # アクティビティ同期サービス
├── storage/                    # ストレージモジュール
│   ├── __init__.py
│   └── oss_client.py           # OSS ファイルアップロード
├── tools/                      # ユーティリティツール
│   ├── __init__.py
│   ├── rename_coros_files.py   # リネームツール
│   └── improved_fit_parser.py  # FIT パーサーツール
├── config.py                   # 統一設定
├── config_manager.py           # 設定マネージャー
├── main.py                     # メインエントリーポイント
├── requirements.txt            # 依存関係
├── config/                     # 設定ファイル
├── downloads/                  # ダウンロードしたアクティビティファイル
│   ├── garmin/                 # Garmin アクティビティファイル
│   └── coros/                  # Coros アクティビティファイル
├── reports/                    # 分析レポート
└── tokens/                     # ログイントークン
    ├── garmin/                 # Garmin トークン
    └── coros/                  # Coros トークン
```

## 使用方法

### 1. メイン同期機能

メインプログラムを実行して Garmin から Coros へのアクティビティ同期を行います：

```bash
python main.py
```

同期プロセスは自動的に以下を行います：
- Garmin アクティビティをダウンロード
- Coros アクティビティをダウンロード
- 同期が必要なアクティビティを分析して特定
- 日付順に Coros にアップロード
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
# Coros ファイルのリネーム（アクティビティタイプの不一致を修正）
python tools/rename_coros_files.py

# FIT ファイルの解析
python tools/improved_fit_parser.py
```

## 注意事項

1. **重要：中国地域版を使用する場合は、VPN やプロキシを使用しないでください**
2. 初回実行時、MFA が有効な場合、プログラムは検証コードの入力を求めます
3. プログラムはログイントークンを自動的に管理し、頻繁なログインを回避します
4. 同期プロセスは、Coros に既に存在するアクティビティを自動的にスキップします
5. walking、indoor_climbing、bouldering タイプのアクティビティはデフォルトでフィルタリングされ、Coros にアップロードされません
6. ホワイトリスト内のアクティビティペアは自動的にスキップされ、手動で処理されたアクティビティや特殊なケースに適しています
7. 特にバッチダウンロードやアップロードを行う場合は、安定したネットワーク接続を確保してください
8. アクティビティファイルは、日付、時刻、アクティビティタイプ、名前、ID を含む統一形式で命名されます

## 技術説明

- garminconnect ライブラリを使用して Garmin Connect API と対話
- urllib3 ライブラリを使用して Coros API と対話
- requests ライブラリを使用して HTTP リクエストを処理
- 複数の地域をサポート：国際版、中国版、欧州版
- 複数のストレージサービスをサポート：Alibaba Cloud OSS と AWS S3

## 更新履歴

- v1.0.0: 初期バージョン、Garmin アクティビティダウンロード機能を追加
- v1.1.0: Coros アクティビティ同期機能を追加
- v1.2.0: アクティビティ分析とレポート生成機能を追加
- v1.3.0: 同期ロジックを最適化、ファイルストレージサポートを追加
- v1.4.0: アクティビティホワイトリスト機能を追加、スキップするアクティビティペアの手動指定をサポート
- v1.5.0: 複数地域サポートを追加（国際版、中国版、欧州版）
- v1.6.0: 依存関係を更新、ログインフローを最適化
- v2.0.0: プロジェクト構造をリファクタリング、モジュラー設計、統一設定管理

## ライセンス

このプロジェクトは個人学習および使用のみを目的としています。商用目的では使用しないでください。

## 免責事項

このツールを使用する際は、Garmin Connect および Coros プラットフォームの利用規約を遵守してください。このツールの使用は、関連プラットフォームの API 使用ポリシーに違反する可能性があり、ユーザー自身のリスクで使用してください。
