from fastapi import FastAPI

from app.api.routes import router
from app.core.db import engine
from app.core.logging import configure_logging
from app.domain.models import Base

configure_logging()
app = FastAPI(title="BoligProspekt-Scanner")
app.include_router(router)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}
