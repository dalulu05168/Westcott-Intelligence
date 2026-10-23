# ChatGPT 自动化总控协议｜2026-10-22

> 作用：让现有 ChatGPT 定时任务、ChatGPT Project 内的对话、Codex/仓库内流程**共享同一份最新来源和验收标准**。本文件不能改变 ChatGPT 产品的全局指令优先级，不能控制未接入该流程的独立聊天，不会自动触发或调用其他任务。不能把提示词约束称为硬性系统级保证。

## 0. 任务分流（先识别，避免混用）
- `WESTCOTT_SCENE`：上午/下午/晚上虚构群聊、活动、答疑、先生、人物对白、编号口吻改写。使用五Skill、正式剧本文档、65人、Notion已批准修订以及下面的出稿检查。
- `WESTCOTT_LESSON`：每周五堂初级股票课程，制作图文Word，周一三五技术、周二四理念。课件独立交付；除非用户请求，不生成群聊。
- `WESTCOTT_QA`：仅针对确有可读取候选稿/正式稿的质检。没有稿件不能自称检查通过。
- `WESTCOTT_AUDIT`：每小时监测仓库/官方文档/规则漂移/已提交材料/可审计执行记录，重大新异常才提示。不窥视或控制其它ChatGPT窗口。
- `PROJECT_QA`：霸王消息控制中心、三合一、财经推送系统等代码、PR、Actions、运行记录与证据审查。不能套用虚构成员对白规则。
- `AI_RADAR`：筛选对现有项目有实际帮助的AI软件/开源技术更新；只研究，不擅自安装。
- 如一次任务涉及多个模式，分别记录所需来源、交付物和可执行边界，不让一个模式冒充另一个模式已完成。

## 0A. 每日05:00五Skill与记忆同步核验（2026-10-23）

- 任务模式：`WESTCOTT_DAILY_SYNC`；马来西亚时间 `Asia/Kuala_Lumpur 05:00`（UTC前一日21:00），与罗马尼亚剧情时间 `Europe/Bucharest` 分别处理，不随欧洲夏冬令时改变05:00。
- 操作流程见 `integrations/chatgpt-scheduled/DAILY-0500-SKILL-SYNC.md`；先读取本仓库最新文件与正式Google Docs（ID `1frtoFvohP3u2HfRzBPRZVLOzMfvnO-8Vi9iX3r5rmiM`），排除AI写入测试、草稿和未采用文本。财经新闻库 `1jhb9N5JY8U_Ut5ngx7RW6235L_b8uDmUFv-08CbruW8` 仅为带时点的市场素材来源，不可升级为永久人物事实。
- 五个实际核心角色Skill：`skills/p004-director/SKILL.md`、`skills/p004-writer/SKILL.md`、`skills/p004-teacher/SKILL.md`、`skills/p004-members/SKILL.md`、`skills/p004-assistant/SKILL.md`；编排入口是 `skills/p004-chat-suite/scene-orchestrator/SKILL.md`，非第六个角色。核查两者与65人身份、每日/长期记忆的一致性。
- 每次写作（人工或定时）都必须按`WESTCOTT_SCENE`执行实际来源读取与出稿门。仓库CI能检存在/规则引用但**不能**证明普通ChatGPT窗口自动调用Skill；只有本次读取回执或可观察工具日志能证明对应调用。
- 自动任务可以按真实权限、版本对比、安全测试与写后读回更新仓库；不得凭任务提示词自称定时同步已成功。无已核实变更不强行改动，失败时列出未完成项；未经批准不自动发布正式剧情、财经消息或证券交易。

## 1. 统一的可追溯来源
- GitHub私有仓库：`dalulu05168/Westcott-Intelligence`；先读取本文件最新内容，再按模式读取入口。
- Westcott 总入口：`START_HERE.md`、`AGENTS.md`、`skills/p004-chat-suite/scene-orchestrator/SKILL.md`，按总入口实际调度导演/编剧/先生/资讯助理/成员Skill。
- 已采用剧情唯一实时源：Google Docs `1frtoFvohP3u2HfRzBPRZVLOzMfvnO-8Vi9iX3r5rmiM` 对应日期页签，须辨别修订、上一条已采用对白、活动答案和课程进度。不可用旧仓库快照假冒最新Docs。
- 已批准纠错：Notion `400fd480b91e816cbb9be0b315d2b976` 中已批准机器规则；与 `skills/p004-chat-suite/scene-orchestrator/references/notion-approved-corrections.json` 比对；存在漂移必须阻止“已全验收”声明。Notion缺权限则标记阻塞；不能默默认为一致。
- 人物身份：`skills/p004-chat-suite/characters/final-identity-65.json`；实际出场的人另读 `characters/profiles/NN.json`、可核实的个体历史与 `voice-management/voice-index-2026-10-21.json`，必要时读最新Docs已采用原话。候选性格不等于用户已批准，缺家庭资料就标未知，不能臆造。
- 真实财经资讯必须核对消息发布时间、交易日、交易所、价格时点与一手来源；不能用未验证新闻做正式事实。
- **读取必须是本次执行实际做过的连接器动作**。只引用路径、记得以前看过、在提示词里声称“强制读取”均不等于实际成功。

