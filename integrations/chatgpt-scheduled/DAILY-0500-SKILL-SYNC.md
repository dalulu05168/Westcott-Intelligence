# ELLERY WESTCOTT｜每日05:00五Skill与记忆同步核验
更新：2026-10-23｜时区：Asia/Kuala_Lumpur｜状态：已配置ChatGPT定时任务；Google Docs→GitHub端到端首轮同步未验证

## 目标与来源
- 每日马来西亚时间05:00检查已连接Google Docs与私有仓库规则；时间固定UTC+8，不因罗马尼亚夏冬令时变化。
- 正式剧情Google Doc ID：`1frtoFvohP3u2HfRzBPRZVLOzMfvnO-8Vi9iX3r5rmiM`。读取本次实际修订号、日期页签及用户已采用正文。排除总汇中非当日稿、空白、候选段落和「AI写入测试」；不能仅根据段落数量判断已采用消息数量。
- 财经新闻库 ID：`1jhb9N5JY8U_Ut5ngx7RW6235L_b8uDmUFv-08CbruW8`。只用于有来源、有发布日期和行情时点的资讯；不能把今日数据写入永久人设或作为已成交证明。
- GitHub `dalulu05168/Westcott-Intelligence` 的 `AUTOMATION-CONTROL-CENTER.md`、`AGENTS.md`、`skills/p004-chat-suite/scene-orchestrator/SKILL.md` 为启动入口；五个核心Skill为 `skills/p004-{director,writer,teacher,members,assistant}/SKILL.md`。此外核对65人身份、`memory/daily/`、`memory/long-term/` 与规则版本。
- 同步应以实际阅读的最新Docs正文为准；仅可把经过用户确认、适合长期复用的角色/剧情进展/规范写入对应Skill与有来源的记忆文件。原始正式剧情不得由此作业编辑。

## 每日执行步骤
1. SOURCE：读取正式Doc和财经库当前版本及相关日期页签，读取仓库五Skill与来源控制文件；记录`READ`、`SOURCE_BLOCKED`、`NOT_REQUIRED`。接口调用失败不能记为READ。
2. DIFF：对比当前生效角色（David Miller）、成员合法出场01—42、65人锁定身份、个性语言证据、课程及未结束剧情。只提取有已采用证据且能定位来源的变更。发生删除、身份冲突、无法判断是否正式采用，标`REVIEW_REQUIRED`，不自动覆盖。
3. PLAN：拟写入长期记忆的每个条目保留日期页签、原文、说话人、证据ID、Docs修订号；只修改实际需要的Skill文件，避免每天机械修改五份；不把候选、新闻报价或交易自述升级为现实成交。
4. WRITE：拥有权限且可验证时先在独立分支提交，检查差异，运行`python scripts/validate_repository.py`及适用测试；只有机器检查实际通过才按仓库既有审核流程合入。写后用连接器重新读取，核对SHA/内容。无法测试或没有审稿依据，保留待审，不能声称已完成同步。
5. CHECK：逐个检查5个Skill存在、可读、入口路径、关键身份和规则是否一致。必要时借GitHub Actions监测文件存在/引用；静态通过不等于GPT在任意聊天中自动调用，也不等于新闻事实真实。
6. REPORT：输出Doc修订与日期、五Skill逐项READ/BLOCKED、已更新文件及提交SHA、CI结果、GPT真实调用证据（如有）、未解决事项。无可靠变更输出「无需更新」，不能为凑成果擅写。

## 撰稿时的入口门
任何使用本仓库的完整晨间/下午/晚间写稿工作流，须先实际读取 `AUTOMATION-CONTROL-CENTER.md` 与剧情编排器，再按五Skill进行角色分工、真实Google Doc续写、人物及财经证据校验、候选稿静态及语义审稿。Project说明必须在实际ChatGPT Project里启用；GitHub文件更新并不会在独立聊天自动安装或执行。若实际缺一来源，清楚说明缺项并只交付受限候选，不得报告五项全通过。

## 当前验收边界
- ChatGPT定时任务是否能在无人交互下使用Google Drive/GitHub写接口：**尚未通过首轮真实05:00运行验证**。
- GitHub定时CI只能检仓库结构与回归，不访问私有Google Doc，也不代表在线记忆已同步。
- 未配置或未确认长期有效的Google API授权与自动运行器前，不可声称实现了独立于ChatGPT的无人值守Docs→GitHub写回。
- 不自动编辑正式剧情、群发、改交易状态、实盘下单，保留原有DRY_RUN/审核门。

## 日期与版本
- 马来西亚05:00 = 前一UTC日21:00。GitHub Actions schedule可能延迟，不可按cron配置直接声称当天已执行。
- 仅按本次实际修订号判断是否有新内容；记录最后成功同步的修订需以真实完成结果为依据，不预写成功标志。
