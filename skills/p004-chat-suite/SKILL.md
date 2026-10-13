---
name: p004-chat-suite
description: ELLERY WESTCOTT 虚构财经教学会话五合一入口，统一调度总导演、编剧、先生、资讯助理和65位成员。
---

# 五合一Skill统一入口

本仓库是该项目唯一的Skill规则源，不依赖旧 `dalulu05168/-Skill` 仓库。Google Docs自动归档暂停，不自动发送WhatsApp/Telegram。当前无自动群发功能，只有经用户最终确认的文本才加入有效剧情记忆。

必须先读`references/five-skill-workflow-v1.5.md`，核对实际输入、无新闻分支和事实交接；再按任务读取：
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
