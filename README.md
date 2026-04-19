# 养生知识自动采集 → 小红书文案 → 微信推送

每天20:00自动从多个中医/养生网站采集最新文章，通过AI改写成小红书风格文案，并推送到你的微信（只推送最好的一篇）。

## 功能特点

- 📡 自动采集10+个中医养生网站的最新内容
- 🤖 使用DeepSeek API改写成爆款小红书文案
- 🧠 智能选文：根据来源权重、关键词等只推送最好的一篇
- 💾 去重缓存：已推送过的文章不会重复发送
- ⏰ 定时运行：GitHub Actions 每天北京时间20:00执行
- 📱 微信推送：通过PushPlus实时接收

## 部署步骤

1. **Fork本仓库** 到你的GitHub账号

2. **获取API密钥**
   - DeepSeek API Key: 访问 https://platform.deepseek.com/ 注册获取
   - PushPlus Token: 微信搜索「PushPlus」公众号，扫码获取

3. **配置GitHub Secrets**
   - 进入仓库 `Settings` → `Secrets and variables` → `Actions`
   - 添加两个Secret：
     - `DEEPSEEK_API_KEY`：你的DeepSeek API Key
     - `PUSHPLUS_TOKEN`：你的PushPlus Token

4. **（可选）自定义写作风格**
   - 编辑 `main.py` 中的 `CUSTOM_STYLE` 变量

5. **（可选）添加自定义数据源**
   - 编辑 `main.py` 中的 `CUSTOM_URLS` 列表

6. **手动测试**
   - 进入仓库 `Actions` 标签页
   - 选择 `Daily XHS Content Push` 工作流
   - 点击 `Run workflow` 手动触发一次

7. **自动运行**
   - 每天北京时间20:00会自动运行
   - 如果当天没有新文章，不会推送

## 注意事项

- 请遵守各网站的 `robots.txt` 协议，不要频繁请求
- DeepSeek API 费用极低，每天5篇以内基本免费
- 如遇到推送失败，检查 PushPlus Token 是否正确

## 文件说明

- `main.py`：主程序（采集、选文、改写、推送）
- `requirements.txt`：Python依赖
- `.github/workflows/schedule.yml`：定时任务配置
- `sent_articles.json`：自动生成，记录已推送的文章链接

## 许可证

MIT
