# '''
# Author: pang, lee
# Date: 2024-07-04 15:54:26
# LastEditTime: 2024-07-04 15:54:26
# LastEditors: LAPTOP-22MC5HRI
# Description: Openai Embedding
# FilePath: \openai\template\create\embeding\openai_embed.py
# '''
import os, json
from .EmbedBase import BaseEmbedding
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from ...logger import Logger
from dotenv import load_dotenv
load_dotenv()
openai_embed_logger = Logger(name='openai_embeddings_logger')

class OpenaiEmbeddings(BaseEmbedding):
    def __init__(self, model: str):
        dimension = 1536 if model in ['text-embedding-ada-002', 'text-embedding-3-small'] else 3072
        self.embeddings = OpenAIEmbeddings(model=model)
        super().__init__(model, dimension)
    
    def transfer_file2doc(self, docs):
        return super().transfer_file2doc(docs=docs)
        
    def embed_vector_db(self, data):
        try:
            manufacturer = os.path.join('./', data['namespace'], data['ID'], 'vectorstore', data['data']['aics_vdb_code'])
        
            if not os.path.exists(manufacturer):
                openai_embed_logger.get_logger().error(f"The {data['namespace']}/{data['ID']} is not exist")
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

            openai_embed_logger.get_logger().info(f"Currently transfering {data['namespace']}/{data['ID']}/vectorstore with {data['data']['aics_vdb_code']} data")

            # 判斷namespace/id/vectorstore裡面是否已經有向量庫資料了
            if any(file.endswith('.pkl') for file in os.listdir(manufacturer)) and any(file.endswith('.faiss') for file in os.listdir(manufacturer)):
                # 加載現有向量庫
                vector_store = FAISS.load_local(
                    folder_path=manufacturer,
                    embeddings=self.embeddings,
                    index_name=data['data']['aics_vdb_code'],
                    allow_dangerous_deserialization=True
                )
                openai_embed_logger.get_logger().info(f"Successfully loaded existing FAISS vector store: {manufacturer}/{data['data']['aics_vdb_code']}")

                # 增量添加新的 documents
                vector_store.add_documents(documents=documents, ids=ids)
                openai_embed_logger.get_logger().info(f"Added {len(documents)} new documents to FAISS vector store")

            else: # 沒有向量庫資料, 初始向量資料庫            
                vector_store = FAISS.from_documents(documents, embedding=self.embeddings, ids=ids)
                openai_embed_logger.get_logger().info(f"Trnasfer {data['namespace']}/{data['ID']}/vectorstore/{data['data']['aics_vdb_code']} data is in vectorstore")
            
            # 保存向量庫
            vector_store.save_local(folder_path=manufacturer, index_name=data['data']['aics_vdb_code'])
            openai_embed_logger.get_logger().info(f"FAISS vector store saved: {manufacturer}/{data['data']['aics_vdb_code']}")

            return self.get_all_documents(manufacturer, data['data']['aics_vdb_code'])

        except Exception as e:
            openai_embed_logger.get_logger().error(f'The embed vector db error: {e}')
            return False, []


    def delete_datasource(self, data):
        try:
            manufacturer = os.path.join('./', data['namespace'], data['ID'], 'vectorstore', data['data']['aics_vdb_code'])

            if not os.path.exists(manufacturer):
                openai_embed_logger.get_logger().error(f"when delete datasource, the {data['namespace']}/{data['ID']} is not exist")
                return False, []

            if not any(file.endswith('.pkl') for file in os.listdir(manufacturer)) and any(file.endswith('.faiss') for file in os.listdir(manufacturer)):
                openai_embed_logger.get_logger().error(f"when delete datasource from vectordb, the {manufacturer} is not exist")
                return False, []

            # 加載 FAISS 向量庫
            vector_store = FAISS.load_local(
                folder_path=manufacturer,
                embeddings=self.embeddings,  # 假設 self.embeddings 是創建時的嵌入函數
                index_name=data['data']['aics_vdb_code'],
                allow_dangerous_deserialization=True  # 如果信任來源，設置為 True
            )
            openai_embed_logger.get_logger().info(f"Successfully loaded FAISS vector store: {manufacturer}/{data['data']['aics_vdb_code']}")
            
            ids = data["ids"]
            # 檢查 ids 是否有效
            if not ids:
                openai_embed_logger.get_logger().warning("No IDs provided for deletion")
                return False, []

            # 檢查哪些 ID 存在於向量庫
            existing_ids = [doc_id for doc_id in ids if doc_id in vector_store.docstore._dict]
            missing_ids = [doc_id for doc_id in ids if doc_id not in vector_store.docstore._dict]
            if missing_ids:
                openai_embed_logger.get_logger().warning(f"IDs not found in vector store: {missing_ids}")

            if not existing_ids:
                openai_embed_logger.get_logger().info("No valid IDs to delete")
                return self.get_all_documents(manufacturer, data['data']['aics_vdb_code'])

            # 刪除指定 IDs
            vector_store.delete(ids=existing_ids)
            openai_embed_logger.get_logger().info(f"Deleted IDs: {existing_ids}")

            # 保存更新後的向量庫
            vector_store.save_local(folder_path=manufacturer, index_name=data['data']['aics_vdb_code'])
            openai_embed_logger.get_logger().info(f"Vector store updated and saved: {manufacturer}/{data['data']['aics_vdb_code']}")

            return self.get_all_documents(manufacturer, data['data']['aics_vdb_code'])
        
        except Exception as e:
            openai_embed_logger.get_logger().error(f'Delete datasource from vectordb error: {e}')
            return False, []


    def get_all_documents(self, manufacturer, index_name):
        try:
            # 檢查路徑是否存在
            if not os.path.exists(manufacturer):
                openai_embed_logger.get_logger().error(f"Vector store path does not exist: {manufacturer}")
                return False, []

            # 檢查向量庫文件
            pkl_path = os.path.join(manufacturer, f"{index_name}.pkl")
            faiss_path = os.path.join(manufacturer, f"{index_name}.faiss")
            if not (os.path.exists(pkl_path) and os.path.exists(faiss_path)):
                openai_embed_logger.get_logger().error(f"Vector store files not found in {manufacturer}")
                return False, []

            # 加載向量庫
            vector_store = FAISS.load_local(
                folder_path=manufacturer,
                embeddings=self.embeddings,
                index_name=index_name,
                allow_dangerous_deserialization=True  # 如果信任來源，設置為 True
            )
            openai_embed_logger.get_logger().info(f"Successfully loaded FAISS vector store: {manufacturer}/{index_name}")

            # 轉換為 array of dict
            array_of_dict = [
                {
                    "doc_id": doc_id,
                    "page_content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc_id, doc in vector_store.docstore._dict.items()
            ]
            openai_embed_logger.get_logger().info(f"Retrieved {len(array_of_dict)} documents from FAISS vector store")

            return True, array_of_dict

        except Exception as e:
            openai_embed_logger.get_logger().error(f"Failed to retrieve documents from vector store: {e}")
            return False, []


