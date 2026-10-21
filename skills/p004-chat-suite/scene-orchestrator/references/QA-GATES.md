# ELLERY WESTCOTT 出稿门禁

## P0必须阻断
01—65人物最终身份被改、性别标签不符、43—65未获授权出场、Ion/Ana同名错认、将旧Jonathan/Henry当作现任David。
当日消息时间/价格/股票代码无可靠来源却声称已核实；用虚构成员发言伪装真实投资者收益；宣称成交/发送/领奖而无真实行动或已采用剧情。
新活动没有先公布上期经过核实的结果，或在不知道上期正式题目时编造答案；课程和人物事实产生严重冲突。

## P1必须修订
重复上一场台词、误引撤回稿、时间顺序错误、未接当日最新最后一句、先生/助理职责不清、成员说话严重同质、凭职业补造家庭/朋友/旧交易。
用户确认已不作为本轮异常的历史旧事项，别反复无意义报警；聚焦真实新问题。

## P2风格优化
空泛夸大、人人统一emoji、固定“我同意”，助理与先生字数太多、机械重复、个人自然口吻被磨平、插图位置不对应讲解。
真实的口头禅/长短不均不应仅为“看起来规整”就删掉。

## 运行静态测试（只有实际运行后才能声称通过）
在仓库根运行：
```bash
python skills/p004-chat-suite/scene-orchestrator/tools/validate_scene.py draft.txt --roster skills/p004-chat-suite/characters/final-identity-65.json --json
```
活动稿加 `--activity`；自动检查成员标签/性别/出场范围、过往先生称谓、Markdown加粗、明显重复对白、活动先后顺序。它**不**校验真实财经数据、Google Doc是否最新、人物语言是否自然或交易真实性。使用 `python -m unittest discover -s skills/p004-chat-suite/scene-orchestrator/tests -v` 测试程序。
失去任一关键来源时，不能输出“全部已验证”，需要以事实限制说明。正文供用户直接复制，不堆测试日志。
