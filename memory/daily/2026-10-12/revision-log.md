# 每日审稿与删除隔离日志

所有异常均保留在提交稿和结构化JSON中，归档“排除”仅指规范化稿与动态记忆不采纳；未破坏性删除原文。

- SOURCE_HEADER_DATE_CONFLICT：源文标题10/13，正文具体是10月12日星期一；保留，不擅自假设将课堂改为13日
- REPEATED_SNO：SNO公告及09男/30男发言重复；按首次出现保留，后续相同版本标重复
- REPEATED_COMPETITION：竞猜开场有两个版本；采用包含明确成员参与的后版，前版保留源文但不再累计
- REPEATED_EUROPE：欧洲股市新闻及20男/30男互动重复；保留格式更完整的一版
- MISATTRIBUTED_DOLLAR_LINE：美元进口食材问句前出现空27女及资讯助理误标，后文27女有正确标签；排除误标版
- BLANK_MEMBER：存在空白27女标签；不得写入人物记忆
- CONTEST_CUTOFF：16:00节点开竞猜同时写16:00截止；历史原样保留，后续活动应明确早于开始或用户正式设定
- OUTDATED_TEACHER_TITLE：晚课场景标签已用先生，但助理下午与开群话术仍称教授；未来生成统一先生Jonathan
- NOT_REAL_MARKET_VALIDATED：新闻事件和行情仅是来源文本中的台词，本轮未逐项外部核实；不可作为10/13或以后新的行情事实
- SOURCE_IS_FICTION：参加、答题、奖励均指虚构群聊剧本，不表示真实群发与中奖或实际回款
- BET_COMPARISON：本稿出现Romgaz+1.25%、H2O-0.46%等数字，没有单独时点来源；不可继承为下一日行情
- MEDIA_REFERENCES：教授称请看两组K线图和量价图，原文未包含图像文件；入库记忆记录“图片位置”，不声称图已真实随稿插入
- REPLAY_CORRECTION：同一原稿的修正稿不叠加为新事件；先替换、再抽取长期记忆
- M025：contest_cutoff_same_as_scene_start_16_00,superseded_by_M032 (源文本行 64 起)
- M026：same_news_repeated_later (源文本行 74 起)
- M027：empty_message (源文本行 77 起)
- M028：user_original_role_attribution_conflict (源文本行 78 起)
- M029：duplicate_of_M022 (源文本行 80 起)
- M030：duplicate_of_M023 (源文本行 84 起)
- M031：duplicate_of_M024 (源文本行 86 起)
- M032：contest_cutoff_same_as_scene_start_16_00,duplicate_of_M025 (源文本行 88 起)
- M038：duplicate_of_M026 (源文本行 111 起)
- M040：orphan_assistant_news_inside_21_member_block,stripped_orphan_news_and_followups_because_duplicate_full_news_later (源文本行 116 起)
- M044：duplicate_of_M041 (源文本行 127 起)
- M045：duplicate_of_M042 (源文本行 129 起)
- M046：legacy_professor_title_inside_text (源文本行 131 起)
- M047：legacy_professor_title_inside_text (源文本行 136 起)
- M053：gender_or_role_mismatch (源文本行 151 起)
- M068：duplicate_of_M063 (源文本行 201 起)

## 先生姓名的后续更正（2026-10-12）

用户再次指定现行先生为 Jonathan Richard Hayes（Jonathan），覆盖先前临时更名 Nicolae Petrescu。原文和逐条消息 text/hash 不变；现行规则、去重视图及长期记忆以 Jonathan 为准。
