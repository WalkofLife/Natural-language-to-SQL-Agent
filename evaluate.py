import json

from evaluation.evaluator import Evaluator

print("Evaluation Started")

with open("evaluation/datasets/eval_set.json") as f:
    dataset = json.load(f)
summary = Evaluator(dataset).run()
print("Evaluation Completed")

print( f"Success Rate: {summary['success_rate']:.2%}")
print(f"Latency: {summary['avg_latency_ms']:.2f} ms")