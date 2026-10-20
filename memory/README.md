# 剧情与人物记忆

`daily/YYYY-MM-DD/final-transcript-submitted.md`只存用户提供的原始稿；`adopted-normalized.md`是清洗视图；`day-memory.json`含源行和稳定ID。`long-term/members/NN.json`只含有依据的个人记忆。原始故事不是实际WhatsApp发送凭证。

教师身份曾用Jonathan，当前正式为Jonathan；不要篡改原文，但新稿和可用的长期身份一律Jonathan。

2026-10-12仍有日期10/13题头及`10男`身份冲突等审稿例外；不得擅自解决。竞猜奖品兑现、真实结果和作业提交不可凭剧中台词推断。

## Member stock participation history

`member-stock/ledger-v1.json` is the read-only entrypoint for 65 fictional-member stock participation histories. It currently contains only 4 previously reviewed 2026-10-16 story-state records; absence of a record means *not yet verified/imported*, not proof of no position. Changes require adopted original member speech with attributable evidence. The CLI is `python scripts/member_stock_ledger.py --check` and `--member NN` / `--symbol TICKER`. See `skills/p004-chat-suite/references/member-stock-participation-v2.6.md`. Fictional self-reports must never be represented as verified real broker trades.
