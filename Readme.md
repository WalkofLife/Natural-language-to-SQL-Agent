NL2SQL Agent Project Reference
Project Purpose
This project builds a Natural Language to SQL Agent using:

- OpenAI models via langchain_openai
- LangGraph workflow orchestration
- FAISS vector search for SQL documentation context
- SQLite sample database
- MLFlow for experiment tracking and model serving

The goal is to convert user questions into safe, executable SQL queries against the local sample database.

Core Files

- main.py
- workflow.py
- sql_generation.py
- vector_store.py
- database.py
- definitions.py
- Main Application Flow (main.py)
- main.py is the app entrypoint:

loads environment variables via .env
sets MLFlow tracking URI and experiment
calls setup_database to prepare SQLite data
calls setup_vector_store to load or create embeddings
loads the MLFlow model registry entrypoint at models:/nl2sql_langgraph_agent@champion
invokes the compiled graph workflow using app.invoke(initial_state)
supports a simple command-line loop for user input
prints either an error message, the generated SQL query, or query results
Workflow Definition (workflow.py)
workflow.py defines the pipeline using langgraph.graph.StateGraph.

Workflow nodes
translate_input

translates incoming user input to English using OpenAI
stores result in state["translated_input"]
pre_safety_check

blocks dangerous SQL intent in user text
checks for keywords like CREATE, DROP, DELETE, UPDATE, INSERT
also runs a toxicity/safety classification prompt
schema_extract

reads SQLite schema from sqlite_master
builds schema text with table and column details
stores it in state["database_schema"]
context_check

asks the LLM whether the user question is answerable using the schema
blocks unrelated queries
generate

retrieves relevant docs from the vector store via similarity search
passes docs, schema, and user message to sql_gen_chain
stores generated SQL as structured output with description and sql_code
increments retry iterations
post_safety_check

validates generated SQL
ensures it contains SELECT
rejects disallowed operations if present
sql_check

runs the SQL in a savepoint transaction
rolls back after validation
if execution fails, marks error and updates messages
run_query

executes validated SQL for final results
sets results and no_records_found
Control logic
The graph connects nodes sequentially with conditional edges.
If pre_safety_check or context_check fails, the workflow ends.
After sql_check, the workflow either:
retries generation up to max_iterations = 3
runs the query
ends if retries exhausted
SQL Generation (sql_generation.py)
This file defines:

SQLQuery Pydantic model with description and sql_code
get_sql_gen_chain(), which builds a prompt chain
uses ChatPromptTemplate and OpenAI gpt-4o-mini
enforces structured output via llm.with_structured_output(SQLQuery)
The prompt asks the model to:

answer the user’s question based on retrieved docs
use provided database schema
return a description and SQL code block
Vector Store Setup (vector_store.py)
setup_vector_store(logger) does either:

load an existing FAISS store from data/vector_store
or create a new one from SQL tutorial docs online
If creating:

downloads content from https://www.sqltutorial.org/sql-count/
uses BeautifulSoup + RecursiveUrlLoader
splits text with RecursiveCharacterTextSplitter
embeds text with OpenAI embeddings
saves the FAISS store locally
The vector store is used in generate() to provide documentation context for SQL generation.

Database Setup (database.py)
This file manages SQLite data:

creates data/database.db
defines tables:
Customers
Orders
OrderDetails
Products
populates each with simple synthetic sample rows if empty
This sample schema is the target database for user SQL queries.

Configuration (definitions.py)
Key constants:

EXPERIMENT_NAME = "nl2sql_agent"
REGISTERED_MODEL_NAME = "nl2sql_langgraph_agent"
MODEL_ALIAS = "champion"
REMOTE_SERVER_URI = "http://127.0.0.1:8080"
These control MLFlow tracking and model registry loading.

Important Notes
The system is built for read-only SQL use (SELECT queries only).
The workflow relies on langchain_openai.ChatOpenAI and langgraph.
Current user interaction is CLI-based only.
The model is loaded via MLFlow and expected to return a compiled graph app.
Improvement Suggestions
Refactor large workflow node definitions into smaller helper modules:

