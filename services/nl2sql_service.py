import time
import mlflow
import logging

from dotenv import load_dotenv

from database import setup_database
from vector_store import setup_vector_store

from definitions import (
    REMOTE_SERVER_URI,
    REGISTERED_MODEL_NAME,
    MODEL_ALIAS,
    EXPERIMENT_NAME
)



class NL2SQLService:
    def __init__(self) -> None:
        # Env
        load_dotenv()
        
        # MLFlow
        mlflow.set_tracking_uri(REMOTE_SERVER_URI)
        mlflow.set_experiment(EXPERIMENT_NAME)
        mlflow.langchain.autolog()
        
        # Logger
        self.logger = logging.getLogger("nl2sql_api")
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        self.logger.info("Initalizing NL2SQL API")
        
        # # Database
        # self.conn = setup_database(self.logger)
        # self.cursor = self.conn.cursor()
        
        # VectorStore
        self.vector_store = setup_vector_store(self.logger)
        
        # Load Model
        model_uri = (f"models:/{REGISTERED_MODEL_NAME}@{MODEL_ALIAS}")
        self.model = mlflow.pyfunc.load_model(model_uri=model_uri)
        
        # model_input = {
        #     "conn" : self.conn,
        #     "cursor": self.cursor,
        #     "vector_store": self.vector_store
        # }
        
        # self.app = model.predict(model_input)
        
        self.logger.info("NL2SQL API ready")
    
    def execute(self, question: str, request_id: str = None):
        start = time.perf_counter()
        self.logger.info("Request ID %s", request_id)
        conn = setup_database(self.logger)
        cursor = conn.cursor()
        
        try:
            model_input = {
                "conn" : conn,
                "cursor": cursor,
                "vector_store": self.vector_store
            }
            
            app = self.model.predict(model_input)
            
            initial_state = {
                "messages": [('user', question)],
                'iterations': 0,
                "error": "",
                "results": None,
                "generation": None,
                "no_records_found": False,
                "translated_input": ""
            }
       
            solution = app.invoke(initial_state)
        finally:
            cursor.close()
            conn.close()
        
        
        latency_ms = int((time.perf_counter() - start)*1000)
        try:
            with mlflow.start_run(nested = True):
                mlflow.log_metric("api_latency_ms", latency_ms)
                mlflow.log_param("request_id", request_id)
       
        except Exception as e:
            self.logger.warning("MLFlow metric logging failed: %s", str(e))
        
        sql = ""
        
        if solution.get("generation"):
            sql = solution.get("generation").sql_code
            self.logger.info("Query Completed in %s ms", latency_ms)
        
        return {
            "sql": sql,
            "results": solution.get("results") or [],
            "success": solution.get("error") != 'yes',
            "latency_ms": latency_ms
        }
    
service = NL2SQLService()
            
            