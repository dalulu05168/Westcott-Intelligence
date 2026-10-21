# 五合一Skill规范

## 2026-10-21 人物说话能力管理强制入口

凡涉及成员对白、口吻优化或人物家庭/职业表达，除原有五Skill流程外，必须额外读取 `skills/p004-chat-suite/voice-management/SKILL.md` 与 `voice-index-2026-10-21.json`，并在生成正式新稿前刷新最新 Google Docs 及对应人物已采用历史。65人身份以 `characters/final-identity-65.json` 最终版为唯一权威；新语言库样本未自动批准为口吻规则，家庭关系未给则空，旧 `dalulu05168/-Skill` 不参与同编号身份合并。新稿只有01—42可出场，43—65不得擅自添加。管理页用户确认的本机规则未导出并正式审定前，禁止声称仓库已同步。

从`skills/p004-chat-suite/SKILL.md`入口读取。当前教师为David Miller（David），股票执行负责人（Head of Equity Execution）；现行身份见skills/p004-chat-suite/references/staff-and-role-identity-20261021.md，历史Jonathan/Henry原文保留，正式标签“先生”。资讯助理、投资顾问Gabriela Ion（Ion）、咨询顾问Ana Maria（Ana）为分立角色。

所有新生成可复制对白不得使用Markdown加粗语法。65人身份以最终65人JSON为准。原始剧本保留原文，规范化版本及长期记忆必须区分来源与后续更正，不能虚构已发送、获利、注册或已领取奖品。

每次提交前运行`python scripts/validate_repository.py`。未通过不合入主分支。旧仓库不作为本库依赖。

## 2026-10-13 65人上传明细对照（持续执行）

新增任何角色、选角、剧本归档或记忆操作，先阅读 [65人逐字段对照报告](skills/p004-chat-suite/characters/IDENTITY-CROSSCHECK-2026-10-13.md)。本次用户上传的65行身份明细与 `final-identity-65.json`、65份独立人物档案一致。**人物主键只能是零填充编号01—65；姓名和NICK不唯一**：41/62同名Matei Cojocaru，07/27同NICK Elena，30/32同NICK Victor；不得因重名或同昵称合并角色或记忆。旧仓库 `dalulu05168/-Skill` 的人物档案不是本项目的身份来源。10月12日M053（10男与10女身份冲突）、10月13日M060（15男发言归属待核）均保留原稿并隔离，不得作为已确认角色记忆，也不得擅自修改正式身份。任何新身份冲突均先复核用户原始65人表。
