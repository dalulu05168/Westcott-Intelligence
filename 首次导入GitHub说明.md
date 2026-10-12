# 首次导入GitHub（一次性步骤）

1. 进入 https://github.com/new，仓库名填 `ellery-westcott-five-skills`，选择 `Private`，不要勾选初始化README、.gitignore和许可证。
2. 点击Create repository。解压本ZIP，打开解压目录，在Windows文件管理器地址栏输入`powershell`回车。
3. 确认已安装Git，然后逐行执行：

```powershell
git init -b main
git add .
git commit -m "Initial clean five Skills, 65 final identities and audited 2026-10-12 memory"
git remote add origin https://github.com/dalulu05168/ellery-westcott-five-skills.git
git push -u origin main
```

4. 如果要求登录，使用您现有GitHub账号经Git Credential Manager授权；不要在聊天中透露密码或Token。仓库创建后，也可以直接让我通过已连接的GitHub插件更新和验收。
5. 先运行 `python scripts/validate_repository.py`；脚本应报告PASS，但个别日期、10号性别及竞猜截止时间属于需审稿事项，不能自行删除。

未完成实际推送前，本ZIP只属于离线准备版，不能叫做GitHub上线。


本版本的现行先生已改为 Jonathan Richard Hayes（昵称 Jonathan），不是此前临时版本的Nicolae。旧仓库须等待新仓库推送并核验成功后再删除。
