# '''
# Author: your name
# Date: 2024-07-05 12:02:34
# LastEditTime: 2024-07-05 12:02:35
# LastEditors: LAPTOP-22MC5HRI
# Description: In User Settings Edit
# FilePath: \openai\test\test_model\retrieverQA\crawler.py
# '''
from langchain_community.document_loaders.url_selenium import SeleniumURLLoader
from fake_useragent import UserAgent
from langchain_core.documents import Document
import logging, time, os, pickle, requests, uuid
from typing import List
from dotenv import load_dotenv
load_dotenv()
from langchain_community.document_transformers import BeautifulSoupTransformer
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from unstructured.partition.html import partition_html

logger = logging.getLogger(__name__)

class FBSeleniumURLLoader(SeleniumURLLoader):
    fb_url = 'https://mbasic.facebook.com/'
    texts_to_remove = ['封鎖此人','尋求支援或檢舉粉絲專頁','取消追蹤','發送訊息','更多', '·', '相片']
    locale = '&locale=zh_TW'
    post_url = ''
    fb_post = []
    
    def __init__(self, urls, arguments):
        # 过滤掉不包含 'facebook' 关键字的 URL，并将 'www' 部分替换为 'mbasic'
        filtered_urls = [url.replace('www', 'mbasic') for url in urls if 'facebook' in url]
        
        super().__init__(urls=filtered_urls, arguments=arguments)
        self.url_list = filtered_urls
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': arguments[0],
            'Accept-Language': 'zh-TW,zh;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Origin': 'https://mbasic.facebook.com',
            'Host': 'mbasic.facebook.com',
            'Refer': "https://mbasic.facebook.com/login.php?next=https%3A%2F%2Fmbasic.facebook.com%2F&refsrc=deprecated&_rdr",
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Request': '1'
        })
    
    def _login_and_save_cookies(self, driver):
        driver.get(self.fb_url)
        username_input = driver.find_element(By.NAME, 'email')
        password_input = driver.find_element(By.NAME, 'pass')
        username_input.send_keys(os.getenv('FB_USER'))
        password_input.send_keys(os.getenv('FB_PASSWORD'))
        password_input.send_keys(Keys.RETURN)
        time.sleep(5)
        
        with open('./facebook_cookies.pkl', 'wb') as file:
            pickle.dump(driver.get_cookies(), file)

        return self._load_cookies_and_entry()
    
    def _load_cookies_and_entry(self):
        if os.path.exists('./facebook_cookies.pkl'):
            with open('./facebook_cookies.pkl', 'rb') as file:
                cookies = pickle.load(file)
            for cookie in cookies:
                self.session.cookies.set(cookie['name'], cookie['value'])
        else:
            return self.__login_and_save_cookies()
    
    def __bs4_parse(self, content):
        return BeautifulSoup(content, features='html.parser')
    
    def __get_main_page(self, url):
        soup = self.__bs4_parse(self.session.get(url).content)
        div_root = soup.find('div', id='root')
        if div_root:
            text_content = div_root.get_text(separator='\n', strip=True)
        
        # 逐一替换要移除的文本內容
        for text_to_remove in self.texts_to_remove:
            text_content = text_content.replace(text_to_remove, '')
            
        # 找到所有的a標籤
        all_a_tags = div_root.find_all('a')
        href_value = None
        
        # 遍歷所有的a標籤，找到值為「動態時報」的a標籤
        for a_tag in all_a_tags:
            if a_tag.string == '動態時報':
                # 取得href屬性的值
                href_value = a_tag.get('href')
                break
        
        if href_value is not None:
            # 獲取貼文的網址
            self.post_url = f'{self.fb_url}{href_value}{self.locale}'
            self.__get_first_post_page()
            
        return text_content
    
    def __get_first_post_page(self):
        soup = self.__bs4_parse(self.session.get(self.post_url).content)

        # 使用 find_all 方法選取所有具有 class="story_body_container" 的 div 元素
        story_containers = soup.find_all('div', class_='story_body_container')
        # 遍歷找到的所有 story_body_container 元素
        for container in story_containers:
            self.fb_post.append({
                'postId': str(uuid.uuid4()),
                'post': container.get_text().strip()
            })
        
        # 找到所有的a標籤
        all_post_tags = soup.find_all('a')    
        
        if self.__check_more_post(all_post_tags):
            self.__get_rest_post_page()

        return self.fb_post
    
    def __get_rest_post_page(self):
        soup = self.__bs4_parse(self.session.get(self.post_url).content)
        
        # 使用 find_all 方法選取所有具有 class="story_body_container" 的 div 元素
        all_article = soup.find_all('article')

        # 遍歷找到的所有 story_body_container 元素
        for article in all_article:
            # 查找並移除 footer 標籤
            footer = article.find('footer')
            if footer:
                footer.decompose()
            
            self.fb_post.append({
                'postId': str(uuid.uuid4()),
                'post': article.get_text().strip()
            })
        
        # 找到所有的a標籤
        all_post_tags = soup.find_all('a')    
        
        if self.__check_more_post(all_post_tags):
            self.__get_rest_post_page()

        return self.fb_post
        
    
    def __check_more_post(self, all_post_tags):
        post_href_value = None

        # 遍歷所有的a標籤，找到值為「查看更多動態」的a標籤
        for post_tag in all_post_tags:
            if post_tag.string == '查看更多動態':
                # 取得href屬性的值
                post_href_value = post_tag.get('href')
                break
        else:
            # 如果遍歷完所有a標籤仍未找到'查看更多動態(最後一筆貼文)'
            self.post_url = ''
            print('未找到 "查看更多動態"')
            return False
        
        self.post_url = f'{self.fb_url}{post_href_value}{self.locale}'
        return True
    
    def scraping(self):
        try:
            for url in self.url_list:
                self._load_cookies_and_entry()
                self.__get_main_page(url)
        except:
            pass
    
    def load(self):
        
        pass
        
        # docs: List[Document] = list()
        # driver = self._get_driver()
        
        # if os.path.exists('./facebook_cookies.pkl'):
        #     self._load_cookies_and_login(driver)
        # else:
        #     self._login_and_save_cookies(driver)
        
        # time.sleep(5)
        
        # for url in self.urls:
        #     try:
        #         time.sleep(5)
        #         driver.get(url)
        #         time.sleep(5)
                
                
        #         # page_content = driver.page_source
        #         # elements = partition_html(text=page_content)
        #         # text = "\n\n".join([str(el) for el in elements])
        #         # metadata = self._build_metadata(url, driver)
        #         # docs.append(Document(page_content=text, metadata=metadata))
        #     except Exception as e:
        #         if self.continue_on_failure:
        #             logger.error(f"Error fetching or processing {url}, exception: {e}")
        #         else:
        #             raise e

        # driver.quit()
        # return docs

