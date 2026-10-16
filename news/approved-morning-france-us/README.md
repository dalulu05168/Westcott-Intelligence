# 法国＋美国（FR+US）独立早间简报

用户确认两份早间信息：原有罗马尼亚＋美国、另增法国＋美国。**这不是改掉原有RO+US，更不是将RO新闻改写成FR新闻。**

## 触发与结果
- 工作日07:30（Europe/Bucharest）复用现有 `westcott-morning-opening.yml` 定时；两个版本独立预览、独立审核、独立发送账本。
- 目的地为现有 Telegram 群组「🌐~~~资讯快报」，机器人 `@NuvexaCheckBot`。不得新建机器人或覆盖群/私人ID。
- 法国版经批准后仅使用 `news/approved-morning-france-us/YYYY-MM-DD.json`；原RO+US仍用 `news/approved-morning/YYYY-MM-DD.json`。两者若缺资料，分别保持 `HELD`，互不阻塞。
- `audit/morning-france-us-delivery/YYYY-MM-DD.json` 独立于原RO早报的 `audit/morning-opening-delivery/`。发送前原子写入PENDING，占位后不自动重发；确认 Telegram `message_ids` 才改DELIVERED。
- 手动运行/PR仅测试和备稿，不向 Telegram 发正式消息。定时运行也必须存在审核包才会发。

## 事实核查
法国关注：重要的法国宏观/金融/企业新事件以及可能影响法国市场的欧盟/ECB消息（如果对法国传导逻辑被核实）。优先原始官网 INSEE、Banque de France、AMF、Euronext、法国政府、ECB/Eurostat。法国 CAC 40 等指数只有拥有可核实的报价实际时间、阶段和来源才允许写入；本版无实时行情服务，也不自动填价格。

美国关注：上一真实美股交易日道指/标普500/纳指，严格区分常规收盘、盘前与盘后；周末、假日及夏令时转换按原市场时间处理。两份简报引用同一份审核的US快照，但面向RO和FR的市场影响说明必须不同；不把美国市场单日涨跌直接推断法国股市涨跌。

代码读取以下可选材料：
- `news/verified-market/us-close-latest.json`（现有US事实结构，必须真正经过来源核实）；
- `news/verified-market/france-morning-latest.json`（由可信审核者准备并实际核实的法国事件数组，至少1项、最多3项，记录来源URL、发布时间、正文SHA256、准确原文摘录、可核实的新事实、对法国市场的有条件影响、后续观察及event_key）。

两项资料缺失仍可运行GitHub验证任务，但只标记HELD，并非发送失败。法国消息不能拿已经发送过的新闻换一种说法当新新闻；代码按已送达官方来源URL阻断重播，更多语义级去重仍需独立审稿。

## 法国版审核文件必填
- `status = APPROVED_FRANCE_US_MORNING`，`local_date`为当天布加勒斯特日期；
- `target_group_title = 🌐~~~资讯快报`，`bot_username = NuvexaCheckBot`；
- `us_market_evidence`、`france_evidence`均为当天独立复核、结构匹配的数据；
- `formal_story` 含 Google Docs 真正document_id、revision_id、当天retrieved_at；不能虚填；
- `editorial_approval` 包含 `approved_by`、`approved_at`、`decision=APPROVED`、`source_review_reference`、`france_country_impact_review` 和 `cross_edition_dedup_review`；
- `approved_text` 原样保留 `scripts/morning_france_us.py` 生成的助理开场、美股回顾、法国事实与来源。增加成员台词前须实际读取各成员的正式身份、独立记忆和最新采用故事；附member_dialogue_reviewed及member_ids，只允许01—40号。

**禁止把测试示例数据当市场数据，禁止伪造已审核、已读Google Docs、已发布和已送达。**本提交只建立独立工作流及安全门禁；实际法国/美国来源快照、Google Docs同步和负责审稿的上游仍需接通。