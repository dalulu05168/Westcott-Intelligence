# Telegram 财经新闻自动推送｜部署说明

独立于现有 ChatGPT 五项任务、Google Docs 正式剧情与 WhatsApp 系统。本模块只转发**官方原始公告标题和链接**，不编造行情、课程、人物对白及作业。尚未接入实时行情和自动新闻翻译。

## 功能与边界

- `N01`–`N12` 按 `Europe/Bucharest` 时区调度，自动适配夏令时；N01 内部备料不发 Telegram，其他 11 节点在工作日运行。重大公告雷达按小时检查，工作日 11:15 由 N06 承接。
- 直接提取 BVB 官方 PressItem 公告，以及欧洲央行 ECB、美国联储 FED 的官方 RSS 标题。原始标题保留来源语言，不假称中文、罗马尼亚语的完整本地化分析已经完成。
- 新闻按官方发布时间过滤，且跨节点去重。N06 即使没有确认的新公告，也会发一条“暂无可核实新增”；其他节点在没有新消息时不重复旧闻。
- 自动保存已送达的 Telegram message_id 和新闻标识到独立 `telegram-news-state` 分支，不自动修改 `main` 下65人档案、课程或剧情。
- 不保证实时股票价格、竞价、成交量、Brent 和 TTF 报价。GitHub Actions 可能延迟，极端情况下可能丢弃定时触发；Telegram 成功投递后若状态写入失败，重试时可能重复消息。

## 首次连接 Telegram

1. 在 Telegram 打开 [官方 BotFather](https://t.me/BotFather)，创建机器人，取得 token。不要把 token 粘贴到聊天、Issue 或源代码。
2. 私聊机器人并发送 `/start`；如使用群组先加机器人，如使用频道授予发布权限。
3. 确认目标 `chat_id`：频道一般可用公开的 `@channelusername`；私聊或群组可通过 Telegram 官方 Bot API 的 `getUpdates`，在机器人收到消息后读取 `message.chat.id`。
4. GitHub 仓库 Settings → Secrets and variables → Actions → New repository secret，分别添加：`TELEGRAM_BOT_TOKEN` 与 `TELEGRAM_CHAT_ID`。
5. 审核并合并相关 PR 到默认 `main` 分支。分支草案创建成功**并不等于已经上线**。
6. 进入 Actions → `Telegram Finance News | 12 Bucharest Nodes` → Run workflow，选择 `N06` + `dry_run=true` 预览；检查实际官方标题、日期和新闻链接。
7. 然后选择 `dry_run=false` 手动试发，检查 Telegram 实际收到消息，再检查定时任务日志。

## 12节点（布加勒斯特本地时间）

| 节点 | 正式内容 | 自动准备 | 说明 |
|---|---|---|---|
| N01 | 07:50 | 07:35 | 只做后台采集，不外发 |
| N02 | 08:00 | 07:45 | 隔夜官方公告 |
| N03 | 09:15 | 09:00 | BVB盘前公告 |
| N04 | 09:45 | 09:30 | BVB竞价阶段公告，非竞价实时价格 |
| N05 | 10:00 | 09:45 | BVB开盘阶段公告，非实时成交 |
| N06 | 11:30 | 11:15 | 午间新闻；无新增时一次空资讯 |
| N07 | 14:00 | 13:45 | 国际官方公告 |
| N08 | 16:00 | 15:45 | 欧洲／美国央行及公告 |
| N09 | 17:45 | 17:30 | BVB尾盘公告，非实时指数 |
| N10 | 20:00 | 19:45 | 晚课新闻素材，非正式课程 |
| N11 | 21:00 | 20:45 | 问答新闻素材，非65人模拟发言 |
| N12 | 22:00 | 21:45 | 收尾新闻素材，非正式作业 |

## 测试及真实性

运行 `python -m unittest discover -s telegram_news -p 'test_*.py'`。`workflow_dispatch` 默认 `dry_run=true`，只预览日志、不发消息和不更新已送达记录。

来源依赖外部网站实际可用性：一个源失败时独立跳过，不能说成“没有新闻”。对于未核验的股价、涨跌比较基准、即时市场状态，不生成任何断言。仅转发官方原始标题，不声称已完成完整正文审校，也不自动将草稿写入正式 Google Doc。

编辑与核验标准：`skills/p004-chat-suite/references/news-release-gate-v1.4.md`、`skills/p004-chat-suite/references/daily-editorial-and-memory-v1.6.md`。

**上线验收要求：** Secrets 已配置 → PR 已合并 → dry-run 预览通过 → Telegram 真正收到一次测试消息 → 次日核对每个任务的日志与去重记录。