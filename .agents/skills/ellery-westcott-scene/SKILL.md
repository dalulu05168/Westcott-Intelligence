---
name: ellery-westcott-scene
description: 在Westcott-Intelligence仓库请求写/续写/改写/校验社群剧情时，自动读取65人角色身份与历史口吻，调度五Skill执行剧情写作、课程、活动、时间新闻事实和QA。
---
# ELLERY WESTCOTT Agent Skill 发现入口
## 人物编号一句话改写入口
发现 `NN男：一句话` / `NN女：一句话` / `按NN号口吻改：一句话` 时，走 `skills/p004-chat-suite/voice-management/NUMBERED-VOICE-REWRITE.md`，先读65人正式身份、对应 `characters/profiles/NN.json` 职业与性格草案、本人voice-index历史对白，再由模型按该人语气改写。多行分别处理，数字事实不动；候选性格不等于用户已批准口吻。无资料时诚实标明，不要让65人统一说话，默认直接返回可复制台词。


遇到用户说“写下午/晚上剧情”“续写上一段”“写活动”“先生授课”“修改人物说话方式”等，先读取 `skills/p004-chat-suite/scene-orchestrator/SKILL.md` 并按其工作流运行。
人物锁定身份 `skills/p004-chat-suite/characters/final-identity-65.json`，个人语言证据 `skills/p004-chat-suite/voice-management/voice-index-2026-10-21.json`；正式剧情必须刷新Google Docs并读有效记忆，不能只读本文件就称验证。
保持五Skill分工；本Skill是总调度，不是第六位人物。身份出场当前01—42；活动先上期结果再本期题；严禁虚构真实成交、真实客户投资见证及自动群发结果。
