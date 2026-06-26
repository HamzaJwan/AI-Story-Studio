from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import config, health, images, jobs, ollama, projects, story, system, tts, videos

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(health.router)
app.include_router(config.router)
app.include_router(ollama.router)
app.include_router(projects.router)
app.include_router(story.router)
app.include_router(tts.router)
app.include_router(images.router)
app.include_router(videos.router)
app.include_router(jobs.router)
app.include_router(system.router)


@app.middleware("http")
async def add_json_charset(request: Request, call_next):
    response = await call_next(request)
    content_type = response.headers.get("content-type", "")
    if content_type.startswith("application/json") and "charset" not in content_type:
        response.headers["content-type"] = "application/json; charset=utf-8"
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "data": {},
            "meta": {"path": str(request.url.path)},
            "errors": [str(error.get("msg", "Invalid request")) for error in exc.errors()],
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "data": {},
            "meta": {"path": str(request.url.path)},
            "errors": ["Unexpected server error."],
        },
    )
