

import os
import logging
from langchain_core.tools import tool
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# Import configuration variables mapped in config.py
from config import embeddings, DB_DIR

# --- Setup Logging ---
logger = logging.getLogger(__name__)

def initialize_vector_db() -> Chroma:
    """
    Bootstraps the Chroma VectorDB with some initial SQL examples 
    if the database directory doesn't exist yet.
    """
    logger.info("Initializing new VectorDB with seed data...")
    seed_data = [
        Document(
            page_content="Finding high risk active loans. Filters the database for all loans currently marked as 'Active' with a 'High' risk rating.", 
            metadata={"sql": "SELECT loan_id, client_name, loan_amount FROM uploaded_data WHERE status = 'Active' AND risk_rating = 'High';"}
        ),
        Document(
            page_content="Portfolio by RM. Aggregates total loan amounts managed by each Relationship Manager.", 
            metadata={"sql": "SELECT rm_name, SUM(loan_amount) as total_portfolio FROM uploaded_data GROUP BY rm_name;"}
        ),
        Document(
            page_content="Defaulted Client List. Lists all client names and amounts for loans that have defaulted.", 
            metadata={"sql": "SELECT client_name, loan_amount FROM uploaded_data WHERE status = 'Default';"}
        ),
        Document(
            page_content="Recent Large Originations. Finds loans over $1M originated in the year 2023 or later.", 
            metadata={"sql": "SELECT * FROM uploaded_data WHERE loan_amount > 1000000 AND origination_date >= '2023-01-01';"}
        ),
    ]
    
    try:
        # Create and persist the DB locally
        db = Chroma.from_documents(
            documents=seed_data, 
            embedding=embeddings, 
            persist_directory=DB_DIR
        )
        logger.info(f"Successfully bootstrapped VectorDB at {DB_DIR} with {len(seed_data)} documents.")
        return db
    except Exception as e:
        logger.error(f"Failed to initialize VectorDB: {e}", exc_info=True)
        raise RuntimeError(f"VectorDB Initialization Error: {e}")

@tool
def retrieve_similar_queries(query: str) -> str:
    """
    RAG Tool: Retrieves similar SQL queries from the Vector DB based on the user's natural language request.
    Connects to ChromaDB and uses Ollama embeddings to perform a semantic similarity search.
    """
    logger.info(f"Tool Execution: Embedding query and searching VectorDB for: '{query}'")
    
    try:
        # Load existing DB or create a new one with seed data if missing
        if not os.path.exists(DB_DIR):
            logger.warning(f"VectorDB directory '{DB_DIR}' not found. Initializing now...")
            db = initialize_vector_db()
        else:
            db = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
            
        # Perform similarity search to find the top 2 most relevant SQL examples
        results = db.similarity_search(query, k=2)
        
        if not results:
            logger.info("No matching SQL examples found in the knowledge base.")
            return "No matching SQL examples found in the knowledge base."
            
        # Format the retrieved documents into a context string for the LLM
        formatted_context = []
        for i, res in enumerate(results):
            summary = res.page_content
            sql = res.metadata.get("sql", "-- No SQL provided")
            
            formatted_context.append(
                f"--- EXAMPLE {i+1} ---\n"
                f"MATCHING SUMMARY: {summary}\n"
                f"EXAMPLE SQL: {sql}\n"
            )
            
        logger.info(f"Successfully retrieved {len(results)} examples from VectorDB.")
        return "\n".join(formatted_context)
        
    except Exception as e:
        logger.error(f"Error during RAG retrieval: {e}", exc_info=True)
        return "Error: Unable to retrieve examples from the knowledge base."