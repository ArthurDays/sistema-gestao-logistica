from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import auth_router, router
from app.core.config import settings
from app.core.security import hash_password
from app.db import SessionLocal
from app.models import Organization, User

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
