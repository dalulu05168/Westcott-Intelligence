# Westcott 候选稿程序验收入口

这个目录只接收**候选**虚构群聊稿，不接收正式已采用/已发送记录。
此流程的目标是把已经写好的草稿导入可测试、可审计的路径；它**不能**控制任意ChatGPT聊天，也**不能**验证真实财经新闻、Google Docs是否真被读取、成员口吻是否自然或用户是否批准。

## 提交一个候选稿（同一个文件夹）
- `automation/submissions/2026-10-22-am/draft.txt`：候选正文，纯UTF-8。
- `automation/submissions/2026-10-22-am/manifest.json`：读取回执和准确的正文SHA256。

示例 manifest（示例占位符**绝不能**冒充真实读取回执）：

```json
{
  "task_mode": "WESTCOTT_SCENE",
  "scene": "morning",
  "story_date": "2026-10-22",
  "activity": false,
  "release_status": "CANDIDATE",
  "draft_sha256": "实际draft.txt的SHA256（64位小写十六进制）",
  "source_receipts": {
    "github_rules": {"status": "READ", "reference": "本次实际取得的GitHub提交SHA"},
    "google_docs": {"status": "READ", "reference": "本次实际读取的日期页签和文档修订信息"},
    "notion_corrections": {"status": "READ", "reference": "本次实际读取的已批准纠错块"},
    "identity_roster": {"status": "READ", "reference": "本次实际读取的65人身份表SHA"}
  }
}
```

必须真实调用连接器后才能填`READ`。连接失败时可输出文字说明和待核草稿，但不能伪造上面的机器准入回执。

## 在仓库中运行
```bash
python scripts/gate_candidate.py --check-all
```

CI：`.github/workflows/westcott-candidate-gate.yml`，在候选文件或相关脚本改变后自动运行单元测试和静态门禁。此门禁可阻止该工作流的**检查通过**，不会自动阻止直接推送到未受保护的主分支。要阻止合并，还需仓库分支保护/规则集要求该状态检查通过；需单独核实GitHub权限及仓库设置。

**机器通过≠内容被采用。** 市场事实与人物口吻必须独立核查，用户批准后再进入正式剧情；绝不自动发送社群消息。
