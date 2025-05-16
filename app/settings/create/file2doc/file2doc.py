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
            # 發送 HTTP 請求
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # 檢查請求是否成功

            # 解析 HTML 內容
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除不必要的標籤（如 script, style）
            for element in soup(['script', 'style', 'header', 'footer', 'nav']):
                element.decompose()

            # 提取純文本
            text = soup.get_text(separator='\n', strip=True)

            # 使用 txt_spliter 進行文本分割
            return self.txt_spliter().create_documents([text])
        except Exception as e:
            file2doc_logger.get_logger().error(f'html2doc fail for {url}: {e}')
            return None
