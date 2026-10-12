# ELLERY WESTCOTT｜五合一Skill独立源码

计划新建GitHub仓库：`dalulu05168/ellery-westcott-five-skills`；建议权限：Private。

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

## 仓库创建

本地资料包可以独立使用，但GitHub新仓库需要用户在网页完成创建（选择Private且不要预建README）；之后可使用`git`或GitHub Desktop导入本目录。此资料包不意味着已推送到GitHub。

## 安全边界

虚构教学对话，不冒充真实投资者或用未核验的数据产生投资背书；不记录未发生的真实交易、奖品领取、成员登录等事实。

## 删除旧仓库前的必要条件

`dalulu05168/-Skill` 仍包含其他项目。只有新私有仓库实际创建、全量推送并完成文件对照及回读后，才可单独按用户指令删除旧仓库。当前资料包本身不能创建或删除GitHub仓库。
