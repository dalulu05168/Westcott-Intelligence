# 新窗口统一启动｜先读这里

**[START_HERE.md](START_HERE.md)**：新ChatGPT/Codex窗口输入“启动Westcott”时的权威引导入口。必须实际读取最新五Skill、正式Google文档、人物历史并核对执行结果；不会因仓库存在文件就自动加载、自动写入或自动发送。

---

## 五Skill V2.1 连续记忆与真实执行

执行入口与命令见 [runtime-v2.1.md](skills/p004-chat-suite/references/runtime-v2.1.md)。源码升级覆盖统一控制器、65人派生记忆、修订复查、课程/事实/发送状态隔离及回归测试；线上任务未应用，人工语义验收待完成。原备用上下文继续保留。

# v1.8 写作前执行与审稿（2026-10-16）

现行补充协议：`skills/p004-chat-suite/references/editorial-execution-v1.8.md`。使用`scripts/editorial_execution.py`生成实际读取凭据、人物证据及场景检查；必须传本轮Google Docs文本与页签快照。同日期旧稿不与新修订重复累计；候选口吻、关系、状态不提升为已采用历史。新闻继续通过既有事实检查，并按原文证据键排除重复。离线校验不代替原文事实/语义审稿，不批准发布。五项暂停任务、机器人部署及发送流程未由此次改动恢复或更新。

# v1.6 最新执行入口（2026-10-14）

从2026-10-15起最新用户规则见 `skills/p004-chat-suite/references/daily-editorial-and-memory-v1.6.md`；明日工作单见 `planning/2026-10-15-editorial-plan.md`。身份表仍保留65位，但当前实际发言只准01—40号。BVB与美股每天各安排一次研究发布，上午下午由用户提前指定；严格筛选重大新闻并核验发布时间和行情口径。每个候选成员必须读取对应profile、近期正式Google Doc / `memory/daily`与 `memory/long-term/members/NN.json`，不再只凭截至10月12日的v1.5.1内置旧快照。编剧取消固定助理→两成员格式，成员之间应有自然回应、分歧和个人记忆连续性。

这是仓库内的内容制作协议，不代表旧的ChatGPT Scheduled任务提示词或Telegram/WhatsApp发送已自动更新或恢复。现有65人人物身份原文件未做改动，新增10月14日已采用人物记忆文件保留来源。2026-10-15新闻和股票标的尚未实时核验，计划状态为待用户指定。

# v1.5.1 原任务运行资料衔接

修复人物身份与语气批准状态混淆、缺历史即取消全部对白的问题。原5项任务完整修订正文内置65人身份/语气与已整理历史快照，减少执行时读取外部人物文件的依赖。原始档案不改动；内置快照不是实时全量历史。线上尚未应用，提示词长度上限尚未确认，不能将源码提交当部署成功。

# ELLERY WESTCOTT｜五Skill v1.5

本版升级原五Skill及统一入口，清理冲突旧规则，补齐无新闻分支、批准事实交接、自然对白与连续教学；修复分析依据链和行情时点检查。固定65人身份与历史、原始Logo及Master V2.0保持原字节。

- 入口：`skills/p004-chat-suite/SKILL.md`
- 执行协议：`skills/p004-chat-suite/references/five-skill-workflow-v1.5.md`
- 离线验证：`python scripts/validate_repository.py`；`python -m unittest discover -s scripts -p "test_news_release_gate.py"`
- 版本验证记录：`VALIDATION-REPORT.json`

本次不修改原五项ChatGPT Scheduled任务正文/ID/日程/通知，不自动同步线上。用户已提供v1.4线上更新回执，但本仓库未取得独立线上全文快照或真实新版运行正文，不能据源码声称推送与新闻准确率通过。Google Docs暂停，自动配图及群外自动发送不启用。以下为历史发布说明，历史状态不当当前线上读回。

---

# v1.4 新闻核验整改

增加逐条证据账本、可执行发布检查、旧稿回归样本及原5项任务完整替换正文。代码及文稿已准备；线上任务写入、运行和送达尚待真实证据。当前事实核验规则见 `skills/p004-chat-suite/references/news-release-gate-v1.4.md`。

# v1.3视觉规范与素材

本次补齐视觉规范与原始Logo，保留五个组件、统一入口及人物历史。下方v1.2提交记录为历史；v1.3发布证据以实际GitHub提交和远端文件读回为准。

# ELLERY WESTCOTT｜五合一Skill独立源码

当前GitHub仓库：`dalulu05168/Westcott-Intelligence`（Private），分支：`main`。

v1.2-review已于2026-10-13入库，首次完整导入提交：`d9e8ba0d2fc4773e5dc0c83ac3d54802c343b90c`。该提交含121个文件；远端文件列表与全部Git blob校验值已对照本地ZIP验证。

项目目标：维护虚构罗马尼亚财经教育群聊的65人固定身份、五个独立Skill、12节点、连续剧情与可审计记忆。

## 当前主身份

先生：Jonathan Richard Hayes（Jonathan）。投资顾问：Gabriela Ion（Ion）。咨询顾问：Ana Maria（Ana）。资讯助理：独立未命名角色。

## 主要入口

- 五个Skill统一入口：`skills/p004-chat-suite/SKILL.md`
- 五个组件：`skills/p004-director/`、`skills/p004-writer/`、`skills/p004-teacher/`、`skills/p004-assistant/`、`skills/p004-members/`
- 用户最终65人身份：`skills/p004-chat-suite/characters/final-identity-65.json`
- 65个独立档案：`skills/p004-chat-suite/characters/profiles/01.json`–`65.json`
- 每日归档：`memory/daily/YYYY-MM-DD/`
- 长期人物记忆：`memory/long-term/members/`

## 上线前检查

执行`python scripts/validate_repository.py`。2026-10-12归档中10号性别与10/13标题的冲突均保留待人工审核；此类审核问题不能自行改写历史。

## 当前运行状态

源码及规则已经入库；现有5项线上任务的配置和日志尚未取得。`config/monitoring-plan.json`仍为DRAFT_NOT_DEPLOYED，不能据此声称后台扫描或自动发布已启用。

新闻准确性标准见`skills/p004-chat-suite/references/news-accuracy-acceptance.md`；准确率尚未实测。v1.3已补齐完整MASTER PROMPT V2.0及用户提供的透明Logo；尚未完成实图验收。暂不修改Google Docs。

## 安全边界

虚构教学对话，不冒充真实投资者或用未核验的数据产生投资背书；不记录未发生的真实交易、奖品领取、成员登录等事实。

## 删除旧仓库前的必要条件

`dalulu05168/-Skill` 仍包含其他项目。本仓库已完成入库与回读，但这不构成删除旧仓库的授权；任何清理仍须用户另行明确指令。
