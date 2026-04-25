import os
import requests
import json
import re

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# 违规词黑名单（含变体）
FORBIDDEN_PATTERNS = [
    r"治疗", r"治愈", r"根治", r"神效", r"特效", r"第一", r"万能",
    r"100%", r"彻底", r"永不复发", r"替代药物", r"代替医生",
    r"保证", r"绝对", r"最有效", r"奇迹", r"药到病除"
]

class DeepSeekWriter:
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
    
    def generate_post(self, topic: str, raw_material: str) -> str:
        """调用DeepSeek生成合规小红书文案，并自动过滤风险词"""
        if not self.api_key or self.api_key == "your_deepseek_api_key_here":
            # 无API Key时返回备用文案
            return self._get_fallback_post(topic)
        
        system_prompt = """你是一位分享传统养生文化的博主，语气亲切、真诚。
要求：
- 不承诺任何医疗效果，不使用“治疗”“治愈”“根治”等词。
- 标题用「」包裹，开头加一个emoji，正文分几点分享。
- 所有关于功效的描述必须加上“有些人觉得”“传统认为”“我的个人体验是”等限定。
- 结尾附上免责声明（简短）。
- 字数250~350左右，适合手机阅读。
- 主题围绕日常习惯、食疗分享、穴位按揉体验等健康生活方式。"""
        
        user_prompt = f"""主题：{topic}

参考素材：{raw_material}

请写一篇小红书风格的笔记，要求无违规词，风格亲切自然。"""
        
        try:
            resp = requests.post(
                DEEPSEEK_API_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 800,
                    "top_p": 0.9
                },
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            # 二次过滤
            content = self._filter_compliance(content)
            return content
        except Exception as e:
            print(f"AI生成失败: {e}")
            return self._get_fallback_post(topic)
    
    def _filter_compliance(self, text: str) -> str:
        """删除或替换违规词，并添加免责声明"""
        for pattern in FORBIDDEN_PATTERNS:
            text = re.sub(pattern, '***', text, flags=re.IGNORECASE)
        
        # 如果文中没有免责声明，添加
        disclaimer = "\n\n⚠️ 免责声明：以上内容仅为个人生活体验及传统养生文化分享，不构成医疗建议。身体如有不适请及时就医。"
        if "免责声明" not in text:
            text += disclaimer
        return text
    
    def _get_fallback_post(self, topic: str) -> str:
        """备用本地模板（完全合规）"""
        return f"""✨「分享我的{topic}小习惯」

最近在学习传统养生，有些小体会想跟大家聊聊～

🌿 个人做法：
根据传统说法，可以试着调整日常作息和饮食：
- 规律三餐，不暴饮暴食
- 早睡早起，晚上尽量11点前关手机
- 适当吃些温和的食物（如小米粥、蒸山药）

🧘 小动作：
有时候按按手三里、足三里（位置网上很多教程），感觉挺放松的

📌 提醒：
以上只是我的个人体验，每个人体质不同，不适合盲目照搬。
如果身体不舒服，还是要去看医生哦！

评论区欢迎分享你的养生小习惯👇

#养生日常 #传统养生 #{topic.replace(' ', '')}"""
