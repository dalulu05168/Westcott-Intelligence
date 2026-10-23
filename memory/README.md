# 剧情与人物记忆

`daily/YYYY-MM-DD/final-transcript-submitted.md`只存用户提供的原始稿；`adopted-normalized.md`是清洗视图；`day-memory.json`含源行和稳定ID。`long-term/members/NN.json`只含有依据的个人记忆。原始故事不是实际WhatsApp发送凭证。

历史剧情曾使用 Jonathan Richard Hayes、Henry 等先生称谓，需保留原文和当时采用状态；**2026-10-21 起的新稿现任先生是 David Miller（股票执行负责人）**。不把历史旧称当作当前身份，也不把既往历史台词改写成 David 的亲身经历。现行规则以 `skills/p004-chat-suite/references/staff-and-role-identity-20261021.md` 为准。

2026-10-12仍有日期10/13题头及`10男`身份冲突等审稿例外；不得擅自解决。竞猜奖品兑现、真实结果和作业提交不可凭剧中台词推断。

## Member stock participation history

`member-stock/ledger-v1.json` is the read-only entrypoint for 65 fictional-member stock participation histories. It currently contains only 4 previously reviewed 2026-10-16 story-state records; absence of a record means *not yet verified/imported*, not proof of no position. Changes require adopted original member speech with attributable evidence. The CLI is `python scripts/member_stock_ledger.py --check` and `--member NN` / `--symbol TICKER`. See `skills/p004-chat-suite/references/member-stock-participation-v2.6.md`. Fictional self-reports must never be represented as verified real broker trades.
