import requests
from bs4 import BeautifulSoup
import schedule
import time
from datetime import datetime
import json
import logging
import os
import sys
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent
import requests.exceptions

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('news_bot.log'),
        logging.StreamHandler()
    ]
)

def load_config():
    """加载配置文件"""
    try:
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                return json.load(f)
        else:
            logging.error("配置文件 config.json 不存在")
            sys.exit(1)
    except Exception as e:
        logging.error(f"加载配置文件失败: {str(e)}")
        sys.exit(1)

# 加载配置
config = load_config()
SERVER_CHAN_KEY = config.get('server_chan_key')

if not SERVER_CHAN_KEY or SERVER_CHAN_KEY == "YOUR_SERVER_CHAN_KEY_HERE":
    logging.error("请在 config.json 中设置有效的 Server酱 SendKey")
    sys.exit(1)

class ProxyPool:
    def __init__(self):
        self.proxies = []
        self.current_index = 0
        self.load_proxies()
        
    def load_proxies(self):
        """从配置文件加载代理列表"""
        try:
            if os.path.exists('proxies.json'):
                with open('proxies.json', 'r') as f:
                    self.proxies = json.load(f)
            else:
                # 默认代理列表
                self.proxies = [
                    {
                        "http": "http://127.0.0.1:7890",
                        "https": "http://127.0.0.1:7890"
                    },
                    {
                        "http": "socks5://127.0.0.1:1080",
                        "https": "socks5://127.0.0.1:1080"
                    }
                ]
                # 保存默认代理配置
                with open('proxies.json', 'w') as f:
                    json.dump(self.proxies, f, indent=2)
        except Exception as e:
            logging.error(f"加载代理配置失败: {str(e)}")
            self.proxies = []

    def get_proxy(self):
        """获取下一个代理"""
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy

    def test_proxy(self, proxy):
        """测试代理是否可用"""
        try:
            response = requests.get('https://www.google.com', 
                                 proxies=proxy, 
                                 timeout=10)
            return response.status_code == 200
        except:
            return False

    def get_working_proxy(self):
        """获取一个可用的代理"""
        if not self.proxies:
            return None
            
        # 尝试所有代理
        for _ in range(len(self.proxies)):
            proxy = self.get_proxy()
            if self.test_proxy(proxy):
                return proxy
        return None

