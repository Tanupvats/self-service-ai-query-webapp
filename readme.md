
# Self Service AI Query WebApp

### *A Multi-Agent, Privacy-First SQL Intelligence System*

This repository contains a full-stack, self-service business intelligence (BI) platform designed for Bank Relationship Managers (RMs) and Senior Leadership. The system leverages a **Stateful Multi-Agent Architecture** to translate complex natural language business requirements into precise, executable SQL queries against loan portfolios.

---

## Demo

[![Demo face Recognition](Face_recog_demo.gif)]()

---

## The Agentic Architecture: A Deep Dive

Unlike standard "Text-to-SQL" wrappers that rely on a single prompt, this system implements a **Directed Acyclic Graph (DAG)** using **LangGraph**. This allows for a modular, iterative reasoning process where specialized agents handle specific parts of the request lifecycle.

### The Orchestration Layer (LangGraph)
The heart of the backend is a state machine that manages transitions between specialized nodes. By maintaining a persistent `AgentState`, the system ensures that context is never lost as it moves from analysis to execution.

#### 1. The Ambiguity Analyzer (The Gatekeeper)
* **Role**: To prevent "Garbage In, Garbage Out."
* **Logic**: This agent evaluates the user's query against the **Dynamic Schema Context** provided by the frontend. 
* **Decision Matrix**: If the query is too broad (e.g., "show loans") or references non-existent columns, the analyzer flags the state as `UNCLEAR`. If valid, it routes to the Retrieval layer.

#### 2. The Clarification Agent (Human-in-the-Loop)
* **Role**: Contextual Refinement.
* **Logic**: When the Analyzer flags a query, this agent takes over. It identifies specifically *what* is missing and asks the user a targeted question.
* **Constraint**: To prevent "AI Hallucination Loops," this agent is limited to **2 turns**. If the user cannot provide a clear intent within two rounds, the agent gracefully terminates the session, protecting compute resources and user experience.

#### 3. The RAG Retriever (The Librarian)
* **Role**: Few-Shot Context Injection.
* **Logic**: This node uses a **Semantic Search Tool** (`tools.py`) to query a local **ChromaDB** vector store. 
* **Mechanism**: It embeds the user's intent using `nomic-embed-text` and finds the top 2 matching "Golden SQL" examples from the knowledge base. This context is then injected into the prompt for the final writer, significantly increasing the success rate for complex joins or aggregations.

#### 4. The SQL Writer (The Expert)
* **Role**: Code Generation.
* **Logic**: Using the user's query, the verified schema, and the RAG examples, this agent formulates a **SQLite-compatible** query. 
* **Output**: It produces a two-part response: a conversational summary explaining the query's logic and the raw SQL code block.

[![system Architecture](system_architectue.png)]()

---

## Agentic state Graph Flow

[![Flow](Face_recog_demo.gif)]()


## Technical Stack & Security

### **Intelligence & Backend**
* **Orchestration**: `LangGraph` (for stateful agent transitions).
* **LLM Engine**: `Ollama` (Local hosting of `Llama3` for data privacy).
* **Vector DB**: `ChromaDB` (Local persistence for SQL knowledge RAG).
* **API Layer**: `FastAPI` (Asynchronous, type-safe Python web framework).

### **Data & Frontend**
* **UI Framework**: `React 18` + `Vite` (High-performance rendering).
* **Local SQL Engine**: `AlaSQL` (Executes generated SQL directly in the browser).
* **Privacy Philosophy**: The actual loan data **never leaves the user's machine**. Only the *schema headers* are sent to the AI agents to inform the SQL writing process.

---

## The Data Lifecycle

1.  **Ingestion**: User uploads a CSV. React parses the headers and creates an in-memory SQL table.
2.  **Request**: User asks, *"Which RM has the highest average interest rate for active loans?"*
3.  **State Initialization**: React sends the column names (Schema) and the Query to the FastAPI `/api/chat` endpoint.
4.  **Graph Execution**: 
    * `Analyzer` confirms "interest rate" and "RM" exist in the schema.
    * `Retriever` finds a similar "Aggregation Example" in ChromaDB.
    * `Writer` generates the `GROUP BY` and `AVG` SQL.
5.  **Delivery**: The UI displays the SQL. The user clicks "Execute," and `AlaSQL` runs the query against the local CSV data.

---

## Installation & Local Setup

### 1. Prerequisite: Ollama
Download and install [Ollama](https://ollama.com/). Once installed, pull the required models:
```bash
ollama pull llama3
ollama pull nomic-embed-text
```

### 2. Backend Environment
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Seed the Vector Knowledge Base & Generate Sample Data
python setup_dummy_data.py

# Launch the Agentic API
python api.py
```

### 3. Frontend Environment
```bash
cd frontend
npm install
npm run dev
```

---

## Modular Project Structure

```text
├── backend/
│   ├── api.py           # REST API Interface & Pydantic Models
│   ├── config.py        # Centralized LLM & VectorDB Settings
│   ├── graph.py         # Multi-Agent State Machine Orchestration
│   ├── nodes.py         # Specialized Agent Logic (The "Brains")
│   ├── state.py         # State Definition & Reducer Logic
│   ├── tools.py         # RAG Semantic Search Implementation
│   └── setup_dummy_data.py  # Data Bootstrapper
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx      # UI, CSV Parsing & Local SQL Engine
│   │   └── main.jsx     # Entry Point
│   └── tailwind.config.js # Styling Config
```

---

##  Governance & Safety
* **Deterministic Routing**: The graph ensures the LLM cannot skip the analysis phase.
* **Local Inference**: Complies with banking regulations by keeping all inference local (no OpenAI/Azure dependencies).
* **Input Sanitization**: The SQL Writer is instructed to use SQLite-only syntax, preventing execution errors on the client-side engine.

---
**Author**: Tanup Vats