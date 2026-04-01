import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

# Import the compiled LangGraph application
from graph import app as agent_app

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --- FastAPI Initialization ---
app = FastAPI(
    title="Loan Data AI Agent API",
    description="Multi-agent LLM backend for translating natural language to SQL.",
    version="1.0.0"
)

# --- CORS Configuration ---
# Allows the React frontend (running on a different port) to communicate securely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your frontend domain (e.g., "http://localhost:5173")
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    user_query: str = Field(..., description="The natural language request from the user.")
    clarification_turns: int = Field(default=0, description="Number of times the agent has asked for clarification.")
    schema_context: str = Field(default="No data uploaded yet.", description="The SQL schema extracted from the user's uploaded CSV.")

class ChatResponse(BaseModel):
    status: str = Field(..., description="'SUCCESS' if SQL was generated, 'NEEDS_CLARIFICATION' otherwise.")
    summary: str = Field(..., description="Agent's explanation or clarifying question.")
    sql: Optional[str] = Field(default="", description="The generated SQLite query (if successful).")
    clarification_turns: int = Field(default=0, description="Current count of clarification turns.")

# --- Endpoints ---

@app.get("/health", tags=["System"])
def health_check():
    """Simple endpoint to verify the API is running."""
    return {"status": "healthy", "service": "LangGraph Multi-Agent Backend"}

@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
def process_chat(request: ChatRequest):
    """
    Main endpoint for the frontend to interact with the LangGraph multi-agent system.
    Takes a natural language query + schema context, and returns either a clarifying question or executable SQL.
    """
    logger.info(f"Received Query: '{request.user_query}' | Turns: {request.clarification_turns}")
    
    try:
        # 1. Prepare the state dictionary for LangGraph
        initial_state = {
            "user_query": request.user_query,
            "clarification_turns": request.clarification_turns,
            "schema_context": request.schema_context,
            "chat_history": [] # Add memory injection here if expanding to multi-turn contextual chat
        }
        
        # 2. Invoke the multi-agent graph (Analyzer -> Clarifier OR Retriever -> SQL Writer)
        logger.info("Invoking LangGraph execution pipeline...")
        result = agent_app.invoke(initial_state)
        
        # 3. Format the response based on the graph's output state
        if result.get("generated_sql"):
            logger.info("Successfully generated SQL.")
            return ChatResponse(
                status="SUCCESS",
                summary=result.get("summary", "Query generated successfully."),
                sql=result.get("generated_sql"),
                clarification_turns=0 # Reset on success
            )
        else:
            logger.info(f"Agent requested clarification. Turn {result.get('clarification_turns')}/2")
            return ChatResponse(
                status="NEEDS_CLARIFICATION",
                summary=result.get("summary", "Could you provide more details?"),
                sql="",
                clarification_turns=result.get("clarification_turns", request.clarification_turns + 1)
            )
            
    except Exception as e:
        logger.error(f"Graph Execution Failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Agent Error: {str(e)}")

# --- Execution ---
if __name__ == "__main__":
    logger.info("Starting Backend Server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)