class NewsBot:
    def __init__(self, push_time="08:00"):
        self.push_time = push_time
        self.news_sources = {
            '通信世界': 'http://www.cww.net.cn/news/list/1',
            '通信产业网': 'http://www.ccidcom.com/',
            'C114通信网': 'http://www.c114.com.cn/news/',
            '广州中考': 'http://www.gzzk.cn/',
            'AI应用': 'https://www.leiphone.com/category/ai',
            '谷歌新闻': 'https://news.google.com/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pKVHlnQVAB'
        }
        self.ua = UserAgent()
        self.proxy_pool = ProxyPool()
        self.setup_driver()
        
    def setup_driver(self):
        """设置Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={self.ua.random}')
        
        # 添加代理设置
        proxy = self.proxy_pool.get_working_proxy()
        if proxy:
            if 'http' in proxy:
                chrome_options.add_argument(f'--proxy-server={proxy["http"]}')
            elif 'socks5' in proxy:
                chrome_options.add_argument(f'--proxy-server={proxy["socks5"]}')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
    def get_news_from_cww(self):
        """从通信世界获取新闻"""
        try:
            self.driver.get(self.news_sources['通信世界'])
            wait = WebDriverWait(self.driver, 10)
            news_items = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.news-list li'))
            )
            
            news_list = []
            for item in news_items[:5]:
                title = item.find_element(By.CSS_SELECTOR, 'a').text
                link = item.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                date = item.find_element(By.CSS_SELECTOR, '.time').text
                news_list.append({
                    'title': title,
                    'link': link,
                    'date': date,
                    'source': '通信世界'
                })
            return news_list
        except Exception as e:
            logging.error(f"从通信世界获取新闻失败: {str(e)}")
            return []

    def get_news_from_ccidcom(self):
        """从通信产业网获取新闻"""
        try:
            self.driver.get(self.news_sources['通信产业网'])
            wait = WebDriverWait(self.driver, 10)
            news_items = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.news-list li'))
            )
            
            news_list = []
            for item in news_items[:5]:
                title = item.find_element(By.CSS_SELECTOR, 'a').text
                link = item.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                date = item.find_element(By.CSS_SELECTOR, '.time').text
                news_list.append({
                    'title': title,
                    'link': link,
                    'date': date,
                    'source': '通信产业网'
                })
            return news_list
        except Exception as e:
            logging.error(f"从通信产业网获取新闻失败: {str(e)}")
            return []

    def get_news_from_gzzk(self):
        """从广州中考网获取新闻"""
        try:
            self.driver.get(self.news_sources['广州中考'])
            wait = WebDriverWait(self.driver, 10)
            news_items = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.news-list li'))
            )
            
            news_list = []
            for item in news_items[:5]:
                title = item.find_element(By.CSS_SELECTOR, 'a').text
                link = item.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                date = item.find_element(By.CSS_SELECTOR, '.time').text
                news_list.append({
                    'title': title,
                    'link': link,
                    'date': date,
                    'source': '广州中考'
                })
            return news_list
        except Exception as e:
            logging.error(f"从广州中考网获取新闻失败: {str(e)}")
            return []

    def get_news_from_ai(self):
        """从AI应用网获取新闻"""
        try:
            self.driver.get(self.news_sources['AI应用'])
            wait = WebDriverWait(self.driver, 10)
            news_items = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.word'))
            )
            
            news_list = []
            for item in news_items[:5]:
                title = item.find_element(By.CSS_SELECTOR, 'h3 a').text
                link = item.find_element(By.CSS_SELECTOR, 'h3 a').get_attribute('href')
                date = item.find_element(By.CSS_SELECTOR, '.time').text
                news_list.append({
                    'title': title,
                    'link': link,
                    'date': date,
                    'source': 'AI应用'
                })
            return news_list
        except Exception as e:
            logging.error(f"从AI应用网获取新闻失败: {str(e)}")
            return []

    def get_news_from_google(self):
        """从谷歌新闻获取新闻"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self.driver.get(self.news_sources['谷歌新闻'])
                wait = WebDriverWait(self.driver, 10)
                
                # 等待新闻列表加载
                news_items = wait.until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'article'))
                )
                
                news_list = []
                for item in news_items[:5]:
                    try:
                        # 获取标题和链接
                        title_element = item.find_element(By.CSS_SELECTOR, 'h3 a')
                        title = title_element.text
                        link = title_element.get_attribute('href')
                        
                        # 获取来源和时间
                        source_element = item.find_element(By.CSS_SELECTOR, 'div[class*="vr1PYe"]')
                        source = source_element.text
                        
                        time_element = item.find_element(By.CSS_SELECTOR, 'time')
                        date = time_element.get_attribute('datetime')
                        
                        # 获取新闻摘要
                        try:
                            summary = item.find_element(By.CSS_SELECTOR, 'div[class*="GI74Re"]').text
                        except:
                            summary = "暂无摘要"
                        
                        news_list.append({
                            'title': title,
                            'link': link,
                            'date': date,
                            'source': f'谷歌新闻 - {source}',
                            'summary': summary
                        })
                    except Exception as e:
                        logging.error(f"处理谷歌新闻项时出错: {str(e)}")
                        continue
                
                return news_list
                
            except Exception as e:
                retry_count += 1
                logging.error(f"从谷歌新闻获取新闻失败 (尝试 {retry_count}/{max_retries}): {str(e)}")
                
                # 如果失败，尝试更换代理
                if retry_count < max_retries:
                    proxy = self.proxy_pool.get_working_proxy()
                    if proxy:
                        self.driver.quit()
                        self.setup_driver()
                    time.sleep(2)  # 等待一段时间后重试
                
        return []

    def send_to_wechat(self, news_list):
        """发送新闻到微信"""
        if not news_list:
            logging.warning("没有新闻可发送")
            return

        # 构建消息内容
        message = f"📰 每日新闻推送 ({datetime.now().strftime('%Y-%m-%d')})\n\n"
        
        for news in news_list:
            message += f"📌 {news['title']}\n"
            message += f"🔗 {news['link']}\n"
            message += f"📅 {news['date']}\n"
            message += f"📢 {news['source']}\n"
            if 'summary' in news:
                message += f"📝 {news['summary']}\n"
            message += "\n"

        # 发送到Server酱
        try:
            response = requests.post(
                f'https://sctapi.ftqq.com/{SERVER_CHAN_KEY}.send',
                data={
                    'title': f'每日新闻推送 ({datetime.now().strftime("%Y-%m-%d")})',
                    'desp': message
                }
            )
            if response.status_code == 200:
                logging.info("新闻推送成功")
            else:
                logging.error(f"新闻推送失败: {response.text}")
        except Exception as e:
            logging.error(f"发送新闻到微信失败: {str(e)}")

    def collect_and_send_news(self):
        """收集并发送新闻"""
        logging.info("开始收集新闻...")
        
        # 收集所有来源的新闻
        all_news = []
        all_news.extend(self.get_news_from_cww())
        all_news.extend(self.get_news_from_ccidcom())
        all_news.extend(self.get_news_from_gzzk())
        all_news.extend(self.get_news_from_ai())
        all_news.extend(self.get_news_from_google())
        
        # 按日期排序
        all_news.sort(key=lambda x: x['date'], reverse=True)
        
        # 发送到微信
        self.send_to_wechat(all_news)
        
        logging.info("新闻收集和发送完成")

    def run(self):
        """运行定时任务"""
        # 设置定时运行
        schedule.every().day.at(self.push_time).do(self.collect_and_send_news)
        
        # 立即运行一次（测试用）
        self.collect_and_send_news()
        
        # 保持程序运行
        while True:
            schedule.run_pending()
            time.sleep(60)

