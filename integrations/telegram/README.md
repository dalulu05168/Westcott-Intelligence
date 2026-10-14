# ELLERY WESTCOTT — Telegram 群组 Bot 接入

状态：**Telegram 群组连接及单条文字测试已验收；自动财经新闻任务仍全部暂停**。此目录不会改变 ChatGPT 已存在的定时任务，也不会自动读取 ChatGPT 任务输出。只有明确运行 `bridge.py send` 且提供可核验正文时才向指定群组发送；`smoke` 仅发送明确标记的连通性测试。

## 已指定机器人

目标 Bot 用户名：`@NuvexaCheckBot`（已在成功的 Telegram `discover` 与 `smoke` 工作流中经 `getMe` 验证）。`discover`、`verify`、`smoke`、`send` 在访问群组或发送前均须通过 `getMe` 实际验证。若 Token 对应其他机器人，直接拒绝发送。目标群组为 **资讯快报**（Telegram 已通过 `getUpdates` 返回群组，且 `smoke` 成功发送消息，回执 `message_id=21`）。`discover` 仅列出 Bot 实际看见且标题严格匹配的群组；`verify`/`smoke`/`send` 在 `getChat` 返回群类型和标题均匹配后才继续。即使找到多个同名群，也不会自动挑一个发送。群组凭据已完成此次测试验证；不得根据显示名推断其他群组的 Chat ID。

## 群组准备

1. 继续使用已指定的 `@NuvexaCheckBot`，在 Telegram 官方 `@BotFather` 获取它当前有效的 token，并保存至密码管理器；不要在聊天、GitHub 文件或 PR 中粘贴 token。
2. 将机器人加入显示名称为 `资讯快报` 的 Telegram 群。确保机器人获准发送消息；需要发送到话题时另外配置 `TELEGRAM_MESSAGE_THREAD_ID`。
3. 群里发送一条新消息（例如 `/start@NuvexaCheckBot`），然后在可信环境运行 `discover` 识别显示名称为 `资讯快报` 的群组及 `-100...` 格式 chat ID。若机器人设有 webhook，getUpdates 可能返回冲突；可改用群组明确提供的 chat ID。由于群组名称可能重复，务必按实际群信息核对 Chat ID，不要把中文显示名当作 Telegram @username。
4. 在私有 GitHub 仓库 Settings → Secrets and variables → Actions 中设置以下 Repository secrets：
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

可选在 Actions variables 设置 `TELEGRAM_MESSAGE_THREAD_ID`，用于有话题的超级群。凭据只能存在于可信秘密管理器，不写入仓库源码。

## 远端人工验收

将当前分支通过 Pull Request 审核合并后，在仓库 Actions → Westcott Telegram Bridge → Run workflow 选择：

- `discover`：列出 Bot 最近可见的 group/supergroup 群 ID（需要在机器人入群后产生群消息）。
- `verify`：只核对 Bot 身份、目标群组类型和标题 `资讯快报`，不发消息。
- `smoke`：明确向指定群发送一条“连接测试”文字，成功时回传 Telegram message_id。
- `send`：粘贴**已经过来源审查**的 `===== 资讯助理 =====` 正文，再执行发送。执行回传接收群 ID 和 message_id；网络故障发生时送达状态可能不确定，不能仅凭运行历史声称已收到。

## 现有新闻系统与集成边界

- ChatGPT Scheduled 任务与 GitHub Actions 是两个分开的运行系统。**仅提交此仓库无法截获 ChatGPT 任务生成的正文**；要真正自动群推送，还需要具有授权访问与稳定消息出口的上游发布器，把已批准正文传入 `WESTCOTT_APPROVED_NEWS_TEXT` 或调用 `send_group_news`。本提交未伪造这种上游连接。
- 实际新闻须先经过项目 `scripts/news_release_gate.py` 和人工/可靠流程证据核对。门禁的 PASS 是账本字段一致性，不等于事件真实性已独立证实。运输层不会自行抓取/润色新闻，也不会生成群员对白、图像或课程。
- 应沿用 Europe/Bucharest 时区、N07 13:45/N08 15:45及其他固定节点，避免把上午旧闻当新增。条件雷达无重大新事件时应静默。
- 任何 Telegram 消息发送成功都以 API 回传 `message_id` 为证据；`getChat` 只能证明目标存在，不能证明消息投递。接收方群组可进一步查看。
- 对于 HTTP 或网络故障，**不会自动重试**以免因请求已成功但响应丢失而重复推送。发布器应有持久化 claim_id / event_id / published_at / quote_as_of 与已发送 message_id，用于跨时段审计和去重；此轻量桥接不提供持久化调度与审计库。
- Bot 与目标群的连通性已通过 GitHub Actions 的 `smoke` 验证，但不能据此声称定时新闻自动转发已经开启。

## 审核后 16:9 新闻图片与 Telegram 图文

- 新增 `preview`：读取 `news/approved/<file>.json`，先调用 `scripts/news_release_gate.py` 做审核账本的一致性校验，然后生成浅蓝白、无文字、1600×900 的匹配主题图片和可复制中文资讯助理稿，输出 GitHub Artifact 供人工检查；**预览不会向 Telegram 发送消息**。
- 新增 `publish`：仅在同一正式证据账本审核通过、在 GitHub Actions 手动输入确认词 `PUBLISH_REVIEWED_NEWS` 后，先写入不可重复的证据指纹记录，再发送图片与文字，最后记录 `photo_message_id`、文字 `message_ids`、`claim_ids` 及来源链接。
- 新闻背景为确定性生成的非新闻照片风格主题线条（能源/银行/科技/宏观/商品/BVB），不在图片中添加任何文字、数字或无依据的走势；**非 AI 图片模型或现场真实照片**。
- 具体操作与账本格式请见 [news/approved/README.md](../../news/approved/README.md)。
- ChatGPT Scheduled 五项任务继续暂停，尚未与 GitHub Telegram 发布器自动对接；不擅自启动、也不把旧新闻当新进展。
