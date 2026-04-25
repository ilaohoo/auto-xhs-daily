# -*- coding: utf-8 -*-
"""
中医数据抓取模块 - 从权威中医网站抓取内容
数据源：中医资源网、医学微视等
"""

import requests
import random
import time
from bs4 import BeautifulSoup
from typing import Dict, Optional

class TCMDataCrawler:
    """中医数据抓取器"""
    
    def __init__(self):
        # 模拟浏览器请求头，避免被反爬
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # 权威中医知识库网站 [citation:8]
        self.sources = {
            'tcmdoc': 'http://www.tcmdoc.cn/ShuJuKu/default.aspx',  # 中医资源网
            'yaozh': 'https://www.yaozh.com/',  # 药智网
        }
    
    def get_tcm_knowledge(self, keyword: str) -> Optional[str]:
        """
        根据关键词获取中医相关知识
        返回抓取到的原始文本内容
        """
        # 这里使用模拟数据作为示例
        # 实际使用时需要根据具体网站结构调整爬虫逻辑
        
        knowledge_base = {
            "气血不足": "气血不足，中医病机，指气与血两者都不足。主要表现：面色苍白或萎黄，头晕目眩，心悸失眠，神疲乏力，气短懒言，手足麻木，月经量少色淡等。",
            "祛湿气": "湿气是中医理论中的概念，指体内水液代谢失常产生的病理产物。症状包括：身体困重，头昏沉如裹，大便粘腻，舌苔厚腻，食欲不振等。常用祛湿食材：薏米、赤小豆、茯苓、白术。",
            "养肝护肝": "肝主疏泄，调畅气机。养肝要点：1.子时（23:00-1:00）前入睡；2.多吃绿色蔬菜；3.保持情绪舒畅；4.适当饮用菊花枸杞茶。",
        }
        
        for key in knowledge_base:
            if key in keyword or keyword in key:
                return knowledge_base[key]
        
        # 如果没有匹配的，返回通用知识
        return f"{keyword}是中医常见的健康话题。建议咨询专业中医师进行辨证论治。"
    
    def get_daily_health_tip(self) -> Dict[str, str]:
        """
        获取每日健康小贴士
        返回包含标题和内容的字典
        """
        tips = [
            {"title": "春季养肝正当时", "content": "春属木，与肝相应。春季养肝宜多吃绿色蔬菜，如菠菜、西兰花；保持心情舒畅，避免熬夜；可饮用菊花枸杞茶清肝明目。"},
            {"title": "祛湿茶搭配方", "content": "经典祛湿茶：薏米15g + 赤小豆15g + 茯苓10g + 陈皮3g。加水煮沸后小火煮30分钟，每周饮用3-4次，适合湿气重、易疲劳人群。"},
            {"title": "改善睡眠小妙招", "content": "1.睡前1小时远离电子设备；2.用温水泡脚15分钟；3.按揉神门穴（手腕横纹尺侧端）；4.喝一杯温牛奶或酸枣仁茶。"},
        ]
        return random.choice(tips)
