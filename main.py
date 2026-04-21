import requests
import json
import hashlib
import os
import re
from datetime import datetime
import feedparser
import pytz
from typing import List, Dict, Optional

# ================= 配置区域 =================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "YOUR_DEEPSEEK_API_KEY")
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "YOUR_PUSHPLUS_TOKEN")

CACHE_FILE = "sent_articles.json"

# ---------- 写作风格（新华社科普 + 小红书元素）----------
CUSTOM_STYLE = """
【小红书爆款科普文要求】
你是一位专业的小红书健康科普博主，请将采集到的文章改写成一篇既权威又易懂、适合小红书的科普笔记。

风格要求：
- 标题：20字以内，带2-3个emoji，直击痛点或引发好奇。例如：“🚫别让这10个习惯偷走你的寿命！”
- 开头：用“姐妹们/宝子们” + 一个生活场景引入，比如：“你的一天是不是这样开始的：清晨匆忙出门，顺手抓一块饼干当早餐……”
- 正文结构：
  - 每条习惯用 **01、02、03……** 加粗小标题（如“**01 不吃早餐**”）
  - 每条内容包含：危害（引用权威研究/数据） + 具体机制 + 改善建议
  - 适当添加emoji（⚠️📊🍚🥤💤🔥），每段不超过4行
- 结尾：总结呼吁（如“从今天开始，改掉一个习惯也是胜利”） + 5-8个相关标签（#健康科普 #饮食习惯 #寿命 #养生日常）
- 禁止：夸大效果、推荐药品、绝对化用语（“治愈”“根治”）

请确保内容真实可信，数据可查（可适当引用《柳叶刀》《中国居民膳食指南》等）。
"""

# ---------- RSS 源列表（使用更稳定的镜像）----------
RSS_SOURCES = [
    {"name": "中医启疾光网", "url": "https://www.zyqjg.com/forum.php?mod=guide&view=newthread&rss=1"},  # 原生RSS
    {"name": "人民网健康", "url": "https://rsshub.bili.xyz/people/health/latest"},
    {"name": "凤凰中医", "url": "https://rsshub.bili.xyz/feng/ifeng/2/1"},
    {"name": "39健康网", "url": "https://rsshub.bili.xyz/39net/news"},
    {"name": "乡间郎中", "url": "https://rsshub.bili.xyz/xjlangzhong"},
    {"name": "老中医养生网", "url": "https://rsshub.bili.xyz/lzyysw"},
    {"name": "三九养生网", "url": "https://rsshub.bili.xyz/39ysw"},
    {"name": "中华药膳门户", "url": "https://rsshub.bili.xyz/25pp"},
    {"name": "健康一线", "url": "https://rsshub.bili.xyz/xgys"},
    {"name": "养生之道网", "url": "https://rsshub.bili.xyz/yszdao"}
]

# ---------- 备用文章（当所有RSS都抓不到时使用）----------
def get_seed_article() -> Dict:
    """返回一篇内置的养生科普文章（每天链接不同，避免缓存重复）"""
    today = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d')
    return {
        'title': '10个饮食习惯正在偷走你的寿命',
        'summary': '《柳叶刀》数据显示，全球每年因不良饮食导致的死亡人数超过1100万。本文盘点10个不良饮食习惯：不吃早餐、吃饭太快、晚餐过晚、暴饮暴食、吃变质食物、高盐饮食、偏爱烫食、甜饮料成瘾、爱吃腌制食品、主食比例不合理。每个习惯都给出了科学依据和改善建议。',
        'link': f'https://example.com/seed-article-{today}',
        'source': '内置科普库'
    }

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
    
    # 如果没有新文章，使用备用文章（但也要检查是否已推送过）
    if not new_articles:
        print("⚠️ 未抓到新文章，尝试使用备用文章...")
        seed = get_seed_article()
        h = get_link_hash(seed['link'])
        if h not in sent_hashes:
            new_articles.append(seed)
            print(f"📝 已添加备用文章：{seed['title']}")
        else:
            print("⏭️ 备用文章今天已推送过，不再重复。")
    
    return new_articles

