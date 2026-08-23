# scripts/ — 常用脚本

独立运行的辅助脚本，复用 `core/` 的逻辑，不复制代码。

## 脚本列表

### upload_keep_activities.py — Keep 历史活动批量上传

将 Keep 运动 App 的历史活动（FIT 文件）批量上传到 Garmin 和 Coros。

```bash
.venv-macos/bin/python scripts/upload_keep_activities.py
```

- 扫描 `downloads/KEEP_merged` 与 `downloads/KEEP_phone` 两个 Keep 活动目录（中文类型自动映射为英文:行走→walking、健身→strength_training、瑜伽→yoga 等）
- 登录复用 `core.downloader._login_garmin` 与 `core.syncer._init_coros_client`（令牌优先，失效回退密码）
- 每个文件分别上传 Garmin 与 Coros，失败不影响后续
- 生成 `reports/others_upload_report.txt` 详细报告

### rename_coros_files.py — Coros 文件活动类型修正

根据 Garmin 活动类型修正 Coros 文件名的活动类型名称（如 `indoor_cardio` → `strength_training`）。

```bash
.venv-macos/bin/python scripts/rename_coros_files.py
```

- 内部调用 `core.analyzer.analyze_activities()` 获取类型分布
- 适用于历史文件名类型标注错误的情况

## 约定

- 脚本可独立运行（`if __name__ == '__main__'`）
- 登录、客户端等复用 `core/`，**不要**在脚本里重新实现
