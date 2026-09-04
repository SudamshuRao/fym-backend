"""
FYM backend entrypoint. Run with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI

from app.core.config import settings
from app.routers import auth, daily_target, food_log, standalone

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.include_router(auth.router)
app.include_router(daily_target.router)
app.include_router(food_log.router)
app.include_router(standalone.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
