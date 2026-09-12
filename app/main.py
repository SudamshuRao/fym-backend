"""
FYM backend entrypoint. Run with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI

from app.core.config import settings
from app.routers import auth, daily_target, food_log, standalone, recommendation, pantry_item, cook

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.include_router(auth.router)
app.include_router(daily_target.router)
app.include_router(food_log.router)
app.include_router(standalone.router)
app.include_router(recommendation.router)
app.include_router(pantry_item.router)
app.include_router(cook.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
