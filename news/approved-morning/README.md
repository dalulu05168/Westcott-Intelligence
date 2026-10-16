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