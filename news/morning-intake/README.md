# Morning evidence handoff (RO + FR + US)

每个工作日 **06:45 Europe/Bucharest**，GitHub Actions 官方资料采集器读取现有官方发布 RSS （BVB/INSEE/ECB/Eurostat/Fed/BLS），按来源和发布时间登记 `news/morning-intake/YYYY-MM-DD.json`。正常排班的 **07:30** 双版早报工作流在后续从同一仓库读取该快照，供真人/ChatGPT有原文依据地审稿。

各候选均包含 `official_article_url`、原始标题、`published_at`、所属市场、可读取的原文摘录和实际SHA256（若原文读取失败，SHA256为空且标记不可用）。内容始终为 `UNREVIEWED`，绝不自动标注REVIEWED，也不合成美股收盘价、BET/CAC40数值、Google Docs修订或成员对白。

**该来源采集不等于自动审稿，也不等于用户群组消息已发送。** 如来源不可读或无足够重要事件，保留审核暂停状态；官方早报必须独立核对原文、行情、Google Docs最新正式剧情和人工/具可追溯证据的ChatGPT审核，才可将批准包写入 `news/approved-morning/` 或 `news/approved-morning-france-us/`。两版使用独立送达审计账本。没有合格数据/审核包不得发空稿。

现有ChatGPT官方审稿任务和工作日06:45采集器是不同运行环境。GitHub运行器不能使用ChatGPT个人Google Drive OAuth或自动复用对话中模型算力。两端正式交接只通过私有仓库的日期版本审稿账本；个人Token不得保存进仓库。