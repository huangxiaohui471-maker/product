# 同行流量雷达 · 使用说明

每天自动跑一遍，产出**六维**情报：同行的账号与视频、小红书种草笔记、TikTok 海外内容、商品卖点、人群痛点、销量。
两条通道配合：**TikHub 免登录通道**管内容与商品（抖音 / 小红书 / TikTok / TikTok Shop），**浏览器通道（蝉妈妈）**管人群与销量。

## 每天你会拿到什么

| 文件 | 内容 |
|---|---|
| `同行雷达/对标榜单_<日期>.html` | 看板，7 个板块，从素材到人群痛点一屏看完 |
| `同行雷达/csv/对标素材榜.csv` | 该抄哪条内容，排序即拆解优先级 |
| `同行雷达/csv/对标账号榜.csv` | 全部过门槛账号，含粉丝、均赞、赞粉比 |
| `同行雷达/csv/账号深挖.csv` | 深挖过的账号：爆款率、**美妆占比**、该怎么用 |
| `同行雷达/csv/小红书种草榜.csv` | 小红书爆款笔记，含收藏数、收藏赞比 |
| `同行雷达/csv/小红书账号榜.csv` | 内容型账号，按代表作热度排序 |
| `同行雷达/csv/TikTok素材榜.csv` | 海外爆款视频，含播放 / 赞 / 评 / 转 / 藏 / 地区 |
| `同行雷达/csv/TikTok账号榜.csv` | 海外内容型账号，含粉丝、场均播放、低粉高赞标记 |
| `同行雷达/csv/卖点分布.csv` | 同行都在讲什么卖点，各覆盖多少商品 |
| `同行雷达/csv/成分分布.csv` | 卖点靠什么成分兑现 |
| `同行雷达/csv/人群痛点榜.csv` | 用户自己说出来的问题（2500+ 词，带曝光与销量） |
| `同行雷达/csv/抖音热销商品榜.csv` | 美妆在榜商品，昨日销量 / 销量结构 / 带货规模 |
| `同行雷达/csv/TikTok商品榜.csv` | 多区域在售商品，销量 / 价格 / 评分 |

## 六个维度分别解决什么

| 维度 | 回答的问题 | 通道 | 今天实测 |
|---|---|---|---|
| 抖音账号与视频 | 谁在起量？该抄哪条内容？ | TikHub 抖音 | 52 词 → 23,233 视频 → 663 个过门槛账号 |
| 小红书种草 | 内容型账号在讲什么干货？谁不挂车也能起量？ | TikHub 小红书 | 6 词 → 106 条笔记 → 102 个账号 |
| TikTok 海外内容 | 欧美/东南亚谁在拍、怎么拍？ | TikHub TikTok | 6 词 → 120 条视频 → 111 个账号（US 占 59） |
| 商品与卖点 | 同行在卖什么？卖点怎么讲？ | TikHub TikTok Shop | 35 词 × 4 区域 → 2,710 个在售商品 |
| 人群 | 用户自己说的问题是什么？ | 浏览器 / 蝉妈妈 | 2,509 个痛点词 |
| 销量 | 这个赛道一天能卖多少？ | 浏览器 / 蝉妈妈 | 抖音美妆 50 条在榜商品 |

**人群这一维是整条链路里最值钱的**：痛点词不是我们猜的，是抖音上真实出现、带曝光量和成交量的表述。实测美妆护肤品类第一是「卡粉」（关联 86 条视频、470w+ 曝光、1.8 万销量），后面是脱妆、皮肤干燥、毛孔粗大、暗沉、黑眼圈 —— **这些词直接就是选题标题和视频前 3 秒的开场句**。

## 手动跑（想换词或换时间窗时）

