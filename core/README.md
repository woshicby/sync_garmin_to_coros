# core/ — 核心包

项目核心逻辑所在，包含下载、分析、同步、平台客户端与配置管理。

## 模块一览

| 模块 | 职责 | 主要函数/类 |
|------|------|------------|
| `config.py` | 路径常量、区域配置、运动类型映射、配置管理器（JSON 读写 + 密码加解密） | `DIRS` / `SPORT_TYPE_MAPPING` / `ConfigManager` / `get_garmin_config()` |
| `downloader.py` | Garmin / Coros 活动下载与登录 | `download_garmin_activities()` / `download_coros_activities()` / `_login_garmin()` |
| `analyzer.py` | 活动差异分析，生成报告 | `analyze_activities()` / `_find_duplicate_activities()` |
| `syncer.py` | Garmin ↔ Coros 双向同步上传 | `sync_activities()` / `sync_coros_to_garmin()` |
| `coros_client.py` | Coros 平台 API 客户端 | `CorosClient` / `login_coros()` |
| `oss_client.py` | 阿里云 OSS / AWS S3 上传 | `OssClient` / `get_oss_client()` |
| `fit_parser.py` | FIT 文件开始时间提取（统一入口） | `extract_fit_start_time()` / `get_tz_offset()` |

## 依赖关系

```
main.py → core（包导出）
downloader → config, fit_parser, coros_client
syncer → config, coros_client, oss_client, downloader
analyzer → config
coros_client → config
oss_client → config
```

## 约定

- 模块顶部统一 `sys.path.insert` 保证以任意工作目录运行时都能找到 `core` 包
- 内部函数以下划线开头（如 `_login_garmin`），跨模块复用时可被 `scripts/` 导入
- 所有输出使用中文，进度使用单行覆盖式，避免刷屏

## 修改提示

- 改 `config.py` 的 `DIRS` 会影响所有路径依赖——先跑 `tests/test_fit_parser.py` 确认
- 改登录逻辑后跑 `tests/test_login.py`（token 回退 / 密码重试 / 防死循环）
