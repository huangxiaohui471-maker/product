# 成分趋势榜单 Demo

本目录合并自独立成分趋势 Demo，当前作为工作台的独立模块保留，不覆盖原有页面。

## 运行

```bash
python3 -m http.server 4177 --directory ingredient-radar-demo
open http://127.0.0.1:4177/
```

## 每日采集

`scripts/collector.py` 会读取 `sources.json` 中的授权平台页面，生成：

- `data/latest.json`：最新各国家成分线索
- `data/history.json`：按日期保存的历史信号
- `../logs/collector.log`：采集日志

页面会优先读取 `data/latest.json`；若当天没有可验证成分，则保留 Demo 数据并显示不可判定状态。平台需要登录或改用授权 API 时，应只修改 `sources.json`，不要把账号密码写入代码。
