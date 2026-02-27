from fastapi import APIRouter

from app.api import auth_routes, articles, dashboard, settings, reports, alerts, skills, ws

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_routes.router, prefix="/auth", tags=["Auth"])
api_router.include_router(articles.router, prefix="/articles", tags=["Articles"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(skills.router, prefix="/skills", tags=["Skills"])
api_router.include_router(ws.router, tags=["WebSocket"])
