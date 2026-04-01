

import os
import csv
import shutil
import logging
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma

# Import configuration variables from our central config module
from config import embeddings, DB_DIR

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

CSV_FILENAME = "sample_loans_data.csv"

def create_dummy_csv() -> None:
    """Generates a dummy CSV file representing bank loan data."""
    logger.info(f"Generating mock dataset: {CSV_FILENAME}...")
    
    headers = [
        "loan_id", "rm_name", "client_name", "loan_amount", 
        "interest_rate", "status", "risk_rating", "origination_date"
    ]
    
    # Mock data representing bank loans
    data = [
        ["L-1001", "Sarah Jenkins", "Acme Corp", 1500000, 5.2, "Active", "Low", "2023-01-15"],
        ["L-1002", "David Chen", "TechFlow Inc", 850000, 6.1, "Active", "Medium", "2023-03-22"],
        ["L-1003", "Sarah Jenkins", "Global Retailers", 3200000, 4.8, "Default", "High", "2022-11-05"],
        ["L-1004", "Michael Ross", "Apex Manufacturing", 450000, 7.5, "Closed", "Low", "2021-06-10"],
        ["L-1005", "David Chen", "Nexus Dynamics", 2100000, 5.9, "Active", "Medium", "2023-08-14"],
        ["L-1006", "Michael Ross", "Stark Logistics", 6000000, 8.2, "Active", "High", "2024-01-02"],
        ["L-1007", "Sarah Jenkins", "Quantum Computing Ltd", 1250000, 6.5, "Active", "High", "2024-02-20"],
    ]

    try:
        with open(CSV_FILENAME, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(data)
            
        logger.info(f"Successfully created {CSV_FILENAME} with {len(data)} rows.")
    except Exception as e:
        logger.error(f"Failed to create CSV file: {e}", exc_info=True)

def setup_vector_db() -> None:
    """Initializes the Chroma vector store with seed SQL queries for the RAG agent."""
    logger.info(f"Initializing Chroma VectorDB at {DB_DIR}...")
    
    # Clear existing DB if it exists to ensure a fresh start
    if os.path.exists(DB_DIR):
        logger.warning("Cleaning up existing database directory...")
        try:
            shutil.rmtree(DB_DIR)
        except Exception as e:
            logger.error(f"Failed to remove existing VectorDB directory: {e}", exc_info=True)
            return

    # Seed documents. The metadata contains the actual SQL we want the agent to learn from.
    # Note: The table name 'uploaded_data' matches the hardcoded table in our React frontend.
    seed_data = [
        Document(
            page_content="Show me all high risk active loans. Filters the database for all loans currently marked as 'Active' with a 'High' risk rating.", 
            metadata={"sql": "SELECT loan_id, client_name, loan_amount FROM uploaded_data WHERE status = 'Active' AND risk_rating = 'High';"}
        ),
        Document(
            page_content="What is the total loan amount managed by each RM? Aggregates total loan amounts grouped by Relationship Manager.", 
            metadata={"sql": "SELECT rm_name, SUM(loan_amount) as total_portfolio FROM uploaded_data GROUP BY rm_name;"}
        ),
        Document(
            page_content="List all defaulted loans and their associated clients. Shows client names and amounts for loans that have defaulted.", 
            metadata={"sql": "SELECT client_name, loan_amount FROM uploaded_data WHERE status = 'Default';"}
        ),
        Document(
            page_content="Show loans over $1M originated after 2023. Finds loans greater than 1,000,000 originated in the year 2023 or later.", 
            metadata={"sql": "SELECT * FROM uploaded_data WHERE loan_amount > 1000000 AND origination_date >= '2023-01-01';"}
        ),
        Document(
            page_content="What is the average interest rate for active loans? Calculates the mean interest rate for loans that are not closed or defaulted.", 
            metadata={"sql": "SELECT AVG(interest_rate) as avg_rate FROM uploaded_data WHERE status = 'Active';"}
        ),
    ]
    
    try:
        logger.info("Embedding documents and saving to disk...")
        Chroma.from_documents(
            documents=seed_data, 
            embedding=embeddings, 
            persist_directory=DB_DIR
        )
        logger.info(f"Successfully seeded VectorDB with {len(seed_data)} SQL examples.")
        
    except Exception as e:
        logger.error(f"Error setting up VectorDB: {e}", exc_info=True)
        logger.error("Ensure Ollama is running and you have executed: `ollama pull nomic-embed-text`")

if __name__ == "__main__":
    logger.info("--- Starting Setup Script ---")
    create_dummy_csv()
    setup_vector_db()
    logger.info("--- Setup Complete ---")
    logger.info("Next Steps:")
    logger.info("1. Start the backend: `python backend/api.py`")
    logger.info("2. Start the frontend.")
    logger.info(f"3. Upload '{CSV_FILENAME}' into the chat interface to begin querying.")