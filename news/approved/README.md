# ELLERY WESTCOTT — 审核后图文发布

本目录只接受经过独立来源核验并提交仓库主分支的事实账本。**不自动抓取新闻、不自动开启 ChatGPT 任务、不自动推送 Telegram。**

## 1. 人工准备消息账本

在本目录新增一个唯一文件，例如 `2026-10-14-market-event.json`。路径必须符合 `news/approved/<filename>.json`。文件不得包含机器人密钥或任何个人账号信息。

所需示意结构（下方数据是**无效占位示例，禁止当新闻发布**）：

```json
{
  "event_id": "unique-event-20261014",
  "executed_at": "2026-10-14T18:00:00+03:00",
  "sources": {
    "s1": {
      "url": "https://OFFICIAL-SOURCE.example/actual-document",
      "access_status": "BODY_READ",
      "source_type": "official",
      "origin_id": "official-issuer",
      "published_at": "2026-10-14T17:40:00+03:00",
      "retrieved_at": "2026-10-14T17:55:00+03:00"
    }
  },
  "claims": [
    {
      "id": "unique-claim-001",
      "text": "经审查、与原始正文逐字核验后才填写的简短中文财经事实。",
      "kind": "fact",
      "review_status": "NOT_REVIEWED",
      "reviewed_by": "",
      "evidence": [
        {
          "source_id": "s1",
          "excerpt": "与原文一致的可定位节选",
          "locator": "原始正文中的小节或段落",
          "supports_exact_claim": false
        }
      ],
      "numbers": []
    }
  ],
  "publish_claim_ids": ["unique-claim-001"]
}
```

需要人工读原始正式正文，逐条核对发布时间、事件时点及行情截至时间、证券代码、合约、货币、单位、比较基准和市场交易阶段。确有核验依据才能将 review_status 设为 `CONFIRMED`、标记 reviewed_by，并把 supports_exact_claim 设为 true。**程序结构性 PASS 不代表新闻真实，也不能替代审稿。**

涉数字事实必须填 `is_numeric: true` 与完整 `numbers` 数组（见 `scripts/news_release_gate.py`）；不允许编造价格、走势或因果。

正文从获批准的 `publish_claim_ids` 对应事实自动组成，每一条均以 `===== 资讯助理 =====` 起始，附原始来源链接。审核元数据不写入群消息。

## 2. 先预览、再发布

打开 [Westcott Telegram Bridge](https://github.com/dalulu05168/Westcott-Intelligence/actions/workflows/westcott-telegram-bridge.yml)：

1. 选择 main 与 `command=preview`，填写 `ledger_path=news/approved/<filename>.json`，运行。
2. 从执行日志的 `image_url` 和 `text_url` 打开已保存到仓库 `news/previews/` 的图片与新闻稿。该预览不占用 GitHub Actions Artifact 配额；图片固定 **1600×900 (16:9)**，浅蓝白渐变、无文字、按审核事实中的能源/银行/BVB/科技/宏观/商品关键词绘制非事实性线条元素。多个主题或无法确认时退回中性全球元素，**不捏造K线**。
3. 确认文图正确后，手动选择 `command=publish`，使用同一 `ledger_path`，并在 `publish_confirmation` 输入 `PUBLISH_REVIEWED_NEWS`。
4. 发布程序先在 `audit/telegram-delivery/<fingerprint>.json` 预留不可重复的事实指纹；再向 **@NuvexaCheckBot / 资讯快报** 发送图片与新闻文字，成功后写入 photo_message_id、message_ids 与原始来源链接。未获得可靠回执、网络模糊失败、写回失败均不得自动重试，以免双发。

不需要 OpenAI API 密钥、不进行付费第三方图像生成。生成图是本地确定性的金融主题矢量风格背景，不是新闻事件的真实照片，不能用来表征经验证的价格或涨跌。

## 3. 边界与保留事项

- 机器人 Token 和群组 Chat ID 只使用 GitHub Actions Secrets，不写入 JSON、文档或日志。
- 现有的纯文字 `discover`、`verify`、`smoke`、`send` 继续保留。真正自动财经新闻雷达与 ChatGPT Scheduled 任务的接通**尚未实现**。
- 36 小时之前审查的旧账本不允许直接发布，需重新核对事实与数据、创建有效新证据。
- 先占坑后发送的审计设计为拒绝重复执行而非保证外部事务原子性；若外部发送已发生但记录只剩 `PENDING_DO_NOT_RETRY`，需要人工比对 Telegram 后处理，不应再次点击 publish。
- 上次连接测试已核实 Telegram `smoke` 成功，群组「资讯快报」收到消息，回执 `message_id=21`，该记录不等于实际财经新闻审核已通过。
