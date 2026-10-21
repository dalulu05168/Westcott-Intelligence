---
name: westcott-voice-management
description: 用用户最终确认的65人身份与Google文档已采用发言来维持多人物社群语言差异。写稿、改稿、校对前调用；禁止臆造家庭、经历、金融交易或无证据口癖。
---
# Westcott Voice Management

## 编号识别→一键人物口吻转换（优先入口）
当用户粘贴 `NN男：原句` / `NN女：原句` 或 `按NN号口吻改：原句`，直接转入 [NUMBERED-VOICE-REWRITE.md](NUMBERED-VOICE-REWRITE.md) 的 `VOICE_REWRITE` 轻量流程；不要求再次说明姓名或职业。
- 自动按编号读取65人最终身份，以及对应 `characters/profiles/NN.json` 的职业、主行为、次行为、兴趣和候选语言字段；**人物职业性格只作辅助，不能压过本人已采用对白**。
- 使用 `voice-index-2026-10-21.json` 的该人 `voice.evidence`，必要时刷新最新已采用Google Docs；同职业成员也必须分开匹配。没证据不能假称匹配历史语气。
- 可用 `tools/prepare_numbered_rewrite.py` 整理输入、身份、职业、性格、历史样本给模型，随后**由语言模型改写**；脚本仅准备资料，不会独立写出自然语言改写。
- 多行多编号逐条对应输出；保持原意、数字、股票代码和不确定性；禁止编造经历、持仓、家庭或语气审批状态。43—65只按明确请求编辑，不获得剧情出场资格。

## 必须执行的前置读取
1. 先读取 `../characters/final-identity-65.json` 或逐人的 `../characters/profiles/NN.json` 的**身份锁定字段**。不可读取旧 `romania-market-director` 同编号的人名来覆盖。
2. 读取 `../references/active-member-roster-v2.2.md` 的现行授权，且在每个新日期检查有无更高优先级更新。当前仅01-42可能出场。
3. 刷新正式 [Google Docs](https://docs.google.com/document/d/1frtoFvohP3u2HfRzBPRZVLOzMfvnO-8Vi9iX3r5rmiM/edit) 当前版本和当日相关时段，不得只靠 `voice-index-2026-10-21.json` 时间点快照。只把**已经采用**的消息纳入人物语言证据；不能使用候选/草稿/文档中的AI写入测试。
4. 读 `voice-index-2026-10-21.json` 对应 `members[].voice.evidence`，遇新增正式发言可抽取新证据，但**不自动设为已批准语言特征**。如当前场景有背景差异，以最新正式已采用消息为准。
5. 当前新稿先生身份只取 `../references/staff-and-role-identity-20261021.md` 的 David Miller；不能合并过往不同先生的风格或资历。01男与Ion顾问、21女与Ana顾问分别是独立人物。
6. 人物当日持仓、交易参与、家庭事实、心理变化均取正式剧情与用户确认，未提供者为未知，不能从职业/年龄/罗马尼亚背景生成。
7. 用户确认的个体声线规则仅来自实际审核的 `westcott-persona-approved-rules.json`（管理页导出）或明确在场指令；未获得这个文件时不可以声称规则已批准。原始`voice-index...`中的 `approved_style` 默认未批准。

## 核心执行顺序（Humanizer）
- Step 0: 识别原文标签、角色身份、历史言语证据和样本密度。逐人建音色，样本不足时如实标记低置信度。
- Pass 1: **先匹配个体表达**。复现句长节奏、反问率、常见语气、词汇域和表情频率的分布，不复制样本的事实、原句或交易行为。每人有权沉默；没有真实动机不强制出场。
- Pass 2: 针对确有问题的地方去除AI式空话、套路排比、无意义铺垫；不能整齐批量改成同一种口语模板，不能让普通成员都像专业券商分析师。
- Pass 3: 自查过度修正、身份漂移、已采用剧情矛盾、日期/金额/股票代码/报价/活动答案/表情管理、人物信息归属、发言时段，未通过不能假装检查完成。
- 出稿输出：角色、所用真实证据标识、是否用户批准口吻、改写正文、未核实项。只有确实完成的校验才标记合格。
- 如涉及金融现实事件，另行查询真实来源/日期；角色语言库不能作为行情真实性资料。

## 编辑行为
口吻管理页的本地「批准」不自动提交 GitHub。需明确获得用户确认并读到导出记录才能同步为正式GitHub口吻规则。禁止未经用户同意修改或删除 `final-identity-65.json` 和已采用历史文档。
