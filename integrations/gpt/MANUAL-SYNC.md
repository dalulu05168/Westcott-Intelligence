# 私有GPT资料接入与手动同步

用户2026-10-25明确选择手动同步，不新建密钥。本目录没有新增工作流、定时器、Telegram调用或自动发布。现有新闻采集及群发暂停状态不在此次修改范围。

## 内容

- `export_repository.py`：仅导出允许名单中的确认规则、五Skill、65人身份/候选profile/有出处历史、每日剧情快照及新闻采集版次。保留源路径和摘要，不导出凭据。
- `service/`：现有Cloudflare资料服务的扩展源码。独立新增repository_exports/chunks表，已有progress/source表不覆盖。
- `GPT-INSTRUCTIONS-V23.txt`：同步后的GPT指令，明确V23、男助理、四标题、新闻官网配图、事实核验和程序检查。

## 接口

- getRuntimeRules：仓库导出版本、确认规则、可用历史日期；role参数可取相应Skill。
- getContext：人物身份、候选profile、带日期和出处的口吻/历史，不能冒称实时Docs。
- getStoryArchive：按日期分页读取剧情快照，每页12条。未导入的日期返回missing。
- getNewsPacket：精确日期/时点，保留官网原图候选和审核状态，不拿未来快照或前一日数据冒充当日资料。
- validateScene：检查编号性别、01—42出场、空标签、条数、原句重复。通过只叫STRUCTURE_PASS，不证明语义与事实通过。
- 原getProgress/saveProgress保留；只有用户确认采用才可写adopted_state。

## 手动刷新

1. 获取main最新版本并验证导出允许名单的内容。运行仓库校验。
2. 运行`python integrations/gpt/export_repository.py --output <本机临时导出文件>`；导出必须标明真实来源commit，脏工作区不能冒充已提交版本。
3. 由维护者使用已有Cloudflare账户授权把导出分块追加到独立资料表，确认完整块数、commit和内容摘要。未提供持续同步密钥，因此不会因GitHub提交自动更新服务。
4. 用私有GPT真实调用getRuntimeRules/getContext/getStoryArchive/validateScene，核对返回版本和原话。网页更新成功与工具端实际调用分别验收。

新闻资料来自仓库已有采集器的候选版次，抓取并非事实核实；原图存在并非视觉对应或转载权已验证。无匹配素材应明确missing，不制造新闻。旧档案中的女助理描述只作历史源文，当前规则为男助理。
