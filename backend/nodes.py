import logging
import re
from langchain_core.messages import HumanMessage, SystemMessage

# Import local modules
from state import AgentState
from config import llm
from tools import retrieve_similar_queries

# --- Setup Logging ---
logger = logging.getLogger(__name__)

# --- Node Implementations ---

def analyze_ambiguity(state: AgentState) -> AgentState:
    """Agent 1: Checks if the user's query is clear enough to write SQL."""
    logger.info("Node Executing: [analyze_ambiguity]")
    
    query = state.get("user_query", "")
    schema = state.get("schema_context", "Unknown Schema")
    
    prompt = f"""You are an expert SQL database architect.
    Active Database Schema: 
    {schema}
    
    User Request: "{query}"
    
    Analyze if the request contains enough specific information to write a valid SQLite query against this EXACT schema. 
    Reply with ONLY the word 'CLEAR' or 'UNCLEAR'. Do not add any other text, punctuation, or explanation."""
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        response_text = response.content.upper().strip()
        
        # Robustly determine if the response indicates clarity
        is_clear = "CLEAR" in response_text and "UNCLEAR" not in response_text
        logger.info(f"Ambiguity Analysis Result: {'CLEAR' if is_clear else 'UNCLEAR'} (Raw: {response_text})")
        
        return {"is_clear": is_clear}
    except Exception as e:
        logger.error(f"Error in analyze_ambiguity: {e}", exc_info=True)
        # Fallback to unclear for safety
        return {"is_clear": False}


def ask_clarification(state: AgentState) -> AgentState:
    """Agent 1a: Asks the user for more information if the query is unclear."""
    logger.info("Node Executing: [ask_clarification]")
    
    turns = state.get("clarification_turns", 0)
    
    # Enforce a strict limit to prevent infinite loops of confusion
    if turns >= 2:
        logger.warning(f"Max clarification turns reached ({turns}). Aborting workflow.")
        return {
            "summary": "I still don't fully understand the requirements based on the uploaded data. This is outside my current scope. Please try rephrasing your request completely.",
            "generated_sql": ""
        }
        
    prompt = f"""You are an AI data assistant. 
    The user asked: "{state.get('user_query', '')}". 
    Active Database Schema: {state.get("schema_context", "Unknown Schema")}
    
    This request is ambiguous, too broad, or refers to columns that don't exist in the schema. 
    Ask ONE brief, direct, and polite clarifying question to understand what columns, filters, or conditions they actually need."""
    
    try:
        response = llm.invoke([SystemMessage(content=prompt)])
        clarification_msg = response.content.strip()
        
        logger.info(f"Clarification generated (Turn {turns + 1}).")
        return {
            "summary": clarification_msg,
            "clarification_turns": turns + 1,
            "generated_sql": ""
        }
    except Exception as e:
        logger.error(f"Error in ask_clarification: {e}", exc_info=True)
        return {
            "summary": "Could you please provide more details or clarify your request?",
            "clarification_turns": turns + 1,
            "generated_sql": ""
        }


def rag_retrieval(state: AgentState) -> AgentState:
    """Agent 2: Executes the RAG tool to retrieve relevant SQL context."""
    logger.info("Node Executing: [rag_retrieval]")
    query = state.get("user_query", "")
    
    try:
        context = retrieve_similar_queries.invoke({"query": query})
        logger.info("Successfully retrieved RAG context.")
        return {"retrieved_context": context}
    except Exception as e:
        logger.error(f"RAG retrieval failed: {e}", exc_info=True)
        return {"retrieved_context": "No context available due to system error."}


def write_sql(state: AgentState) -> AgentState:
    """Agent 3: Formulates the SQL and provides a summary based on RAG context."""
    logger.info("Node Executing: [write_sql]")
    
    prompt = f"""You are an elite SQL writer agent.
    Active Database Schema: 
    {state.get("schema_context", "Unknown Schema")}
    
    User Request: "{state.get('user_query', '')}"
    
    Here are similar validated queries from our knowledge base to use as a guide (if applicable):
    {state.get('retrieved_context', '')}
    
    TASK:
    Write a valid SQLite query strictly satisfying the user's request. 
    The target table name is ALWAYS 'uploaded_data'. Do NOT invent column names; use ONLY the schema provided.
    
    Format your response EXACTLY like this:
    SUMMARY: <a 1-sentence summary of what the query accomplishes>
    SQL:
    ```sql
    <your complete sqlite query here>"""