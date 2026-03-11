import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
from pathlib import Path
import time
import re

class GZZhongkaoCrawler:
    def __init__(self):
        self.base_url = "https://gzzk.gz.gov.cn/zkzz/zkxx/lnfs/"
        self.output_dir = Path('zhongkao_data')
        self.output_dir.mkdir(exist_ok=True)
        self.setup_logging()
        
        # 请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        self.target_batches = ['第二批', '第三批', '二批', '三批']
        self.exclude_keywords = ['特长', '艺术', '体育', '高水平运动队']
        
    def setup_logging(self):
        logging.basicConfig(
            filename=self.output_dir / 'crawler.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            encoding='utf-8'  # 添加编码设置
        )
        
    def get_page_content(self, url, retries=3):
        """获取页面内容，支持重试"""
        for i in range(retries):
            try:
                response = requests.get(url, headers=self.headers)
                response.encoding = 'utf-8'
                return response.text
            except Exception as e:
                logging.error(f"第{i+1}次获取页面失败: {str(e)}")
                if i < retries - 1:
                    time.sleep(2)  # 失败后等待
                continue
        return None
            
    def parse_score_table(self, html):
        try:
            soup = BeautifulSoup(html, 'html.parser')
            # 1. 首先查找所有table
            tables = soup.find_all('table')
            
            # 2. 遍历每个table查找符合条件的
            for table in tables:
                headers = [th.text.strip() for th in table.find_all(['th', 'td'])]
                if '学校名称' in headers and '最低分' in headers:
                    # 找到目标表格
                    return self._extract_table_data(table)
                    
            logging.warning("未找到包含录取分数的表格")
            return None
            
        except Exception as e:
            logging.error(f"解析表格失败: {str(e)}")
            return None

    def _extract_table_data(self, table):
        try:
            data = []
            rows = table.find_all('tr')
            
            # 获取表头
            headers = [th.text.strip() for th in rows[0].find_all(['th', 'td'])]
            logging.info(f"表头: {headers}")
            
            # 提取数据行
            for row in rows[1:]:
                cols = row.find_all(['td', 'th'])
                if cols:
                    row_data = [col.text.strip() for col in cols]
                    if len(row_data) == len(headers):
                        data.append(row_data)
                        
            if data:
                df = pd.DataFrame(data, columns=headers)
                logging.info(f"成功提取数据: {len(data)}行")
                return df
            else:
                logging.warning("未提取到有效数据行")
                return None
                
        except Exception as e:
            logging.error(f"提取表格数据失败: {str(e)}")
            return None
        
    def extract_year_batch(self, title):
        """从标题中提取年份和批次信息，过滤非目标批次"""
        year_pattern = r'(\d{4})年'
        batch_pattern = r'[第]?([一二三四五六七八九十]+)批'
        
        # 检查是否包含需要排除的关键词
        if any(keyword in title for keyword in self.exclude_keywords):
            return None
            
        year = re.search(year_pattern, title)
        batch = re.search(batch_pattern, title)
        
        if not batch:
            return None
            
        # 转换批次为标准格式
        batch_text = f"第{batch.group(1)}批"
        if batch_text not in self.target_batches:
            return None
            
        return {
            'year': year.group(1) if year else None,
            'batch': batch_text
        }
        
    def get_page_links(self):
        """获取所有页面的链接"""
        all_links = []
        page = 1
        
        while True:
            if page == 1:
                url = self.base_url
            else:
                url = f"{self.base_url}index_{page}.html"
                
            logging.info(f"正在获取第{page}页数据")
            page_content = self.get_page_content(url)
            
            if not page_content:
                if page > 1:  # 第一页失败直接退出
                    break
                else:
                    raise Exception("获取第一页失败")
                    
            soup = BeautifulSoup(page_content, 'html.parser')
            links = soup.find_all('a', href=re.compile(r'lnfs'))
            
            if not links:
                break
                
            all_links.extend(links)
            page += 1
            time.sleep(2)  # 避免请求过快
            
        return all_links
        
    def run(self):
        """运行爬虫"""
        try:
            # 获取所有页面的链接
            links = self.get_page_links()
            if not links:
                logging.error("未获取到任何链接")
                return
                
            logging.info(f"共获取到 {len(links)} 个链接")
            all_data = []
            
            for link in links:
                title = link.text.strip()
                logging.info(f"处理链接: {title}")
                
                # 提取年份和批次信息
                year_batch = self.extract_year_batch(title)
                if not year_batch:
                    logging.info(f"跳过非目标批次: {title}")
                    continue
                
                if not year_batch['year'] or int(year_batch['year']) < 2020:
                    logging.info(f"跳过非目标年份: {title}")
                    continue
                
                url = link.get('href')
                if not url.startswith('http'):
                    url = self.base_url + url
                
                logging.info(f"开始获取数据: {year_batch['year']}年 {year_batch['batch']}")
                page_content = self.get_page_content(url)
                if page_content:
                    df = self.parse_score_table(page_content)
                    if df is not None:
                        df['年份'] = year_batch['year']
                        df['批次'] = year_batch['batch']
                        all_data.append(df)
                        logging.info(f"成功获取数据: {df.shape[0]}行")
                    else:
                        logging.warning(f"解析表格失败: {title}")
                
                time.sleep(2)  # 避免请求过快
            
            # 合并并保存数据
            if all_data:
                final_df = pd.concat(all_data, ignore_index=True)
                
                # 按年度和批次保存
                years = final_df['年份'].unique()
                for year in sorted(years, reverse=True):
                    year_data = final_df[final_df['年份'] == year]
                    batches = year_data['批次'].unique()
                    for batch in sorted(batches):
                        batch_data = year_data[year_data['批次'] == batch]
                        filename = f"{year}年_{batch}_录取分数.xlsx"
                        batch_data.to_excel(self.output_dir / filename, index=False)
                        logging.info(f"保存文件: {filename}")
                
                # 按学校分类保存
                if '学校名称' in final_df.columns:
                    school_grouped = final_df.groupby('学校名称')
                    for school, data in school_grouped:
                        filename = f"{school}_历年普通批录取分数.xlsx"
                        data.sort_values(['年份', '批次'], ascending=[False, True]).to_excel(
                            self.output_dir / filename, index=False
                        )
                        logging.info(f"保存学校数据: {filename}")
                
                logging.info("数据提取完成")
            else:
                logging.warning("未获取到任何数据")
                
        except Exception as e:
            logging.error(f"爬虫运行失败: {str(e)}")
            raise

if __name__ == "__main__":
    crawler = GZZhongkaoCrawler()
    crawler.run()