urls = [
    'https://www.facebook.com/FiedoraTW/?locale=zh_TW'
]

# # Load HTML
loader = FBSeleniumURLLoader(urls=urls, arguments=[f'user-agent={UserAgent().random}']).load()
print(loader)

# # Transform
# bs_transformer = BeautifulSoupTransformer()
# docs_transformed = bs_transformer.transform_documents(html, tags_to_extract=["div"])

# # Result
# docs_transformed[0].page_content[0:500]
# print(docs_transformed[0].page_content[0:500])









# # 创建 Session 对象
# session = requests.Session()

# # 设置 User-Agent
# user_agent = UserAgent().random
# session.headers.update({
#     'User-Agent':user_agent,
#     'Accept-Language':'zh-TW,zh;q=0.9',
#     'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
#     'Origin':'https://mbasic.facebook.com',
#     'Host': 'mbasic.facebook.com',
#     'Refer':"https://mbasic.facebook.com/login.php?next=https%3A%2F%2Fmbasic.facebook.com%2F&refsrc=deprecated&_rdr",
#     'Sec-Fetch-Mode':'navigate',
#     'Sec-Fetch-Dest':'document',
#     'Sec-Fetch-User':'?1',
#     'Upgrade-Insecure-Request':'1'
# })

# # 加载保存的 cookies
# with open('./facebook_cookies.pkl', 'rb') as file:
#     cookies = pickle.load(file)
#     for cookie in cookies:
#         session.cookies.set(cookie['name'], cookie['value'])

