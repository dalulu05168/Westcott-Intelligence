## 2026-10-16 发布门禁修订

本目录仅保留原标题采集预览。工作流只能dry_run运行，send_message与非dry_run直接拒绝发送，不能通过TELEGRAM_NEWS_ENABLED绕过原文核验。正式中文资讯助理消息统一由integrations/telegram的已审核账本发布链路处理，使用@NuvexaCheckBot及「资讯快报」。私人连接检测工具只作显式连接测试，不构成正式新闻发布入口。

下方原节点设计及私聊发送说明为历史记录，以当前修订及代码为准。

# Telegram 财经新闻自动推送｜部署说明

独立于现有 ChatGPT 五项任务、Google Docs 正式剧情与 WhatsApp 系统。本模块只转发**官方原始公告标题和链接**，不编造行情、课程、人物对白及作业。尚未接入实时行情和自动新闻翻译。

## 功能与边界

- `N01`–`N12` 按 `Europe/Bucharest` 时区调度，自动适配夏令时；N01 内部备料不发 Telegram，其他 11 节点在工作日运行。重大公告雷达每天每小时第15分钟检查；工作日11:15与N06可能同时触发，但工作流串行和事件ID去重。
- 直接提取 BVB 官方 PressItem 公告，以及欧洲央行 ECB、美国联储 FED 的官方 RSS 标题。原始标题保留来源语言，不假称中文、罗马尼亚语的完整本地化分析已经完成。
- 新闻按官方发布时间过滤，且跨节点去重。N06 即使没有确认的新公告，也会发一条“暂无可核实新增”；其他节点在没有新消息时不重复旧闻。
- 自动保存已送达的 Telegram message_id 和新闻标识到独立 `telegram-news-state` 分支，不自动修改 `main` 下65人档案、课程或剧情。
- 不保证实时股票价格、竞价、成交量、Brent 和 TTF 报价。GitHub Actions 可能延迟，极端情况下可能丢弃定时触发；Telegram 成功投递后若状态写入失败，重试时可能重复消息。

## Telegram 私人聊天专用连接步骤（本版本优先）

本次只允许机器人私聊发送，发送前使用 Telegram getChat 确认数字 ID 对应的 `type=private`；误填群组、频道或公开用户名会直接失败。

1. 继续使用你掌控的 [@NuvexaCheckBot](https://t.me/NuvexaCheckBot)（如果 Telegram BotFather 中该机器人仍归你管理）。先在 Telegram 打开机器人，点击 Start 或发送 `/start`。
2. 在仓库 Settings → Secrets and variables → Actions → Repository secrets 中设置 `TELEGRAM_BOT_TOKEN`（从你自己的 BotFather 获取）。**不要把 Token 发到聊天、GitHub Issue、Commit 中。**
3. 合并 PR 后，去 Actions → **Telegram Private Chat Connection** → Run workflow → `mode=discover`。运行日志会显示机器人身份和最近发送过 `/start` 的私人会话 ID；确认显示的账号确实是你本人。此操作只读取消息，不清除更新，也不会自动发送新闻。**如果机器人正在使用 webhook，getUpdates 会返回冲突：禁止未经许可删除现有 webhook。**
4. 将核实过的个人数字 chat ID 保存为另一个 Actions Repository Secret：`TELEGRAM_CHAT_ID`。
5. 在 **Telegram Private Chat Connection** 选择 `mode=test`。机器人将发送一条带当前时间的私人连接测试；务必到 Telegram 实际确认收到了这条测试消息。
6. Actions → **Telegram Finance News | 12 Bucharest Nodes** → Run workflow，先选 `node=N06`、`dry_run=true` 检查新闻来源；再手动 `dry_run=false` 做一次新闻推送验收（如果有新消息；否则为午间无新增通知）。
7. 只有上述步骤通过后，才在 Settings → Secrets and variables → Actions → **Variables** 新增 `TELEGRAM_NEWS_ENABLED=true`。**变量不存在或非 true 时，所有计划触发的新闻推送任务均跳过。**原5项ChatGPT任务的暂停/启用状态不变。

最新确认的范围是**私人聊天**，不是群聊或频道。后续要改发送位置必须另外明确提出并先修改私人聊天锁定逻辑。
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
