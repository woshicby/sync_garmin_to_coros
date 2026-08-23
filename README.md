# Garmin Connect 与 Coros 双向活动同步工具

## 语言切换 / Language Switch / 言語切り替え

[![中文](https://img.shields.io/badge/中文-Chinese-red)](#garmin-connect-与-coros-双向活动同步工具)
[![English](https://img.shields.io/badge/English-%E8%8B%B1%E6%96%87-blue)](#garmin-connect-and-coros-bidirectional-activity-sync-tool)
[![日本語](https://img.shields.io/badge/日本語-Japanese-green)](#garmin-connect-と-coros-の双向アクティビティ同期ツール)

> **注意：英文和日语版本内容由AI生成，可能存在翻译误差，请以中文版本为准。**
> **Note: English and Japanese versions are AI-generated and may contain translation errors. Please refer to the Chinese version for accuracy.**
> **注意：英語版と日本語版はAIによって生成されており、翻訳エラーが含まれている可能性があります。正確性については、中国語版を参照してください。**

一个强大的工具，实现 Garmin Connect 和 Coros 平台之间的双向活动同步，自动管理跨平台运动数据。

> **重要说明：本工具仅支持国服 Garmin Connect，使用时请不要挂梯子或使用 VPN，否则可能导致登录失败或无法正常下载活动数据。**
> **gitignore 里已经设置好忽略密码和凭证，但若要将本地使用的代码上传到 git，请再次确认是否修改过。若有修改，请及时更新 gitignore 文件。**

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
- 生成三种分析报告：活动类型不匹配报告 / Coros 独有活动报告 / Garmin 独有活动报告
- 统计活动类型分布

### 辅助工具
- **Keep 历史活动上传工具**：批量上传 Keep 运动记录到 Garmin 和 Coros
- **Coros 文件重命名工具**：根据 Garmin 活动类型修正 Coros 文件的活动类型名称
- **FIT 文件名修正工具**（归档）：批量将 FIT 文件名中的日期时间修正为文件内部记录的开始时间
- **FIT 文件解析工具**（归档）：解析 FIT 文件并提取时间戳信息

## 项目结构

```
sync_garmin_to_coros/
├── main.py                      # 主入口：下载 → 分析 → 同步 → 重新下载
├── core/                        # 核心包（下载 / 分析 / 同步 / 客户端 / 配置）
│   ├── config.py                #   路径常量 + 配置管理器（含密码加解密）
│   ├── downloader.py            #   Garmin / Coros 活动下载（含登录逻辑）
│   ├── analyzer.py              #   活动差异分析，生成报告
│   ├── syncer.py                #   Garmin ↔ Coros 同步上传
│   ├── coros_client.py          #   Coros 平台 API 客户端
│   ├── oss_client.py            #   阿里云 OSS / AWS S3 上传客户端
│   └── fit_parser.py            #   FIT 文件时间提取（统一入口）
├── scripts/                     # 常用脚本
│   ├── upload_keep_activities.py   # Keep 历史活动批量上传
│   └── rename_coros_files.py       # Coros 文件活动类型修正
├── archive/                     # 一次性调试工具（留档，一般不再使用）
│   ├── rename_fit_files.py
│   └── improved_fit_parser.py
├── tests/                       # pytest 测试（fit_parser / login / analyzer）
├── config/                      # 配置文件目录（gitignore）
│   └── sync_whitelist.md        # 同步白名单
├── downloads/                   # 下载的活动文件（gitignore）
│   ├── garmin/                  # Garmin 活动文件
│   ├── coros/                   # Coros 活动文件
│   ├── KEEP_merged/             # Keep 合并活动文件
│   └── KEEP_phone/              # Keep 手机活动文件
├── reports/                     # 分析报告目录（gitignore）
├── tokens/                      # 登录令牌目录（gitignore）
│   ├── garmin/                  # Garmin 令牌
│   └── coros/                   # Coros 令牌
├── requirements.txt             # 依赖列表
├── LICENSE
└── README.md
```

## 环境准备

推荐使用 Python 3.12（Homebrew）创建独立虚拟环境：

```bash
# 创建虚拟环境（macOS）
/opt/homebrew/bin/python3.12 -m venv .venv-macos

# 安装依赖
.venv-macos/bin/pip install -r requirements.txt
```

> 注：仓库中保留的 `.venv-windows/` 是从 Windows 迁移项目时带过来的旧环境，**不可在 macOS 使用**，仅作参考保留。

主要依赖包：
- garminconnect / garth —— Garmin Connect API
- garmin-fit-sdk —— FIT 文件解析
- requests / urllib3 / certifi —— HTTP 基础
- oss2 —— 中国区存储（必须）
- boto3 —— 国际区 / 欧洲区存储（必须）

## 配置说明

### 区域配置

| 区域 | API 地址 | 存储服务 |
|------|---------|---------|
| 国际区 | teamapi.coros.com | AWS S3 |
| 中国区 | teamcnapi.coros.com | 阿里云 OSS |
| 欧洲区 | teameuapi.coros.com | AWS S3 |

### 配置文件

1. 首次运行前，程序会自动创建所需的配置文件和目录结构。
2. 配置文件位置：
   - `config/garmin_config.json`：Garmin Connect 登录配置
   - `config/coros_config.json`：Coros 登录配置
   - `config/sync_whitelist.md`：同步白名单配置（可选）

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

> 密码以 Base64 编码存储，程序读写时自动加解密。

**config/sync_whitelist.md**（指定需要跳过的活动对，每行一对）：
```
# 格式：佳明活动完整文件名 高驰活动完整文件名
```

## 使用方法

### 1. 主同步功能

```bash
.venv-macos/bin/python main.py
```

主流程按 5 个步骤执行：
1. **下载活动文件**（Coros → Garmin；失败会提示重试 / 继续 / 退出）
2. **分析活动差异**
3. **同步佳明活动到高驰**
4. **同步高驰活动到佳明**
5. **上传后重新下载**（仅当有上传时）

### 2. 单独使用各模块

```bash
# 仅下载
.venv-macos/bin/python -c "from core import download_garmin_activities; download_garmin_activities()"

# 仅分析
.venv-macos/bin/python -c "from core import analyze_activities; analyze_activities()"
```

### 3. 使用辅助工具

```bash
# Keep 历史活动批量上传（注意：需先确认 downloads/ 下的 Keep 目录）
.venv-macos/bin/python scripts/upload_keep_activities.py

# Coros 文件活动类型修正
.venv-macos/bin/python scripts/rename_coros_files.py
```

### 4. 运行测试

```bash
.venv-macos/bin/python -m pytest tests/ -v
```

## 登录机制说明

Garmin 登录采用"令牌优先，密码兜底"策略：

1. **令牌登录**：优先使用 `tokens/garmin/` 下已保存的 OAuth 令牌
2. **令牌失效回退**：令牌过期/失效时，自动提示重新输入用户名和密码（支持 MFA 验证码）
3. **密码重试**：密码错误可重新输入；网络等非认证错误不会无限重试
4. 登录成功后自动保存新令牌，下次直接复用

> 如果你的 Garmin 登录一直失败，请检查：令牌是否过期（删除 `tokens/garmin/` 下旧文件重登）、密码是否正确、是否误开代理/VPN。

## FIT 文件时间提取说明

- 使用 `garmin_fit_sdk` 解析 FIT 文件，优先读取 `activity_mesgs` 中的 `local_timestamp` 与 `timestamp` 差值计算时区偏移
- 若文件无时区信息，回退到默认 UTC+8
- 提取逻辑统一在 `core/fit_parser.py`，下载与工具脚本共用

## 注意事项

- 本工具仅支持国服 Garmin Connect，请勿挂梯子或使用 VPN
- 上传操作不可逆，同步前请确认白名单与报告
- 批量下载/上传时程序有 1-1.5 秒的请求间隔，避免触发平台限流
- 大量历史活动首次同步可能耗时较长，属正常现象

## 更新日志

### 2026-08-23（v2.0 结构重构）
- **目录重组**：`services/` `clients/` `storage/` 合并为 `core/` 包；`tools/` 拆分到 `scripts/`（常用）与 `archive/`（留档）
- **配置合并**：`config.py` + `config_manager.py` 合并为 `core/config.py`；配置路径改为绝对路径（不再依赖运行目录）
- **FIT 解析统一**：抽取 `core/fit_parser.py`，消除 downloader 与工具脚本中的重复实现
- **登录流程修复**：Garmin 令牌失效时回退到用户名/密码交互登录（可重试、防死循环），不再静默跳过
- **下载失败不再静默**：main.py 下载失败时提供 重试 / 继续 / 退出 选项
- **控制台输出整理**：步骤分隔线标题 + 单行覆盖式下载进度，不再逐条刷屏
- **新增测试**：`tests/` 覆盖 FIT 解析、登录回退、活动匹配（13 个用例）

### 历史版本
- 2026-06：支持 Keep 历史活动批量上传
- 2026-05：支持多区域配置（国际区 / 中国区 / 欧洲区）
- 2026-04：Coros 平台支持、双向同步

## 许可证

MIT License

## 免责声明

本工具仅供个人学习与使用。使用本工具同步数据时请遵守 Garmin、Coros 及 Keep 平台的服务条款。因使用本工具产生的一切后果由使用者自行承担。

---

<a id="garmin-connect-and-coros-bidirectional-activity-sync-tool"></a>

## English (Summary)

A tool that syncs activities bidirectionally between Garmin Connect and Coros.

- **Sync**: find platform-exclusive activities and upload them to the other side
- **Download**: auto-login (token-first, password fallback with MFA), download .fit files, extract precise start times (UTC+8)
- **Structure**: `core/` (download/analyze/sync/clients/config), `scripts/` (keep-upload, rename), `archive/` (one-off tools), `tests/` (pytest)
- **Setup**: `python3.12 -m venv .venv-macos && .venv-macos/bin/pip install -r requirements.txt`
- **Run**: `.venv-macos/bin/python main.py` (5 steps: download → analyze → sync Garmin→Coros → sync Coros→Garmin → re-download)
- **Login**: expired token falls back to interactive email/password login (retryable, MFA supported); non-auth errors do NOT retry
- **Tests**: `.venv-macos/bin/python -m pytest tests/ -v`

**Note**: Garmin CN only — do NOT use proxy/VPN.

---

<a id="garmin-connect-と-coros-の双向アクティビティ同期ツール"></a>

## 日本語 (概要)

Garmin Connect と Coros の間でアクティビティを双方向に同期するツールです。

- **同期**: 各プラットフォーム独占のアクティビティを検出し、相手側にアップロード
- **ダウンロード**: 自動ログイン（トークン優先・パスワードフォールバック、MFA 対応）、.fit ファイルのダウンロード、正確な開始時刻の抽出（UTC+8）
- **構成**: `core/`（ダウンロード/分析/同期/クライアント/設定）、`scripts/`（Keep アップロード、リネーム）、`archive/`（旧ツール）、`tests/`（pytest）
- **セットアップ**: `python3.12 -m venv .venv-macos && .venv-macos/bin/pip install -r requirements.txt`
- **実行**: `.venv-macos/bin/python main.py`（5 ステップ：ダウンロード → 分析 → 同期 → 再ダウンロード）
- **ログイン**: トークン失効時はメール/パスワードの対話ログインにフォールバック（再試行可、MFA 対応）
- **テスト**: `.venv-macos/bin/python -m pytest tests/ -v`

**注意**: 中国版 Garmin のみ対応 — プロキシ/VPN は使用しないでください。
