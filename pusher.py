import os
import requests

PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN")

class WeChatPusher:
    def __init__(self):
        self.token = PUSHPLUS_TOKEN
    
    def send(self, title: str, content: str) -> bool:
        if not self.token or self.token == "your_pushplus_token_here":
            print("未设置 PUSHPLUS_TOKEN，请在 GitHub Secrets 中添加。")
            return False
        
        url = "https://www.pushplus.plus/send"
        data = {
            "token": self.token,
            "title": title,
            "content": content,
            "template": "html"   # 换行符 <br> 可正常解析
        }
        try:
            resp = requests.post(url, json=data, timeout=10)
            result = resp.json()
            if result.get("code") == 200:
                print("微信推送成功")
                return True
            else:
                print(f"推送失败: {result.get('msg')}")
                return False
        except Exception as e:
            print(f"推送异常: {e}")
            return False
