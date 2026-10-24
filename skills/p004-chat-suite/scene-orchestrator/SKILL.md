---
name: ellery-westcott-scene-orchestrator
description: ELLERY WESTCOTT 65人虚构社群剧情写作总Skill；用户说写早间、下午、晚上、续写、活动、晚课、改人物口吻、质量巡检时自动触发，调度五Skill、正式Google Docs、65人锁定身份和Humanizer语言档案。
license: MIT
metadata:
  version: 1.0.0
  canonical-repo: dalulu05168/Westcott-Intelligence
---

## 2026-10-24｜长期规则与来源切换

先读取[仓库长期记忆入口](../../../memory/runtime/REPOSITORY-MEMORY-START-HERE.md)及其中用户确认规则。保留本仓库01—42出场、David身份、09:00上午开群等现行规则；用户停止的Google OAuth排障只作用于其私有GPT连接，不暂停其他任务。仓库可读、已入库与私有GPT已接通须分别验证。


# ELLERY WESTCOTT · 一体化剧情/人物语言总Skill

## 0. 一句话任务入口
只要用户说“写剧情/写早报/写下午或晚课/继续刚才/加成员互动/活动/修改人物口吻/缩短/扩写/审稿”等，主动运行本Skill。**不要要求用户打开人物窗口、复制人物提示词或每次重讲身份。** 本总Skill统一调度原有五Skill：导演、编剧、先生、资讯助理、成员，它自身不是第六个虚构角色。

将任务标记为 WRITE_SCENE、CONTINUE、REWRITE、ACTIVITY、LESSON 或 QA。用户明确指明的长度、时段、人物、表情、插图位置优先；只改指定部分，其余沿用已采用的连续剧情。无指定段数时自然决定，不强制凑稿。

## 1. 生成前必须真实读取

