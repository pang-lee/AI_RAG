# '''
# Author: pang-lee
# Date: 2024-08-28 14:34:48
# LastEditTime: 2024-08-28 14:34:49
# LastEditors: LAPTOP-22MC5HRI
# Description: In User Settings Edit
# FilePath: \openai\application\settings\create\file2doc\file2doc.py
# '''
import os, json, uuid
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import Docx2txtLoader
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders.csv_loader import CSVLoader
from ...logger import Logger
file2doc_logger = Logger(name='file2doc_logger')

class file2doc:
    def __init__(self, docs):
        file2doc_logger.get_logger().info(f'Initializing file2doc with docs: {docs}')
        self.docs = docs
        # self.docs = [os.path.join( os.path.abspath(__file__), '..', 'test_doc.txt')]

    def process_docs(self):
        transfer = []
        for doc in self.docs:
            if doc.endswith('.txt'):
                transfer.append({'file_id': str(uuid.uuid4()), 'file_content': self.txt2doc(doc)})
            elif doc.endswith('.csv'):
                transfer.append({'file_id': str(uuid.uuid4()), 'file_content': self.csv2doc(doc)})
            elif doc.endswith('.pdf'):
                transfer.append({'file_id': str(uuid.uuid4()), 'file_content': self.pdf2doc(doc)})
            elif doc.endswith('.doc') or doc.endswith('.docx'):
                transfer.append({'file_id': str(uuid.uuid4()), 'file_content': self.docx2doc(doc)})
            elif doc.endswith('.xls') or doc.endswith('.xlsx'):
                transfer.append({'file_id': str(uuid.uuid4()), 'file_content': self.excel2doc(doc)})
            elif doc.startswith('http://') or doc.startswith('https://'):
                transfer.append({'file_id': str(uuid.uuid4()), 'file_content': self.html2doc(doc)})
            else:
                file2doc_logger.get_logger().info(f"Unsupported file type: {doc}")
                return None
        
        try:
            json_data = []
            for item in transfer:
                file_id = item['file_id']
                file_split_content = []
                for doc in item['file_content']:
                    file_split_content.append({
                        "doc_id": str(uuid.uuid4()),  # 添加 UUID 給每個 Document
                        "page_content": doc.page_content
                    })
                
                json_data.append({
                    "file_id": file_id,
                    "file_split_content": file_split_content
                })

            return json.dumps(json_data, ensure_ascii=False, indent=4)
        except Exception as e:
            file2doc_logger.get_logger().error(f"Except in process_doc: {e}")
            return None

    def read_file(self, file_path):
        if not os.path.exists(file_path):
            file2doc_logger.get_logger().info(f"File does not exist: {file_path}")
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                doc_content = f.read()
            
            return doc_content
        
        except Exception as e:
            file2doc_logger.get_logger().error(f"Error reading {file_path}: {e}")
            return None

    def txt_spliter(self):
        return RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=200,
                separators=[
                "\n\n",
                "\n",
                " ",
                ".",
                ",",
                "\u200b",  # Zero-width space
                "\uff0c",  # Fullwidth comma
                "\u3001",  # Ideographic comma
                "\uff0e",  # Fullwidth full stop
                "\u3002",  # Ideographic full stop
                "",
            ],
        )

    def txt2doc(self, doc):
        try:
            doc_content = self.read_file(doc)
            
            return self.txt_spliter().create_documents([doc_content])
        except Exception as e:
            file2doc_logger.get_logger().error(f'txt2doc fail: {e}')
            return None
        
    def csv2doc(self, doc):
        try:
            return CSVLoader(file_path=doc).load()
        except Exception as e:
            file2doc_logger.get_logger().error(f'csv2doc fail: {e}')
            return None
        
    def pdf2doc(self, doc):
        try:
            return PyMuPDFLoader(doc, extract_images=True).load()
        except Exception as e:
            file2doc_logger.get_logger().error(f'pdf2doc fail: {e}')
            return None

    def docx2doc(self, doc):
        try:
            data = Docx2txtLoader(doc).load()

            return self.txt_spliter().split_documents(data)
        except Exception as e:
            file2doc_logger.get_logger().error(f"Failed to process {doc_path}: {e}")
            return None

    def excel2doc(self, doc):
        try:
            # 讀取 Excel 檔案
            df = pd.read_excel(doc, engine='openpyxl')
            
            # 將表格內容轉為字串，每行作為一個段落
            content = ""
            for index, row in df.iterrows():
                # 格式化每行，例如 "Name: Alice | Age: 25 | City: Taipei"
                row_content = " | ".join([f"{col}: {val}" for col, val in row.items()])
                content += row_content + "\n\n"  # 每行後加兩個換行符，符合 txt_spliter 的分隔符
            
            # 使用 txt_spliter 切割內容
            documents = self.txt_spliter().create_documents([content])
            
            # 為每個 Document 添加檔案路徑的元數據
            for doc in documents:
                doc.metadata["source"] = doc
                
            return documents
        except Exception as e:
            file2doc_logger.get_logger().error(f'excel2doc fail: {e}')
            return None

    def html2doc(self, url):
        try:
            # 設定 Chrome 為無頭模式（可選）
            options = Options()
            options.add_argument("--headless=new")  # 使用新版的 Headless 模式

            # 初始化 WebDriver（Selenium 4.6+ 會自動管理驅動程式）
            driver = webdriver.Chrome(options=options)

            try:
                # 開啟目標網頁
                driver.get(url)  # 請將此處的 URL 替換為您要爬取的網頁

                # 等待 <main> 元素出現在 DOM 中
                wait = WebDriverWait(driver, 10)
                main_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))

                # 取得 <main> 元素的 HTML 內容
                main_html = main_element.get_attribute("innerHTML")

                # 使用 BeautifulSoup 解析 HTML 並提取純文本
                soup = BeautifulSoup(main_html, "html.parser")
                text = soup.get_text(separator='\n', strip=True)

                return self.txt_spliter().create_documents([text])

            finally:
                # 關閉瀏覽器
                driver.quit()

        except Exception as e:
            file2doc_logger.get_logger().error(f'html2doc fail for {url}: {e}')
            return None
