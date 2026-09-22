# TikHub 接入验收样例（2026-09-20）

真实调用产出，非构造数据。用于说明该通道能拿到什么。

| 文件 | 内容 | 来源命令 |
|---|---|---|
| `search_sample.json` | 抖音搜索「精华液」近 7 天 5 条作品（标题/作者/URL/互动） | `toolbox.py search-douyin` |
| `detail_sample.json` | 单作品详情：播放/点赞/评论/转发/收藏 + 命中的接口路由 | `toolbox.py douyin-detail` |
| `transcript_sample.json` | 该作品整条口播转写，33 段带时间戳 | `toolbox.py audio` → `toolbox.py transcribe` |

样例作品是「防脱健发精华液」类广告。抽帧后 OCR 另读到：
`森之宣言防脱健发精华液  国妆特字202410635` + 合规话术「非医疗暗示 / 非前后对比 / 非夸大效果」。

两点注意：

1. `play_count` 在源数据里为 0 但互动为正，适配器按「未知」处理并在 `metric_warnings` 标注，不代表 0 播放。
2. 抖音 CDN 直链有时效（`cdn_url_expired`），取到后需及时下载。

凭据配置位置：`~/.config/content-creative-intelligence/tikhub.json`（键名 `api_token`，权限 600）。
