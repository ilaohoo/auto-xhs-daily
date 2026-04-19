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
# 请通过 GitHub Secrets 设置以下环境变量
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "YOUR_DEEPSEEK_API_KEY")
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "YOUR_PUSHPLUS_TOKEN")

# 缓存文件（记录已推送的文章链接哈希）
CACHE_FILE = "sent_articles.json"

# ---------- 自定义写作风格（可随意修改）----------
CUSTOM_STYLE = """
【我的写作风格要求】
- 喜欢用“姐妹们”、“宝子们”开头，亲切感强
- 善用比喻，比如“脾胃就像身体的发动机”
- 段落之间加分隔线“···”
- 每段不超过3行，多留白
- 常用emoji：🌱🍎🥣✨🔥
- 结尾一定有“💬 评论区告诉我你的困扰，下次专门为你出一期！”
"""

# ---------- 自定义URL爬虫（可选，留空则跳过）----------
# 格式示例: {"name": "网站名", "url": "https://example.com", "selector": "h2 a"}
CUSTOM_URLS = []  # 按需填写

# ================= 智能选文模块 =================
def select_best_article(articles: List[Dict]) -> Optional[Dict]:
    """
    从多篇文章中选出一篇最适合推送的。
    你可以修改 source_weights 和 high_value_keywords 来调整评分逻辑。
    """
    if not articles:
        return None

    # 不同来源的权重（数字越大越优先）
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
    }

    # 高价值关键词（出现在标题中加分）
    high_value_keywords = [
        "健脾", "祛湿", "补气血", "养肝", "助眠", "便秘",
        "食疗", "药膳", "四神汤", "八珍", "黄芪", "艾灸"
    ]

    best = None
    best_score = -1

    for art in articles:
        score = 0
        title = art.get("title", "")
        source = art.get("source", "")
        summary = art.get("summary", "")

        # 来源权重
        score += source_weights.get(source, 1)

        # 标题包含高价值关键词
        for kw in high_value_keywords:
            if kw in title:
                score += 3

        # 内容长度适中（摘要越长信息量可能越大）
        score += min(len(summary) / 200, 5)  # 最多加5分

        # 避免标题过短或过泛
        if len(title) < 5:
            score -= 2

        if score > best_score:
            best_score = score
            best = art

    print(f"🏆 选中文章：【{best['source']}】{best['title']} (得分: {best_score:.1f})")
    return best

# ================= 数据采集模块 =================
def load_sent_articles() -> set:
    """加载已经推送过的文章链接哈希集合"""
    if not os.path.exists(CACHE_FILE):
        return set()
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get("sent_hashes", []))
    except:
        return set()

def save_sent_articles(sent_hashes: set):
    """保存已推送的文章链接哈希"""
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump({"sent_hashes": list(sent_hashes)}, f, ensure_ascii=False, indent=2)

def get_link_hash(link: str) -> str:
    """生成链接的哈希值，用于去重"""
    return hashlib.md5(link.encode('utf-8')).hexdigest()

# RSS 源列表
RSS_SOURCES = [
    {"name": "中医启疾光网", "url": "https://www.zyqjg.com/forum.php?mod=guide&view=newthread&rss=1"},
    {"name": "人民网健康", "url": "https://rsshub.app/people/health/latest"},
    {"name": "凤凰中医", "url": "https://rsshub.app/feng/ifeng/2/1"},
    {"name": "39健康网", "url": "https://rsshub.app/39net/news"},
    {"name": "乡间郎中", "url": "https://rsshub.app/xjlangzhong"},
    {"name": "老中医养生网", "url": "https://rsshub.app/lzyysw"},
    {"name": "三九养生网", "url": "https://rsshub.app/39ysw"},
    {"name": "中华药膳门户", "url": "https://rsshub.app/25pp"},
    {"name": "健康一线", "url": "https://rsshub.app/xgys"},
    {"name": "养生之道网", "url": "https://rsshub.app/yszdao"}
]

def fetch_from_rss() -> List[Dict]:
    """从RSS源抓取文章"""
    articles = []
    for source in RSS_SOURCES:
        print(f"📡 RSS抓取：{source['name']}")
        try:
            feed = feedparser.parse(source['url'])
            for entry in feed.entries[:2]:  # 每个源取最新2篇
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

def fetch_from_custom_urls() -> List[Dict]:
    """从自定义URL爬取文章（需要安装beautifulsoup4）"""
    if not CUSTOM_URLS:
        return []
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("⚠️ 未安装 beautifulsoup4，自定义爬虫不可用。请运行: pip install beautifulsoup4 lxml")
        return []
    articles = []
    for item in CUSTOM_URLS:
        name = item.get("name")
        url = item.get("url")
        selector = item.get("selector")
        print(f"🔧 自定义爬虫：{name}")
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')
            elements = soup.select(selector)
            for elem in elements[:2]:
                link = elem.get('href')
                if not link.startswith('http'):
                    link = requests.compat.urljoin(url, link)
                title = elem.get_text(strip=True)
                if title and link:
                    articles.append({
                        'title': title,
                        'summary': f"来自 {name} 的文章",
                        'link': link,
                        'source': name
                    })
        except Exception as e:
            print(f"   ❌ 失败：{e}")
    return articles

def fetch_all_new_articles() -> List[Dict]:
    """获取所有新文章（未推送过的）"""
    sent_hashes = load_sent_articles()
    all_articles = fetch_from_rss() + fetch_from_custom_urls()
    # 基于链接去重
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
    return new_articles

# ================= AI改写模块 =================
def build_prompt(article: Dict) -> str:
    """构建发送给AI的提示词（融合自定义风格）"""
    return f"""
你是一位专业的小红书养生博主，请将下面这篇文章改写成爆款小红书文案。

{CUSTOM_STYLE}

【内容要求】
1. 标题：20字以内，带2-3个emoji，要吸引点击。
2. 正文：口语化，多用短句和emoji，分点清晰，每段不超过3行。
3. 结尾：加上5-8个相关话题标签，例如 #养生日常 #中医食补 #健脾祛湿。
4. 禁止：夸大效果（不能说“治愈”）、不能推荐具体药品。

【原始文章】
来源：{article['source']}
标题：{article['title']}
内容摘要：{article['summary']}

请直接输出完整的小红书文案（标题单独一行，然后空一行再写正文）。
"""

def rewrite_for_xiaohongshu(article: Dict) -> Optional[str]:
    """调用DeepSeek API改写"""
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
        "max_tokens": 800
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

# ================= 微信推送模块 =================
def send_to_wechat(content: str):
    """推送文案到微信"""
    if not content:
        return
    if len(content) > 4000:
        content = content[:3900] + "\n\n...（内容过长已截断）"
    title = f"📅 养生知识日报 - {datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d')}"
    url = "http://www.pushplus.plus/send"
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
        print("没有新文章，结束运行。")
        return

    # 从所有新文章中选一篇最好的
    best_article = select_best_article(new_articles)
    if not best_article:
        print("无法选择文章，退出。")
        return

    # 改写并推送这一篇
    print(f"📝 正在改写最佳文章...")
    xhs_post = rewrite_for_xiaohongshu(best_article)
    if xhs_post:
        send_to_wechat(xhs_post)

    # 将所有新文章（包括未选中的）都标记为已处理，避免重复
    sent_hashes = load_sent_articles()
    for art in new_articles:
        sent_hashes.add(get_link_hash(art['link']))
    save_sent_articles(sent_hashes)
    print(f"💾 已缓存 {len(new_articles)} 篇文章（仅推送了其中1篇）")

    print("✅ 脚本执行完毕。")

if __name__ == "__main__":
    main()