def create_startup_script():
    """创建开机启动脚本"""
    if sys.platform == 'win32':
        # Windows系统
        startup_script = f'''@echo off
cd /d {os.path.dirname(os.path.abspath(__file__))}
python {os.path.basename(__file__)}
'''
        startup_path = os.path.join(os.getenv('APPDATA'), 'Microsoft\\Windows\\Start Menu\\Programs\\Startup\\news_bot.bat')
        with open(startup_path, 'w') as f:
            f.write(startup_script)
        logging.info(f"开机启动脚本已创建: {startup_path}")
    else:
        # Linux/Mac系统
        startup_script = f'''#!/bin/bash
cd {os.path.dirname(os.path.abspath(__file__))}
python3 {os.path.basename(__file__)}
'''
        startup_path = os.path.expanduser('~/.config/autostart/news_bot.desktop')
        os.makedirs(os.path.dirname(startup_path), exist_ok=True)
        with open(startup_path, 'w') as f:
            f.write(f'''[Desktop Entry]
Type=Application
Name=News Bot
Exec={os.path.abspath(__file__)}
Terminal=false
''')
        os.chmod(startup_path, 0o755)
        logging.info(f"开机启动脚本已创建: {startup_path}")

if __name__ == "__main__":
    # 创建开机启动脚本
    create_startup_script()
    
    # 获取用户输入的推送时间
    push_time = input("请输入推送时间（格式：HH:MM，直接回车默认为08:00）：").strip()
    if not push_time:
        push_time = "08:00"
    
    # 启动机器人
    bot = NewsBot(push_time=push_time)
    bot.run() 