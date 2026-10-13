# PROJECT-CATALOG｜项目归属与资料隔离

**仓库唯一项目：P004 · ELLERY WESTCOTT Intelligence / 财经剧本及五Skill。**

## 正式文件归属
- **65人正式身份唯一来源**：`skills/p004-chat-suite/characters/final-identity-65.json`；65份独立档案：`skills/p004-chat-suite/characters/profiles/01.json` 到 `65.json`。
- 用户原始人物表：`source/用户最终65人人物表.md`。身份发生冲突时按用户最终表和迁移审计处理，不能从其他仓库补写身份。
- 五个Skill统一入口：`skills/p004-chat-suite/SKILL.md`；独立助理、成员、先生、编剧、导演模块均在 `skills/p004-*/`。
- 定时任务资料：`integrations/chatgpt-scheduled/`。仓库内提示词并不代表已更新线上原有任务。
- 正式采用记录与记忆：`memory/daily/`、`memory/long-term/members/`。
- 验证和配置：`scripts/`、`config/`、`VALIDATION-REPORT.json`。
- 源码版本线：v1.5 / v1.5.1 调整信息请查根目录 `README.md`；人物身份文件本身不因为提示词版本变动而自动改变。

## 严格隔离
- **不从 `dalulu05168/-Skill` 的 `romania-market-director/characters` 读取或合并65人**：两套是不同人物，编号相同不表示同一人。
- 不从 CRM 仓库 `dalulu05168/-`、教程仓库 `desktop-tutorial` 导入人物、新闻稿、交易资料或记忆。
- 同一项目新增人物、图片、剧情、任务说明、验收记录，必须归入上述相应项目目录；不要新建第二套65人身份总表。
- 需要跨项目复用代码时应明确依赖边界，禁止复制成无法溯源的第二份事实来源。

## GitHub仓库分工
- `Westcott-Intelligence`：本项目的**正式 P004 65人及五Skill**。
- `-Skill`：旧罗马尼亚财经工作台、独立验收工具与历史资料（不是本项目的人物来源）。
- `-`：Brantone Veylor CRM。
- `desktop-tutorial`：独立教程/说明仓库。

本目录是项目归属登记，不代表线上任务已经部署，也不执行跨库数据迁移。
