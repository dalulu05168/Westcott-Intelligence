# 五Skill V2.1｜连续记忆与真实执行

本轮升级控制器和本地回归，不增加第六个Skill，不启用或更新任何发送任务。

## 统一执行入口

`scripts/editorial_execution.py` 的命令行现在委托给 `editorial_runtime_v21.py`。原v1.8函数仅保留给归档回归；不能把原函数的结果当v2.1执行验收。五角色共享 `config/editorial-policy-v2.1.json`，不各自复制机器可校验规则。自然度、新闻因果仍须人工语义审稿。

先由已连接Google Drive读取完整原生Doc（全部页签及文本），保存documentId、revisionId、retrieved_at、tabs、paragraphs。再次读取文档修订号并保存同样ID/修订号和带时区retrieved_at为revision-check。控制器检查两次读取顺序、修订一致、5分钟有效期。来源文件只是读取凭据，无法凭JSON本身证明来源真实性；需要保留连接器操作证据。也可使用 --fetch-google-docs，经进程环境GOOGLE_ACCESS_TOKEN直接读API两次，程序不写出token。不要在聊天或命令参数粘贴秘密。

```powershell
python scripts/editorial_execution.py --date 2026-10-19 --snapshot current-snapshot.json --revision-check current-revision.json --members 25,34,38,40 --scene scene.json --output context.json
```

日期是计划创作日期，不替换实际读取时点。周末读取周五已采用剧情是正常行为；未来空页签不算已发生故事。原生空月汇总父页签跳过，日期子页签按源顺序读取，也支持月汇总正文中的明确日期标题。未知非空无日期内容直接拦截。

每轮返回最新故事日期、页签、时段、末句、开闭群、原始署名数、缺标签片段、去重与待审数。缺标签隔离，未经确认的晚间闭群不会并入01号台词。人工修正只写独立review文件，绑定修订和完整正文哈希，保留原文。重复检测仅做保守去重，语义近重复、残句仍须审阅。

## 记忆入口与动态状态

`memory/derived/v2.1/member-index.json`提供65个入口；`members/NN.json`保留证据原句与动态记录。没有经历的人明确无确认记录，不生成家庭、持仓或关系。既有36份legacy文件不删除、不覆盖；25/38的新正式经历在统一派生入口可检索。生成时重新用最新Doc替换同日旧有效视图；不会将两版剧情累加。先前已采用的身份错误、待核归属继续隔离。

`memory/curated/*-dynamic-state.json`保存少量持久状态与学习进度，须有消息ID、日期+人物+规范化原文的evidence_fingerprints、审核者及语义支持声明；程序检查证据内容与人物一致，不声称理解原句语义。插入空标签导致序号移动时，只能重连唯一的相同内容；撤回/改写或指纹缺失则阻止继续沿用，需重新审稿。已审标签通过原标签、人物、性别、日期和规范化原文指纹复用，不推断新标签归属。空错误性别标签保留为checkpoint.source_anomalies，不算人物发言。25号余仓、34与40号AA状态分开；未知股数保持null。所有股票自述仅属虚构剧情，不是实盘证明。

关系分为候选、直接交流与稳定关系，读取既有relationship-seeds但不凭共同出场升级。人物可隔段互答、沉默、生活交流；不固定助理后几人。重复节奏只是审稿提醒，不强塞互动。人名和GIF没有配额，沿用已确认的个人习惯；实际素材缺失不声称发出。

## 课程和周日复盘

周日晚由助理与先生进行本周市场、推荐股票、当前形势和下周重点复盘，具体时刻待用户指定。`planning/course-progress-v2.1.json`单独记录周一已选材料与后续待补课程。计划、素材读过、正文已讲、作业布置、作业提交及图片送达不能互相推导。周五MACD已讲，不能重报尚未开始；不自动补写未布置的作业。

## 财经与发布状态

通过 --ledger 和 --event-history 连接现有news_release_gate及证据去重，无历史不称去重完成；相同原文换标题阻止。缺价格/时点/来源的结构化报价拦截；未标注的自然语言事实仍依赖人工核查，绝不称自动证明所有新闻真实。

`facts`、`story`、`delivery`独立。控制器输出始终publication_allowed=false，事实结构PASS不批准发布。Telegram message_id仅表示平台接受，不证明终端送达/已读。既有发送器、授权、任务和备用长上下文原样保留；尚未接入线上执行。

## 本地验证

```powershell
python scripts/rebuild_editorial_archive_v21.py --check
python -m unittest discover -s scripts -p 'test_*.py' -v
python scripts/validate_repository.py
python scripts/sync_runtime_memory.py --check
```

Windows临时目录受限时，将TEMP和TMP设为本仓库 .test-tmp。rebuild不访问外网；它按已审源重建派生归档，并永远标记ARCHIVE_REQUIRES_LIVE_REFRESH。新来源或状态更新先审稿，再显式重建；不能将归档检查当实时读取。

验收需分开：源码与离线测试、真实Doc读取、候选生成端到端、人物自然度人工评分、线上任务应用、消息回执。当前P2人工审核保持PENDING_HUMAN_REVIEW。

`scripts/continuity_acceptance.py`提供采用核对与阶段计划函数。verify_adoption必须传入story_date，逐条匹配目标日期的正式原文，同时验证用户确认凭据、候选摘要与修订号；project_events只做幂等提案视图。二者均不写正式记忆，调用者仍须真实读取来源和取得具体采用确认；字符串凭据本身不证明人类授权。独立进程恢复测试不等同新聊天验证。验收记录见audit/continuity-acceptance-20261018.json，候选见planning/acceptance-20261018/。

## v2.5｜最新晨间运行配置（2026-10-20）

读取 [上午09:00—12:00及时区](romania-morning-session-v2.5.md)及`config/editorial-policy-v2.1.json.group_sessions`；上午09:00开群、11:00仍开放、11:45—12:00 N06结尾、12:00闭群，12:00—14:00不生成上午成员对白。早报07:30/N01仍是后台。使用Europe/Bucharest自动处理2026-10-20 EEST/UTC+3 与2026-10-25之后EET/UTC+2。配置及离线测试不等于实际发送器已经部署了这些执行时间。
