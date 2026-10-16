# 2026-10-16 官网图片与分国小时排名修复

正式发布强制同时满足：已核验原文与数字；真实匹配且审核通过的官网原图；RO或FR目标国家；对应国家的有条件影响分析及后续关注方向；完整60分钟官方源候选快照与逐项影响评估。任何一项缺失即HELD，不再降级为无图新闻。预览可显示链接，但不等于正式发布。

候选快照位于news/editions/，不按关键词或前12条截断候选；全部配置源必须读取成功，任何遗漏、截断、正文不可读都会阻止影响力比较。当前原始来源包括Fed、ECB、BVB、INSEE、美国BLS与Eurostat。每次快照不自动批准事实或伪造评分。

每国对全部当小时候选评估市场覆盖30%、本地传导25%、量级20%、预期差15%、时效10%；各维度0至5分，须有原文摘录、正文哈希、审稿者和理由。程序计算得分，只有最高分且达到70分的候选可发布。该排名仅限明确列出的官方源覆盖集合，不声称涵盖全球所有事件。第一名没有可用原图时暂停该国该小时，不拿有图的第二名补位。

RO显示🔵罗马尼亚，FR显示🔴法国。每国每UTC小时使用独立、原子写入的slot锁，最多一件；相同全球事件可分别分析两个国家。原文证据去重也按国家隔离，已送达或不确定状态均不自动重发。

新账本增加target_country、local_impact_claim_id、watch_next_claim_id及hourly_selection。两个analysis claim均需标记相同target_country，并通过现有条件分析与事实前提门禁。hourly_selection包含edition_path、edition_sha256、selected_candidate_id和对该快照每个候选的assessments；字段与测试示例见test_editorial_policy.py。先做事实、图片及影响评审，再提交已审核账本，不能将采集结果自动标记CONFIRMED。

每条正式图片必须从原文章自己的OG元数据或article/main正文图片中重新找到；不接受图库替代、导航Logo或AI背景图。没有对应原图就不发。抓取到的候选图片本身不等于图片匹配及转载审核完成。

这次修复不启用原五项ChatGPT暂停任务，不冒称已接通全自动中文语义审稿；小时影响评估仍需可信审稿输入。新门禁与源可用性以本次GitHub验收为准，旧的消息送达记录不能代表这些新增要求已通过。

下方为历史记录，如有冲突以当前代码及本节为准。

---

# 2026-10-16 维护更新

官方雷达自动采集候选、正文快照及原图元数据，仍标记UNREVIEWED；不自行批准新闻。可信审核者核对原文、数字、时间及中文事实后，将证据账本提交到news/approved/。新增Verified News Delivery每小时处理已审核队列，发布前重新读取原文比对摘录，超过36小时或原文不可读即阻止发送。中文资讯助理文字由批准事实生成，并附原文链接。

原始send入口已禁用，只能通过证据账本发布。仅使用实际getMe核对的@NuvexaCheckBot及getChat核对的「资讯快报」。发送前登记占位，成功保存message_id；PENDING禁止自动重发。claim改号不再绕过去重。每条来源URL与规范化证据摘录另建原子占位，改写中文、改event_id或文件名也不会重复；同源更新必须提供新原文证据。同一BVB公告多语PDF与唯一官网文章归组，保留各原始链接供审核。

没有获准官网原图时使用原文链接预览。PDF或受限原文不能被当前HTML读取器核验，会阻止发送，不能仅凭RSS标题批准。未配置自动中文翻译服务，中文稿需要可信审核者写入账本，不能把机器采集当作事实审核。

维护分支CI执行明确标记的连接测试及官方源读取；实测状态以Actions日志为准。原有五项线上任务未调用、未恢复；离线人物快照更新不构成上线。

下方为历史接入记录，如有冲突以上述更新及当前代码为准。

---

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

## 新闻官网配图与 Telegram 发布

- **停用并删除旧的 16:9 浅蓝白插画生成器**，不再生成、裁剪、添加新闻背景图，也不使用 AI 自动搜图。
- `preview`：仅核对 `news/approved/<file>.json` 审核账本，并把已核实的资讯助理文字保存到 `news/previews/`。执行结果返回原文页面链接及（确有授权时）原新闻图片链接，不会复制、下载、生成任何图片。
- `publish`：只能手动触发、确认 `PUBLISH_REVIEWED_NEWS` 后发布。如果图片确实属于该新闻且已确认允许转载，调用 Telegram `sendPhoto` 直接使用官网图片 URL；其他情况则发送中文稿与**原文链接预览**，由 Telegram 展示该网站公开的分享缩略图（不保证一定展示）。
- 所用 `article_url` 必须是当前已审核 claim 的真实来源，图片 URL 和可转载依据需人工核对。独立授权标记不可代替实际版权核查；审核不通过则不上传图片。
- 对同一组已核实事实及来源生成防重复指纹，发送前写审计占位；发送成功写入群组消息编号，状态不确定时不会自动重发。
- 使用指南及数据字段见 [news/approved/README.md](../../news/approved/README.md)。旧的 `smoke_image` 已停止支持，因为不再生成示意图。
- 原有 ChatGPT Scheduled 五项定时任务继续暂停，没有自动接入此 GitHub 发布流程。

## 从官方原文识别新闻图片

- GitHub Actions 新增 `inspect`：手动提供 `article_url`，抓取原新闻官网文章的 OG 分享图信息（如 `og:image`）、标题和 canonical，**不下载图片、不发布 Telegram**。
- `preview`：在已有审核账本内自动识别对应原站候选配图并返回 `official_page_metadata` 供人工核验。
- `publish`：如指定了获准转载的官网图片 URL，发布前重新核实它等于原始文章自己公开的分享图片 URL；不一致或原站不可检查则阻止发布。没有核实授权的图片使用原文链接预览。
- 图片候选识别不是版权许可证明，也不能自动判断报道语义，必须人工确认；某些官网阻止网页读取时只能返回无法识别。
- 原五项 ChatGPT 财经定时任务继续暂停，不自行激活定时抓取或群推送。

## 官方资讯自动发现（严格未审核）

- 新增 [Westcott Official News Radar](../../.github/workflows/westcott-official-news-radar.yml)：每小时从 Fed / ECB / BVB 官方 RSS 抓取候选新闻，筛选最近36小时的新事件，保存到 `news/candidates/`。
- 只生成 `UNREVIEWED` 队列及官方文章的 `og:image` 候选链接，**不触发 Telegram**，不编写“审核通过”的假证明；没有拿到网页原文时也不冒充已经读取。
- 已有 `news_release_gate.py` 仍要求审查后的完整证据；从候选变成可正式发送的女性资讯助理中文稿，尚需可信的上游核验及发布批准。
- 队列采集与原有五项已暂停的 ChatGPT 新闻任务相互独立。请勿把队列产生误当成已向 Telegram 「资讯快报」送达。
- 使用说明见 [news/candidates/README.md](../../news/candidates/README.md)。

