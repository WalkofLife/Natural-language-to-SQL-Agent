import mlflow
from definitions import REMOTE_SERVER_URI
from workflow import get_workflow

mlflow.set_tracking_uri(REMOTE_SERVER_URI)

class SQLGenerator(mlflow.pyfunc.PythonModel):
    def predict(self, context, model_input):
        return get_workflow(
            model_input['conn'], model_input['cursor'], model_input['vector_store']
        )
        
mlflow.models.set_model(SQLGenerator())

