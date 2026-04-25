import random
from datetime import datetime
from config import TOPICS
from crawler import TCMDataCrawler
from ai_writer import DeepSeekWriter
from pusher import WeChatPusher

def main():
    print(f"开始执行任务 - {datetime.now()}")
    
    # 轮询主题（按日期索引）
    today_index = datetime.now().day % len(TOPICS)
    topic = TOPICS[today_index]
    print(f"今日主题: {topic}")
    
    # 获取素材
    crawler = TCMDataCrawler()
    raw_material = crawler.get_tcm_knowledge(topic)
    
    # 生成文案
    writer = DeepSeekWriter()
    post = writer.generate_post(topic, raw_material)
    
    # 推送微信
    pusher = WeChatPusher()
    title = f"🍵 每日养生小分享 - {datetime.now().strftime('%m/%d')}"
    
    # 将换行符转为 <br> 以适应 HTML 模板
    html_content = post.replace("\n", "<br>")
    success = pusher.send(title, html_content)
    
    if success:
        print("今日推送完成")
    else:
        print("推送失败，稍后可手动重试")

if __name__ == "__main__":
    main()
