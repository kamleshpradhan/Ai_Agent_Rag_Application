from concurrent.futures import ThreadPoolExecutor
from typing import List
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_core.documents import Document
from dotenv import load_dotenv
import os
import chromadb
from pathlib import Path
import asyncio

class AsyncDocumentVectorizer:
    def __init__(self, openai_api_key: str, persist_directory: str = "./chroma_db"):
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=openai_api_key,
            model="text-embedding-3-large"
        )
        self.persist_directory = persist_directory
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        # Create thread pool for blocking operations
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def _load_document_sync(self, file_path: str) -> List[Document]:
        """Synchronous document loading"""
        file_extension = Path(file_path).suffix.lower()
        

        print(file_extension)
        if file_extension == '.pdf':
            loader = PyPDFLoader(file_path)
        elif file_extension == '.txt':
            loader = TextLoader(file_path, encoding='utf-8')
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        return loader.load()
    
    def _process_and_store_sync(self, documents: List[Document], 
                               collection_name: str, document_id: str) -> dict:
        """Synchronous processing and storage"""
        try:
            # Add metadata
            for doc in documents:
                doc.metadata.update({
                    "document_id": document_id,
                    "source_file": Path(doc.metadata.get("source", "")).name,
                })
            
            # Split into chunks
            chunks = self.text_splitter.split_documents(documents)
            
            # Create vector store
            vector_store = Chroma(
                collection_name=collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
            
            # Add documents (synchronous operation)
            chunk_ids = vector_store.add_documents(chunks)
            
            return {
                "success": True,
                "document_id": document_id,
                "chunks_created": len(chunks),
                "chunk_ids": chunk_ids,
                "collection": collection_name
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "document_id": document_id
            }
    
    async def vectorize_document_async(self, file_path: str, 
                                     collection_name: str, 
                                     document_id: str) -> dict:
        """Main async vectorization function"""
        loop = asyncio.get_event_loop()
        
        try:
            # Step 1: Load document asynchronously
            documents = await loop.run_in_executor(
                self.executor, 
                self._load_document_sync, 
                file_path
            )
            
            print(f"✅ Loaded {len(documents)} pages from {file_path}")
            
            # Step 2: Process and store asynchronously
            result = await loop.run_in_executor(
                self.executor,
                self._process_and_store_sync,
                documents,
                collection_name,
                document_id
            )
            
            print(f"✅ Vectorization completed: {result}")
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "document_id": document_id
            }



def get_chroma_client():
    return chromadb.PersistentClient(path="./chroma_db")



def get_chroma_collections(collection_name: str, document_id: str):
    try:
        client = get_chroma_client()
        collection = client.get_collection(collection_name)
        results = collection.get(
            where={"document_id": document_id},
        )
     
        if not results["documents"]:
            print(f"❌ No document found with ID: {document_id}")
            return None

        full_content = ""
        chunks_info = []
        for i in range(len(results["documents"])):
            print(results["documents"][i])
            chunk_content = results["documents"][i]
            chunk_metadata = results["metadatas"][i]
            chunk_id = results["ids"][i]

            chunks_info.append({
                "chunk_id": chunk_id,
                "content": chunk_content,
                "metadata": chunk_metadata
            })

            full_content += chunk_content + "\n\n"

            return {
                "document_id": document_id,
                "full_content": full_content.strip(),
                "chunks": chunks_info,
                "total_chunks": len(results["documents"])
            }
    except Exception as e:
        print(f"❌ Error getting document: {str(e)}")
        return None
        
        