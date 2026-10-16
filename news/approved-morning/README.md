## 2026-10-16｜RO+US早报必须有罗马尼亚当地独立官方材料

除了三个美国指数已核实收盘资料，早间正式发布还要求 `romania_evidence`，其中包含 `target_country=RO`、当天核验人/核验时间、至少一个BVB/BNR/INS等官方发布的重要新事件、原文URL、原文SHA256、发布时间、忠于原文的简体中文事实、对罗马尼亚市场的有条件影响和后续观察。发布前 `scripts/morning_group_delivery.py` 将 `scripts/morning_romania_us.py` 的独立审核内容与原美股回顾共同逐项核对。没有罗马尼亚来源的早报继续HELD，不能把只有美股指数的消息标为“罗马尼亚＋美国”。

新的 `news/morning-intake/YYYY-MM-DD.json` 由工作日06:45官方RSS采集器提供候选来源；它仍是UNREVIEWED，不能自动标注REVIEWED。真实审稿和Google Docs当天修订必须单独完成；代码自动采集不等于已发送。

## 2026-10-16｜所有正式财经新闻必须附官网原始链接

- Telegram「🌐~~~资讯快报」的每条正式新闻正文必须包含可见的、可直接点击的 `https://` **官方原文URL**（不能只有链接卡片、图片、来源名字或者媒体转载链接）；多条不同事件须分别对应来源，缺失即HELD不发送。
- 罗马尼亚/法国正式新闻从批准事实的 `sources[source_id].url` 提取原文，并检查 `source_type=official`；正式 Telegram 图片存在时也必须在文字中保留其对应原文URL。链接的官网归属、正文真实内容、发布日期仍须独立核查，字段标为official本身不是审核证据。
- 罗马尼亚＋美国、法国＋美国的早间回顾：道指与标普500分别给出S&P Dow Jones Indices官网原始来源，纳斯达克综合指数给出Nasdaq官网原始来源；法国每条重大事件继续附自己的官方原文地址，严禁仅给一个笼统首页链接冒充指标数据来源。
- 若当轮无可确认的官方网页、报价来源或页面无法核对，保留HELD，不发布未核验数字，也不虚构官方链接。不能用GitHub工作流成功代替Telegram送达回执。

# 早间开群与美股回顾 · Telegram 发送门禁

目标固定为 Telegram 群组 **🌐~~~资讯快报**，机器人 **@NuvexaCheckBot**；沿用 GitHub Secrets 中现有的 `TELEGRAM_CHAT_ID` 和 `TELEGRAM_BOT_TOKEN`，不建立新目标、不向私人聊天误发。机器人身份和实际群组标题在发送前必须由 Telegram API 核对。

**每天工作日07:30（Europe/Bucharest）**：现有工作流继续生成早间候选稿。新增的发送步骤只读取 `news/approved-morning/YYYY-MM-DD.json` 的当日人工核实、批准包。没有该文件或任何检查失败即 **HELD，不发消息**。工作流仅在主分支自动定时运行时允许发送；手动 Run workflow 和 PR 只执行预览和测试。

批准文件要求包含：

- `status = APPROVED_FOR_MORNING_GROUP`、`local_date`、`target_group_title = 🌐~~~资讯快报`、`bot_username = NuvexaCheckBot`。
- `formal_story`：官方 Google Docs 的 `document_id`、当天真实 `revision_id`、`retrieved_at`；无法读取时不得伪造值。
- `market_evidence`：符合 `scripts/morning_opening.py` 的美国上一交易日三大指数核验结构；来自真实可追溯原文，不得用测试数据或旧数据冒充。
- `editorial_approval`：`approved_by`、`approved_at`、`decision = APPROVED`、`source_review_reference`；若包含成员对白，还需 `member_dialogue_reviewed = true` 以及 `member_ids`，只允许01—40号，逐人检查编号和性别。
- `approved_text`：以 `===== 资讯助理 =====` 开头，并原样包含程序从核验数据生成的早间开场和美股回顾；其余新闻或成员内容必须由真实编辑进一步核对。

**重要：结构校验不能代替权威官网数据核实或人工语义审稿；**不得由自动采集器把未审核数据直接标记为批准。当前仓库不具备自动拉取当天正式 Google Docs 修订并独立完成上述全套审稿的能力，因此在补齐上游前会安全静默。

发送前先向 `audit/morning-opening-delivery/YYYY-MM-DD.json` 写入 `PENDING` 独占记录；相同日期的任意已有状态均不自动重发。Telegram 确认回传 `message_ids` 后才记录 `DELIVERED`；网络不明结果保持 `PENDING` 并停止。不能把工作流成功等同群组送达。

现有官方新闻审稿和发送工作流保持不变；历史早间新闻任务不恢复。