## 2. 所有任务的启动门（source gate）
开始工作时建立本次内部读取回执：task_mode、run_date、GitHub入口路径和具体版本（如可得）、已成功读取/未读取的源、对应Doc日期及最后已采用节点、Notion规则状态、所涉人物编号及口吻证据、查证新闻/教材来源、与任务有关的未解决冲突。
每个关键源的状态只能为 `READ`、`SOURCE_BLOCKED`、`NOT_REQUIRED`；不要把`SOURCE_BLOCKED`写成`READ`。
- 任何身份/原始数字/新闻/上一期活动答案缺证据，不得编造或标记已核实；可交付清楚标明限制的局部草稿。
- 权限/工具不支持时，指出哪个动作未完成，而不是只说“全部已加载”。
- 正式已采用剧情只能由用户确认；新稿都是候选，不擅自更新正式Google Docs。

## 3. Westcott 出稿门（output gate）
- 剧情：罗马尼亚时间 Europe/Bucharest，工作日09:00开群、12:00闭群、14:00下午开群；资讯助理负责早间报道，现任先生 David Miller 晚课，01—42号可出场、43—65不能新出场；活动直接发布当期题目、选项及参与方式，默认不公布上期答案或结果；上期未结算不阻断新活动。课表及当天用户最新批准调整优先于旧文档。
- 人物：按编号身份、该成员历史短/长句与真实个人说法，先匹配人物再做Humanizer；不把所有成员写成同一种分析师口吻，职业可影响关注但不推断家庭、成交或收益；emoji按已批准规则。
- 静态检查：能够运行时，实际用 `skills/p004-chat-suite/scene-orchestrator/tools/validate_scene.py`、65人名册及目标场次参数执行；没有实际执行不得称“机器通过”。检查阻断项未解决不得标记可发布。
- 语义核验：剧情连续性、人物历史、资讯新旧和因果、活动真实结果、课程进度、教案图表完整性需要独立有证据核查，静态脚本不能证明已通过。
- 课程：每次交付五份完整图文Word；优先已确认课程进度和原Logo；统一尺寸位置/色系/居中标题、技术图表有实际讲解价值、每图正文解释观察与失效条件。没有图文文件不得称“完成五课”。
- 只有静态和证据审查实际满足，状态可写 `CANDIDATE_QA_PASSED`；未经用户批准，严禁写`PUBLISHED`或`ADOPTED`。

## 4. 自动化分工与失败处理
1. **Westcott每周课件**：只负责五份教案交付与课件审查，不写群聊、不更新正式剧情。
2. **Westcott五Skill巡检**：只针对可审计的新增重大P0/P1、规则漂移和阻断源报告；与日常讲稿质检不重复报告同一旧问题。
3. **财经社群讲稿质检**：检查实际有的稿件，给出具体替换建议；不创建无来源的虚假“已审”结果。
4. **项目质量监察官**：代码变更、测试和运行证据，区分测试通过/失败/未执行/无权限。
5. **AI新技术侦察员**：面向当前项目给出高价值资讯，不自动安装。
这些任务**各自按自己的定时器执行**，不会由本文件自动排序调用彼此；无法调用别的任务、不能从别的ChatGPT窗口取得私有过程。共享的是本协议及真正可访问的外部源，而不是跨任务共享思维或运行日志。

## 5. 输出最小验收格式（不污染可复制正文）
报告类：`结果状态｜已核对的来源｜新增发现或交付物｜明确未完成事项｜可验证链接`。
写稿类：先输出不含Markdown加粗的可复制候选正文；必要限制另起简短说明。严禁用“已同步记忆”“已发布”“全部验证通过”掩盖未执行的工具步骤。
不擅自启用已暂停的财经通知、群发、股票操作或更改他人的消息；若需启用对外发布先单独征得用户批准。

## 6. ChatGPT Project接入说明
把 `skills/p004-chat-suite/scene-orchestrator/CHATGPT-PROJECT-INSTRUCTIONS.md` 中的指令放入常用ChatGPT Project的项目说明，并在那里发起写稿对话。GitHub上这份文件和自动化任务**不会自动改写用户ChatGPT Project设置**。即便有项目指令，仍需每次运行真正读取外部源，不能保证普通GPT绝不违背；能可靠约束的是受控工作流中的程序校验与人工批准门。


## 2026-10-23｜Airtable辅助剧情记忆安全门（新增）

在 `WESTCOTT_SCENE`/`WESTCOTT_QA` 中，现可将 Airtable base `apptVGZxcEdZkdN5a` 的「人物索引、正式对白证据、剧情事件、人物关系、学习进度」作为**辅助查询**；正式Google Docs、65人身份和Notion已批准纠错优先级保持不变。实际写稿时必须**由本次运行连接器读取**人物近期原话证据（含日期、页签和原文），不得因为数据库存在就声称已调用其记忆；缺权限则标注 `AIRTABLE_SOURCE_BLOCKED` 并从已验证的Docs继续受限创作。

增量核对工具 `skills/p004-chat-suite/scene-orchestrator/tools/airtable_memory_gate.py` 只对本次实际获取的Docs+Airtable快照提出动作计划，支持按“编号+原话”保留稳定证据、识别段落移动、隔离修改/删除/身份冲突。不在脚本内使用账号凭据、不静默覆盖已有证据、不把虚构交易当真实金融事实。任何发现旧证据失效的情况先写到「07_同步冲突待审」供审核；无误的新证据仍须在连接器写入后**重新读取确认**才可报告完成。

上述规则没有配置定时任务，也不能改变ChatGPT其它窗口的插件授权。自动同步必须单独部署可运行调度并检查真实日志；仅有代码、CI通过或Airtable表不是自动同步已生效。
