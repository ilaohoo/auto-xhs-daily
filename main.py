import requests
import json
import hashlib
import os
import random
from datetime import datetime
import feedparser
import pytz
from typing import List, Dict, Optional

# ================= 配置 =================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "YOUR_DEEPSEEK_API_KEY")
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "YOUR_PUSHPLUS_TOKEN")

CACHE_FILE = "sent_articles.json"

# ---------- 小红书爆款风格（优化版）----------
CUSTOM_STYLE = """
你是一位资深小红书养生博主。请将以下文章改写成爆款小红书笔记。

【标题】⚠️ + 数字/痛点 + emoji，例如“⚠️别吃了！这10个习惯正在偷走寿命”
【开头】姐妹们， + 生活场景 + 权威数据（如《柳叶刀》）
【正文】每条用 **01** 格式，包含：危害 + 数据 + 建议，适当加emoji
【结尾】互动提问：“你中了几个？评论区告诉我😭” + 相关标签 #健康科普 #养生 #药食同源 #养生茶
【禁止】治愈、根治、推荐药品
"""

# ---------- RSS 源（包含药食同源+养生茶）----------
RSS_SOURCES = [
    # 原有稳定源
    {"name": "中医启疾光网", "url": "https://www.zyqjg.com/forum.php?mod=guide&view=newthread&rss=1"},
    {"name": "人民网健康", "url": "https://rsshub.bili.xyz/people/health/latest"},
    {"name": "凤凰中医", "url": "https://rsshub.bili.xyz/feng/ifeng/2/1"},
    {"name": "39健康网", "url": "https://rsshub.bili.xyz/39net/news"},
    {"name": "健康一线", "url": "https://rsshub.bili.xyz/xgys"},
    {"name": "养生之道网", "url": "https://rsshub.bili.xyz/yszdao"},
    
    # 新增：药食同源 & 养生茶
    {"name": "药食同源资讯", "url": "https://rsshub.bili.xyz/health/drug-food"},
    {"name": "养生茶专题", "url": "https://rsshub.bili.xyz/health/herbal-tea"},
    {"name": "中国日报健康", "url": "https://rsshub.bili.xyz/chinadaily/health"},
]

# ---------- 药食同源/养生茶选题库（备用，每天不同）----------
HERBAL_TEA_TOPICS = [
    {
        "title": "苹果黄芪水：熬夜脸黄的救星",
        "summary": "苹果黄芪水在小红书爆火，近30天130家店铺疯卖。配方：苹果、黄芪、麦冬、红枣、枸杞。主打'素颜好气色''熬夜内调'。小红书话题浏览量从43万增长至85万。"
    },
    {
        "title": "酸枣仁助眠饮：失眠人群的'救星'",
        "summary": "配方：酸枣仁、百合、人参、GABA。小红书'失眠'话题超百万讨论，助眠类产品年增速达40%。0蔗糖0脂肪，适合年轻人。"
    },
    {
        "title": "红豆薏米祛湿茶：南方人的'祛湿刚需'",
        "summary": "配方：赤小豆、薏米、茯苓、芡实。主打'祛湿=减肥/消水肿'。天猫祛湿类产品年增长超60%。"
    },
    {
        "title": "黄芪红枣元气茶：办公室养生必备",
        "summary": "配方：黄芪、红枣、枸杞、苹果片。补气养血，独立茶包设计。盒马数据显示，早餐滋补品类销售额同比增长184%。"
    },
    {
        "title": "姜黄肉桂奶茶：药食同源的'社交货币'",
        "summary": "将药膳融入奶茶，成都某医院姜黄奶茶一度卖断货。配方：姜黄粉、肉桂、牛奶、红糖。兼具好喝与养生。"
    },
    {
        "title": "即食阿胶糕：女性滋补的'刚需单品'",
        "summary": "配方：阿胶、核桃、黑芝麻、黄酒。免煮即食。东阿阿胶'桃花姬'年销过亿，年货节需求暴增153%。"
    },
    {
        "title": "五色入五脏：养生的'色彩密码'",
        "summary": "《黄帝内经》'五色入五脏'：青入肝、赤入心、黄入脾、白入肺、黑入肾。例如西红柿养心、黑豆养肾、山药养脾。"
    },
    {
        "title": "清肺利咽饮：换季必备代茶饮",
        "summary": "济南市卫健委推荐配方。适合换季咽喉不适、干燥上火。食材多为药食同源，可在药店购买。"
    },
    {
        "title": "祛湿健脾：茯苓薏米水的正确喝法",
        "summary": "茯苓、薏米是经典祛湿搭配，但薏米性寒需炒制。正确做法：薏米炒至微黄，配茯苓、芡实，煮水代茶饮。"
    },
    {
        "title": "当归生姜羊肉汤：古方驱寒暖宫",
        "summary": "源自《金匮要略》经典方，主打驱寒暖宫。现代简化：当归、生姜、羊肉炖煮，适合冬季手脚冰凉、痛经女性。"
    }
]

