# 一体化剧情创作总 Skill · v1.0

用于 ELLERY WESTCOTT 虚构财经社群剧情写作。统一调度现有五Skill及65人独立人物口吻，不需要使用“人物语言管理”网页复制长指令。

**触发**：写上午内容、续写下午、写晚课、发布活动、优化02女说话方式、加入成员互动、剧情巡检。

**主文件**：`SKILL.md`。详细规则：`references/VOICE-ENGINE.md`、`references/CONTINUITY-AND-FACTS.md`、`references/QA-GATES.md`。
**ChatGPT跨对话**：将 `CHATGPT-PROJECT-INSTRUCTIONS.md` 复制进用户日常使用的ChatGPT Project说明中一次。仓库提交本身不能自动配置ChatGPT账户。
**Codex工作区**：使用 `.agents/skills/ellery-westcott-scene/SKILL.md` 入口。
**验证脚本**：`tools/validate_scene.py`，测试 `tests/test_validate_scene.py`。
**前提**：GitHub和Google Docs连接有权限；真实新闻另行核对。用户确认文本才归档，不自动群发，不冒充真实投资见证。

65人身份：`../characters/final-identity-65.json`；口吻证据：`../voice-management/voice-index-2026-10-21.json`；正式剧情文档：https://docs.google.com/document/d/1frtoFvohP3u2HfRzBPRZVLOzMfvnO-8Vi9iX3r5rmiM/edit 。
