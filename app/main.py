from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app import models  # noqa: F401 реєструє моделі в Base.metadata
from app.audit.middleware import AuditMiddleware
from app.audit.router import router as audit_router
from app.auth.router import router as auth_router
from app.config import CORS_ORIGINS
from app.crypto.key_manager import get_blind_index_key, get_fernet
from app.database import Base
from app.middleware.rate_limiter import limiter
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.routes.admin import router as admin_router
from app.routes.students import router as students_router
from app.routes.teachers import router as teachers_router

# Fail fast: без валідних ключів сервіс не стартує
get_fernet()
get_blind_index_key()

app = FastAPI(title="Електронний деканат", version="2.0.0")

# Rate Limiting (slowapi)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Аудит: внутрішній шар (бачить кінцевий статус відповіді)
app.add_middleware(AuditMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Заголовки безпеки: зовнішній шар (ставиться на ВСІ відповіді)
app.add_middleware(SecurityHeadersMiddleware)

# Підключення роутерів
app.include_router(auth_router)
app.include_router(students_router)
app.include_router(teachers_router)
app.include_router(admin_router)
app.include_router(audit_router)

@app.get("/")
def root():
    return {"message": "Electronic Dean's Office API"}

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "SQLite",
        "tables": len(Base.metadata.tables),
    }
