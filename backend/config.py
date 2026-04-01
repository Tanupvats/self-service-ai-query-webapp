import os
import logging
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings

# --- Setup Logging ---
logger = logging.getLogger(__name__)

# --- Configuration Variables ---
# Fetch from environment variables, fallback to local development defaults
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
DB_DIR = os.getenv("DB_DIR", "./chroma_db")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))

# --- Global Instances ---
# Initialize global LLM and Embeddings instances to be imported by other modules
logger.info(f"Configuring LLM: {LLM_MODEL} (Temp: {LLM_TEMPERATURE}) at {OLLAMA_BASE_URL}")
logger.info(f"Configuring Embeddings: {EMBEDDING_MODEL}")

try:
    llm = ChatOllama(
        model=LLM_MODEL, 
        base_url=OLLAMA_BASE_URL, 
        temperature=LLM_TEMPERATURE
    )

    embeddings = OllamaEmbeddings(
        model=EMBEDDING_MODEL, 
        base_url=OLLAMA_BASE_URL
    )
except Exception as e:
    logger.error(f"Failed to initialize Ollama connections: {e}")
    raise RuntimeError(f"Ensure Ollama is running at {OLLAMA_BASE_URL} and models are pulled. Details: {e}")