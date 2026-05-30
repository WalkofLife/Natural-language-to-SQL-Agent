import logging
import re
from typing import List, Optional

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from sql_generation import get_sql_gen_chain
from typing_extensions import TypedDict, Annotated
from pydantic import Field

# Initalize the logger
_logger = logging.getLogger(__name__)
# _logger.setLevel(logging.INFO)

# if not _logger.handlers:
#     handler = logging.StreamHandler()

#     formatter = logging.Formatter(
#         "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
#     handler.setFormatter(formatter)
#     _logger.addHandler(handler)
    


class GraphState(TypedDict):
    error: str # Tracks if an error has occured
    messages: List # List of messages(user input and assistant messages)
    generation: Optional[str] # Holds the generated SQL query
    iterations: int # Keeps track of how many times the workflow has retried
    results: Optional[List] # Holds the results of SQL execution
    no_records_found: bool # FLag for whether any records were found in the SQL result
    translated_input: str # Holds the translated user input
    database_schema: str # Holds the extracted database schema for context checking


    
def get_workflow(conn, cursor, vector_store):
    """Define and compile the LangGraph workflow."""
    
    # Max Iterations: defines how many time
    max_iterations = 3
    
    # SQL Generation chain: this is a chain that will generate SQL based on retrieved docs
    sql_gen_chain = get_sql_gen_chain()
    
    # Initialize OpenAI LLM for transloation and safety checks
    llm = ChatOpenAI(temperature=0, model="gpt-4o-mini")
    
    # Translate Input
    def translate_input(state: GraphState) -> GraphState:
        """Translates user input to English using an LLM. If the input is already in English it is returned as is.
        This ensures consistent input for downstream processing.
        
        Args:
            state (GraphState): The current graph state containing user messages.
            
        Returns:
            GraphState: The updated state with the translated input"""
        _logger.info("Starting translation of user input to English.")
        messages = state['messages']
        user_input = messages[-1][-1] # Get the latest user input
        
        # Translation prompt for the model
        translation_prompt = f"""
        Translate the following text to English. If the text is already in English, repeat it exactly without any additional explaination.
        
        Text:
        {user_input}
        """
        
        # Call the openAI LLM to translate the text
        translated_response = llm.invoke(translation_prompt)
        translated_text = translated_response.content.strip() # Access the 'content' attribute and strip any extra spaces
        
        # Update state with the translated input
        state['translated_input'] = translated_text
        _logger.info("Translation completed successfully. Translated input: %s", translated_text)
        
        return state

    # Pre-safety Check
    def pre_safety_check(state: GraphState) -> GraphState:
        """Perform safety checks on the user input to ensure that no dangerous SQL operations or inappropriate content is present.
        The function checks for SQL operations like DELETE, DROP, and others, and also evaluates the input for toxic or unsafe content.

        Args:
            state (GraphState): The current graph state containing the translated user input.

        Returns:
            GraphState: The updated state with error status and messages if any issues are found.
        """
        _logger.info("Performing Safety checks")
        translated_input = state['translated_input']
        messages = state['messages']
        error = "no"
        
        # List of disallowed SQL operations 
        disallowed_operations = ['CREATE', 'DELETE', "DROP", 'ALTER', "INSERT", 'UPDATE', 'TRUNCATE', 'EXEC', 'EXECUTE']
        pattern = re.compile(r'\b(' + '|'.join(disallowed_operations) + r')\b', re.IGNORECASE)
        
        # Check if the input contains disallowed SQL operations
        if pattern.search(translated_input):
            _logger.warning("Input contains disallowed SQL operations. Halting the workflow")
            error = "yes"
            messages += [('assistant', "Your query contains disallowed SQL operations and cannot be processed")]
        else:
            # Check if the input contains inappropriate content
            safety_prompt = """
            Analyze the following input for any inappropriate or toxic content.
            Respond with only "safe" or "unsafe" and nothing else.
            
            INPUT:
            {translated_input}
            """
            safety_invoke = llm.invoke(safety_prompt)
            safety_response = safety_invoke.content.strip().lower()
            
            if safety_response == 'safe':
                _logger.info("Input passed the pre safety check")
            else:
                _logger.warning("Input failed the pre safety check. Halting workflow")
                error = "yes"
                messages+= [('assistant', "Your query contains inappropriate content and can not be processed")]
        
        state['error'] = error
        state['messages'] = messages
        
        return state
            
    # Schema Extraction
    ## Future Enhancements -> 1. Save it once instead of calling it everytime 2. Use SQLAlchemy 
    def schema_extract(state: GraphState) -> GraphState:
        """Extract the database schema, including all the tables and their respective columns, from the connected SQLite Database.
        This function retrieves the list of tables and iterates through each table to gather column definitions (name and data types)

        Args:
            state (GraphState): Current graph state, which will be updated with the database schema

        Returns:
            GraphState: The updated state with the extracted database schema.
        """
        _logger.info("Extracting Database Schema")
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        schema_details = []

        # Loop through each table and retrieve column information
        for table_name_tuple in tables:
            table_name = table_name_tuple[0]
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()

            # Format column definitions
            column_defs = ', '.join([f"{col[1]} ({col[2]})" for col in columns])
            schema_details.append(f"- {table_name}({column_defs})")

        # Save the schema in the state
        database_schema = '\n'.join(schema_details)
        state["database_schema"] = database_schema
        _logger.info(f"Database schema extracted:\n{database_schema}")

        return state
            
    def context_check(state: GraphState) -> GraphState:
        """
        Checks whether the user's input is relevant to the database schema by comparing the user's question with the database schema.
        Uses a language model to determine if the question can be answered using the provided schema.
        
        Args:
            state (GraphState): The current graph state, which contains the translated input
                                and the database schema.

        Returns:
            GraphState: The updated state with error status and messages if the input is irrelevant.
        """
        _logger.info("Checking whether the user's input is relevant to the database schema")
        
        # Extract relevant data from the state
        translated_input = state['translated_input']
        error = "no"
        messages = state['messages']
        database_schema = state['database_schema'] # Get the schema from the state
        
        # Use the LLM to determine if the input is relevant to schema or not
        context_prompt = f"""
        Determine whether the following user input is a question that can be answered using the database schema provided below.
        Respond with only "relevant" if the input is relevant to the database schema, or "irrelevant" if it is not.
        
        User Input:
        {translated_input}
        
        Database Schema:
        {database_schema}
        """
        # Call the LLM for context check
        llm_invoke = llm.invoke(context_prompt)
        llm_response = llm_invoke.content.strip().lower()
        
        if llm_response == "relevant":
            _logger.info("Input is relevant to database schema")
        else:
            _logger.info("Input is not related to the database. Halting the workflow")
            error = "yes"
            messages += [('assistant', 'Your question is not related to the database and cannot be processed.')]
            
        # Update state
        state['error'] = error
        state['messages'] = messages
        
        return state

    # Generate SQL Query
    def generate(state: GraphState) -> GraphState:
        """Generate SQL query based on user input. The node retrives relevant documents from the vector store and uses a generation chain to produce SQL query."""
        _logger.info("Generating SQL Query")
        
        # Extract relevant data from state
        messages = state['messages']
        iterations = state['iterations']
        translated_input = state['translated_input']
        database_schema = state['database_schema']
        
        # Retrive relevant documents from the vector store based on the translated input
        docs = vector_store.similarity_search(translated_input, 4)
        retrieved_docs = "\n\n".join([doc.page_content for doc in docs])
        
        # Generate the SQL query using the SQL generation chain
        sql_solution = sql_gen_chain.invoke(
            {
                "retrieved_docs": retrieved_docs,
                "database_schema": database_schema,
                "messages": [("user", translated_input)],
            }
        )
        
        # Save the generated SQL query in the state
        messages += [
            (
                "assistant",
                f"{sql_solution.description}\nSQL Query:\n{sql_solution.sql_code}"
            )
        ]
        iterations += 1
        
        # Log the generated Query
        _logger.info("Generated SQL Query:\n%s",sql_solution.sql_code)
        
        # Update the state
        state['generation'] = sql_solution
        state['messages'] = messages
        state['iterations'] = iterations
        
        return state
    
    # Post Safety Check
    # The post_safety_check node ensures the generated SQL query is safe by performing a final validation for harmful SQL commands. While the earlier pre-safety check identifies disallowed operations in user inputs, this post-safety check verifies that the SQL query produced after generation adheres to security guidelines. This two-step approach ensures that even if disallowed operations are inadvertently introduced during query generation, they can be caught and flagged. If unsafe queries are detected, the node halts the workflow, updates the state with an error flag, and provides feedback to the user.
    def post_safety_check(state: GraphState) -> GraphState:
        """Perform safety checks on the generated SQL query to ensure it doesn't contain disallowed operations such as CREATE, DELETE, DROP, etc.
        """
        _logger.info("Performing Post Safety Check on the generated SQL Query")
        
        sql_solution = state.get('generation', {})
        sql_query = sql_solution.sql_code
        messages = state['messages']
        error = "no"
        
        if "SELECT" not in sql_query.upper():
            _logger.warning("Generated SQL query does not contain any SELECT query")
            error = "yes"
            messages += [('assistant', f"The generated SQL query does not have SELECT operation")]
            
        else:
            # List of disallowed SQL operations
            disallowed_operations = ['CREATE', 'DELETE', 'DROP', 'INSERT', 'UPDATE', 'ALTER', 'TRUNCATE', 'EXEC', 'EXECUTE']
            pattern = re.compile(r'\b(' + '|'.join(disallowed_operations) + r')\b', re.IGNORECASE)
            
            # Check if the generated SQL query contains disallowed SQL operations
            found_operations = pattern.findall(sql_query)
            if found_operations:
                _logger.warning(
                    "Gemerated SQL query contains disallowed SQL operations: %s. Halting the workflow.",
                    ", ".join(set(found_operations))
                )
                error = 'yes'
                messages += [('assistant', f"The generated SQL query contains disallowed SQL operations: {', '.join(set(found_operations))} and cannot be processed.")]
            else:
                _logger.info("Generated SQL query passed the safety check.")
            
        # Update state with error status and messages
        state['messages'] = messages
        state['error'] = error
        
        return state
    
    # SQL Query Check
    #The sql_check node ensures the generated SQL query is safe and syntactically valid by executing it within a transactional savepoint. Any changes are rolled back after validation, with errors flagged and detailed feedback provided to maintain query integrity.
    def sql_check(state: GraphState) -> GraphState:
        """Validates the generated SQL query by attempting to execute it on the database.
        If the query is valid, the changes are rolled back to ensure no data is modified.
        If there is an error during execution, the error is logged and the state is updated accordingly."""
        _logger.info("Validating SQL query.")
        
        # Extract relevant data from the state
        messages = state['messages']
        sql_solution = state['generation']
        error = 'no'
        
        sql_code = sql_solution.sql_code.strip()
        try:
            # Start a savepoint for the transaction to allow rollback
            conn.execute("SAVEPOINT sql_check;")
            # Attempt to execute the SQL query
            cursor.execute(sql_code)
            # Roll back to the savepoint to undo any changes
            conn.execute("ROLLBACK TO sql_check;")
            _logger.info("SQL query validation: success.")
        except Exception as e:
            # Roll back incase of error
            conn.execute('ROLLBACK TO sql_check;')
            _logger.error("SQL query validation failed. Error: %s", e)
            messages += [('user', f'Your SQL query failed to execute: {e}')] # Feedback to LLM
            error = "yes"
            
        # Update the state with the error status
        state['error'] = error
        state['messages'] = messages
        
        return state
    
    # Run Query
    # run_query node executes the validated SQL query, connecting to the database to retrieve results. It updates the state with the query output, ensuring the data is formatted for further analysis or reporting while implementing robust error handling.
    def run_query(state: GraphState) -> GraphState:
        """Executes the generated SQL query on the database and retrieves the results if it is a SELECT query.
        If no records are found for a SELECT query, the 'no_records_found' flag is set to True."""
        _logger.info("Running SQL query.")
        
        # Extract the SQL query from the state
        sql_solution = state['generation']
        sql_code = sql_solution.sql_code.strip()
        results = None
        no_records_found = False # Flag to indicate no records found
        
        try:
            # Execute the SQL query
            cursor.execute(sql_code)
            results = cursor.fetchall()
            if not results:
                no_records_found = True
                _logger.info("SQL query execution: success. No records found.")
            else:
                _logger.info("SQL query execution: success.")
        except Exception as e:
            _logger.error("SQL query execution failed. Error: %s", e)
        
        # Update the state with results and flag for no records found
        state["results"] = results
        state["no_records_found"] = no_records_found

        return state   
    
    # Decision Step: Determine Next Action
    #The decide_next_step function acts as a control point in the workflow, deciding what action should be taken next based on the current state. It evaluates the error status and the number of iterations performed so far to determine if the query should be run, the workflow should be finished, or if the system should retry generating the SQL query.
    """
    - If there is no error (error == "no"), the system proceeds with running the SQL query.
    - If the maximum number of iterations (max_iterations) has been reached, the workflow ends.
    - If an error occurred and the maximum iterations haven't been reached, the system will retry the query generation.
    """
    def decide_next_step(state: GraphState) -> str:
        """Determines the next step in the workflow based on the current state, including whether the query
        should be run, the workflow should be finished, or if the query generation needs to be retried.

        Args:
            state (GraphState): The current graph state, which contains error status and iteration count.

        Returns:
            str: The next step in the workflow, which can be "run_query", "generate", or END
        """
        _logger.info("Deciding next step based on current state.")
        
        error = state['error']
        iterations = state['iterations']
        
        if error == "no":
            _logger.info("Error status: no. Proceeding with running the query")
            return "run_query"
        elif iterations < max_iterations:
            _logger.info("Error detected. Retrying SQL query generation.")
            return "generate"
        else:
            _logger.info("Maximum iterations reached. Ending the workflow")
            return  END
        
    # Build the workflow graph
    workflow = StateGraph(GraphState)
    
    # Define the workflow nodes
    workflow.add_node("translate_input", translate_input) # Translate user input to english
    workflow.add_node("pre_safety_check", pre_safety_check) # Performs a presafety check on input
    workflow.add_node("schema_extract", schema_extract) # Extracts schema
    workflow.add_node("context_check", context_check) # Checks if question matches the context from schema
    workflow.add_node("generate", generate) # Generate SQL query
    workflow.add_node("post_safety_check", post_safety_check) # Checks the Generated SQL query
    workflow.add_node("sql_check", sql_check) # Validates Generated SQL query
    workflow.add_node("run_query", run_query) # Executes the SQL Query
    
    # Define workflow edges
    workflow.add_edge(START, "translate_input")
    workflow.add_edge("translate_input", 'pre_safety_check')
    
    # Define workflow conditional edge
    workflow.add_conditional_edges(
        "pre_safety_check",
        lambda state: "schema_extract" if state['error'] == "no" else END,
        {"schema_extract" : "schema_extract", END : END}
    )
    workflow.add_edge("schema_extract", 'context_check')
    
    # Conditional edge after context check
    workflow.add_conditional_edges(
        'context_check',
        lambda state: "generate" if state['error'] == "no" else END,
        {"generate" : "generate", END : END}
    )
    
    # Post safety check after generation
    workflow.add_edge("generate", "post_safety_check")
    
    # Conditional edge after post_safety check
    workflow.add_conditional_edges(
        "post_safety_check",
        lambda state: 'sql_check' if state['error'] == "no" else END,
        {'sql_check' : "sql_check", END : END}
    )
    
    # Retry logic
    workflow.add_conditional_edges(
        "sql_check",
        decide_next_step,
        {
            'run_query' : 'run_query',
            "generate" : 'generate',
            END : END
        }
    )
    
    workflow.add_edge('run_query', END) # Validated SQL executed 
    
    # Compile and return the workflow application
    app = workflow.compile()
    
    return app