1. 读取本私有仓库根 `AGENTS.md` → `skills/p004-chat-suite/SKILL.md` → 本文件，以及按需读取 `p004-director`、`p004-writer`、`p004-teacher`、`p004-assistant`、`p004-members` 的SKILL。
2. 使用已连接 Google Docs 读取正式文档：https://docs.google.com/document/d/1frtoFvohP3u2HfRzBPRZVLOzMfvnO-8Vi9iX3r5rmiM/edit ，选择用户指定日期的页签。续写时确认最新修订号、最后一条**已采用**消息、上一个活动题目与结果、课程最后节点。排除候选草稿与“AI写入测试”。必要时读前一日结尾；不可把10月21日索引当成实时文档。
3. 身份唯一权威 `skills/p004-chat-suite/characters/final-identity-65.json`；只用01—65补零编号，核对姓名、性别、年龄、职业、投资年限、资金规模、新老学员、所在地、背景备注。入场人物另读 `characters/profiles/NN.json`，候选voice不等于用户批准。
4. 人物口吻证据：`skills/p004-chat-suite/voice-management/voice-index-2026-10-21.json` 的 `members[].voice.evidence` 与最新Docs已采用原话；实际存在经用户批准的口吻文件才读取为确定风格，网页本机保存不等于已同步。无样本则如实标低置信度，不臆造固定口癖。
5. 剧情事实：必要时读 `memory/daily/YYYY-MM-DD/`、`memory/long-term/members/NN.json`、`memory/curated/`、`memory/member-stock/ledger-v2.json`；跟推荐买票按已确认**小说剧情参与状态**记录，不反复索要成交证明，但不造价格、股数、盈亏或真实交易回执。
6. 新闻、指数、股票价格、日期、活动结果：必须另外核对对应有效资讯源与时点。BVB盘中/收盘、美股盘前/盘后/收盘不可混淆；缺可靠来源宁可少说，不编数字。
7. **Notion纠错实时核对**：在写上午/下午/晚间场次或做质量巡检时，使用已连接的Notion读取 [ELLERY WESTCOTT剧情控制中心](https://app.notion.com/p/400fd480b91e816cbb9be0b315d2b976)；读取“机器可读的已确认纠错规则”下 `EW-CORRECTION`、`status=approved` 的JSON，并与 `references/notion-approved-corrections.json` 按规则id、status、scene、severity、title及关键词字段逐项比对。不能仅凭GitHub旧快照说已经读取了Notion。若两边不一致，标记 `RULE_DRIFT`，不得报告“五Skill全验收通过”；只有核实属于用户正式批准修订后才用GitHub连接器更新快照，并复读验证。Notion不可用时标 `SOURCE_BLOCKED`；这条是**写稿时的连接器核验流程**，不是无人值守Notion→GitHub实时同步。
8. **上午场次硬门禁**：生成前先由导演按Europe/Bucharest时钟写内部节点规划：09:00开群→隔夜美股与罗马尼亚盘前资讯→成员围绕新闻自然互动→11:45后收尾→12:00闭群。发现把昨晚课程收获、课后作业、技术复盘写成上午主线，必须重写，不得用财经关键词掩盖主线错位；参见 `references/QA-GATES.md` 的P0规则。

**触发后是实际连接器读取，不是“假装我记住了”。** 缺权限或查不到相关日期时标 SOURCE_BLOCKED，不能声称全面核验。纯粹对用户粘贴的单句做语气编辑，且不依赖当日历史时，可只读取该人物必要样本，避免无谓大范围检索。

## 2. 人物与时间权威

- 目前01—42号可按剧情需要出场；43—65号留档不得自动发言。现行规则 `references/active-member-roster-v2.2.md`，若用户之后更改则遵循最近已确认授权。10号为女；41男与42女的身份以最终65人表为准。
- 新稿主讲先生为**David Miller**，Ellery Westcott 股票执行负责人。标签 `===== 先生 =====`。历史Jonathan/Henry不追溯更改，但不得当现任或将旧人台词搬成David的既往经历。
- 日间主持为**资讯助理**；Gabriela Ion负责课后作业；Ana Maria负责咨询。01男 Ion Dumitrescu ≠ 顾问Ion；21女 Ana-Maria Mitroi ≠ 顾问Ana。
- 正式身份原表并未提供详细家庭关系，不能以年龄、职业、地理推测配偶、子女、财务计划或稳定关系。旧 `dalulu05168/-Skill` 的同编号人名冲突不继承。
- 每次按 Europe/Bucharest 的当地故事时钟确定开闭群、16点互动和晚课。当前正式课表与用户本轮课程安排优先，杜绝旧时间规则覆盖新规则。
- 冲突优先：用户本轮明确指示 > 最近正式批准修订 > 最新Google Docs已采用文本 > 65人身份表/现行授权 > 最新五Skill规则 > 已采用人物记忆 > 文档语言证据 > 未批准创作候选。此顺序不允许改变锁定身份或编造现实市场事实。

## 3. 五Skill内部流水线（一次任务自动执行）
- 资讯助理模块先做真实事实和活动结果核验，交“已知事实＋未知项”，不可把猜测写成新闻。
- 总导演确认场次/剧情时间、承接点、课程安排，挑选有发言动机的角色、与谁互动，允许沉默；不凑话术或机械轮号。
- 成员模块只加载真正上场人物的身份、发言样本、过去剧情记忆、emoji习惯，并确定“当前会怎么说”“绝对不能声称什么”。
- 编剧模块编排可直接复制的群聊对白：短长句混合、可以接话/追问/轻微玩笑或不同意，群员不是人人都是券商分析师。不要固定“助理一条→成员两条”循环。
- 先生模块仅处理现任David晚课、答疑、例图、作业；专业但好懂，不杜撰资格、客户订单或承诺收益。
最终由统一审核模块完成身份、新闻、话语真实性、剧情前后和格式检查再交付。必要内部记录不用混进正文。

## 3A. 编号人物口吻转换｜VOICE_REWRITE
用户只要输入 `14男：一句话`、`02女：一句话`、`按14男口吻改：一句话`，或多行不同人物台词，**直接识别编号并按该人物的正式历史说话方式改写**。详细执行 `../voice-management/NUMBERED-VOICE-REWRITE.md`。这是独立轻量任务：只读相关人物的正式身份、历史对白和已确认口吻，不必加载整天剧情或每次先跑五Skill完整场次流程。改写时保持原意、数字、事实和人物标签，不增写交易、家庭或剧情。只输出可复制的改写台词；无编号时才问要按几号改。43—65仅允许指定文本编辑，不因此获得正式剧情出场资格。

## 4. Humanizer 人物说话能力（强制先匹配，再润色）
详细阅读 [VOICE-ENGINE.md](references/VOICE-ENGINE.md)，顺序不得颠倒：
1. 对每位上场人物抽取**多个本人正式发言**，归纳语句长度的分布、字词、疑问/断言比例、情绪、话题兴趣、表情出现方式与真实缺席情况。只归纳证据能支持的东西，不以罗马尼亚人身份套刻板模板。
2. 根据人物当前动机先写属于该人的话，再参考上游 [hannsxpeter/humanizer](https://github.com/hannsxpeter/humanizer) 的六类32种机械写法诊断。不要把AI词语换另一套固定AI口语；原本自然的句子尽量不改。
3. 反向审稿：真实人物的小习惯是否被磨掉？原文数字/股票代码/不确定性/事实是否变化？是否从语气样本无端借来了交易或家庭经历？发现则撤回。不可给“人物相似度100%”等虚假机器评分。
4. emoji参照 `references/member-emoji-guidelines-v2.7.md` 和已采用原句，可完全不用，也不可每句统一😂🚀。普通成员多用易懂短句，职业背景仅影响关注点，不自动证明金融专业资格。
5. 多人对照防复制腔：同一短语/语气/表情不应反复机械刷屏；同职业人物也有各自差异；若无自然发言原因，允许不出场。

## 5. 课程、活动、配图、输出
- 续写先对齐本日Doc最后有效发言，避免同一新闻重复开场和课程先后倒置；用户要两个成员问候就只自然插两条，不另写一大段。
- **新活动直接发布当期题目、选项、参与方式，不要求先公布上期答案或结果**。默认不公开上一期答案、竞猜结果或结算信息；上一期未核实或未结算不阻断当期活动。只有用户明确要求时，才另行公布已核实的答案或结果；不得编造答案、成绩或积分。参考 `references/weekly-activities.md`。
- 课程有需要时在概念对应段落插 `[配图位置：具体图意]`，该标注只是建议位置并不代表已经生成图像。先生与资讯助理讲解文字适中，既专业又听得懂。
- 正文格式仅使用 `===== 资讯助理 =====`、`===== 先生 =====`、`NN男：`、`NN女：`。**可复制正文禁止Markdown加粗**。用户要指定篇幅时，校验实际字数/条数，但事实正确性优先于强行凑字。
- 小说中不以虚构成员利益/跟票发言冒充现实第三方真实客户投资见证，也不宣称系统已真实发群或真实执行证券订单。

## 6. 审稿门禁
参见 [QA-GATES.md](references/QA-GATES.md) 和 [CONTINUITY-AND-FACTS.md](references/CONTINUITY-AND-FACTS.md)。
- P0阻断：身份/性别/出场权限错误、主讲/顾问混淆、虚构活动答案、未经核实行情、擅称送达/真实获利。
- P1重大：剧情最后节点未接上、人物已采用经历矛盾、课程/活动顺序错误、封群时点与当日场次矛盾、多人对白模板化严重。
- P2语言：AI空话、重复emoji、太长、人物声音被抹平、图片位置不相关。
- 在可运行Python环境执行 `python skills/p004-chat-suite/scene-orchestrator/tools/validate_scene.py draft.txt --roster skills/p004-chat-suite/characters/final-identity-65.json --scene morning --json`（上午稿；下午/晚间分别使用 `--scene afternoon`/`--scene evening`）；写活动时加 `--activity`。**不得省略场次参数**，否则无法触发上午P0静态初筛。脚本仅能检身份标签/准入/重复/加粗/旧先生/当期活动存在；不能验证行情真实性或人设自然度。若没运行不可谎称机器通过。
- 用户曾明确取消的旧异常（例如之前某次闭群发言、旧报价提醒）不继续反复提示；重心是新稿的真实重大问题。

## 7. 交付协议
用户要剧情：**直接给完整可复制正文**，不先输出每个人物的分析表、冗长自证或检查日志；只对未核实的关键事实简短声明。用户要巡检：列P0/P1/P2真正新发现与修复；不要把“读取过”当成验证。
用户说“改短/换口吻”时只改指明内容；人物身份、数字、活动先后不擅自变。用户确认之后才归档为已采用状态，不自动发布、WhatsApp/Telegram发消息或改Google Doc。

## 8. ChatGPT新对话的能力边界
当前会话可以依据本Skill工作；**仅在GitHub更新SKILL.md不会让任意新的ChatGPT对话自动加载私有代码。** 如需该触发词在ChatGPT常用项目长期可用，将 [CHATGPT-PROJECT-INSTRUCTIONS.md](CHATGPT-PROJECT-INSTRUCTIONS.md) 加到对应ChatGPT Project的项目说明，并确保GitHub和Google Docs连接可用。Codex可通过仓库 `.agents/skills/ellery-westcott-scene/SKILL.md` 发现入口。不要声称GitHub同步等于ChatGPT产品全局安装。

## 9. Notion 已批准纠错实时对照｜强制前置
Notion页面：https://app.notion.com/p/400fd480b91e816cbb9be0b315d2b976
GitHub规则快照：references/notion-approved-corrections.json
本项是**出稿时连接器读取与比对**，不是后台常驻同步。不得声称已安装Notion自动同步或GitHub CI已通过，除非实际获得结果。

每次完整场次创作前：
1. 通过已连接Notion读取页面中「机器可读的已确认纠错规则」JSON代码块；仅采用record_type=EW-CORRECTION且status=approved的规则。
2. 读取仓库JSON快照并按id逐项比较状态、场次、禁用短语、必需主题；若Notion有新增或更新，必须先将已确认规则同步到仓库快照，或标记CORRECTION_DRIFT并阻断正式出稿，不得悄悄继续沿用旧快照。
3. Notion不可访问则标记NOTION_SOURCE_BLOCKED；允许做清楚标为“未完成Notion实时核验”的草案，但不能宣称全部通过。
4. 每次上午稿实际使用 --scene morning 和最新快照运行validate_scene.py；其结果只有“静态检查”，不能代替五Skill语义验收、真实财经新闻与Google Docs校验。
5. 未经用户明确同意，不将候选稿写成已采用剧情；Notion与Docs具有不同职责。

**重要**：连接器读取必须每次实际调用，仓库修改不等于ChatGPT自动执行。若需要无人值守实时同步，仍需另设已授权Notion API/受托运行环境，现阶段没有部署。

## 自动化任务挂接（2026-10-22）
从ChatGPT自动化/Project入口进入本总Skill时，先读取仓库根 `AUTOMATION-CONTROL-CENTER.md` 的来源门禁与出稿验收规则；不得仅凭任务提示词就宣称已读取GitHub、Google Docs和Notion，也不能把其它GPT窗口视为受此文件约束。任务完成后依本文件的交付协议输出。


## 2026-10-23｜Airtable正式对白辅助记忆读取与增量冲突门（V3候选）

本门仅增强检索与质检；**Google Docs仍为已采用剧情权威、`characters/final-identity-65.json`仍为65人身份权威**。Airtable不是第二份正式剧情，更不能用于直接修改Google Docs、实盘交易、领奖状态或发布。
- 辅助记忆库：Airtable base `apptVGZxcEdZkdN5a`（「ELLERY WESTCOTT｜剧情与65人记忆辅助索引」）；成员索引、正式对白证据、剧情事件、人物关系、学习进度，以及「增量同步检查点」「同步冲突待审」七张表。连接不保证每个ChatGPT窗口都具有授权；需在**本轮**实际成功读取才标记 `AIRTABLE_READ`。
- **写稿前强制读取**：先执行GitHub入口、Notion批准纠错、当前正式Docs最新日期页签与修订号、65人身份和各人已采用口吻，再通过已连接Airtable按拟出场编号查询「02_正式对白证据」最近有效原话，并参考「03_剧情事件」「04_人物关系」「05_学习进度」。若Airtable不可用则标 `AIRTABLE_SOURCE_BLOCKED`；允许凭可核对的Google Docs和GitHub继续给出受限候选稿，**不准声称已使用Airtable记忆**。返回的口吻索引和观察记录不等于新批准的人设规则。
- 每一人物至少保留来源日期、正式页签、原话、证据ID、文档修订号；不得依姓名/昵称合并重复姓名角色，不把候选/试听/AI写入测试和虚构跟票台词升级为真实成交证据。
- **增量对照**：可使用 `tools/airtable_memory_gate.py`，传入本次连接器实际读到的官方Doc原始段落、65人身份和Airtable证据快照；对**同一日期/页签的成员编号+原话全文**进行逐条多重匹配。原文未变但段落前移/后移时保留原证据ID、只标记位置变化；原话修改或消失、性别冲突、非授权43—65号、重复证据ID或来源错误都进入待审，不删除、不覆盖、不凭位置当作新人物发言。不确定的新增在冲突处理前暂停。纯比对脚本不联网、不写入任何应用、不证明行情事实或发布状态。
- 已审核的人物上下文应展示来源引文，而不是直接把职业偏好推广为稳定说话口癖。若发现同一日有效原话与Airtable引文不符，以实时Docs为准，记录 `MEMORY_CONFLICT_REVIEW`，阻断“全量记忆验收通过”，相关记录先审核。
- 同步操作必须明确区分 `MATCHED`、`MOVE_REVIEW`、`NEW_PROPOSED`、`EDIT_OR_DELETE_REVIEW`、`SOURCE_BLOCKED`；只有逐项验证的正式引用才允许写入Airtable辅助表。写完重新读取核对唯一主键、日期、身份、来源，**GitHub文件或Airtable表建立不等于定时任务已开启**；任何自动触发和写回需要另行部署并验证。
