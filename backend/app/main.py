import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from starlette.responses import Response

from app.api import auth_router, router
from app.core.config import settings
from app.core.logging import configure_logging, configure_sentry, request_id_context
from app.core.security import hash_password
from app.db import SessionLocal
from app.models import Organization, User

configure_logging()
configure_sentry()
logger = logging.getLogger(__name__)

# O processo HTTP apenas monta infraestrutura e rotas; regras de negócio ficam nos módulos de domínio.
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(auth_router)


@app.middleware("http")
async def correlate_request(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = request_id_context.set(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "http_request",
            extra={
                "context": {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                }
            },
        )
        return response
    except Exception:
        logger.exception(
            "http_request_failed",
            extra={"context": {"method": request.method, "path": request.url.path}},
        )
        raise
    finally:
        request_id_context.reset(token)


@app.on_event("startup")
def bootstrap_admin() -> None:
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        return
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)):
            return
        organization = db.scalar(select(Organization).limit(1))
        if organization is None:
            return
        db.add(User(
            organization_id=organization.id,
            email=settings.bootstrap_admin_email.casefold(),
            password_hash=hash_password(settings.bootstrap_admin_password),
            role="admin",
        ))
        db.commit()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