# # 发送请求
# fb_url = 'https://mbasic.facebook.com'
# url = 'https://mbasic.facebook.com/FiedoraTW?locale=zh_TW'
# response = session.get(url)
# time.sleep(5)

# texts_to_remove = ['封鎖此人','尋求支援或檢舉粉絲專頁','取消追蹤','發送訊息','更多', '·', '相片']

# # 输出响应
# if response.status_code == 200:
#     soup = BeautifulSoup(response.content, features='html.parser')
#     div_root = soup.find('div', id='root')
    
#     if div_root:
#         text_content = div_root.get_text(separator='\n', strip=True)
        
#         # 逐一替换要移除的文本內容
#         for text_to_remove in texts_to_remove:
#             text_content = text_content.replace(text_to_remove, '')

#         #------------------ 獲取商家第一頁貼文 -----------------#
        
#         # 找到所有的a標籤
#         all_a_tags = div_root.find_all('a')

#         # 遍歷所有的a標籤，找到值為「動態時報」的a標籤
#         for a_tag in all_a_tags:
#             if a_tag.string == '動態時報':
#                 # 取得href屬性的值
#                 href_value = a_tag.get('href')
        
#         # 獲取貼文的網址
#         post_url = f'{fb_url}{href_value}&locale=zh_TW'
#         # 發送GET請求並獲取響應
#         response2 = session.get(post_url)

#         # 檢查響應狀態碼，確保請求成功
#         if response.status_code == 200:
#             soup2 = BeautifulSoup(response2.content, features='html.parser')
            
#             # 找到所有的a標籤
#             all_post_tags = soup2.find_all('a')
#             post_href_value = None

#             # 遍歷所有的a標籤，找到值為「查看更多動態」的a標籤
#             for post_tag in all_post_tags:
#                 if post_tag.string == '查看更多動態':
#                     # 取得href屬性的值
#                     post_href_value = post_tag.get('href')
#                     break
#             else:
#                 # 如果遍歷完所有a標籤仍未找到'查看更多動態(最後一筆貼文)'
#                 print('未找到 "查看更多動態"')
            
#             # 創建一個空列表來存放整理後的貼文資料
#             fan_page_posts = []
            
#             # 使用 find_all 方法選取所有具有 class="story_body_container" 的 div 元素
#             story_containers = soup2.find_all('div', class_='story_body_container')
            
#             # 遍歷找到的所有 story_body_container 元素
#             for container in story_containers:
#                 fan_page_posts.append({
#                     'postId': str(uuid.uuid4()),
#                     'post': container.get_text().strip()
#                 })
            
#             #--------------------------重複找尋貼文---------------------------#

#             # 獲取貼文的網址
#             more_post_url = f'{fb_url}{post_href_value}&locale=zh_TW'
#             # 發送GET請求並獲取響應
#             response3 = session.get(more_post_url)
#             time.sleep(5)
#             soup3 = BeautifulSoup(response3.content, features='html.parser')
            
#             # 找到所有的a標籤
#             all_more_post_tags = soup3.find_all('a')
#             more_post_href_value = None
            
#             # 使用 find_all 方法選取所有具有 class="story_body_container" 的 div 元素
#             all_article = soup3.find_all('article')
            
#             # 遍歷找到的所有 story_body_container 元素
#             for article in all_article:
#                 # 查找並移除 footer 標籤
#                 footer = article.find('footer')
#                 if footer:
#                     footer.decompose()
                
#                 fan_page_posts.append({
#                     'postId': str(uuid.uuid4()),
#                     'post': article.get_text().strip()
#                 })
#             print('---------------------------------------------')
#             print('secoond result: ', fan_page_posts)
#         else:
#             print(f"請求失敗，狀態碼：{response.status_code}")
#     else:
#         print('找不到 id 为 root 的 div 元素')
# else:
#     print(f"请求失败，状态码：{response.status_code}")