# ================= 智能选文 =================
def select_best_article(articles: List[Dict]) -> Optional[Dict]:
    if not articles:
        return None

    exclude_keywords = [
        "保险", "政策", "制度", "实施方案", "通知", "政府", 
        "医保", "社保", "会议", "领导", "习近平", "国务院",
        "长期护理", "养老金", "退休", "委员会", "印发", "文件"
    ]

    source_weights = {
        "中医启疾光网": 5,
        "人民网健康": 4,
        "凤凰中医": 4,
        "39健康网": 3,
        "乡间郎中": 4,
        "老中医养生网": 3,
        "三九养生网": 3,
        "中华药膳门户": 3,
        "健康一线": 2,
        "养生之道网": 2,
        "内置科普库": 4  # 备用文章权重较高
    }

    high_value_keywords = [
        "健脾", "祛湿", "补气血", "养肝", "助眠", "便秘",
        "食疗", "药膳", "四神汤", "八珍", "黄芪", "艾灸",
        "寿命", "饮食习惯", "科普", "危害", "改善"
    ]

    best = None
    best_score = -1

    for art in articles:
        title = art.get("title", "")
        source = art.get("source", "")
        summary = art.get("summary", "")

        if any(kw in title for kw in exclude_keywords):
            print(f"⏭️ 跳过非养生文章：{title[:50]}...")
            continue

        score = 0
        score += source_weights.get(source, 1)
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
        print(f"🏆 选中文章：【{best['source']}】{best['title']} (得分: {best_score:.1f})")
    return best

# ================= AI 改写 =================
def build_prompt(article: Dict) -> str:
    return f"""
你是一位专业的小红书健康科普博主。请将下面这篇关于饮食/养生的文章，改写成一篇既权威又易懂、适合小红书的爆款科普笔记。

{CUSTOM_STYLE}

【原始文章信息】
来源：{article['source']}
标题：{article['title']}
内容摘要：
{article['summary']}

请直接输出改写后的小红书文案，格式要求：
- 第一行：标题（带emoji）
- 空一行
- 正文（按01、02……结构）
- 空一行
- 结尾标签
"""

def rewrite_for_xiaohongshu(article: Dict) -> Optional[str]:
    prompt = build_prompt(article)
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
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
        xhs_content = result["choices"][0]["message"]["content"].strip()
        print(f"✅ 改写成功：{article['title'][:40]}")
        return xhs_content
    except Exception as e:
        print(f"❌ 改写失败：{e}")
        return None

# ================= 微信推送 =================
def send_to_wechat(content: str):
    if not content:
        print("⚠️ 内容为空，不推送")
        return
    if len(content) > 4000:
        content = content[:3900] + "\n\n...（内容过长已截断）"
    title = f"📅 养生知识日报 - {datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d')}"
    url = "https://www.pushplus.plus/send"  # 使用 https
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": "markdown"
    }
    try:
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        print(f"📡 PushPlus 返回码: {result.get('code')}")
        print(f"📡 PushPlus 返回消息: {result.get('msg')}")
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
        print("没有新文章（备用文章也已用过），结束运行。")
        return

    best_article = select_best_article(new_articles)
    if not best_article:
        print("无法选择文章，退出。")
        return

    print(f"📝 正在改写最佳文章...")
    xhs_post = rewrite_for_xiaohongshu(best_article)
    if xhs_post:
        send_to_wechat(xhs_post)
    else:
        print("⚠️ 改写失败，未推送。")

    # 缓存所有新文章（包括备用文章）
    sent_hashes = load_sent_articles()
    for art in new_articles:
        sent_hashes.add(get_link_hash(art['link']))
    save_sent_articles(sent_hashes)
    print(f"💾 已缓存 {len(new_articles)} 篇文章（仅推送了其中1篇）")

    print("✅ 脚本执行完毕。")

if __name__ == "__main__":
    main()
