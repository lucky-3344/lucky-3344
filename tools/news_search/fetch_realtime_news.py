import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime

# 设置SOCKS5代理
proxies = {
    'http': 'socks5://127.0.0.1:1080',
    'https': 'socks5://127.0.0.1:1080'
}

def fetch_cnn_headlines():
    """获取CNN头条"""
    try:
        url = 'https://edition.cnn.com/world'
        response = requests.get(url, timeout=20, proxies=proxies)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        headlines = []
        # 查找新闻标题
        for item in soup.find_all(['h2', 'h3', 'span'], class_=re.compile('headline|title', re.I))[:15]:
            text = item.get_text(strip=True)
            if text and len(text) > 15 and len(text) < 200:
                headlines.append(text)
        
        # 去重
        return list(set(headlines))[:10]
    except Exception as e:
        print(f"CNN fetch error: {e}")
        return []

def fetch_github_trending():
    """获取GitHub趋势"""
    try:
        url = 'https://github.com/trending'
        response = requests.get(url, timeout=20, proxies=proxies)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        repos = []
        for article in soup.find_all('article', class_='Box-row')[:10]:
            # 获取仓库名
            name_elem = article.find('h2', class_='h3')
            if name_elem:
                name = name_elem.get_text(strip=True).replace(' ', '').replace('\n', '')
                
                # 获取描述
                desc_elem = article.find('p', class_='col-9')
                desc = desc_elem.get_text(strip=True) if desc_elem else 'No description'
                
                # 获取星星数
                stars_elem = article.find('a', class_=re.compile('Link--muted', re.I))
                stars = stars_elem.get_text(strip=True) if stars_elem else 'N/A'
                
                repos.append({
                    'name': name,
                    'desc': desc[:120],
                    'stars': stars
                })
        
        return repos
    except Exception as e:
        print(f"GitHub fetch error: {e}")
        return []

def fetch_cnn_section(section):
    """获取CNN特定板块"""
    try:
        url = f'https://edition.cnn.com/world/{section}'
        response = requests.get(url, timeout=20, proxies=proxies)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = []
        for item in soup.find_all('span', class_='container__headline-text')[:8]:
            text = item.get_text(strip=True)
            if text:
                articles.append(text)
        
        return list(set(articles))[:5]
    except Exception as e:
        print(f"CNN {section} fetch error: {e}")
        return []

def generate_briefing():
    """生成新闻简报"""
    print("Fetching CNN headlines...")
    cnn_headlines = fetch_cnn_headlines()
    
    print("Fetching GitHub trending...")
    github_repos = fetch_github_trending()
    
    print("Fetching CNN China news...")
    china_news = fetch_cnn_section('china')
    
    print("Fetching CNN Tech news...")
    tech_news = fetch_cnn_section('asia')  # 先用asia
    
    # 生成markdown简报
    now = datetime.now().strftime('%Y年%m月%d日 %H:%M')
    
    briefing = f"""# 综合新闻简报 - {datetime.now().strftime('%Y年%m月%d日')}

**生成时间**: {now} (Asia/Shanghai)  
**状态**: ✅ 实时获取（通过SOCKS5代理）

---

## 🌍 CNN国际头条

"""
    if cnn_headlines:
        for i, headline in enumerate(cnn_headlines, 1):
            briefing += f"{i}. {headline}\n"
    else:
        briefing += "- 暂无数据\n"
    
    briefing += "\n---\n\n## 🇨🇳 CNN中国相关新闻\n\n"
    if china_news:
        for news in china_news:
            briefing += f"- {news}\n"
    else:
        briefing += "- 暂无数据\n"
    
    briefing += "\n---\n\n## 🔥 GitHub趋势项目 (今日热门)\n\n"
    if github_repos:
        for i, repo in enumerate(github_repos, 1):
            briefing += f"""### {i}. {repo['name']}
- 📝 {repo['desc']}
- ⭐ {repo['stars']}

"""
    else:
        briefing += "- 暂无数据\n"
    
    briefing += """---

*简报由OpenClaw通过代理实时生成*  
*代理配置: 127.0.0.1:1080 (SOCKS5)*
"""
    
    # 保存文件
    filename = f"C:\\Users\\lucky\\projects\\my_project\\realtime_news_briefing_{datetime.now().strftime('%Y%m%d')}_{datetime.now().strftime('%H%M')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(briefing)
    
    print(f"\n✅ Briefing saved to: {filename}")
    print(f"\n=== 简报预览 ===")
    print(briefing[:800] + "...")
    
    return briefing

if __name__ == '__main__':
    print("=== 开始实时新闻获取 ===\n")
    generate_briefing()
