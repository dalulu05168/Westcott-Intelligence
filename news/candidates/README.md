# ELLERY WESTCOTT — 官方新闻候选队列

该目录只保存从固定 **美联储 / 欧洲央行 / 布加勒斯特交易所 BVB** 官方 RSS 收集的候选线索。工作流独立于 ChatGPT 的五项已暂停定时任务。

**禁止把候选等同于正式发布。** 收集器不能自动判断完整原文是否正确、标题是否具有重大市场影响、图片是否获准转载，也不负责用 GPT 编造行情或因果关系。

## 自动搜集（不向 Telegram 推送）

`.github/workflows/westcott-official-news-radar.yml` 每小时 UTC 第 37 分运行一次：

- 读取 Fed 货币政策官方 RSS `https://www.federalreserve.gov/feeds/press_monetary.xml`
- 读取 ECB 官方新闻 RSS `https://www.ecb.europa.eu/rss/press.html`
- 读取 BVB 官方市场新闻 RSS `https://www.bvb.ro/Rss/StiriBVB.ashx`
- 读取 BVB 官方交易所操作与公告 RSS `https://www.bvb.ro/Rss/OperatiuniSiComunicateBVB.ashx`
- 只接受指定官网域名的文章链接，以及带时区、发布时间不早于 36 小时的条目。
- 按利率、货币政策、银行、流动性等关键词初筛，不足以保证它是“重大”新闻。
- 按文章 URL 的稳定 SHA-256 指纹只创建一次 `news/candidates/<id>.json`；发现同一新闻不会覆盖已存在的档案。
- 尝试读取候选文章的 `og:image` 官方分享图链接，仅保存候选 URL；从不生成、复制、转载图片。
- 每条档案都写 `intake_status=UNREVIEWED`、`telegram_publishable=false`，不得自动发出。
- 任何一个官网不可达都记录错误；所有来源都不可达则整个搜集运行失败，而不会伪称“没有新闻”。

这只是 **官方 RSS 候选发现**，并不意味着已完成正式的新闻核验、GPT 中文撰写或机器人自动推送。已加入 BVB 官网新闻与公告，但不等同于覆盖所有公司财报详情、完整交易数据或 Reuters 等媒体报道。

## 检查结果

在 GitHub Actions 打开 `Westcott Official News Radar (Review Queue Only)`：

- 手动选择 `dry-run`：在日志中查看候选结果，不写仓库。
- 手动选择 `queue`：尝试创建未审核档案，仍不会向 Telegram 发送任何消息。
- 日常定时：仅执行 `queue`，不会调用 Telegram Bot，**没有 Telegram Token**。

档案中的标题来自官方 RSS，保留原始文字、发布时间与来源链接。审核人员必须点击官方文章查原文、确认新闻时点和数值，并按 `scripts/news_release_gate.py` 整理独立已审事实账本 `news/approved/*.json`，才能进入旧版 `preview`、`publish` 流程。

先前已暂停的五项 ChatGPT 任务仍然全部保持关闭；此处新增的是 GitHub 独立新闻线索采集，不是重新打开 ChatGPT 推送，也不向群组发送信息。
