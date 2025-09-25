from fastapi import FastAPI
from fastapi.requests import Request
import time
import logging
logger = logging.getLogger("uvicorn.access")

def register_middleware(app: FastAPI):
    @app.middleware("http")
    async def custom_logging(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        processing_time = time.time() - start_time
        client = request.client.host if request.client is not None else "unknown"
        message = f"{client} - {request.method} {request.url.path} - completed after {processing_time:.3f}s"
        logger.info(message)
        return response
    
    print("Middleware registered", custom_logging)






