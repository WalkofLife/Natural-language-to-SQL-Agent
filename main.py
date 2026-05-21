import os
import logging

import mlflow
from database import setup_database
from definitions import (
    EXPERIMENT_NAME,
    MODEL_ALIAS,
    REGISTERED_MODEL_NAME,
    REMOTE_SERVER_URI,
)
from dotenv import load_dotenv
from vector_store import setup_vector_store

mlflow.set_tracking_uri(REMOTE_SERVER_URI)
mlflow.set_experiment(EXPERIMENT_NAME)
mlflow.langchain.autolog()

# Initialize the logger
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
_logger.addHandler(handler)

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Setup database and vector store
    conn = setup_database(_logger)
    cursor = conn.cursor()
    vector_store = setup_vector_store(_logger)    
    
    # Load the model
    model_uri = f"models:/{REGISTERED_MODEL_NAME}@{MODEL_ALIAS}"
    model = mlflow.pyfunc.load_model(model_uri)
    model_input = {"conn": conn, "cursor": cursor, 'vector_store': vector_store}
    app = model.predict(model_input)
    
    # Save Image
    app.get_graph().draw_mermaid_png(
        output_file_path = 'sql_agent_graph.png'
    )
    
    # Example user interaction
    _logger.info("Welcome to the SQL Assistant!!")
    while True:
        question = input("\nEnter your SQL question (or type 'exit' to quit): ")
        if question.lower() == 'exit':
            break
        
        # Initialize the state with all required keys
        initial_state = {
            "messages": [('user', question)],
            'iterations': 0,
            'error': "",
            'results': None,
            "generation": None,
            'no_records_found': False,
            "translated_input": ""
        }
        
        solution = app.invoke(initial_state)
        
        # Check if an error was set during the safety check
        if solution['error'] == 'yes':
            _logger.info("\nAssistant Message:\n")
            _logger.info(solution['messages'][-1][-1])
            continue
        
        # Extract the generated SQL query
        sql_query = solution['generation'].sql_code
        _logger.info("\nGenerated SQL Query:\n")
        _logger.info(sql_query)
        
        # Extract and display the query results
        if solution.get("no_records_found"):
            _logger.info("\nNo records found matching your query")
        elif "results" in solution and solution["results"] is not None:
            _logger.info("\nQuery Results:\n")
            for row in solution["results"]:
                _logger.info(row)
        else:
            _logger.info("\nNo results returned or query did not execute successfully.")
            
    _logger.info("Goodbye!")
    
if __name__ == '__main__':
    main()
        
        
    