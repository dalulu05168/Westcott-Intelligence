# Westcott P1 人物档案与长期记忆验收报告

- 日期：2026-10-16
- 证据：GitHub Actions [38881634810](https://github.com/dalulu05168/Westcott-Intelligence/actions/runs/38881634810)
- 对应源码提交：`4d99653b23d085586e23697dd04fea0c333dfa26`
- 测试结果：工作流 completed / success；回归 `Ran 67 tests` / `OK`
- 人物审计原始摘要：`P1_AUDIT_SUMMARY`，见工作流日志

## 实际结果

| 项目 | 结果 |
|---|---|
| 固定身份总表 | 65 条 |
| 独立 profile JSON 逐份解析与11个锁定身份字段比对 | 65/65 PASS |
| voice 状态字段及未批准草案边界 | 65/65 checked |
| 已存在长期记忆独立 JSON | 36/36 checked |
| 无独立长期记忆文件 | 29，**不等于没有任何已采用剧情** |
| 身份与记忆冲突错误 | 0 |
| 本次校验器警告 | 0 |

独立长期记忆文件缺失编号：`06, 19, 25, 38, 41–65`。这些角色应标记为 `NO_SEPARATE_LONG_TERM_MEMORY_FILE`，而不是未经证据就标记 `NO_ADOPTED_HISTORY`。其中25号在10月16日Google Docs正式剧情里有发言，尤不可将无独立长期记忆误解为从未出场。

## 证据审计范围及限制

- 脚本 `scripts/validate_member_p1.py` 解析实际文件、比对身份字段、检查voice草案标签，并将36份长期记忆的记录逐条与可读取每日已采用档案进行匹配。找不到旧归档ID时记录人工复核线索，不能将检索不到等同虚构；身份/内容直接冲突则阻断CI。
- 第26号的 `message_count=2`，其 `observed_in_submitted_story` 包含3项（含1项 reaction）；校验器已按 `kind=message` 计数，避免把reaction算成文字消息。
- 已存档10月16日90段正式内容仍仅是保留原文的归档快照，不代表即时Google Docs同步，不代表真实交易、送达或65人的逐项人工语义认可。
- 角色voice为 `CREATIVE_DRAFT_NOT_USER_APPROVED` 时是拟定语言风格，不应提升为固定事实或历史。
- P1本次为**文件结构、身份字段和可追溯证据的自动化验收**；长期人物关系的语义质量及逐句人工角色口吻审核仍需编辑复核。

## CI与防回归

`.github/workflows/validate-member-memory.yml` 现执行 `python scripts/validate_member_p1.py`，审计在每次push/PR触发；审计结果写入CI Job日志及Step Summary。因GitHub Actions artifact存储配额不足，已停止上传制品，避免无关CI失败。此报告为本轮验证结论的仓库持久记录；未来CI每轮以该轮日志为准。

## 剧情保护

未更改正式剧情、Google Docs、10月16日正式快照及 `memory/runtime/latest-checkpoint.json`。最后已核对检查点依旧是2026年10月16日上午闭群，下一剧情节点为下午开群；新会话必须先比较Google Docs当前修订号与检查点再继续。
