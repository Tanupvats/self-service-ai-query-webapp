"""
State definition module for the LangGraph multi-agent workflow.

This module defines the schema for the state object passed between nodes
in the LangGraph execution environment.
"""

import operator
from typing import TypedDict, Annotated, List, Dict, Any

class AgentState(TypedDict):
    """
    Defines the state structure that is passed between nodes in the LangGraph workflow.
    Each node in the graph reads from and writes to this shared state dictionary.
    
    The `Annotated` type with `operator.add` tells LangGraph how to handle updates 
    to the `chat_history` key (i.e., by appending new messages to the existing list 
    rather than overwriting it).
    """
    # The natural language request provided by the user.
    user_query: str
    
    # A list of message dictionaries appended over time (for multi-turn memory).
    # operator.add acts as a reducer, appending new lists to the existing list.
    chat_history: Annotated[List[Dict[str, Any]], operator.add]
    
    # Counter tracking how many times the agent has asked for clarification.
    clarification_turns: int
    
    # Boolean flag indicating if the user's query is unambiguous against the schema.
    is_clear: bool
    
    # The stringified output from the RAG tool containing similar SQL examples.
    retrieved_context: str
    
    # The final executable SQLite query produced by the writer agent.
    generated_sql: str
    
    # A conversational summary or clarifying question returned to the user.
    summary: str
    
    # The database schema dynamically extracted from the user's uploaded CSV.
    schema_context: str