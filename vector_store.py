import logging
import os

from bs4 import BeautifulSoup as Soup

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

def setup_vector_store(logger: logging.Logger):
    """Setup or load the vector store."""
    if not os.path.exists("data"):
        os.makedirs("data")
        
    vector_store_dir = "data/vector_store"
    
    if os.path.exists(vector_store_dir):
        # Load the vector store fro disk
        logger.info("Loading vector store from disk..")
        vector_store = FAISS.load_local(
            vector_store_dir,
            OpenAIEmbeddings(),
            allow_dangerous_deserialization=True
        )
    else:
        logger.info("Creating new vector store...")
        # Load SQL Documentation
        url = "https://www.sqltutorial.org/sql-count/"
        loader = RecursiveUrlLoader(
            url=url, max_depth=2, extractor=lambda x: Soup(x, "html.parser").text
        )
        docs = loader.load()
        
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap = 50,
            separators=['\n\n', "\n", ".", "!", "?", ",", " ", ""]
        )
        documents = []
        for doc in docs:
            splits = text_splitter.split_text(doc.page_content)
            for i, split in enumerate(splits):
                documents.append({
                    "content": split,
                    "metadata": {'source': doc.metadata['source'], "chunk": i}
                })
                
        # Compute embeddings and create vector store
        embedding_model = OpenAIEmbeddings()
        vector_store = FAISS.from_texts(
            [doc['content'] for doc in documents],
            embedding_model,
            metadatas = [doc['metadata'] for doc in documents]
        )
        
        # Save the vector store to disk
        vector_store.save_local(vector_store_dir)
        logger.info("Vector store created and saved to disk")
        
    return vector_store

            
