# '''
# Author: pang, lee
# Date: 2024-07-04 15:58:20
# LastEditTime: 2024-07-04 15:58:20
# LastEditors: LAPTOP-22MC5HRI
# Description: The base of Embedding
# FilePath: \openai\template\create\embeding\EmbedBase.py
# '''
from abc import ABC
from ..file2doc.file2doc import file2doc
import os, json
import torch
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from ...logger import Logger
logger = Logger(name='embeddings_logger')

class BaseEmbedding(ABC):
    def __init__(self, model, dimension, embedding):
        self.dimension = dimension
        self.embeddings = embedding
        self.log = logger.get_logger()
        self.log.info(f"\n\nCurrent Embedding Model is: {model}")

    def compute_dimension(self, text: str) -> int: # 假设这里是根据文本计算维度的逻辑，这里简单地返回文本长度作为示例
        return len(text)
    
    def transfer_file2doc(self, docs):
        return file2doc(docs).process_docs()

    def embed_vector_db(self, data):
        try:
            manufacturer = os.path.join('./', data['namespace'], data['ID'], 'vectorstore', data['data']['aics_vdb_code'])
        
            if not os.path.exists(manufacturer):
                self.log.error(f"The {data['namespace']}/{data['ID']} is not exist")
                return False, []

            documents, ids = [], []

            for item in json.loads(data['data']['files_docs']):
                for doc in item['file_split_content']:
                    document = Document(
                        id=doc['doc_id'],
                        page_content=doc['page_content']
                    )
                    documents.append(document)
                    ids.append(doc['doc_id'])

            self.log.info(f"Currently transfering {data['namespace']}/{data['ID']}/vectorstore with {data['data']['aics_vdb_code']} data")

            # 判斷namespace/id/vectorstore裡面是否已經有向量庫資料了
            if any(file.endswith('.pkl') for file in os.listdir(manufacturer)) and any(file.endswith('.faiss') for file in os.listdir(manufacturer)):
                # 加載現有向量庫
                vector_store = FAISS.load_local(
                    folder_path=manufacturer,
                    embeddings=self.embeddings,
                    index_name=data['data']['aics_vdb_code'],
                    allow_dangerous_deserialization=True
                )
                self.log.info(f"Successfully loaded existing FAISS vector store: {manufacturer}/{data['data']['aics_vdb_code']}")

                # 增量添加新的 documents
                vector_store.add_documents(documents=documents, ids=ids)
                self.log.info(f"Added {len(documents)} new documents to FAISS vector store")

            else: # 沒有向量庫資料, 初始向量資料庫            
                vector_store = FAISS.from_documents(documents, embedding=self.embeddings, ids=ids)
                self.log.info(f"FAISS Init And Trnasfer {data['namespace']}/{data['ID']}/vectorstore/{data['data']['aics_vdb_code']} data in vectorstore")
            
            # 保存向量庫
            vector_store.save_local(folder_path=manufacturer, index_name=data['data']['aics_vdb_code'])
            self.log.info(f"FAISS vector store saved: {manufacturer}/{data['data']['aics_vdb_code']}")

            return self.get_all_documents(manufacturer, data['data']['aics_vdb_code'])

        except Exception as e:
            self.log.error(f'The embed vector db error: {e}')
            return False, []

    def delete_datasource(self, data):
        try:
            manufacturer = os.path.join('./', data['namespace'], data['ID'], 'vectorstore', data['data']['aics_vdb_code'])

            if not os.path.exists(manufacturer):
                self.log.error(f"when delete datasource, the {data['namespace']}/{data['ID']} is not exist")
                return False, []

            if not any(file.endswith('.pkl') for file in os.listdir(manufacturer)) and any(file.endswith('.faiss') for file in os.listdir(manufacturer)):
                self.log.error(f"when delete datasource from vectordb, the {manufacturer} is not exist")
                return False, []

            # 加載 FAISS 向量庫
            vector_store = FAISS.load_local(
                folder_path=manufacturer,
                embeddings=self.embeddings,  # 假設 self.embeddings 是創建時的嵌入函數
                index_name=data['data']['aics_vdb_code'],
                allow_dangerous_deserialization=True  # 如果信任來源，設置為 True
            )
            self.log.info(f"Successfully loaded FAISS vector store: {manufacturer}/{data['data']['aics_vdb_code']}")
            
            ids = data["ids"]
            # 檢查 ids 是否有效
            if not ids:
                self.log.warning("No IDs provided for deletion")
                return False, []

            # 檢查哪些 ID 存在於向量庫
            existing_ids = [doc_id for doc_id in ids if doc_id in vector_store.docstore._dict]
            missing_ids = [doc_id for doc_id in ids if doc_id not in vector_store.docstore._dict]
            if missing_ids:
                self.log.warning(f"IDs not found in vector store: {missing_ids}")

            if not existing_ids:
                self.log.info("No valid IDs to delete")
                return self.get_all_documents(manufacturer, data['data']['aics_vdb_code'])

            # 刪除指定 IDs
            vector_store.delete(ids=existing_ids)
            self.log.info(f"Deleted IDs: {existing_ids}")

            # 保存更新後的向量庫
            vector_store.save_local(folder_path=manufacturer, index_name=data['data']['aics_vdb_code'])
            self.log.info(f"FAISS Vector store updated and saved: {manufacturer}/{data['data']['aics_vdb_code']}")

            return self.get_all_documents(manufacturer, data['data']['aics_vdb_code'])
        
        except Exception as e:
            self.log.error(f'Delete datasource from vectordb error: {e}')
            return False, []

    def get_all_documents(self, manufacturer, index_name):
        try:
            # 檢查路徑是否存在
            if not os.path.exists(manufacturer):
                self.log.error(f"Vector store path does not exist: {manufacturer}")
                return False, []

            # 檢查向量庫文件
            pkl_path = os.path.join(manufacturer, f"{index_name}.pkl")
            faiss_path = os.path.join(manufacturer, f"{index_name}.faiss")
            if not (os.path.exists(pkl_path) and os.path.exists(faiss_path)):
                self.log.error(f"FAISS Vector store files not found in {manufacturer}")
                return False, []

            # 加載向量庫
            vector_store = FAISS.load_local(
                folder_path=manufacturer,
                embeddings=self.embeddings,
                index_name=index_name,
                allow_dangerous_deserialization=True  # 如果信任來源，設置為 True
            )
            self.log.info(f"Successfully loaded FAISS vector store: {manufacturer}/{index_name}")

            # 轉換為 array of dict
            array_of_dict = [
                {
                    "doc_id": doc_id,
                    "page_content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc_id, doc in vector_store.docstore._dict.items()
            ]
            self.log.info(f"Retrieved {len(array_of_dict)} documents from FAISS vector store")

            return True, array_of_dict

        except Exception as e:
            self.log.error(f"Failed to retrieve documents from vector store: {e}")
            return False, []


