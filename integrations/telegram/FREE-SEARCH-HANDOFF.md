# 免费搜索到审核队列的实际交接

2026-10-17：固定8个栏目不是全球雷达的搜索范围。它们的空窗口不能代替广泛搜索，也不能证明没有重要新闻。继续沿用原Scheduled任务，不新增任务或付费API。正式审核、70分门槛、60分钟比较窗口、20分钟新鲜度和原子去重均保持现行代码。

## 每次原任务必须执行

1. 实际使用现有免费搜索工具，分别覆盖RO、FR、US、GLOBAL。围绕本国宏观与央行、财政/监管、上市公司公告与财报、金融科技、能源与地缘主线检索；不以8个栏目为空直接结束。媒体报道可以提供线索，正式证据必须回溯官方原文。记录实际查询词、执行UTC时间、结果URL和访问失败，不能伪造查询记录。不能声称搜索穷尽全球。
2. 读取现有最新完整小时快照。缺失或超过20分钟，按原news/intake-requests规则只登记同小时一次补采；取得新快照再继续。只创建补采文件就结束，属于未完成交接。
3. 将实际检索记录保存为news/searches/<UTC时间>.json。结构为searches数组（每项region=RO/FR/US/GLOBAL、query、searched_at含时区、status=OK；搜索失败用ERROR并保持HELD），articles数组（每项article_url、publisher_basis_url、published_at、source、title）。另保留实际搜索返回的线索URL、查询限制和无法核对的时间。publisher_basis_url是需要独立审核的官网归属证据链接，不是自动的官方认证。
4. 用新入口合并搜索候选与固定来源快照：

   python integrations/telegram/search_intake.py --edition news/editions/<实际快照>.json --manifest news/searches/<实际搜索记录>.json --output news/editions/<同一窗口时间>-search.json

   命令读取真实原文、保存哈希，保留未读到正文的候选并标INCOMPLETE；过期文章记录OUTSIDE_WINDOW，不改原发布时间，不换成抓取时间，不放宽窗口。原快照和现有输出均不覆盖。文件名须符合editorial_policy.EDITION_PATH（小写字母、数字、短横线或下划线）。不能复制过去窗口假装当前发现。
5. 对合并后的完整候选集逐国审核。READ/COMPLETE仅代表资料捕获，不等于事实、官方身份、数字或重要性已确认。用真实原文独立核验来源身份、每个事实与数字、时间、全部候选的比较及稳定event_key；所有相关候选都必须评估，不能丢掉不方便核验的候选来提高排名。无合格新闻保持静默；搜索或正文失败不能说成无新闻。
6. 按EDITORIAL-AUTOMATION.md和现行发布器的真实契约构建news/approved/账本：来源、原文摘录、数字单位、条件影响、后续关注和完整hourly_selection（指向合并快照及其digest）。只在本次实际语义核验后写CONFIRMED，reviewed_by如实标记ChatGPT及时间，不能冒称真人审核。没有核验原图时附官方原文链接。
7. 实际执行scripts/validate_repository.py、news_release_gate.evaluate、reviewed_publish.prepare、editorial_policy.validate_release。先检查已有审计/claim/event/slot占位；已发送或PENDING均不重发。通过后将搜索记录、合并快照及审核账本一起提交main，由原GitHub发布链路发送至@ZhaoCai2026Bot所在「🌐~~~资讯快报」。若通过工具分次提交，先搜索记录/快照，最后提交approved账本触发发送；已有路径不覆盖。
8. 核对本次对应账本的GitHub运行、DELIVERED与Telegram message_id。任务提示词、网页搜索、采集成功、离线测试、提交成功和连接测试都不能代替正式新闻送达。没有符合当前规则的新稿时不强制发布；不能用重发旧稿或把人工单条补发称为自动验收。

## 能力与故障边界

搜索工具没有可用权限、无法读取原文、没有执行代码或GitHub写入能力时，记录具体阻塞，不停留在“已配置自动发送”的说法。重要性不足、过期、重复、未读到正文、搜索范围失败、提交失败和传输失败是不同结果。持续故障需通知用户；正常无合格新稿保持静默。保留原任务ID、时间表及其他暂停任务。
