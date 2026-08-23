# tests/ — 自动化测试

基于 pytest 的回归测试，覆盖核心逻辑。

## 运行方式

```bash
.venv-macos/bin/python -m pytest tests/ -v
```

## 测试文件

| 文件 | 覆盖内容 | 说明 |
|------|---------|------|
| `test_fit_parser.py` | FIT 时间提取、时区偏移计算 | 使用 `downloads/garmin/` 下的**真实 FIT 文件**，验证提取时间与文件名日期一致 |
| `test_login.py` | Garmin 登录回退/重试逻辑 | mock `garminconnect`，不触网：令牌失效回退密码、密码重试、网络错误不重试、输入中断不死循环 |
| `test_analyzer.py` | 活动重复匹配、运动类型映射 | 纯函数测试 |

## 测试约定

- `conftest.py` 负责把项目根加入 `sys.path`
- 登录测试通过 mock 隔离网络与配置文件写入（不会污染真实 `config/` 与 `tokens/`）
- FIT 解析测试依赖 `downloads/garmin/` 有真实数据；目录为空时相关用例会失败（提示需先下载）
