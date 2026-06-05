import chromadb
from datetime import datetime
import os
import time
from tqdm import tqdm

# --- NEW LLAMAINDEX IMPORTS ---
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.node_parser import SentenceSplitter

class VectorMemory:
    def __init__(self, db_path="./chroma_db"):
        self.client = chromadb.PersistentClient(path=db_path)
        
        # 1. YOUR EXISTING EPISODIC MEMORY
        self.collection = self.client.get_or_create_collection(name="marcus_episodic_memory")
        
        # 2. NEW: DOCUMENT KNOWLEDGE BASE
        self.doc_collection = self.client.get_or_create_collection(name="marcus_document_library")
        self.vector_store = ChromaVectorStore(chroma_collection=self.doc_collection)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        
        # 3. NEW: LOCAL ZERO-COST EMBEDDINGS
        print("[ System ] Booting local embedding engine...")
        # This runs 100% locally on your machine. No API tokens used.
        self.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
        
        # We chunk large textbooks into small 512-token pieces so we don't blow up Groq's context window
        self.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

    # --- EXISTING EPISODIC METHODS ---
    def remember_interaction(self, user_query, marcus_response):
        """Saves the exact wording of a conversation."""
        timestamp = datetime.now().isoformat()
        doc_id = f"interaction_{timestamp}"
        content = f"User asked: '{user_query}'\nMarcus replied: '{marcus_response}'"
        
        self.collection.add(
            documents=[content], metadatas=[{"timestamp": timestamp}], ids=[doc_id]
        )

    def search_past_conversations(self, current_query, n_results=3):
        """Searches past conversations for semantic similarity."""
        try:
            results = self.collection.query(
                query_texts=[current_query], n_results=n_results
            )
            if results['documents'] and results['documents'][0]:
                return "\n".join(results['documents'][0])
            return ""
        except Exception as e:
            print(f"[ Vector DB Error ]: {e}")
            return ""

   
    # --- NEW DOCUMENT RAG METHODS ---
    def ingest_document(self, filepath):
        """Reads a file from the Watchdog, chunks it, and saves it to the vector database."""
        
        # ========================================================
        # THE SHIELD: Prevent Git, Venv, DB, and Build Caches from being indexed
        # ========================================================
        ignored_paths = [
            ".git", ".venv", "__pycache__", "chroma_db", "temp", 
            "node_modules", "build", "dist", "android", "ios", 
            ".next", ".expo", "out", "coverage", ".idea", ".gradle"
        ]
        ignored_extensions = [".json", ".sqlite3", ".log", ".env", ".pack", ".idx", ".exe", ".dll"]
        
        filepath_str = str(filepath).replace("\\", "/")
        
        # Block bad folders
        if any(ignored in filepath_str for ignored in ignored_paths):
            return 
            
        # Block bad file types
        if any(filepath_str.endswith(ext) for ext in ignored_extensions):
            return
        # ========================================================

        # Calculate File Size
        try:
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
        except:
            size_mb = 0.0
            
        print(f"[ Document Engine ] Digesting {os.path.basename(filepath)} ({size_mb:.2f} MB)...")
        
        try:
            # 1. Load the raw text
            documents = SimpleDirectoryReader(input_files=[filepath]).load_data()
            
            # 2. Extract into 512-token chunks
            nodes = self.node_parser.get_nodes_from_documents(documents)
            
            # 3. Connect to the existing DB Index
            index = VectorStoreIndex.from_vector_store(
                self.vector_store, 
                embed_model=self.embed_model
            )
            
            # --- THE FIX: Throttled "Pressure Release" Insertion Loop ---
            batch_size = 4
            for i in tqdm(range(0, len(nodes), batch_size), desc="Embedding Chunks"):
                batch = nodes[i:i+batch_size]
                index.insert_nodes(batch)
                
                # Yield the CPU to the PySide6 UI loop so the UI never stutters
                time.sleep(0.05) 
            # ------------------------------------------------------------
            
            print(f"[ Document Engine ] Successfully indexed {os.path.basename(filepath)}")
        except Exception as e:
            print(f"[ Document Engine Error ]: Failed to digest {filepath}: {e}")

    def search_documents(self, query, top_k=3):
        """Retrieves the top 3 most relevant document chunks for the LLM context."""
        try:
            # Rebuild the index from the ChromaDB storage
            index = VectorStoreIndex.from_vector_store(
                self.vector_store, 
                embed_model=self.embed_model
            )
            
            # Create a retriever to fetch the Top-K chunks
            retriever = index.as_retriever(similarity_top_k=top_k)
            nodes = retriever.retrieve(query)
            
            if not nodes:
                return ""
                
            # Format the output so Marcus knows exactly what file the data came from
            context = "\n\n".join([f"Source File ({node.metadata.get('file_path', node.metadata.get('file_name', 'Unknown'))}):\n{node.text}" for node in nodes])
            return context
        except Exception as e:
            print(f"[ Document Engine Error ]: {e}")
            return ""
        

    def wipe_documents(self):
        """Deletes the entire document library and starts fresh."""
        try:
            print("[ Vector DB ] Erasing Neural Document Library...")
            self.client.delete_collection("marcus_document_library")
            
            # Recreate an empty collection
            self.doc_collection = self.client.get_or_create_collection(name="marcus_document_library")
            self.vector_store = ChromaVectorStore(chroma_collection=self.doc_collection)
            self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            print("[ Vector DB ] Document Library has been reset.")
            return True
        except Exception as e:
            print(f"[ Vector DB Error ]: Failed to wipe docs: {e}")
            return False