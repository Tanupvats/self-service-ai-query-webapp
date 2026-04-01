import logging
from typing import Literal
from langgraph.graph import StateGraph, START, END

# Import local modules
from state import AgentState
from nodes import analyze_ambiguity, ask_clarification, rag_retrieval, write_sql

# --- Setup Logging ---
logger = logging.getLogger(__name__)

# --- Routing Logic ---
def route_after_analysis(state: AgentState) -> Literal["retriever", "clarifier"]:
    """
    Routes the graph based on whether the user's query is clear enough to proceed.
    """
    if state.get("is_clear"):
        logger.info("Graph Router: Query is CLEAR. Proceeding to RAG retrieval.")
        return "retriever"
    
    logger.info("Graph Router: Query is UNCLEAR. Proceeding to clarification.")
    return "clarifier"

def route_after_clarification(state: AgentState) -> str:
    """
    Ends the current graph execution to wait for user input.
    """
    logger.info("Graph Router: Clarification generated. Pausing execution.")
    return END

# --- Graph Construction ---
def build_graph():
    """
    Constructs, configures, and compiles the LangGraph multi-agent workflow.
    """
    logger.info("Building LangGraph Multi-Agent StateMachine...")
    
    try:
        # Initialize the state graph with our typed dictionary
        workflow = StateGraph(AgentState)

        # 1. Add Nodes (The agents doing the work)
        workflow.add_node("analyzer", analyze_ambiguity)
        workflow.add_node("clarifier", ask_clarification)
        workflow.add_node("retriever", rag_retrieval)
        workflow.add_node("sql_writer", write_sql)

        # 2. Add Edges & Routing (The workflow logic)
        workflow.add_edge(START, "analyzer")
        
        # Branching logic after the analyzer checks the query
        workflow.add_conditional_edges(
            "analyzer", 
            route_after_analysis,
            {
                "retriever": "retriever",
                "clarifier": "clarifier"
            }
        )

        # Success path: Retrieve context -> Write SQL -> End
        workflow.add_edge("retriever", "sql_writer")
        workflow.add_edge("sql_writer", END)

        # Ambiguity path: Ask Clarification -> End (Wait for user reply)
        workflow.add_conditional_edges(
            "clarifier", 
            route_after_clarification,
            {
                END: END
            }
        )

        # 3. Compile the graph into a runnable application
        compiled_app = workflow.compile()
        logger.info("Successfully compiled LangGraph application.")
        
        return compiled_app

    except Exception as e:
        logger.error(f"Failed to build LangGraph workflow: {e}", exc_info=True)
        raise RuntimeError(f"Graph construction error: {e}")

# Expose the compiled app globally for the API server (api.py) to consume
app = build_graph()