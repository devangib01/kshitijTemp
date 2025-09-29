from fastapi import FastAPI
from dependencies.middleware import register_middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.requests import Request
import logging
from routers import patients_router, auth_router, hospital_router
from config.config import Config
from centralisedErrorHandling.ErrorHandling import UserServiceError
app = FastAPI(title="AI Avatar Doctor Backend")


logging.basicConfig(level=logging.INFO)
 

app.include_router(patients_router.router)
app.include_router(auth_router.router)
app.include_router(hospital_router.router)
# CORS: set your actual origin(s) when deploying
origins = [
    "http://localhost:8000",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
if getattr(Config, "ENFORCE_TRUSTED_IPS", False):
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]
    )

TRUSTED_IPS = ["127.0.0.1", "::1"]

if getattr(Config, "ENFORCE_TRUSTED_IPS", False):
    @app.middleware("http")
    async def trusted_ip_middleware(request: Request, call_next):
        ip = str(request.client.host) if request.client else "unknown"
        path = request.url.path or "/"
        if path in ("/docs", "/redoc", "/openapi.json"):
            return await call_next(request)
        if ip not in TRUSTED_IPS:
            return JSONResponse(content="403 - Forbidden: Access is denied", status_code=403)
        return await call_next(request)

register_middleware(app)

# Global exception handler
from fastapi.responses import PlainTextResponse
from starlette.requests import Request as StarletteRequest

@app.get("/health")
async def health_check():
    # Optional DB connectivity check
    from sqlalchemy import text
    from database.database import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as s:
            await s.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception as e:
        return {"status": "degraded", "db": str(e)}


@app.exception_handler(Exception)
async def global_exception_handler(request: StarletteRequest, exc: Exception):
    logging.exception("Unhandled error: %s", exc)

    # If it's a known UserServiceError, return structured JSON (message, code, context)
    if isinstance(exc, UserServiceError):
        payload = {
            "error": exc.__class__.__name__,
            "message": getattr(exc, "message", str(exc)),
            "error_code": getattr(exc, "error_code", None),
            "context": getattr(exc, "context", {}) or {},
        }
        return JSONResponse(status_code=400, content=payload)

    if getattr(Config, "SHOW_ERRORS", True):
        return PlainTextResponse(str(exc), status_code=500)
    return PlainTextResponse("Internal Server Error", status_code=500)

