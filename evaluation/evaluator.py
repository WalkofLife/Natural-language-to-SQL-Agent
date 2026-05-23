import json
import mlflow
from evaluation.config import (
    DATASET_VERSION,
    WORKFLOW_VERSION,
    TRANSPORT
)
from services.nl2sql_service import NL2SQLService

from evaluation.metrics import (
    sql_generated_rate,
    execution_success_rate,
    avg_latency_ms,
    safety_block_rate,
    invalid_question_handling_rate
)

class Evaluator:
    def __init__(self, dataset) -> None:
        self.dataset = dataset
        self.service = NL2SQLService()
    
    def run(self):
        results = []
        for index, case in enumerate(self.dataset):
            try:
                response = self.service.execute(
                    question=case['question'],
                    request_id = f"eval_{index}"
                ) # type: ignore
                results.append({
                    "question": case['question'],
                    'category': case['category'],
                    'generated_sql': bool(response.get('sql')),
                    "execution_result": response.get('results'),
                    "latency_ms": response.get('latency_ms', 0),
                    "success": response.get('success', False)   
                })
            except:
                results.append({
                    "question": case["question"],
                    "category": case["category"],
                    "generated_sql": False,
                    "execution_result": None,
                    "latency_ms": 0,
                    "success": False})
        summary = {
            "cases": len(results),
            "execution_success_rate": execution_success_rate(results),
            "sql_generated_rate": sql_generated_rate(results),
            "avg_latency_ms": avg_latency_ms(results),
            "safety_block_rate": safety_block_rate(results),
            "invalid_question_handling_rate": invalid_question_handling_rate(results)
        }
        self.save_summary(summary)
        self.log_mlflow(summary)
        return summary
    
    def log_mlflow(self, summary):
        try:
            run_name = f"eval_{WORKFLOW_VERSION}_{DATASET_VERSION}"
            with mlflow.start_run(run_name=run_name):
                mlflow.log_params({
                    'DATASET_VERSION': DATASET_VERSION,
                    "WORKFLOW_VERSION": WORKFLOW_VERSION,
                    "TRANSPORT": TRANSPORT
                })
                mlflow.log_metrics({
                    "execution_success_rate": summary['execution_success_rate'],
                    "sql_generated_rate": summary['sql_generated_rate'],
                    "avg_latency_ms": summary['avg_latency_ms'],
                    "safety_block_rate": summary['safety_block_rate'],
                    "invalid_question_handling_rate": summary['invalid_question_handling_rate']
                })
                mlflow.log_artifact("evaluation_summary.json")
        except Exception as e:
            print("MLFlow not logged for evaluation due to error \n%s", str(e))
    def save_summary(self, summary):
        with open("evaluation_summary.json","w") as f:
            json.dump(summary, f, indent=2)