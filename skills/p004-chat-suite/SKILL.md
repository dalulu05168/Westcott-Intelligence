---
name: p004-chat-suite
description: ELLERY WESTCOTT 虚构财经教学会话五合一入口，统一调度总导演、编剧、先生、资讯助理和65位成员。
---

## V2.1 执行入口（2026-10-17）

每次生成候选前读取[连续记忆与真实执行](references/runtime-v2.1.md)，通过统一控制器检查最新Doc修订、时段、人物记忆及事实引用；CLI已接入V2.1，旧归档函数不代表新运行验收。机器规则以config/editorial-policy-v2.1.json为准。历史协议保留，冲突以本轮用户指令及本节明确的新执行门禁为准；自然度、新闻因果和采用仍须审稿，不自动发送。

## v1.8 每次必须执行（2026-10-16）

先读取并执行[记忆、事实和剧情执行协议](references/editorial-execution-v1.8.md)。在沿用v1.6/v1.7选角与时段规则的基础上，读取最新正式Google Doc并运行`scripts/editorial_execution.py`，保留真实文件读取凭据、逐人已采用原句、候选口吻与本轮回复/记忆/事实引用。当前文档覆盖同日期旧快照，不能重复累计或继承已撤回台词；缺来源不编往事。输出前检查错误，再审稿口吻、成员互答、新闻语义新增和课程承接。程序检查不证明新闻真实，不批准发布，不自动恢复暂停任务。


# 五合一Skill统一入口

本仓库是该项目唯一的Skill规则源，不依赖旧 `dalulu05168/-Skill` 仓库。Google Docs自动归档暂停，不自动发送WhatsApp/Telegram。当前无自动群发功能，只有经用户最终确认的文本才加入有效剧情记忆。

必须先读`references/daily-editorial-and-memory-v1.6.md`（2026-10-14最新用户指令，当前只允许01—40号出场、每天BVB/美股各一次、角色记忆强制读取），再读`references/five-skill-workflow-v1.5.md`，核对实际输入、无新闻分支和事实交接；再按任务读取：
- `references/staff-and-role-identity-20261012.md`（最新：先生 Jonathan Richard Hayes）
- `characters/final-identity-65.json`（用户确认的65人、11项身份字段）
- `references/session-rules.md`、`references/final-transcript-memory-and-format-20261012.md`
- `references/sop.md`、`references/weekly-activities.md`
- `references/editorial-gate.md`、`references/drama-and-language.md`
- `../p004-director/SKILL.md`、`../p004-writer/SKILL.md`、`../p004-teacher/SKILL.md`、`../p004-assistant/SKILL.md`、`../p004-members/SKILL.md`

执行步骤：按 Europe/Bucharest 识别故事日期与12节点；由资讯助理核验新闻来源及观测时间，形成批准事实集；导演从合规名单中按话题、历史、专业程度挑选成员；编剧处理人物对白；先生负责20:00课堂；资讯助理负责报道/竞猜/闭群；用户批准后，保存可追溯的日期+消息ID，不将试听台词、撤回稿当正式历史。

硬边界：所有新生成人物标签必须匹配最终编号性别，正文不得含Markdown加粗语法；默认中文审阅稿，罗马尼亚语仅按用户要求。不得冒充真实群参与者或虚构持仓/投资成绩。

当前档案：`memory/daily/2026-10-12/`；源文`10/13`题头与10月12日周一活动冲突仍待确认；第10号源稿写`10男`，但名册为`10女`，不加入10号记忆。26女点赞是reaction，不计文字消息。

06男/16女/26女/36男/46男/56男属于大额投资人设；根据各自职业及投资年限呈现稍成熟讨论，而不是统一专业分析师口吻。先读各自profiles/NN.json。

版本发布：每次改变规则必须更新CHANGELOG、运行`scripts/validate_repository.py`且保留校验结果；GitHub实际推送成功才宣称远端更新完成。

## v1.5 统一交付

五个组件是导演、编剧、先生、资讯助理、成员；本文件为统一入口，不是第六个组件。人物是65人，文件数量不是人物数量。采编核验由资讯助理承担，视觉为共享检查步骤。

后台记录实际读取资料、event_id、本次新增和每条claim_id；各角色只使用同一批准事实集。N01仅后台备料不含成员对白，N06工作日11:15无新增也准备午间稿。普通雷达无新增不凑通知；旧闻无持续影响退出。适宜群聊节点提供3–6条可选虚构成员对白，未采用不算历史。

图片按需读取`references/MASTER_PROMPT_V2.0.md`、`references/visual-v2-execution-20261013.md`、`references/visual-qa-15.json`，简约少字多图、字体突出重点、原始Logo不重绘。正式新闻验收读取`references/news-release-gate-v1.4.md`、`references/news-accuracy-acceptance.md`；离线测试与源码重建不当真实运行证据。


## v1.5.1 人物资料加载

遇到人物资料不可访问、语气草案未批准或缺少历史而取消全部候选时，读取`references/runtime-loading-v1.5.1.md`。任务内置快照在`references/runtime-context-v1.5.1.txt`；据实际读取方式记录来源，缺历史不编往事，身份已确认则可创作待选台词。N01仍不生成成员对白。




## 2026-10-14 最新用户执行修订 v1.6（优先于本文件旧描述）

**必须先读取** `references/daily-editorial-and-memory-v1.6.md`，根据每日最新正式Google Doc、独立长期记忆和近期已采用剧情选角。身份仍为65人锁定，但**当前仅01—40号允许在剧情中发言**；41—65号保留档案但不出场。每天准备一只BVB与一只美国市场股票研究，上午下午各一次、具体先后由用户提前确定；未确定时记PENDING_USER_SLOT，不自行安排或声称实际发送。资讯主线最多1—2条重大、有实质新增的事件，避免重复和无意义热度；助理自然讲事实、变化、条件与可讨论方向。**禁止“助理1条→成员2条”机械循环**，必须体现成员彼此接话与个人记忆，允许连续互答、少人回应或沉默。若本文旧规则与v1.6不符，优先v1.6。GitHub规则同步不是线上自动任务或真实群发送。

## 跨页面统一启动（2026-10-16，V2.0）

每次新页面/新会话启动前，先读取 `references/cross-page-unified-v2.0.md`，并继续执行现行 `references/editorial-execution-v1.8.md` 的实际读取凭据与审稿步骤。`memory/runtime/latest-checkpoint.json` 当前仅为占位模板，不能作为已核验剧情或实时同步证据。新会话必须重新读取正式Google Doc并核对页签、修订号、最后有效发言；读取失败时说明限制，不可声称已加载。不得因此恢复暂停任务或自动发送。