# ================= 辅助函数 =================
def load_sent_articles() -> set:
    if not os.path.exists(CACHE_FILE):
        return set()
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get("sent_hashes", []))
    except:
        return set()

def save_sent_articles(sent_hashes: set):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump({"sent_hashes": list(sent_hashes)}, f, ensure_ascii=False, indent=2)

def get_link_hash(link: str) -> str:
    return hashlib.md5(link.encode('utf-8')).hexdigest()

# ================= 数据采集 =================
def fetch_from_rss() -> List[Dict]:
    articles = []
    for source in RSS_SOURCES:
        print(f"📡 RSS抓取：{source['name']}")
        try:
            feed = feedparser.parse(source['url'])
            for entry in feed.entries[:2]:
                link = entry.get('link', '')
                if not link:
                    continue
                articles.append({
                    'title': entry.get('title', '无标题'),
                    'summary': entry.get('summary', '无摘要'),
                    'link': link,
                    'source': source['name']
                })
        except Exception as e:
            print(f"   ❌ 失败：{e}")
    return articles

def get_seed_article() -> Dict:
    """从选题库中按日期选择一篇（每天不同）"""
    today = datetime.now(pytz.timezone('Asia/Shanghai'))
    # 使用年月日作为随机种子，确保当天固定，隔天变化
    index = (today.year * 365 + today.timetuple().tm_yday) % len(HERBAL_TEA_TOPICS)
    topic = HERBAL_TEA_TOPICS[index]
    return {
        'title': topic['title'],
        'summary': topic['summary'],
        'link': f"https://example.com/herbal-tea-{today.strftime('%Y%m%d')}",
        'source': '药食同源选题库'
    }

def fetch_all_new_articles() -> List[Dict]:
    sent_hashes = load_sent_articles()
    all_articles = fetch_from_rss()
    
    # 去重
    unique = {}
    for art in all_articles:
        link = art['link']
        if link not in unique:
            unique[link] = art
    
    # 过滤已推送
    new_articles = []
    for art in unique.values():
        h = get_link_hash(art['link'])
        if h not in sent_hashes:
            new_articles.append(art)
    
    print(f"📊 总抓取 {len(unique)} 篇，新文章 {len(new_articles)} 篇")
    
    # 如果没有新文章，使用选题库中的文章（但也要检查是否已推送过）
    if not new_articles:
        print("⚠️ 未抓到新文章，尝试使用药食同源选题库...")
        seed = get_seed_article()
        h = get_link_hash(seed['link'])
        if h not in sent_hashes:
            new_articles.append(seed)
            print(f"📝 已添加选题库文章：{seed['title']}")
        else:
            print("⏭️ 今天的选题库文章已推送过，不再重复。")
    
    return new_articles

