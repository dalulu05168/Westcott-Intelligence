---
name: evidence-first-verification
version: "1.0.0"
description: Required before claims of completion, successful execution, confirmed market data, today's financial news, or approved original-event images. Read real sources, run checks, record evidence and reject unverified assertions.
---

# Evidence First Verification — 必须执行的证据验收 Skill

## 开源方法来源
本 Skill 参考 [obra/superpowers/verification-before-completion](https://github.com/obra/superpowers/tree/main/skills/verification-before-completion) 的 evidence-before-claims 方法。上游仓库许可：MIT（2026-10-31 通过 GitHub 仓库元数据确认）。本文件为适配 Westcott 的独立实现；不要求付费模型 API。

## 触发与调用顺序
在本仓库的任何 **完成 / 已部署 / 已修复 / 测试通过 / 已保存 / 已连接** 声明之前，以及任何 **财经新闻当日确认、指标准确性核查、新闻原图放行** 之前，必须在该次执行中实际读取本 Skill。只知道路径、不读文件不算调用成功。

1. 明确对象、目标仓库和 commit、原始要求以及本次拥有的工具/权限。
2. 从本次真实的连接器调用、官网原始公告、代码运行、下载、截图或第三方读回取得证据。不可从模型猜想或旧缓存伪造执行回执。
3. 新闻任务先运行已有 `scripts/news_release_gate.py` 和对应 `integrations/telegram/` 原文/配图核验。它们的静态通过不意味着官方发布信息真实；必须真实查看该次官方正文，逐项审核原文。
4. 把已执行动作与日志/来源快照写入证据回执。每个完成项至少一个可核查证据文件和 SHA-256；缺证据只能标注 `BLOCKED` 或 `PARTIAL`。
5. 能执行 Python 时用 `python scripts/verify_completion_receipt.py RECEIPT.json --root PROJECT_ROOT` 审核本次回执。退出码 2 表示阻断，禁止声明完成。无执行环境时清楚标记「未运行」，不得假装检查通过。
6. GitHub 写入后重新读取文件内容与提交 SHA；仅有 create_file/update_file 响应不等于最终交付验收。外部网站、Telegram 消息和部署须有对应独立实际回执。
7. 报告必须含 `任务状态 / 实际执行 / 实际结果 / 验证情况 / 剩余问题`。声明不得超过证据。

## 新闻专项：四道硬门槛
- **真实性**：官方网站、交易所、央行、监管机构等可定位原文。记录第一次发布日期与事件日期；官方原文不可读则不通过。
- **时效性**：目标市场当地时区（Europe/Bucharest 等，处理 DST）；首次发布日期、事件发生日期、观测时间、抓取时间分别记录。旧闻更新不能冒充新事件。
- **准确性**：每一个数值都记录名称、值、币种/单位、比较基准、状态（盘中/收盘/预期/实际/修订）、原始数值和观测时间。一个关键数值未证实即整体不可按完全核实发布。
- **原图**：仅在前述条件达标后核对官方媒体原始图片、对应新闻事件、照片发布时间和授权/复用限制。没有原图就明确「未找到」，绝不生成或拿旧图冒充。

## 机器门禁的边界
`scripts/verify_completion_receipt.py` 只检查回执格式、证据文件存在与哈希、时间、数字一致性、状态及部分配图标记。**它不能证明快照来自真正的官网，不能证明译文准确，不能检测图片是否真的同一事件，更不能阻止其他 ChatGPT 窗口捏造回答。** 它不是事实认证器。

正式新闻还必须依赖源页面实际核查、独立复核及原有发布器的实时校验。必须在需要的各个 GitHub Actions 工作流中接入门禁，并通过受保护的分支 Required status checks、独立审批和真实运行日志，才能形成仓库范围的技术强制；GitHub 不会凭 SKILL.md 自动执行，不能称已全局启用。

## 允许的状态
- `COMPLETED`：所有被要求的动作实际执行并且具备本次证据、验收项全部通过。
- `PARTIAL`：能够核对部分工作，但有缺项、权限阻断或尚未验证事项。
- `BLOCKED`：无原始来源、时间冲突、关键指标错误、核验工具不可用等。

测试夹具一律写明 synthetic，不能当真实市场新闻、实际图像或对外发布证据。

## 使用例
`python -m unittest discover -s scripts -p 'test_verify_completion_receipt.py' -v`

`python scripts/verify_completion_receipt.py /path/to/receipt.json --root /path/to/evidence/root`

该 Skill 仅对**实际加载并执行该流程**的代理有效，不能自动修改 ChatGPT 产品的系统指令，也不会直接操纵外部仓库可见性或启动 Telegram 发布。
