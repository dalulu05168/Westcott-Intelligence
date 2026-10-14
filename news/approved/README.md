# ELLERY WESTCOTT — 新闻原网站配图发布

**正式规则：不再调用 AI 或本地脚本生成新闻背景图，不再将图片强制裁剪为 16:9。** 保留新闻官网原图的尺寸、内容与署名，选择必须与当次审核新闻完全匹配的原文配图。

本工作流仅手动启动，不会抓取新闻、修改 ChatGPT 定时任务或自动转发 ChatGPT 任务结果。

## 需要准备的新闻账本

在 `news/approved/` 下创建一份 JSON，按 `scripts/news_release_gate.py` 要求记录：
- 原始文章 `sources.s1.url`、原文阅读及发布时间、原始正文可定位证据；
- 已核实的 `claims`、`publish_claim_ids`、`executed_at`、审稿人员；
- 含数字的报价：实际 `as_of`、证券代码、合约、交易阶段、货币与比较基准。不能把成交量说成净流入。

账本可以只包含这些新闻资料，此时 **不上传任何图片**：Telegram 将发送中文资讯助理稿与原新闻链接，尝试显示原文网页的链接缩略图。缩略图是否出现、内容是什么由新闻网站的分享信息和 Telegram 决定，不能保证。

如新闻图片已确认属于该篇原文、而且确有转载授权，可另外填写：

```json
{
  "primary_article_source_id": "s1",
  "original_image": {
    "source_id": "s1",
    "article_url": "https://publisher.example.org/exact-original-article",
    "image_url": "https://images.publisher.example.org/exact-original-photo.jpg",
    "matches_article_reviewed": true,
    "reuse_permission_verified": true,
    "reviewed_by": "具体审核负责人",
    "rights_evidence_url": "https://publisher.example.org/photo-license-or-permission"
  }
}
```

这是 **字段示范，不是真实新闻，也不代表示范网站授权**。原网站文章地址必须与实际已审核的 `sources.s1.url` 完全一致，且 s1 必须为已批准事实的证据来源。支持原网站使用的正规 CDN 图片地址，但审核人员需要确认图片出现在相关报道中、没有误配、该次转载有权使用，并保存权限出处。不要把“网站上能看见图片”等同于“允许把图片转载到 Telegram”。

缺少授权或没有查到配图时，本系统自动降级为 **原文链接预览**，不会抓取第三方图片、使用图库替代图，也不会生成示意插画。原图不添加行情文字、logo 或人工涨跌箭头，原图长宽比由官网决定。

## 自动识别原新闻网站的配图（不会自动发布）

可以直接在 GitHub Actions 的 `Westcott Telegram Bridge` 运行 `command=inspect`，在 `article_url` 粘贴官网 HTTPS 新闻文章地址，或者新闻官网的 JPG/PNG/WebP 图片地址。**不需要再把图片地址转换成文章地址才能执行检测。**

如果输入原始图片 URL（例如 Reuters `/resizer/v2/...jpg`），系统返回 `IMAGE_URL_RECOGNIZED`，不再错误地尝试按网页 HTML 解析；但它只确认链接格式是图片 URL，并不能据此证明该照片属于哪一篇新闻、可以打开或允许转载。真实图文发布仍必须提供经过审查的文章与图片匹配证据。系统仅读取该页的 Open Graph `og:image` / `og:image:secure_url` / `twitter:image`、文章标题和 canonical 地址，并在执行日志输出原站配图候选链接。不会下载图片、裁剪、生成图片或向 Telegram 发送消息。

重要：网页的分享配图只能算“原站宣称的候选图”，不自动证明图片与新闻事件准确对应，也不代表允许在 Telegram 转发原图。仍需人工确认图片及相关许可。遇到 403、重定向、反爬限制、网页没有元信息或不支持访问时，返回无法识别，不擅自使用替代图片。

在正式新闻 `preview` 时，也会自动检查审核账本的主要原始文章，输出 `official_page_metadata`（包括 `image_candidate_url`）。如需直接上传新闻照片，需在账本中填写匹配的官网图片 URL 与可转载依据；`publish` 时会重新读取原站元信息，不一致则停止发送。若没有已确认的可转载图片，保留原始文章链接预览作为默认方案。

## 预览与人工发布

进入 [Westcott Telegram Bridge](https://github.com/dalulu05168/Westcott-Intelligence/actions/workflows/westcott-telegram-bridge.yml)：

1. 选择 `main`，`command=preview`，填写 `ledger_path=news/approved/<filename>.json`，先审核输出的 `text_url`、`original_article_url`、`original_image_url`、`image_decision`、`official_page_metadata`。预览不会向 Telegram 发送消息或生成图片。
2. 如果图片的出处或授权有问题，改用原文链接预览；如果文字事实有问题，阻止发布并修正证据。
3. 仅人工确认之后，运行 `command=publish`、相同 `ledger_path`，填写确认短语 `PUBLISH_REVIEWED_NEWS`。
4. 脚本先登记 `audit/telegram-delivery/<fact-fingerprint>.json` 防重，再发送已核实照片（仅有授权时）或原始报道链接预览，与中文新闻稿一起发布到 `@NuvexaCheckBot` 所在「资讯快报」群。Telegram `message_id` 和采用的图片模式写入审计记录。
5. 若图片 URL 不能被 Telegram 获取，发送可能失败，记录停留在 `PENDING_DO_NOT_RETRY`；**不要直接重试**，先查群里是否实际收到，以免重复推送。

新闻发布时间、原始证据与图片版权都必须在发布前由人员核对。代码层的 PASS 只代表账本字段一致性，并不等于新闻和图片版权被程序独立验证。

## 暂停事项

- 原有五项 ChatGPT 定时新闻任务继续暂停；此 GitHub 工作流不自动读取它们的输出。
- 目前仅对明确指定的原文文章链接执行元数据检查；没有持续定时抓取、新闻发现引擎或 Telegram 持续自动推送。
- `discover`、`verify`、`smoke`、`send` 既有文字命令继续可用；此前文字测试回执 `message_id=21`。