# ================= 智能选文 =================
def select_best_article(articles: List[Dict]) -> Optional[Dict]:
    if not articles:
        return None

    # 排除明显非养生的关键词
    exclude_keywords = ["保险", "政策", "制度", "通知", "政府", "医保", "社保", "会议", "领导", "习近平", "国务院"]

    source_weights = {
        "中医启疾光网": 5, "人民网健康": 4, "凤凰中医": 4,
        "39健康网": 3, "健康一线": 2, "养生之道网": 2,
        "药食同源资讯": 5, "养生茶专题": 5, "中国日报健康": 4,
        "药食同源选题库": 4  # 备用文章权重也不错
    }

    high_value_keywords = [
        "健脾", "祛湿", "补气血", "养肝", "助眠", "便秘",
        "食疗", "药膳", "四神汤", "八珍", "黄芪", "艾灸",
        "寿命", "饮食习惯", "养生茶", "药食同源", "代茶饮",
        "红枣", "枸杞", "茯苓", "薏米", "酸枣仁", "阿胶"
    ]

    best = None
    best_score = -1

    for art in articles:
        title = art.get("title", "")
        source = art.get("source", "")
        summary = art.get("summary", "")

        if any(kw in title for kw in exclude_keywords):
            print(f"⏭️ 跳过：{title[:40]}...")
            continue

        score = source_weights.get(source, 1)
        for kw in high_value_keywords:
            if kw in title:
                score += 3
        score += min(len(summary) / 200, 5)
        if len(title) < 5:
            score -= 2

        if score > best_score:
            best_score = score
            best = art

    if best:
        print(f"🏆 选中：【{best['source']}】{best['title']} (得分: {best_score:.1f})")
    return best

# ================= AI 改写 =================
def build_prompt(article: Dict) -> str:
    return f"""
{CUSTOM_STYLE}

【原文】
来源：{article['source']}
标题：{article['title']}
摘要：{article['summary']}

请输出小红书文案（标题+正文+互动+标签）。
"""

def rewrite_for_xiaohongshu(article: Dict) -> Optional[str]:
    prompt = build_prompt(article)
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 1200
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()
        print(f"✅ 改写成功：{article['title'][:40]}")
        return content
    except Exception as e:
        print(f"❌ 改写失败：{e}")
        return None

# ================= 微信推送 =================
def send_to_wechat(content: str):
    if not content:
        return
    if len(content) > 4000:
        content = content[:3900] + "\n\n...（截断）"
    title = f"📅 养生知识日报 - {datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d')}"
    url = "https://www.pushplus.plus/send"
    data = {"token": PUSHPLUS_TOKEN, "title": title, "content": content, "template": "markdown"}
    try:
        resp = requests.post(url, json=data, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        print(f"📡 PushPlus 返回码: {result.get('code')}, 消息: {result.get('msg')}")
        if result.get("code") == 200:
            print("🎉 微信推送成功！")
        else:
            print(f"⚠️ 推送失败：{result.get('msg')}")
    except Exception as e:
        print(f"❌ 推送异常：{e}")

# ================= 主函数 =================
def main():
    print(f"🚀 启动时间：{datetime.now(pytz.timezone('Asia/Shanghai'))}")
    new_articles = fetch_all_new_articles()
    if not new_articles:
        print("没有新文章，今日不推送。")
        return

    best = select_best_article(new_articles)
    if not best:
        print("没有合适文章，放弃推送。")
        return

    xhs_post = rewrite_for_xiaohongshu(best)
    if xhs_post:
        send_to_wechat(xhs_post)
    else:
        print("改写失败，不推送。")

    # 缓存本次所有新文章
    sent_hashes = load_sent_articles()
    for art in new_articles:
        sent_hashes.add(get_link_hash(art['link']))
    save_sent_articles(sent_hashes)
    print(f"💾 已缓存 {len(new_articles)} 篇新文章")

    print("✅ 完成")

if __name__ == "__main__":
    main()
