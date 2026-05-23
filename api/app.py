from fastapi import FastAPI, Request
from observability.tracing import generate_request_id, set_request_id
from api.routes import router

app = FastAPI(title="NL2SQL Agent API", version="1.0.0")

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or generate_request_id()
    set_request_id(request_id)
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers['X-Request-ID'] = request_id
    return response

app.include_router(router)

@app.get("/health")
def health():
    return {'status': "ok"}

