#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BBC中文网新闻获取脚本
用于定时任务获取热点新闻TOP10并生成简报
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os

def fetch_bbc_news():
    """获取BBC中文网热点新闻"""
    url = 'https://www.bbc.com/zhongwen'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return {'error': f'HTTP {response.status_code}'}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取新闻标题和链接
        news_list = []
        
        # 查找主要新闻区域的链接
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            title = link.get_text(strip=True)
            
            # 筛选新闻链接（排除图片、视频、直播等）
            if ('/news/' in href or '/world/' in href) and title and len(title) > 5:
                if title not in [n['title'] for n in news_list]:
                    news_list.append({
                        'title': title,
                        'url': 'https://www.bbc.com' + href if href.startswith('/') else href
                    })
        
        # 取前10条
        top_news = news_list[:10]
        
        return {
            'success': True,
            'count': len(top_news),
            'news': top_news,
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        return {'error': str(e)}

def generate_briefing(news_data, output_path):
    """生成新闻简报"""
    today = datetime.now().strftime('%Y年%m月%d日')
    
    content = f"""# BBC中文网热点新闻简报

**生成时间**: {news_data.get('fetch_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}
**新闻来源**: BBC中文网 (https://www.bbc.com/zhongwen)

---

## 今日热点新闻 TOP {len(news_data.get('news', []))}

"""
    
    if 'error' in news_data:
        content += f"[X] 获取新闻失败: {news_data['error']}\n\n"
        content += "**可能原因**: \n"
        content += "- 网络连接问题\n"
        content += "- BBC网站访问限制\n"
        content += "- 页面结构变化\n\n"
        content += "**建议操作**: \n"
        content += "- 稍后重试\n"
        content += "- 手动访问BBC中文网查看新闻\n"
    else:
        for i, news in enumerate(news_data.get('news', []), 1):
            content += f"**{i}.** [{news['title']}]({news['url']})\n\n"
        
        content += f"\n---\n\n"
        content += f"**共计**: {len(news_data.get('news', []))} 条热点新闻\n"
        content += f"**获取时间**: {news_data.get('fetch_time', '')}\n"
        content += f"\n*本简报由自动脚本生成*\n"
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return content

if __name__ == '__main__':
    # 获取今天的日期
    today = datetime.now().strftime('%Y%m%d')
    output_path = f'C:\\Users\\lucky\\projects\\my_project\\news_briefing_{today}.md'
    
    print(f"开始获取BBC中文网新闻... ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    
    # 获取新闻
    news_data = fetch_bbc_news()
    
    # 生成简报
    content = generate_briefing(news_data, output_path)
    
    print(f"\n[OK] 简报已生成: {output_path}")
    print(f"[NEWS] 新闻数量: {news_data.get('count', 'N/A')}")
