import mlflow
from definitions import (
    EXPERIMENT_NAME,
    MODEL_ALIAS,
    REGISTERED_MODEL_NAME,
    REMOTE_SERVER_URI
)
from mlflow import MlflowClient

client = MlflowClient(REMOTE_SERVER_URI)

mlflow.set_tracking_uri(REMOTE_SERVER_URI)
mlflow.set_experiment(EXPERIMENT_NAME)

with mlflow.start_run():
    logged_model_info = mlflow.pyfunc.log_model(
        python_model="sql_model.py",
        name="sql_generator",
        registered_model_name=REGISTERED_MODEL_NAME,
        code_paths=['workflow.py']
    )

client.set_registered_model_alias(
    REGISTERED_MODEL_NAME, MODEL_ALIAS, logged_model_info.registered_model_version
)
