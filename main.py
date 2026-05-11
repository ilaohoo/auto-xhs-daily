import requests
import json
import hashlib
import os
from datetime import datetime
import feedparser
import pytz
from typing import List, Dict, Optional

# ================= 配置 =================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "YOUR_DEEPSEEK_API_KEY")
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "YOUR_PUSHPLUS_TOKEN")

CACHE_FILE = "sent_articles.json"

# ---------- 小红书图文爆款风格（体质食补专版）----------
CUSTOM_STYLE = """
你是一位小红书养生博主，专注“体质食补”领域，只做图文笔记。请将以下内容改写成**收藏率极高**的小红书图文笔记。

【标题公式】
- 形式：数字/痛点 + 解决方案 + emoji，控制在18字以内
- 示例：“1分钟自测：你是哪种体质？附9大食谱”、“气虚必喝3碗汤，喝完不再累”

【正文结构】
- 开头：用“姐妹们/宝子们”+ 痛点场景（1-2句话）
- 中间：分点列出（01、02、03…），每条包含：
  - 症状/问题（一句话）
  - 原因或原理（一句话，引用中医知识或数据）
  - 具体食谱/方法（食材+大致做法）
- 结尾：
  - 总结：“收藏起来，慢慢对照喝”
  - 互动提问：“你是什么体质？评论区告诉我”
  - 标签：#体质调理 #食疗 #养生 #药食同源

【特殊要求】
- 每条内容必须包含**具体食材和大致做法**（用户能照着做）
- 适当加入emoji（⚠️🍵✅📊），每段不超过3行
- 不要写“治愈”“根治”，用“调理”“改善”
- 不要推荐具体药品或保健品，只推荐药食同源的食材
- 正文总长度500-800字（适合图文阅读）
"""

# ---------- RSS 源（包含药食同源+养生茶）----------
RSS_SOURCES = [
    {"name": "中医启疾光网", "url": "https://www.zyqjg.com/forum.php?mod=guide&view=newthread&rss=1"},
    {"name": "人民网健康", "url": "https://rsshub.rssforever.com/people/health/latest"},
    {"name": "凤凰中医", "url": "https://rsshub.rssforever.com/feng/ifeng/2/1"},
    {"name": "39健康网", "url": "https://rsshub.rssforever.com/39net/news"},
    {"name": "健康一线", "url": "https://rsshub.rssforever.com/xgys"},
    {"name": "养生之道网", "url": "https://rsshub.rssforever.com/yszdao"},
    {"name": "药食同源资讯", "url": "https://rsshub.rssforever.com/health/drug-food"},
    {"name": "养生茶专题", "url": "https://rsshub.rssforever.com/health/herbal-tea"},
]

