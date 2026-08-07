import uuid
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi import FastAPI


class AppException(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details
        self.request_id = str(uuid.uuid4())


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": exc.request_id,
                },
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.detail if isinstance(exc.detail, str) else "HTTP_ERROR",
                    "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
                    "details": None,
                    "request_id": str(uuid.uuid4()),
                },
            },
        )

    @app.exception_handler(Exception)
    async def internal_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred",
                    "details": None,
                    "request_id": str(uuid.uuid4()),
                },
            },
        )