```bash
PY=/Users/huizidemac/.workbuddy/binaries/python/versions/3.13.12/bin/python3
RADAR=~/.workbuddy/skills/run-work-flywheel/scripts/adapters
PROJ=/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47
D=_build/runs/$(date +%F)
cd $PROJ

# ① 账号与视频（中文关键词）
$PY $RADAR/rival_radar.py discover --terms-file _build/config/rival_terms.json --days 7 --out $D-rival.json
$PY $RADAR/rival_radar.py deep --from-discover $D-rival.json --top 12 --top-posts 25 --out $D-deep.json

# ② 小红书种草（复用 `_build/config/rival_xhs_terms.json`，脚本内已带 6 秒串行间隔）
$PY $RADAR/rival_xhs.py discover --terms-file _build/config/rival_xhs_terms.json --pages 1 --out $D-xhs.json

# ③ TikTok 海外内容侧（**英文词**，脚本内已带 7 秒串行间隔）
$PY $RADAR/rival_tiktok.py discover --terms-file _build/config/rival_tiktok_terms.json \
    --region US --count 20 --out $D-tiktok.json

# ④ 商品与卖点（英文词表，多区域）
$PY $RADAR/rival_product.py search --words-file _build/config/rival_product_terms.json \
    --regions US,TH,VN,MY --count 20 --out $D-products.json
$PY $RADAR/rival_product.py detail --from-search $D-products.json --top 30 --out $D-detail.json
$PY $RADAR/rival_product.py claims --details $D-detail.json --out $D-claims.json

# ⑤ 人群与销量（浏览器通道，需 webbridge 在线且已登录蝉妈妈）
$PY $RADAR/rival_market.py all --category 美妆护肤 --days 7 --top 50 --out $D-market.json

# ⑥ 评论热词（人群在问什么）
$PY $RADAR/rival_product.py comments --from-discover $D-rival.json --top 12 --out $D-comments.json

# ⑦ 出报告
$PY $RADAR/rival_report.py --discover $D-rival.json --deep $D-deep.json --xhs $D-xhs.json \
    --tiktok $D-tiktok.json \
    --products $D-products.json --detail $D-detail.json --claims $D-claims.json \
    --market $D-market.json --comments $D-comments.json \
    --out-html 同行雷达/对标榜单_$(date +%F).html --out-csv-dir 同行雷达/csv
```

常用参数：

| 参数 | 作用 |
|---|---|
| `rival_radar discover --track 知识型` | 只跑某一类关键词（品类型/成分型/痛点型/知识型/培训型） |
| `rival_radar discover --days 30` | 时间窗放宽到 30 天（可选 3/7/30） |
| `rival_radar discover --min-max-likes 2000` | 提高账号入榜门槛，榜单更短更精 |
| `rival_product detail --top 60` | 多拉详情（每个商品多花 1 次调用） |
| `rival_product search --regions US,GB` | 换区域。**ID 与 GB 搜索恒为 0 条**，别选 |
| `rival_xhs discover --pages 2` | 小红书翻页加深（每词 20 条/页，**必须串行**，脚本已带 6 秒间隔） |
| `rival_tiktok discover --region TH` | TikTok 内容侧换地区（region 只是排序倾向，实测结果会混其它地区） |
| `rival_market rank --period 7天` | 商品榜换周期（昨天/7天/30天） |

## 关键词怎么改

- `_build/config/rival_terms.json` —— 抖音侧中文词，五类分轨（品类型管带货对标，知识型管课程/科普对标）。
- `_build/config/rival_xhs_terms.json` —— 小红书侧中文词，六类（护肤方法论/成分科普/敏感肌/油痘肌/抗老/干货收藏）。小红书词要偏**方法与成分**，不像抖音那样偏品类词。
- `_build/config/rival_tiktok_terms.json` —— TikTok 内容侧**英文**词，四轨（功效成分/问题解决/趋势概念/内容形态）。比商品词多一层「怎么拍」的意图（review / routine / before after）。
- `_build/config/rival_product_terms.json` —— TikTok 商品侧**英文**词，四轨（核心功效/问题解决/品类扩面/趋势概念）。

四处词表里以 `_` 开头的键都是备注，不会被当成关键词。

## 五条必须记住的边界

**1. 抖音侧只覆盖挂了商品的视频。** 纯知识科普号（不挂车）收录很少 —— 实测「护肤知识」只回 128 条、「护肤讲师」只回 1 条。想找纯内容型账号，得走浏览器通道搜抖音搜索页。

**2. 榜首不一定是美妆号。** 萌娃号、情绪号、AI 动画号靠一条产品植入就能冲进榜单，实测 Top10 里 6 个美妆内容占比不到 30%。**看榜单必须看「怎么用」那一列**。

**3. 卖点两边口径不同，不能相加。** TikTok 侧是商品描述原文里抽的卖点，抖音侧只有商品标题上的平台标签。对照看差异，而不是求总和 —— 两个市场的共识卖点不重合的地方，正是差异化切入口。

**4. 小红书是内容主场，别按带货逻辑读它。** 这条通道的价值是补上抖音侧的缺口 —— 抖音只收录挂了车的视频，纯知识/方法型账号基本收不到，而小红书不挂车也能起量。读法也不同：**收藏数 > 点赞数**的笔记是工具型干货（用户存下来准备用），这类最值得改造成自家的科普内容与私域沉淀；点赞高但收藏低的多是情绪共鸣型，参考结构而不是照搬话题。

