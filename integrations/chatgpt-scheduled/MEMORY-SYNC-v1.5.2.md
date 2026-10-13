# Westcott 65人记忆同步（v1.5.2）

当前为 **GitHub仓库内准备稿**，不是ChatGPT线上五项任务已更新的证明。任务ID、原定时设置、时区 Europe/Bucharest、启用状态、推送方式均保持原状，不得新建任务。

## 权威来源

- 固定身份和独立人物资料：`skills/p004-chat-suite/characters/`，65人完整。
- 已被用户采用的每日剧情：`memory/daily/YYYY-MM-DD/day-memory.json`，仅采用标记为 `ADOPTED_IN_SUBMITTED_TRANSCRIPT` 或 `ADOPTED_IN_USER_SUBMITTED_STORY` 的人物台词。
- 对应历史长期记忆：`memory/long-term/members/<编号>.json` 中 `observed_in_submitted_story`。无已采用事实则不得补造。15号待核台词不可当正式记忆。
- 运行资料：`skills/p004-chat-suite/references/runtime-context-v1.5.2.txt`。仅说明内置快照，不能声称远端动态加载。

截至2026-10-13：65份固定人物资料，31份长期记忆文件，30人共77条确认互动（10月12日35条，10月13日42条），15号仅待审；其余34人未建立长期记忆文件。不得虚构真实交易、交易盈亏、真实群聊送达。

## 同步与验收

```bash
python scripts/sync_runtime_memory.py --check
python scripts/validate_repository.py
python -m unittest discover -s scripts -p test_runtime_context.py -v
```

**新剧情已正式采用后**，先将原文保存到新日期的每日记忆并与人物编号、说话内容核对；仅通过该流程的已采用片段更新对应人物长期记忆。再运行：

```bash
python scripts/sync_runtime_memory.py --write
python scripts/sync_runtime_memory.py --check
```

`--write` 只重新生成本仓库内五份 **现有任务** 提示词导出及其 SHA-256 元数据，不向ChatGPT平台执行更新。它不会修改五项真实任务ID、日程或触发行为，也不会自行安排任务。

若后续需要应用到**线上现有五项任务**，必须先按任务ID读取线上最新正文，合并其他线上修改，仅更新对应 prompt，随后重新读取确认日程/时区/启用/通知配置不变。线上应用验证之前，`UPDATE-EXISTING-TASKS.json` 的状态必须继续保持 `PREPARED_NOT_APPLIED`。
