# WESTCOTT P2｜剧情语义质量扩展验收记录

- 运行日期：2026-10-16
- 状态：**P2_AUTOMATED_HEURISTIC_CHECKS_PASSED; PENDING_HUMAN_REVIEW**（不代表P2语义验收完成）
- GitHub Actions：[38884686803](https://github.com/dalulu05168/Westcott-Intelligence/actions/runs/38884686803)，`completed/success`
- 代码提交：`fb66c0184f9ff4c8955c800dcbc2ab4028faba49`（检测器），`3534586142990ff0fa0cc096b9114b8a2a8304a3`（扩展测试）
- 测试：原始GitHub Actions日志 `Ran 77 tests`、`OK`
- 样本：`memory/daily/2026-10-16/formal-google-doc-snapshot.json`，原始90段，来源修订 `AHj4eMRhrTY68cR6uMrZ0n3R35sp7ZZ656_aPJ7A5QXkKKWk2SGBI_7hx1Wc7kos_aF-AuCgg4YlDx0JLKYAlqq-5JY2kE7-DKWjzNzwrXo`

## 自动化真实样本结果

| 检查指标 | 结果 | 必须保留的解释 |
|---|---:|---|
| 解析出完整发言轮次 | 33 | 从先前32修正；第576段存在同段隐藏控制字符 |
| 结构异常 | 3 | `DOC-P562` 缺性别；`DOC-P576` 内嵌25男标签；`DOC-P572-P574` 13男近似重复 |
| 成员→成员相邻发言 | 21 | 仅表示相邻，**不能**据此认证直接回复/亲密关系 |
| 显式成员编号提及 | 1 | 仅为可追溯文本引用，不代表已建立固定关系 |
| 角色台词涉及买卖、持仓等 | 10 | 含各种人物虚构剧情叙述；**不是**10笔已证实交易 |
| 资讯人员发言的数字化市场陈述候选 | 3 | **未经外部权威行情源核实**；真假未定 |
| 口吻样本分布、平均长度、疑问句、表情使用 | 已运行 | 描述性统计；不能自动证明角色口吻具有自然差异 |
| 跨角色近乎相同对白 | 检查器已运行 | 高相似仅触发待审；未获得编辑认可不得升级为人格结论 |

## 关键证据链

1. `DOC-P560`：25号讲述自己此前持有FOJE；`DOC-P568`：25号补充买入价、部分卖出和犹豫；`DOC-P576`：25号再回应“之前那笔确实赚到了一点”；`DOC-P583`：25号讲述未等通知就部分卖出及后悔。这些**彼此可构成同场角色台词的连续性线索**，但不是现实交易流水。不可因此推断真实收益、账户执行状态或先前未记录交易。
2. `DOC-P531`：09号明确提及18号；仅证明存在成员指向的文字，不因此升级为固定熟人关系。
3. `DOC-P505`、`DOC-P516`、`DOC-P539`：涉及美国/罗马尼亚指数与股价等可核验市场叙述；P2检测器只列为事实证据候选，**必须另行比对独立、带日期时区的可靠行情来源**，不能拿剧本原文本身当金融事实证据。
4. `DOC-P562`、`DOC-P576`、`DOC-P572-P574` 三处异常不改变原始采用状态；仅修改读取/审稿逻辑。

## 通过与未通过的明确界限

- **通过**：新增解析、相邻互动统计、显式提及、交易台词溯源、财经数字待核验标注、口吻统计及跨人物文本相似度的回归测试；CI整体成功。
- **未通过人审**：是否说话真正有个性、成员对话是否自然、剧情情绪和关系发展是否可信、资产成交是否有正式记录，以及财经数字是否真实。
- **未变更**：Google Docs、正式90段快照、65人人物身份与长期记忆、V2.0五Skill规则及运行检查点。
- **下一关**：用编辑评分单对样本逐轮标记 `APPROVED / REWRITE_REQUIRED / EVIDENCE_REQUIRED`；对财务数字逐项接入权威时点证据和新旧新闻去重。未有审核结论时保持 `PENDING_HUMAN_REVIEW`。

P2检测器及测试文件：
- [scripts/validate_scene_p2.py](https://github.com/dalulu05168/Westcott-Intelligence/blob/main/scripts/validate_scene_p2.py)
- [scripts/test_validate_scene_p2.py](https://github.com/dalulu05168/Westcott-Intelligence/blob/main/scripts/test_validate_scene_p2.py)
