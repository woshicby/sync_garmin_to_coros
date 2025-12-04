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
- 过滤掉特定活动类型（如 walking）
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
- selenium
- webdriver-manager
- requests
- beautifulsoup4
- lxml

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
   - `config/oss_config.json`: 文件存储服务配置（可选）
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

   **config/oss_config.json** (用于文件存储):
   ```json
   {
     "appId": "your_app_id",
     "sign": "your_sign_key"
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

### 3. Coros 活动下载

单独下载 Coros 活动：

```bash
python coros_download.py
```

### 4. 活动分析

分析已下载的活动文件：

```bash
python analyze_activity_files.py
```

分析结果将保存在 `reports` 目录下。

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

- 使用 selenium 自动化工具与 Garmin Connect 交互
- 使用 urllib3 库与 Coros API 交互
- 使用 requests 库处理 HTTP 请求
- 支持多区域的 Garmin Connect 和 Coros 平台
- 支持多种存储服务：阿里云 OSS 和 AWS S3

## 文件结构

- `sync_garmin_to_coros.py`: 主程序，实现数据同步功能
- `garmin_download.py`: Garmin 活动下载功能
- `coros_download.py`: Coros 活动下载功能
- `coros_client.py`: Coros API 客户端
- `oss_client.py`: 文件存储服务客户端
- `analyze_activity_files.py`: 活动文件分析工具
- `improved_fit_parser.py`: FIT 文件解析工具
- `utils.py`: 通用工具函数
- `config/`: 配置文件目录
- `downloads/`: 下载的活动文件目录
  - `downloads/garmin/`: Garmin 活动文件
  - `downloads/coros/`: Coros 活动文件
- `reports/`: 分析结果目录
- `tokens/`: 登录令牌存储目录
- `activity_samples/`: 活动样本文件目录

## 更新日志

- v1.0.0: 初始版本，添加 Garmin 活动下载功能
- v1.1.0: 添加 Coros 活动同步功能
- v1.2.0: 添加活动分析和报告生成功能
- v1.3.0: 优化同步逻辑，添加文件存储支持
- v1.4.0: 添加活动白名单功能，支持手动指定需要跳过的活动对
- v1.5.0: 支持多区域配置（国际区、中国区、欧洲区）
- v1.6.0: 更新依赖库，优化登录流程

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
- Filtering of specific activity types (such as walking)
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
- selenium
- webdriver-manager
- requests
- beautifulsoup4
- lxml

## Configuration Instructions

### Regional Configuration

The tool supports three regions with different API endpoints and storage services:

| Region | Garmin API | Coros API | Storage Service |
|--------|------------|-----------|----------------|  
| International | connectapi.garmin.com | teamapi.coros.com | AWS S3 |
| Chinese | connectapi.garmin.cn | teamapi.coros.com.cn | Alibaba Cloud OSS |
| European | connectapi.garmin.eu | teamapi.coros.com | AWS S3 |

1. Before running for the first time, the program will automatically create the required directory structure:

   ```
   .
   ├── config/              # Configuration files directory
   ├── downloads/           # Downloaded activity files directory
   │   ├── coros/          # Coros activity files
   │   └── garmin/         # Garmin activity files
   ├── logs/               # Log files directory
   └── reports/            # Analysis reports directory
   ```

   Additionally, you can create an optional whitelist configuration file:

   **config/sync_whitelist.txt** (for specifying activity pairs to skip):
   ```
   # Sync whitelist configuration file
   # Format: Garmin activity full filename Coros activity full filename
   # Each line represents a pair of activities to skip
   # Example:
   20230711-174102-multi_sport-莆田市复合运动-256118606.fit 20230711-175127-running-461428804292739075.fit
   ```
   
   **How to use the whitelist:**
   1. Use when you have manually uploaded a Garmin activity to Coros, or when you want to skip automatic sync for specific activities
   2. The format must be strictly followed: Garmin activity filename + space + Coros activity ID
   3. You can obtain the correspondence of synced activities through the analysis report (`reports/sync_report.txt`)
   4. Activity pairs in the whitelist will be automatically skipped during the sync process to avoid duplicate uploads
   5. Comment lines start with # and will not be parsed by the program

   Main configuration files:

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

   **config/oss_config.json** (for file storage):
   ```json
   {
     "appId": "your_app_id",
     "sign": "your_sign_key"
   }
   ```

2. Password/Credential Storage Instructions:
   - Passwords are stored in base64 encoded format, and the program will automatically decode them
   - For security reasons, please do not save passwords in plain text format

## Usage

### 1. Main Sync Function

Run the main program for Garmin to Coros activity sync:

```bash
python sync_garmin_to_coros.py
```

The sync process will automatically:
- Download Garmin activities
- Download Coros activities
- Analyze and find activities that need to be synced
- Upload to Coros in date order
- Generate sync report

### 2. Garmin Activity Download

Download Garmin activities separately:

```bash
python garmin_download.py
```

### 3. Coros Activity Download

Download Coros activities separately:

```bash
python coros_download.py
```

### 4. Activity Analysis

Analyze downloaded activity files:

```bash
python analyze_activity_files.py
```

Analysis results will be saved in the `reports` directory.

## Notes

1. **Important: For the Chinese region version, please do not use a VPN or proxy when using this tool**
2. On first run, if MFA is enabled, the program will prompt for a verification code
3. The program will automatically manage login tokens to avoid frequent logins
4. The sync process will automatically skip activities already existing in Coros
5. Activities of type walking are filtered by default and will not be uploaded to Coros
6. Activity pairs in the whitelist will be automatically skipped, suitable for handling manually processed or special case activities
7. Please ensure a stable network connection, especially when batch downloading or uploading activities
8. Activity files will be named according to a unified format, including date, time, activity type, name, and ID

## Technical Notes

- Uses selenium with webdriver-manager to interact with Garmin Connect
- Uses urllib3 library to interact with Coros API
- Uses requests library to handle HTTP requests
- Supports multiple regions: International, Chinese, and European regions
- Supports multiple storage services: Alibaba Cloud OSS and AWS S3

## File Structure

- `sync_garmin_to_coros.py`: Main program, implementing data sync functionality
- `garmin_download.py`: Garmin activity download functionality
- `coros_download.py`: Coros activity download functionality
- `coros_client.py`: Coros API client
- `oss_client.py`: File storage service client
- `analyze_activity_files.py`: Activity file analysis tool
- `improved_fit_parser.py`: FIT file parsing tool
- `utils.py`: General utility functions
- `config/`: Configuration file directory
- `downloads/`: Downloaded activity file directory
  - `downloads/garmin/`: Garmin activity files
  - `downloads/coros/`: Coros activity files
- `reports/`: Analysis results directory
- `tokens/`: Login token storage directory
- `activity_samples/`: Activity sample files directory

## Changelog

- v1.0.0: Initial version, added Garmin activity download functionality
- v1.1.0: Added Coros activity sync functionality
- v1.2.0: Added activity analysis and report generation functionality
- v1.3.0: Optimized sync logic, added file storage support
- v1.4.0: Added activity whitelist functionality, supporting manual specification of activity pairs to skip
- v1.5.0: Added multiple region support (International, Chinese, European)
- v1.6.0: Added Coros activity download functionality, updated technical implementation using selenium

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
- 特定のアクティビティタイプ（walking など）をフィルタリング
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
- selenium
- webdriver-manager
- requests
- beautifulsoup4
- lxml

## 設定の説明

### 地域設定

このツールは、異なる API エンドポイントとストレージサービスを持つ 3 つの地域をサポートしています：

| 地域 | Garmin API | Coros API | ストレージサービス |
|------|------------|-----------|----------------|
| 国際版 | connectapi.garmin.com | teamapi.coros.com | AWS S3 |
| 中国版 | connectapi.garmin.cn | teamapi.coros.com.cn | Alibaba Cloud OSS |
| 欧州版 | connectapi.garmin.eu | teamapi.coros.com | AWS S3 |

1. 初回実行前に、プログラムは必要なディレクトリ構造を自動的に作成します：

   ```
   .
   ├── config/              # 設定ファイルディレクトリ
   ├── downloads/           # ダウンロードしたアクティビティファイルディレクトリ
   │   ├── coros/          # Coros アクティビティファイル
   │   └── garmin/         # Garmin アクティビティファイル
   ├── logs/               # ログファイルディレクトリ
   └── reports/            # 分析レポートディレクトリ
   ```

2. オプションのホワイトリスト設定ファイル：

   **config/sync_whitelist.txt**（スキップするアクティビティペアを指定するため）：
   ```
   # 同期ホワイトリスト設定ファイル
   # 形式：Garminアクティビティの完全なファイル名 Corosアクティビティの完全なファイル名
   # 各行はスキップするアクティビティのペアを表します
   # 例：
      20230711-174102-multi_sport-莆田市复合运动-256118606.fit 20230711-175127-running-461428804292739075.fit
   ```
   
   **ホワイトリストの使用方法：**
   1. 特定のGarminアクティビティをCorosに手動でアップロードした場合、または特定のアクティビティの自動同期をスキップしたい場合に使用します
   2. 形式は厳密に守ってください：Garminアクティビティファイル名 + スペース + CorosアクティビティID
   3. 分析レポート（`reports/sync_report.txt`）を通じて、同期済みアクティビティの対応関係を取得できます
   4. ホワイトリスト内のアクティビティペアは同期プロセス中に自動的にスキップされ、重複アップロードが回避されます
   5. コメント行は#で始まり、プログラムによって解析されません

   主要な設定ファイル：

   **config/garmin_config.json**：
   ```json
   {
     "email": "your_garmin_email@example.com",
     "password": "base64_encoded_password"
   }
   ```

   **config/coros_config.json**：
   ```json
   {
     "email": "your_coros_email@example.com",
     "password": "base64_encoded_password"
   }
   ```

   **config/oss_config.json**（ファイルストレージ用）：
   ```json
   {
     "appId": "your_app_id",
     "sign": "your_sign_key"
   }
   ```

3. パスワード/認証情報の保存に関する注意事項：
   - パスワードは base64 エンコード形式で保存され、プログラムによって自動的にデコードされます
   - セキュリティ上の理由から、平文形式でパスワードを保存しないでください

## 使用方法

### 1. メイン同期機能

メインプログラムを実行して、Garmin から Coros へのアクティビティ同期を行います：

```bash
python sync_garmin_to_coros.py
```

同期プロセスは自動的に：
- Garminアクティビティをダウンロード
- Corosアクティビティをダウンロード
- 同期する必要のあるアクティビティを分析・見つける
- 日付順にCorosにアップロード
- 同期レポートを生成

### 2. Garmin アクティビティダウンロード

Garmin アクティビティを単独でダウンロード：

```bash
python garmin_download.py
```

### 3. Coros アクティビティダウンロード

Coros アクティビティを単独でダウンロード：

```bash
python coros_download.py
```

### 4. アクティビティ分析

ダウンロードしたアクティビティファイルを分析：

```bash
python analyze_activity_files.py
```

分析結果は `reports` ディレクトリに保存されます。

## 注意事項

1. **重要：中国地域版を使用する場合は、VPN やプロキシを使用しないでください**
2. 初回実行時、MFA が有効になっている場合、プログラムは検証コードの入力を要求します
3. プログラムは自動的にログイントークンを管理し、頻繁なログインを回避します
4. 同期プロセス中に、Coros にすでに存在するアクティビティは自動的にスキップされます
5. walking タイプのアクティビティはデフォルトでフィルタリングされ、Coros にアップロードされません
6. ホワイトリスト内のアクティビティペアは自動的にスキップされ、手動で処理されたアクティビティや特殊なケースのアクティビティに適しています
7. 特に一括ダウンロードやアップロードを行う際には、安定したネットワーク接続を確保してください
8. アクティビティファイルは統一された形式で命名され、日付、時間、アクティビティタイプ、名前、ID が含まれます

## 技術的な説明

- selenium と webdriver-manager を使用して Garmin Connect と対話
- urllib3 ライブラリを使用して Coros API と対話
- requests ライブラリを使用して HTTP リクエストを処理
- 複数の地域をサポート：国際版、中国版、欧州版
- 複数のストレージサービスをサポート：Alibaba Cloud OSS と AWS S3
- 整理されたディレクトリ構造で自動的なファイル管理を実装
- 安全なパスワードストレージのために base64 エンコーディングを使用

## ファイル構造

- `sync_garmin_to_coros.py`：メインプログラム、データ同期機能を実装
- `garmin_download.py`：Garmin アクティビティダウンロード機能
- `coros_download.py`：Coros アクティビティダウンロード機能
- `coros_client.py`：Coros API クライアント
- `analyze_activity_files.py`：アクティビティファイル分析ツール
- `config/`：設定ファイルディレクトリ
  - `garmin_config.json`：Garmin ログイン設定
  - `coros_config.json`：Coros ログイン設定
  - `oss_config.json`：ストレージサービス設定
  - `sync_whitelist.txt`：同期ホワイトリスト設定
- `downloads/`：ダウンロードしたアクティビティファイルディレクトリ
  - `garmin/`：Garmin .fit アクティビティファイル
  - `coros/`：Coros アクティビティファイル
- `logs/`：ログファイルディレクトリ
- `reports/`：分析レポートディレクトリ

## 更新履歴

- v1.0.0：初期バージョン、Garmin アクティビティダウンロード機能を追加
- v1.1.0：Coros アクティビティ同期機能を追加
- v1.2.0：アクティビティ分析とレポート生成機能を追加
- v1.3.0：同期ロジックを最適化し、ファイルストレージサポートを追加
- v1.4.0：アクティビティホワイトリスト機能を追加、スキップするアクティビティペアの手動指定をサポート
- v1.5.0：複数の地域サポート（国際版、中国版、欧州版）を追加
- v1.6.0：Coros アクティビティダウンロード機能を追加、selenium を使用した技術実装を更新

## ライセンス

このプロジェクトは個人の学習と使用のみを目的としており、商用目的での使用は固く禁止されています。

## 免責事項

このツールを使用する際は、Garmin Connect および Coros プラットフォームの利用規約を遵守してください。このツールの使用は関連プラットフォームの API 使用ポリシーに違反する可能性があり、ユーザーは自己責任でリスクを負うものとします。