# ---------- 体质食补选题库（备用，每天不同，收藏爆款）----------
CONSTITUTION_TOPICS = [
    {
        "title": "1分钟自测：你是哪种体质？附9大体质食补清单",
        "summary": "中医将体质分为9种：平和质、气虚质、阳虚质、阴虚质、痰湿质、湿热质、血瘀质、气郁质、特禀质。本文提供快速自测法，并给出每种体质的核心食补建议（如气虚喝黄芪鸡汤，血瘀喝山楂红糖水）。"
    },
    {
        "title": "气虚体质必看！这3道补气汤，喝完不再“懒得动”",
        "summary": "症状：乏力、气短、自汗、易感冒。原因：元气不足，脏腑功能减退。食谱：①黄芪党参鸡汤（黄芪15g+党参10g+鸡肉）；②四君子汤（人参+白术+茯苓+甘草）；③山药红枣粥（鲜山药+红枣+粳米）。"
    },
    {
        "title": "血瘀体质脸暗沉？这3杯茶喝出红润气色",
        "summary": "症状：面色晦暗、唇色紫暗、痛经、舌有瘀点。原因：血液循环不畅。食谱：①山楂红糖水（山楂干+红糖煮水）；②玫瑰花茶（干玫瑰花+蜂蜜）；③三七粉饮（温水冲服1-2g，每周2-3次）。"
    },
    {
        "title": "湿热体质爱长痘？这4碗祛湿汤，亲测有效",
        "summary": "症状：面部油腻、易生痤疮、口苦口臭、大便粘滞。原因：湿与热蕴结体内。食谱：①红豆薏米水（赤小豆+炒薏米）；②绿豆百合粥（绿豆+百合+大米）；③冬瓜薏米汤（冬瓜+薏米+排骨）；④土茯苓瘦肉汤。"
    },
    {
        "title": "阳虚怕冷星人！冬天这3碗汤让你暖起来",
        "summary": "症状：畏寒肢冷、腰膝酸软、夜尿多。原因：阳气不足，温煦失职。食谱：①当归生姜羊肉汤（当归+生姜+羊肉）；②姜枣茶（生姜3片+红枣5颗煮水）；③桂圆红枣汤（桂圆+红枣+枸杞+红糖）。"
    },
    {
        "title": "阴虚体质口干舌燥？这4种滋阴食物要常吃",
        "summary": "症状：口干咽燥、五心烦热、盗汗、舌红少苔。原因：阴液亏少，虚热内生。食谱：①银耳百合羹（银耳+百合+冰糖）；②石斛麦冬茶（石斛+麦冬泡水）；③桑葚膏（桑葚熬膏冲服）；④沙参玉竹汤。"
    },
    {
        "title": "痰湿体质大肚子？这3个祛湿食谱，小腹平了",
        "summary": "症状：体型肥胖、腹部松软、胸闷、痰多。原因：水湿内停，痰浊凝聚。食谱：①茯苓白术粥（茯苓+白术+粳米）；②陈皮薏米水（陈皮+炒薏米）；③荷叶茶（干荷叶泡水，饭后饮用）。"
    },
    {
        "title": "气郁体质爱叹气？这3杯解郁茶，心情都好了",
        "summary": "症状：情绪低落、胸闷胁胀、易叹气。原因：气机郁滞，疏泄失常。食谱：①玫瑰花佛手茶（玫瑰花+佛手片）；②茉莉花茶（茉莉花+绿茶）；③合欢花茶（合欢花+蜂蜜）。"
    },
    {
        "title": "特禀体质（过敏）怎么吃？这3碗汤增强免疫力",
        "summary": "症状：过敏体质，易患荨麻疹、哮喘、鼻炎。原因：先天禀赋异常。食谱：①黄芪固表汤（黄芪+白术+防风+瘦肉）；②金针菇豆腐汤（金针菇+豆腐）；③生姜红枣饮（生姜+红枣煮水，晨起喝）。"
    },
    {
        "title": "平和体质也要养！这套全年养生食谱照着吃",
        "summary": "症状：精力充沛，面色红润，无不适。目标：保持平衡，预防疾病。食谱：①春季：韭菜炒鸡蛋（助阳气）；②夏季：绿豆薏米粥（清热祛湿）；③秋季：银耳雪梨汤（润肺）；④冬季：当归生姜羊肉汤（温补）。"
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
    """从体质食补选题库中按日期选择一篇（每天不同）"""
    today = datetime.now(pytz.timezone('Asia/Shanghai'))
    index = (today.year * 365 + today.timetuple().tm_yday) % len(CONSTITUTION_TOPICS)
    topic = CONSTITUTION_TOPICS[index]
    return {
        'title': topic['title'],
        'summary': topic['summary'],
        'link': f"https://example.com/constitution-{today.strftime('%Y%m%d')}",
        'source': '体质食补选题库'
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
    
    # 如果没有新文章，使用选题库中的文章
    if not new_articles:
        print("⚠️ 未抓到新文章，使用体质食补选题库...")
        seed = get_seed_article()
        h = get_link_hash(seed['link'])
        if h not in sent_hashes:
            new_articles.append(seed)
            print(f"📝 已添加选题：{seed['title']}")
        else:
            print("⏭️ 今天的选题已推送过，不再重复。")
    
    return new_articles

# ================= 智能选文 =================
def select_best_article(articles: List[Dict]) -> Optional[Dict]:
    if not articles:
        return None

    exclude_keywords = ["保险", "政策", "制度", "通知", "政府", "医保", "社保", "会议", "领导", "习近平", "国务院"]
    source_weights = {
        "中医启疾光网": 5, "人民网健康": 4, "凤凰中医": 4, "39健康网": 3,
        "健康一线": 2, "养生之道网": 2, "药食同源资讯": 5, "养生茶专题": 5,
        "体质食补选题库": 4
    }
    high_value_keywords = [
        "体质", "气虚", "血瘀", "湿热", "阳虚", "阴虚", "痰湿", "气郁", "特禀", "食疗",
        "健脾", "祛湿", "补气血", "养肝", "助眠", "食谱", "汤", "茶"
    ]

    best = None
    best_score = -1
    for art in articles:
        title = art.get("title", "")
        source = art.get("source", "")
        summary = art.get("summary", "")
        if any(kw in title for kw in exclude_keywords):
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

【原始素材】
来源：{article['source']}
标题：{article['title']}
内容摘要：
{article['summary']}

【额外要求】
- 如果原始素材中没有食谱，请根据中医常识补充1-2个经典食谱（食材必须是药食同源的，如红枣、枸杞、山药、茯苓等）
- 不要编造数据，但可以引用常见研究（如“《中国居民膳食指南》建议…”）
- 输出格式：标题 + 空一行 + 正文（01、02结构） + 空一行 + 结尾标签

请直接输出小红书文案。
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

    sent_hashes = load_sent_articles()
    for art in new_articles:
        sent_hashes.add(get_link_hash(art['link']))
    save_sent_articles(sent_hashes)
    print(f"💾 已缓存 {len(new_articles)} 篇新文章")
    print("✅ 完成")

if __name__ == "__main__":
    main()
