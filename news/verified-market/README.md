# 07:30 早间开群与上一美股交易日回顾：材料契约

工作流 `Westcott Morning Opening and Prior US Close (Review Only)` 每工作日 07:30 按 Europe/Bucharest 调度。
这是**早间开群和美股回顾**，与用户要求删除的「07:30 早间新闻」并非同一任务。

当前程序 `scripts/morning_opening.py` 不发送 Telegram / WhatsApp，不更改 Google Docs / 人物记忆；只生成 Actions 工件 `morning-review.json`、`morning-review.txt`。状态为 `HELD_SOURCE_REQUIRED`、`HELD_INVALID_MARKET_EVIDENCE` 或 `READY_FOR_EDITORIAL_REVIEW`。即使 READY，也仍需复核原文、正式剧情与去重，再决定发布；校验通过不等于采用或送达。

## 如何接入美股上一收盘数据

经可信上游采集并核对原文后，把最近一个已经结束的纽约交易日常规时段收盘快照写入 `news/verified-market/us-close-latest.json`。格式要求：

- `market=US`、`phase=REGULAR_CLOSE`、`session_date`（纽约日期 YYYY-MM-DD）。
- `source_url`、`source_checked_at`（带时区）、`review_status=REVIEWED`、`reviewed_by`、`evidence_reference`、`source_body_sha256`。
- `indices` 恰好包含 `DJIA`、`SPX`、`IXIC`，每项有 `symbol`、`close`、`previous_close`、`change_pct`、`quote_as_of`（带时区）、`phase=REGULAR_CLOSE`、`source_url`、`evidence_excerpt`。
- 检查纽约当地交易日、时区、节假日与实际收盘阶段；不把休市时段当常规收盘，不把盘前/盘后/期货数据冒充现货指数常规收盘。

**所有 REVIEWED 字段和证据字段都只供代码结构校验，程序无法据此独立证明原始网页或数字真实。** 上游必须实际核对所填原文，不能用测试用例的虚构数字。

## 五Skill与剧情

GitHub Runner 当前没有同步读取正式 Google Docs 的最新文本、页签和修订号的权限。故本工作流不伪造成员互动、已开群、历史记忆或自动采用状态；仅准备女性资讯助理开场和（如有已核材料）指数收盘回顾候选。要增加成员对话，须实际读取当日正式文档、01—40号身份档案及记忆，运行 `scripts/editorial_execution.py` 并做语义审稿。

如未来需要自动群发，必须先确认独立的群组目标与授权、新闻事实门禁、重复事件锁、真实 Telegram message_id 审计。**现有「🌐~~~资讯快报」是财经新闻通道，不能假定它就是早间剧情群组。**

本工作流不启用已停用且待删除的07:30旧晨报、不修改其他现有任务或已暂停的 Skill 通道。
