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

# ---------- 小红书爆款风格优化版 ----------
CUSTOM_STYLE = """
【小红书爆款科普文要求】
你是一位资深小红书养生博主，擅长把枯燥的健康知识写成爆款笔记。请将采集到的文章改写成以下风格的笔记：

【标题公式】
- 格式：⚠️ + 痛点/数字 + 情绪词 + 结果
- 示例1：⚠️别吃了！这10个习惯正在偷走你的寿命
- 示例2：10个作死饮食习惯😭我中了5个，你呢？
- 标题长度控制在18字以内，带2个emoji。

【开头套路】
- 第一句必须是“姐妹们，”或“宝子们，”
- 然后用一个生活场景引发共鸣：“你是不是也这样？早上抓块饼干当早餐，午饭5分钟扒拉完……”
- 紧接着抛出一个权威数据制造焦虑：“《柳叶刀》说，全球每年因不良饮食死亡超1100万！”
- 最后给出价值承诺：“今天盘10个最伤身的习惯，中招的赶紧改👇”

【正文结构】
- 每条习惯用 **01、02、03……** 加粗小标题
- 每一条格式：危害（一句话）+ 数据支撑（引用研究）+ 具体建议（一句话）
- 适当加入emoji：⚠️📊🍚🥤💤🔥
- 段落之间空一行，每段不超过3行

【结尾互动】
- 必须加一句互动提问：“你中了几个？评论区告诉我😭”
- 再加一句呼吁：“从今天开始，改掉一个坏习惯就是胜利！”
- 最后加上5-8个标签： #健康科普 #饮食习惯 #寿命 #养生日常 #避雷 #变健康

【禁止事项】
- 绝对不能说“治愈”“根治”“神效”
- 不能推荐具体药品或保健品
- 不要用“专家说”，改用“研究发现”“数据显示”
"""

# ---------- RSS 源列表（使用稳定镜像）----------
RSS_SOURCES = [
    {"name": "中医启疾光网", "url": "https://www.zyqjg.com/forum.php?mod=guide&view=newthread&rss=1"},
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

# ---------- 备用文章（内置一篇高互动选题）----------
def get_seed_article() -> Dict:
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
    
    unique = {}
    for art in all_articles:
        link = art['link']
        if link not in unique:
            unique[link] = art
    
    new_articles = []
    for art in unique.values():
        h = get_link_hash(art['link'])
        if h not in sent_hashes:
            new_articles.append(art)
    
    print(f"📊 总抓取 {len(unique)} 篇，新文章 {len(new_articles)} 篇")
    
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
        "内置科普库": 4
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
你是一位资深小红书养生博主。请将下面这篇文章改写成一篇爆款小红书笔记，严格遵循以下风格要求：

{CUSTOM_STYLE}

【原始文章信息】
来源：{article['source']}
标题：{article['title']}
内容摘要：
{article['summary']}

请直接输出改写后的小红书文案，必须包含：
- 标题（单独一行，带emoji）
- 空一行
- 正文（按01、02结构，每一条有危害+数据+建议）
- 空一行
- 互动提问 + 标签
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
    url = "https://www.pushplus.plus/send"
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

    sent_hashes = load_sent_articles()
    for art in new_articles:
        sent_hashes.add(get_link_hash(art['link']))
    save_sent_articles(sent_hashes)
    print(f"💾 已缓存 {len(new_articles)} 篇文章（仅推送了其中1篇）")

    print("✅ 脚本执行完毕。")

if __name__ == "__main__":
    main()