move translate_input, pre_safety_check, etc. into separate functions or files
keep workflow.py as orchestration only
Fix prompt formatting issues:

safety_prompt is defined with {translated_input} but not formatted
context_prompt and translation prompt usage should be checked for exact interpolation
Address potential bug:

sql_check() currently does not return state
generate() uses retrieved_doc key but the prompt expects retrieved_docs
these should be aligned and verified
Consider caching schema extraction once per run instead of every request.

Add structured logging and better error reporting for production use.

How to Use
Ensure .env and OpenAI credentials are set for langchain_openai
Run main.py
Enter a natural language SQL question
The system will:
translate input
verify safety and schema relevance
generate SQL
validate SQL
execute the query and print results
If you want, I can also turn this into a ready-to-save file content block with no extra commentary.

Checking the actual folder contents for `NL2SQL MLFlow` and then I’ll return the full tree structure.

Read [](file:///c%3A/Users/anirudh.sharma/OneDrive%20-%20Nihilent%20Limited/Learning/Chatbot/NL2SQL%20MLFlow)

Read [](file:///c%3A/Users/anirudh.sharma/OneDrive%20-%20Nihilent%20Limited/Learning/Chatbot/NL2SQL%20MLFlow/data)

Read [](file:///c%3A/Users/anirudh.sharma/OneDrive%20-%20Nihilent%20Limited/Learning/Chatbot/NL2SQL%20MLFlow/mlartifacts)

Read [](file:///c%3A/Users/anirudh.sharma/OneDrive%20-%20Nihilent%20Limited/Learning/Chatbot/NL2SQL%20MLFlow/mlartifacts/1)

Read [](file:///c%3A/Users/anirudh.sharma/OneDrive%20-%20Nihilent%20Limited/Learning/Chatbot/NL2SQL%20MLFlow/data/vector_store)

Read [](file:///c%3A/Users/anirudh.sharma/OneDrive%20-%20Nihilent%20Limited/Learning/Chatbot/NL2SQL%20MLFlow/mlartifacts/1/models)

Read [](file:///c%3A/Users/anirudh.sharma/OneDrive%20-%20Nihilent%20Limited/Learning/Chatbot/NL2SQL%20MLFlow/mlartifacts/1/models/m-51c1798cfe5d48a0a2dcfb00703a780d)

Read [](file:///c%3A/Users/anirudh.sharma/OneDrive%20-%20Nihilent%20Limited/Learning/Chatbot/NL2SQL%20MLFlow/mlartifacts/1/models/m-55835618575948e38c8266556f982cb7)

Read [](file:///c%3A/Users/anirudh.sharma/OneDrive%20-%20Nihilent%20Limited/Learning/Chatbot/NL2SQL%20MLFlow/mlartifacts/1/models/m-51c1798cfe5d48a0a2dcfb00703a780d/artifacts)

Read [](file:///c%3A/Users/anirudh.sharma/OneDrive%20-%20Nihilent%20Limited/Learning/Chatbot/NL2SQL%20MLFlow/mlartifacts/1/models/m-51c1798cfe5d48a0a2dcfb00703a780d/artifacts/code)

Read [](file:///c%3A/Users/anirudh.sharma/OneDrive%20-%20Nihilent%20Limited/Learning/Chatbot/NL2SQL%20MLFlow/mlartifacts/1/models/m-55835618575948e38c8266556f982cb7/artifacts)

Read [](file:///c%3A/Users/anirudh.sharma/OneDrive%20-%20Nihilent%20Limited/Learning/Chatbot/NL2SQL%20MLFlow/mlartifacts/1/models/m-55835618575948e38c8266556f982cb7/artifacts/code)

## Folder tree for `NL2SQL MLFlow`

```
NL2SQL MLFlow/
├── .env
├── database.py
├── definitions.py
├── log_model.py
├── main.py
├── mlflow.db
├── Readme.md
├── sql_agent_graph.png
├── sql_generation.py
├── sql_model.py
├── test.ipynb
├── vector_store.py
├── workflow.py
├── __pycache__/
├── data/
│   ├── database.db
│   └── vector_store/
│       ├── index.faiss
│       └── index.pkl
└── mlartifacts/
    └── 1/
        └── models/

```