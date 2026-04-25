# -*- coding: utf-8 -*-
"""
配置文件 - 存放所有API密钥和配置信息
使用前请替换为你的实际密钥
"""

# DeepSeek API配置
DEEPSEEK_API_KEY = "your_deepseek_api_key_here"  # 在 platform.deepseek.com 获取
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# PushPlus配置
PUSHPLUS_TOKEN = "your_pushplus_token_here"  # 在 http://www.pushplus.plus 注册获取

# 定时任务配置（每天发布时间，建议早上8-9点或晚上7-9点）
SCHEDULE_TIME = "08:30"  # 每天上午8:30发布

# 小红书文案配置
TOPICS = [
    "气血不足",
    "养肝护肝", 
    "祛湿气",
    "失眠调理",
    "脾胃虚弱",
    "脱发掉发",
    "痛经调理",
    "免疫力提升"
]  # 轮流使用不同主题
