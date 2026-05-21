from fastapi import FastAPI

from api.routes import router

app = FastAPI(title="NL2SQL Agent API", version="1.0.0")
app.include_router(router)

@app.get("/health")
def health():
    return {'status': "ok"}