**5. TikTok 内容侧的 region 是排序倾向，不是过滤器。** 传 US 也会混进菲律宾/加拿大/英国的内容（实测 120 条里 US 只占 59 条）。要「纯美国内容」得按每条自带的 `region` 列自己筛。另外这个维度每个词只回一页，账号语料稀疏是正常的，**别把「只出现一次」当成「刚起号」** —— 判断可学性看代表作结构与「低粉高赞」标记（作品均播放 ≥ 粉丝数 3 倍）。

## 取数通道可信度（2026-09-20 实测，勿踩坑）

### TikHub

| 端点 | 状态 |
|---|---|
| `douyin/index/fetch_item_query` | ✅ 关键词视频池 |
| `douyin/web/handler_user_profile` | ✅ 账号画像 |
| `douyin/app/v3/fetch_user_post_videos` | ✅ 作品列表（web 版该路由会 400） |
| `douyin/web/fetch_one_video_by_share_url` | ✅ 视频详情 |
| `douyin/billboard/fetch_hot_comment_word_list` | ✅ 评论热词（需过停用词） |
| `xiaohongshu/app_v2/search_notes` | ✅ 笔记搜索（真数据，已用「有意义词 vs 工程词」双测验证，两组交集 ≤2/20） |
| `xiaohongshu/app_v2/search_products` | ✅ 商品搜索（含价格、店铺），暂未接入 |
| `tiktok/app/v3/fetch_video_search_result` | ✅ 内容搜索（真数据，双测交集 0/20）；列表在 `search_item_list` 不是 `aweme_list` |
| `tiktok/web/fetch_search_video` | ❌ 恒 HTTP 400（疑似需 cookie），已禁用 |
| `tiktok/shop/web/fetch_search_products_list` | ✅ 商品搜索，参数名是 `search_word` |
| `tiktok/shop/web/fetch_product_detail_v3` | ✅ 卖点全文、销量、店铺、类目 |
| `tiktok/shop/web/fetch_hot_selling_products_list` | ❌ 服务端 400 |
| `tiktok/shop/web/fetch_product_reviews(_v2)` | ❌ 服务端 400（评价文本拿不到，只有评分与条数） |
| `douyin/search/*` | ❌ 返回固定 mock，与关键词无关 |
| `douyin/index/fetch_item_user_profile` | ❌ 返回「系统异常」 |
| `wechat_channels/*` | ❌ HTTP 405 |

### 蝉妈妈（浏览器通道）

| 能力 | 状态 |
|---|---|
| `content-strategy?content_type=USER_PAIN_POINTS` | ✅ 同源直连、明文、无需签名 |
| `content-strategy?content_type=<其他>` | ❌ 一律「参数错误」，只有 USER_PAIN_POINTS 有效 |
| `v1/product/categoryV7` | ✅ 品类树，字段名是 `label` 不是 `name` |
| `v6/product/search`（榜单） | ⚠️ 请求体加密，**只能读页面渲染后的表格** |
| 品类筛选 | ⚠️ URL 参数无效，必须模拟点击 |

**webbridge 动作名写错会返回 HTTP 502**（不是 404）。别把 502 当成守护进程没起来 —— 调 `list_tabs` 探活，能返回 `{success, tabs:[...]}` 就是活的。

## 凭据与前置条件

- **TikHub**：token 存 `~/.config/content-creative-intelligence/tikhub.json`（键名 `api_token`，权限 600）。失效时报 `authorization`，换新 token 即可。约 $0.002/次，一轮全量（约 250 次调用）不到 $0.5。
- **蝉妈妈**：需要本机 webbridge 守护进程在线（`127.0.0.1:10086`）且浏览器已登录蝉妈妈。取不到时人群与销量两节会缺，其余三节照常产出。

## 已验证但暂未接入的通道

- `xiaohongshu/app_v2/search_products` ✅ 小红书商品搜索可用（含价格、店铺），评价概览要 `sku_id`，暂未接入。
- `douyin/creator_v2/fetch_item_audience_portrait` 需要创作者中心 cookie，且只覆盖**自己**的作品，对竞品无效，已放弃。
- FastMoss（SageSurf 浏览器内已登录）、Olive Young 韩国榜，是另外的取数腿，不在本链路内。
