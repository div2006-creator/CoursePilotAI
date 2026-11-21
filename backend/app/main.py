from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.api.routes import auth as auth_routes
from app.api.routes import courses as course_routes
from app.api.routes import diagnostic as diagnostic_routes
from app.api.routes import knowledge_gaps as knowledge_gap_routes
from app.api.routes import topics as topic_routes
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks (e.g. database connectivity verification, model preload checks)
    yield
    # Cleanup tasks on application shutdown


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API for CoursePilot AI — Personalized Learning Recovery Platform for DSA",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# CORS (Cross-Origin Resource Sharing) Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "message": message,
            "detail": exc.detail,
        },
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = exc.errors()
    first_msg = errors[0].get("msg", "Validation error") if errors else "Validation error"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "success": False,
            "data": None,
            "message": first_msg,
            "detail": errors,
        },
    )


# Mount API Routers
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(
    auth_routes.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["auth"],
)
app.include_router(
    course_routes.router,
    prefix=f"{settings.API_V1_STR}/courses",
    tags=["courses"],
)
app.include_router(
    topic_routes.router,
    prefix=settings.API_V1_STR,
    tags=["topics"],
)
app.include_router(
    diagnostic_routes.router,
    prefix=settings.API_V1_STR,
    tags=["diagnostic"],
)
app.include_router(
    knowledge_gap_routes.router,
    prefix=settings.API_V1_STR,
    tags=["knowledge_gaps"],
)


@app.get("/", tags=["system"], summary="Root Information Endpoint")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "docs_url": "/docs",
        "health_check": f"{settings.API_V1_STR}/health",
    }
