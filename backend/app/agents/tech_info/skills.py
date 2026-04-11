"""Tech Info Agent skills — delegates to shared engine with tech-specific queries."""
from app.skills.engine import run_importance_scoring, generate_daily_report

__all__ = ["run_importance_scoring", "generate_daily_report"]
